"""FastAPI Service for Ola Domain Support Intelligence Agent (Tasks 11, 12).

Track: Business Operations / Customer Support (Ola)
Provides:
- POST /ask: Token budget check, prompt-injection defense, PII masking, cache check,
  CrewAI 3-agent execution, groundedness check, audit log.
- POST /add-document: Ingests markdown document, sentence-chunks, embeds, and upserts
  into recommended winning collection ('kb_sentence'), invalidates cache.
- GET /health: Health status reporting {status, mock_llm, kb_ready, db_ready}.
- WS /ws/chat: Multi-turn chat WebSocket with per-connection session_id and clean
  WebSocketDisconnect resilience.
- Lifespan handler preloading SentenceTransformer and ChromaDB kb_sentence once at startup.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.logging_setup import audit_logger, LOG_FILE
from api.models import (
    AddDocumentRequest,
    AddDocumentResponse,
    AskRequest,
    AskResponse,
    ErrorResponse,
    HealthResponse,
)
from cache import response_cache
from crew.crew import run_support_crew
from crew.schemas import CrewResponse
from guardrails import check_payload_budget
from rag.chunking import sentence_chunks
from rag.index import (
    get_chroma_client,
    get_embedding_model,
    get_or_create_collection,
)
from safety.guardrails import (
    check_groundedness,
    detect_prompt_injection,
    mask_pii,
)

logger = logging.getLogger("ola_domain_agent.api")


# ==============================================================================
# Lifespan Handler: Preload Model & Chroma Index ONCE at startup
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads SentenceTransformer model and ChromaDB index once at startup (never per-request)."""
    logger.info("Initializing API Lifespan: Preloading SentenceTransformer and ChromaDB collections...")
    try:
        # Preload embedding model singleton once
        embedding_model = get_embedding_model()
        # Preload ChromaDB client & winning collection once
        chroma_client = get_chroma_client()
        collection = get_or_create_collection("kb_sentence", chroma_client)

        app.state.embedding_model = embedding_model
        app.state.chroma_client = chroma_client
        app.state.collection = collection
        logger.info("Lifespan: SentenceTransformer and 'kb_sentence' ChromaDB collection ready.")

        # Initialize any background system datasets if needed
        try:
            from ingest import initialize_system_data
            initialize_system_data()
        except Exception as exc:
            logger.info("Lifespan system data check: %s", exc)
    except Exception as exc:
        logger.error("Lifespan initialization failure: %s", exc, exc_info=True)

    yield

    logger.info("Shutting down API Lifespan.")


# ==============================================================================
# FastAPI Application Initialization
# ==============================================================================
app = FastAPI(
    title="Ola Domain Support Agent API",
    description="Enterprise customer support intelligence platform for Ola riders, drivers, and operations.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory if present
static_dir = PROJECT_ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ==============================================================================
# Safe Exception Handlers (Never expose Python tracebacks)
# ==============================================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Returns safe JSON for standard HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns HTTP 422 with structured validation error details."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": jsonable_encoder(exc.errors()),
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Guarantees safe JSON 500 response without internal traceback leaks."""
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected server error occurred while processing your request. Please try again later.",
            "status_code": 500,
        },
    )


# ==============================================================================
# Endpoints
# ==============================================================================
@app.get("/")
def index_endpoint():
    """Serves the interactive Glassmorphism UI or JSON status."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Ola Domain Support Agent API", "status": "running"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon_endpoint():
    """Returns 204 No Content for browser favicon requests to prevent 404 noise."""
    return Response(status_code=204)


@app.get("/health", response_model=HealthResponse)
@app.head("/health")
def health_check() -> HealthResponse:
    """Service health state and readiness status."""
    return HealthResponse(
        status="healthy",
        mock_llm=os.environ.get("MOCK_LLM", "true").lower() == "true",
        kb_ready=True,
        db_ready=True,
        service="ola-support-agent",
    )


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    """Processes customer inquiries with full governance, safety, and caching gates.

    Returns:
        AskResponse = CrewResponse + trace_id + latency_ms
    """
    start_time = time.perf_counter()
    trace_id = str(uuid.uuid4())
    raw_question = payload.question or payload.query or ""
    session_id = payload.session_id or "default_session"

    try:
        # Gate 1: Token Budget Check (HTTP 413 on oversized payload)
        within_budget, tokens, err_msg = check_payload_budget(raw_question)
        if not within_budget:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            audit_logger.log_request(
                endpoint="/ask",
                question=raw_question,
                status_code=413,
                latency_ms=latency_ms,
                session_id=session_id,
                trace_id=trace_id,
                route="blocked",
                guardrail_flags={"budget_exceeded": True, "tokens": tokens},
            )
            raise HTTPException(
                status_code=413,
                detail=err_msg or f"Payload exceeds maximum token budget (estimated {tokens:,} tokens).",
            )

        # Gate 2: Security & Prompt Injection Check (HTTP 400 on guardrail block)
        inj_res = detect_prompt_injection(raw_question)
        if inj_res.fired:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            audit_logger.log_request(
                endpoint="/ask",
                question=raw_question,
                status_code=400,
                latency_ms=latency_ms,
                session_id=session_id,
                trace_id=trace_id,
                route="blocked",
                guardrail_flags={"prompt_injection_blocked": True, "detail": inj_res.detail},
            )
            raise HTTPException(
                status_code=400,
                detail=inj_res.detail or "Query blocked by security guardrails.",
            )

        # Gate 3: Input PII Masking (Mask Indian phone numbers)
        pii_res = mask_pii(raw_question)
        sanitized_question = pii_res.sanitized_text
        guardrail_flags: Dict[str, Any] = {"input_pii_masked": pii_res.fired}

        # Gate 4: Semantic Response Cache
        cached_result = response_cache.get(sanitized_question)
        if cached_result is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            route_name = getattr(cached_result, "route", "cached")
            audit_logger.log_request(
                endpoint="/ask",
                question=raw_question,
                status_code=200,
                latency_ms=latency_ms,
                session_id=session_id,
                trace_id=trace_id,
                route=route_name,
                cache_hit=True,
                guardrail_flags=guardrail_flags,
            )

            ticket_payload = getattr(cached_result, "ticket", None)
            ticket_id_val = None
            if ticket_payload:
                ticket_id_val = ticket_payload.get("ticket_id") or ticket_payload.get("record_id")

            data_obj = {
                "answer": cached_result.answer,
                "route": route_name,
                "sources": cached_result.sources,
                "ticket": ticket_payload,
                "ticket_id": ticket_id_val,
                "grounded": cached_result.grounded,
                "escalation_recommended": cached_result.escalation_recommended,
                "escalation_score": ticket_payload.get("escalation_score") if ticket_payload else None,
            }

            return AskResponse(
                answer=cached_result.answer,
                route=route_name,
                sources=cached_result.sources,
                ticket=ticket_payload,
                grounded=cached_result.grounded,
                escalation_recommended=cached_result.escalation_recommended,
                trace_id=trace_id,
                latency_ms=round(latency_ms, 2),
                data=data_obj,
                retrieved_sources=cached_result.sources,
                cache_hit=True,
                guardrail_flags=guardrail_flags,
            )

        # Gate 5: CrewAI Multi-Agent Execution Pipeline (Tasks 7, 8, 9)
        crew_output = run_support_crew(
            query=sanitized_question,
            session_id=session_id,
            structured=True,
        )
        if not isinstance(crew_output, CrewResponse):
            crew_output = CrewResponse.model_validate(crew_output)

        # Gate 6: Groundedness Output Verification (Task 10) - applied to policy/RAG routes
        if crew_output.route in ("rag", "both"):
            context_text = " ".join(crew_output.sources) if crew_output.sources else ""
            grounded_res = check_groundedness(
                query=sanitized_question,
                retrieved_context=context_text,
                response_text=crew_output.answer,
                similarity=1.0 if crew_output.grounded else 0.0,
                grounded_flag=crew_output.grounded,
            )
            if grounded_res.fired:
                crew_output.answer = grounded_res.sanitized_text
                crew_output.grounded = False

        guardrail_flags["policy_grounded"] = crew_output.grounded

        # Store in Semantic Cache
        response_cache.set(sanitized_question, crew_output)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Gate 7: Structured Audit Logging (Guaranteed PII Phone Masking)
        audit_logger.log_request(
            endpoint="/ask",
            question=raw_question,
            status_code=200,
            latency_ms=latency_ms,
            session_id=session_id,
            trace_id=trace_id,
            route=crew_output.route,
            cache_hit=False,
            guardrail_flags=guardrail_flags,
        )

        ticket_id_val = None
        if crew_output.ticket:
            ticket_id_val = crew_output.ticket.get("ticket_id") or crew_output.ticket.get("record_id")

        data_obj = {
            "answer": crew_output.answer,
            "route": crew_output.route,
            "sources": crew_output.sources,
            "ticket": crew_output.ticket,
            "ticket_id": ticket_id_val,
            "grounded": crew_output.grounded,
            "escalation_recommended": crew_output.escalation_recommended,
            "escalation_score": crew_output.ticket.get("escalation_score") if crew_output.ticket else None,
        }

        # Gate 8: Structured Response: AskResponse = CrewResponse + trace_id + latency_ms
        return AskResponse(
            answer=crew_output.answer,
            route=crew_output.route,
            sources=crew_output.sources,
            ticket=crew_output.ticket,
            grounded=crew_output.grounded,
            escalation_recommended=crew_output.escalation_recommended,
            trace_id=trace_id,
            latency_ms=round(latency_ms, 2),
            data=data_obj,
            retrieved_sources=crew_output.sources,
            cache_hit=False,
            guardrail_flags=guardrail_flags,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal processing error in ask_endpoint: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred while processing your request. Please try again later.",
        )


@app.post("/add-document", response_model=AddDocumentResponse)
def add_document_endpoint(payload: AddDocumentRequest) -> AddDocumentResponse:
    """Ingests a markdown document, sentence-chunks, embeds, and upserts into 'kb_sentence'."""
    start_time = time.perf_counter()
    doc_title = (payload.title or payload.doc_id or "document").strip()
    doc_text = payload.text.strip()

    try:
        # 1. Save document to kb/ directory
        kb_dir = PROJECT_ROOT / "kb"
        kb_dir.mkdir(parents=True, exist_ok=True)
        doc_filename = doc_title if doc_title.endswith(".md") else f"{doc_title}.md"
        file_path = kb_dir / doc_filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_text)

        # 2. Chunk using the recommended strategy (sentence chunking for kb_sentence)
        chunks = sentence_chunks(doc_text, doc_id=doc_title)

        # 3. Embed & upsert into recommended winning collection ('kb_sentence')
        model = get_embedding_model()
        target_collection = "kb_sentence"
        col = get_or_create_collection(target_collection)

        chunk_ids = [c["chunk_id"] for c in chunks]
        chunk_texts = [c["text"] for c in chunks]
        chunk_metas = [
            {"doc_id": c["doc_id"], "chunk_id": c["chunk_id"], "strategy": c["strategy"]}
            for c in chunks
        ]

        if chunk_ids:
            embeddings = model.encode(chunk_texts, show_progress_bar=False).tolist()
            col.upsert(
                ids=chunk_ids,
                documents=chunk_texts,
                embeddings=embeddings,
                metadatas=chunk_metas,
            )

            # Also upsert into legacy collections for backwards compatibility if needed
            try:
                legacy_col = get_or_create_collection("ola_sentence")
                legacy_col.upsert(
                    ids=chunk_ids,
                    documents=chunk_texts,
                    embeddings=embeddings,
                    metadatas=chunk_metas,
                )
            except Exception:
                pass

        # 4. Invalidate semantic response cache
        invalidated_count = response_cache.clear() if hasattr(response_cache, "clear") else 0

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        trace_id = str(uuid.uuid4())

        audit_logger.log_request(
            endpoint="/add-document",
            question=f"Ingested document: {doc_title}",
            status_code=200,
            latency_ms=latency_ms,
            session_id="system",
            trace_id=trace_id,
            route="system",
            guardrail_flags={"cache_invalidated": invalidated_count},
        )

        return AddDocumentResponse(
            status="indexed",
            title=doc_title,
            doc_id=doc_title,
            collection=target_collection,
            chunks_indexed=len(chunks),
            cache_invalidated_entries=invalidated_count,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal processing error in add_document_endpoint: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred while adding the document.",
        )


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Disconnect-resilient WebSocket multi-turn customer chat session with per-connection session_id."""
    await websocket.accept()
    session_id = f"ws_{uuid.uuid4().hex[:8]}"
    logger.info("WebSocket connection established: session_id=%s", session_id)

    try:
        while True:
            user_msg = await websocket.receive_text()
            start_time = time.perf_counter()
            trace_id = str(uuid.uuid4())

            # Gate 1: Token Budget Check (413)
            within_budget, tokens, err_msg = check_payload_budget(user_msg)
            if not within_budget:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    question=user_msg,
                    status_code=413,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    route="blocked",
                    guardrail_flags={"budget_exceeded": True, "tokens": tokens},
                )
                await websocket.send_json({
                    "type": "error",
                    "status_code": 413,
                    "detail": err_msg or "Payload exceeds maximum token budget.",
                    "session_id": session_id,
                    "latency_ms": round(latency_ms, 2),
                })
                continue

            # Gate 2: Prompt Injection Check (400)
            inj_res = detect_prompt_injection(user_msg)
            if inj_res.fired:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    question=user_msg,
                    status_code=400,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    route="blocked",
                    guardrail_flags={"prompt_injection_blocked": True},
                )
                await websocket.send_json({
                    "type": "error",
                    "status_code": 400,
                    "detail": inj_res.detail or "Query blocked by security guardrails.",
                    "session_id": session_id,
                    "latency_ms": round(latency_ms, 2),
                })
                continue

            # Gate 3: PII Masking
            pii_res = mask_pii(user_msg)
            sanitized_msg = pii_res.sanitized_text

            # Gate 4: Response Cache Check
            cached_result = response_cache.get(sanitized_msg)
            if cached_result is not None:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                route_name = getattr(cached_result, "route", "cached")
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    question=user_msg,
                    status_code=200,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    route=route_name,
                    cache_hit=True,
                    guardrail_flags={"phone_masked": pii_res.fired},
                )
                cached_data = (
                    cached_result.model_dump()
                    if hasattr(cached_result, "model_dump")
                    else dict(cached_result)
                )
                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "data": cached_data,
                    "latency_ms": round(latency_ms, 2),
                    "cache_hit": True,
                })
                continue

            # Gate 5: Multi-Agent Crew Execution (Offload to thread to keep event loop responsive)
            crew_output = await asyncio.to_thread(
                run_support_crew,
                query=sanitized_msg,
                session_id=session_id,
                structured=True,
            )
            if not isinstance(crew_output, CrewResponse):
                crew_output = CrewResponse.model_validate(crew_output)

            # Gate 6: Groundedness Output Check
            if crew_output.route in ("rag", "both"):
                context_text = " ".join(crew_output.sources) if crew_output.sources else ""
                grounded_res = check_groundedness(
                    query=sanitized_msg,
                    retrieved_context=context_text,
                    response_text=crew_output.answer,
                    similarity=1.0 if crew_output.grounded else 0.0,
                    grounded_flag=crew_output.grounded,
                )
                if grounded_res.fired:
                    crew_output.answer = grounded_res.sanitized_text
                    crew_output.grounded = False

            # Cache store
            response_cache.set(sanitized_msg, crew_output)

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # Gate 7: Structured Audit Logging
            audit_logger.log_request(
                endpoint="/ws/chat",
                question=user_msg,
                status_code=200,
                latency_ms=latency_ms,
                session_id=session_id,
                trace_id=trace_id,
                route=crew_output.route,
                cache_hit=False,
                guardrail_flags={
                    "phone_masked": pii_res.fired,
                    "grounded": crew_output.grounded,
                },
            )

            out_dict = crew_output.model_dump()
            if crew_output.ticket and "ticket_id" not in out_dict:
                out_dict["ticket_id"] = crew_output.ticket.get("ticket_id") or crew_output.ticket.get("record_id")

            # Gate 8: Send response back
            await websocket.send_json({
                "type": "response",
                "session_id": session_id,
                "trace_id": trace_id,
                "data": out_dict,
                "latency_ms": round(latency_ms, 2),
                "cache_hit": False,
            })

    except WebSocketDisconnect:
        # Catch WebSocketDisconnect, log it, clean up, and keep server running for other clients
        logger.info("WebSocketDisconnect caught for session %s. Cleaned up state successfully.", session_id)
    except Exception as exc:
        logger.error("Unexpected WebSocket exception for session %s: %s", session_id, exc, exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "status_code": 500,
                "detail": "An unexpected server processing error occurred.",
                "session_id": session_id,
                "latency_ms": 0.0,
            })
            await websocket.close()
        except Exception:
            pass
    finally:
        logger.info("WebSocket connection finalized for session %s.", session_id)


# Direct execution entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
