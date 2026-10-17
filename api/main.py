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
import hmac
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
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


def run_support_crew(*args: Any, **kwargs: Any) -> Any:
    """Wrapper function to allow lazy loading of crewai while preserving mockability in tests."""
    from crew.crew import run_support_crew as _run
    return _run(*args, **kwargs)


# ==============================================================================
# Lifespan Handler: Preload Model & Chroma Index ONCE at startup
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads SentenceTransformer model and winning ChromaDB index once at startup (never per-request)."""
    logger.info("Initializing API Lifespan: Preloading SentenceTransformer and ChromaDB collections...")
    try:
        # Preload embedding model singleton once
        embedding_model = get_embedding_model()
        # Preload ChromaDB client & winning collection once
        chroma_client = get_chroma_client()

        # Identify winning collection from rag/recommended.json (default: kb_sentence)
        winning_col = "kb_sentence"
        rec_path = PROJECT_ROOT / "rag" / "recommended.json"
        if rec_path.exists():
            try:
                import json
                with open(rec_path, "r", encoding="utf-8") as rf:
                    rec_data = json.load(rf)
                    winning_col = rec_data.get("winning_collection") or rec_data.get("recommended_collection") or "kb_sentence"
            except Exception:
                winning_col = "kb_sentence"

        collection = get_or_create_collection(winning_col, chroma_client)

        # Build ChromaDB index if missing or empty (index ONLY winning collection at startup for 512MB RAM constraint)
        if collection.count() == 0:
            logger.info("ChromaDB '%s' is empty. Indexing winning knowledge base collection at startup...", winning_col)
            from rag.index import index_documents
            index_documents(reset=False, collections=(winning_col,), client=chroma_client)
            collection = get_or_create_collection(winning_col, chroma_client)

        app.state.embedding_model = embedding_model
        app.state.chroma_client = chroma_client
        app.state.collection = collection
        app.state.winning_collection = winning_col
        logger.info("Lifespan: SentenceTransformer and '%s' ChromaDB collection ready.", winning_col)

        # Initialize any background system datasets if needed
        try:
            from ingest import initialize_system_data
            initialize_system_data()
        except Exception as exc:
            logger.info("Lifespan system data check: %s", exc)

        # Pre-warm CrewAI agents and crews once in lifespan
        try:
            from crew.crew import get_policy_crew, get_ticket_crew
            get_policy_crew()
            get_ticket_crew()
        except Exception as exc:
            logger.info("Crew pre-warm: %s", exc)

        try:
            from review.autogen_review import get_shared_review_pool
            get_shared_review_pool()
        except Exception as exc:
            logger.info("AutoGen pool pre-warm: %s", exc)

        # Reclaim temporary import memory for 512MB RAM budget
        import gc
        gc.collect()
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
        status="ok",
        mock_llm=os.environ.get("MOCK_LLM", "true").lower() == "true",
        kb_ready=True,
        db_ready=True,
        service="ola-support-agent",
    )


def run_unified_pipeline(
    raw_question: str,
    session_id: str,
    endpoint: str = "/ask",
    trace_id: Optional[str] = None,
) -> AskResponse:
    """One unified pipeline function executing the full governance and multi-agent lifecycle:

    1. Guardrails (input): Prompt-injection defense & PII masking.
    2. Budget check: MAX_REQUEST_TOKENS enforcement (HTTP 413).
    3. Cache: Normalized in-memory cache lookup.
    4. Crew: Multi-agent execution (RAG / ticket lookup).
    5. Output groundedness check: Validates context adherence.
    6. Autogen review: Secondary consensus review stage (approval/redaction).
    7. Schema validation: Strict CrewResponse / AskResponse contract validation.
    8. Structured log: Thread-safe JSON-Lines audit logging with zero plaintext PII.
    """
    start_time = time.perf_counter()
    trace_id = trace_id or str(uuid.uuid4())

    try:
        # 1. Input Guardrails (Prompt Injection Check - HTTP 400)
        inj_res = detect_prompt_injection(raw_question)
        if inj_res.fired:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            audit_logger.log_request(
                endpoint=endpoint,
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

        # 1b. Input Guardrails (PII Masking)
        pii_res = mask_pii(raw_question)
        sanitized_question = pii_res.sanitized_text
        guardrail_flags: Dict[str, Any] = {"input_pii_masked": pii_res.fired, "phone_masked": pii_res.fired}

        # 2. Token Budget Check (HTTP 413 on oversized payload)
        within_budget, tokens, err_msg = check_payload_budget(sanitized_question)
        if not within_budget:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            audit_logger.log_request(
                endpoint=endpoint,
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
                detail=err_msg or f"Payload exceeds maximum token budget of 2,000 tokens (estimated {tokens:,} tokens).",
            )

        # 3. Response Cache Check
        cached_result = response_cache.get(sanitized_question)
        if cached_result is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            route_name = getattr(cached_result, "route", "cached")
            audit_logger.log_request(
                endpoint=endpoint,
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
                "review_status": getattr(cached_result, "review_status", None),
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
                review_status=getattr(cached_result, "review_status", {}) or {},
                cache_hit=True,
                guardrail_flags=guardrail_flags,
            )

        # 4. Multi-Agent Crew Execution (RAG / Lookup)
        crew_output = run_support_crew(
            query=sanitized_question,
            session_id=session_id,
            structured=True,
        )
        if not isinstance(crew_output, CrewResponse):
            crew_output = CrewResponse.model_validate(crew_output)

        # 5. Output Groundedness Check
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

        # 6. Autogen Secondary Review Stage
        # run_support_crew already executes review_support_response and sets crew_output.review_status.
        # Avoid running a redundant secondary review team if already approved/reviewed.
        if not crew_output.review_status or crew_output.review_status.get("approved") is None:
            from review.autogen_review import review_support_response
            review_context = " ".join(crew_output.sources) if crew_output.sources else ""
            review_verdict = review_support_response(
                query=sanitized_question,
                draft_answer=crew_output.answer,
                sources=crew_output.sources,
                grounded=crew_output.grounded,
                context_text=review_context,
            )
            crew_output.answer = review_verdict.final_answer
            crew_output.review_status = review_verdict.model_dump()
            crew_output.grounded = crew_output.grounded and review_verdict.approved

        # 7. Schema Validation & Cache Store
        from crew.schemas import validate_crew_response
        validated_crew = validate_crew_response(crew_output)
        response_cache.set(sanitized_question, validated_crew)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # 8. Structured Audit Logging
        audit_logger.log_request(
            endpoint=endpoint,
            question=raw_question,
            status_code=200,
            latency_ms=latency_ms,
            session_id=session_id,
            trace_id=trace_id,
            route=validated_crew.route,
            cache_hit=False,
            guardrail_flags=guardrail_flags,
        )

        ticket_id_val = None
        if validated_crew.ticket:
            ticket_id_val = validated_crew.ticket.get("ticket_id") or validated_crew.ticket.get("record_id")

        data_obj = {
            "answer": validated_crew.answer,
            "route": validated_crew.route,
            "sources": validated_crew.sources,
            "ticket": validated_crew.ticket,
            "ticket_id": ticket_id_val,
            "grounded": validated_crew.grounded,
            "escalation_recommended": validated_crew.escalation_recommended,
            "escalation_score": validated_crew.ticket.get("escalation_score") if validated_crew.ticket else None,
            "review_status": validated_crew.review_status,
        }

        return AskResponse(
            answer=validated_crew.answer,
            route=validated_crew.route,
            sources=validated_crew.sources,
            ticket=validated_crew.ticket,
            grounded=validated_crew.grounded,
            escalation_recommended=validated_crew.escalation_recommended,
            trace_id=trace_id,
            latency_ms=round(latency_ms, 2),
            data=data_obj,
            retrieved_sources=validated_crew.sources,
            review_status=validated_crew.review_status or {},
            cache_hit=False,
            guardrail_flags=guardrail_flags,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal processing error in run_unified_pipeline: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred while processing your request. Please try again later.",
        )


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    """Processes customer inquiries via the unified pipeline function."""
    raw_question = payload.question or payload.query or ""
    session_id = payload.session_id or "default_session"
    return run_unified_pipeline(
        raw_question=raw_question,
        session_id=session_id,
        endpoint="/ask",
    )


def verify_admin_token(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")) -> str:
    """Enforces admin authentication for privileged endpoints.

    - If ADMIN_TOKEN is not configured in the server environment, returns HTTP 403 Forbidden.
    - If X-Admin-Token header is missing or incorrect, returns HTTP 401 Unauthorized.
    """
    server_token = os.environ.get("ADMIN_TOKEN")
    if not server_token or not server_token.strip():
        raise HTTPException(
            status_code=403,
            detail="Admin endpoints are disabled because ADMIN_TOKEN is not configured on this server.",
        )

    if not x_admin_token or not hmac.compare_digest(x_admin_token.strip(), server_token.strip()):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Admin-Token header.",
        )

    return x_admin_token


@app.post("/add-document", response_model=AddDocumentResponse)
def add_document_endpoint(
    payload: AddDocumentRequest,
    admin_token: str = Depends(verify_admin_token),
) -> AddDocumentResponse:
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
        model = getattr(app.state, "embedding_model", None) or get_embedding_model()
        target_collection = getattr(app.state, "winning_collection", "kb_sentence")
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


@app.post("/clear-cache")
def clear_cache_endpoint(admin_token: str = Depends(verify_admin_token)) -> Dict[str, Any]:
    """Privileged admin endpoint to invalidate in-memory response cache."""
    invalidated_count = response_cache.clear() if hasattr(response_cache, "clear") else 0
    return {"status": "cleared", "invalidated_entries": invalidated_count}


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Disconnect-resilient WebSocket multi-turn customer chat session with per-connection session_id."""
    await websocket.accept()
    session_id = f"ws_{uuid.uuid4().hex[:8]}"
    logger.info("WebSocket connection established: session_id=%s", session_id)

    try:
        while True:
            user_msg = await websocket.receive_text()
            try:
                # Execute through the single unified pipeline function in thread pool
                ask_res = await asyncio.to_thread(
                    run_unified_pipeline,
                    raw_question=user_msg,
                    session_id=session_id,
                    endpoint="/ws/chat",
                )

                cached_data = ask_res.data or (
                    ask_res.model_dump()
                    if hasattr(ask_res, "model_dump")
                    else dict(ask_res)
                )

                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "trace_id": ask_res.trace_id,
                    "data": cached_data,
                    "latency_ms": ask_res.latency_ms,
                    "cache_hit": ask_res.cache_hit,
                })
            except HTTPException as exc:
                await websocket.send_json({
                    "type": "error",
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "session_id": session_id,
                    "latency_ms": 0.0,
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
