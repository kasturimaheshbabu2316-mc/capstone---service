"""FastAPI Service for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Provides:
- POST /ask: Token budget check, PII masking, cache check, CrewAI run, AutoGen review, audit log
- POST /add-document: Document ingestion, Chroma upsert, cache invalidation
- WS /ws/chat: Multi-turn chat WebSocket with clean WebSocketDisconnect resilience
- GET /health: Service health and offline status check
"""

import asyncio
import os
import time
import uuid
from typing import Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    AskRequest,
    AskResponse,
    AddDocumentRequest,
    AddDocumentResponse,
    ErrorResponse,
)
from app.logging_utils import audit_logger
from crew.schema import SupportResponse
from crew.crew import run_support_crew
from crew.memory import session_memory
from guardrails.input_guard import (
    mask_phone_numbers,
    detect_prompt_injection,
)
from guardrails.output_guard import verify_groundedness
from governance.budget import check_budget_limit
from cache import response_cache
from review.autogen_review import review_support_response
from rag.chunking import fixed_chunking, sentence_chunking
from rag.index import get_or_create_collection, get_embedding_model

app = FastAPI(
    title="Ola Domain Support Agent API",
    description="Enterprise-grade support agent for Ola riders, drivers, and operations.",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets for Glassmorphism UI
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index_endpoint():
    """Serves the interactive Glassmorphism web console."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Ola Domain Support Agent API", "status": "running"}


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Health status and offline capability flag."""
    return {
        "status": "healthy",
        "service": "ola-support-agent",
        "mock_llm": os.environ.get("MOCK_LLM", "true") == "true",
        "telemetry_disabled": os.environ.get("CREWAI_DISABLE_TELEMETRY", "true") == "true",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon_endpoint():
    """Returns 204 No Content for browser favicon requests to avoid 404 logs."""
    from fastapi import Response
    return Response(status_code=204)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest) -> AskResponse:
    """Processes customer inquiries with full governance, safety, and caching gates."""
    start_time = time.perf_counter()
    trace_id = str(uuid.uuid4())
    raw_query = payload.query
    session_id = payload.session_id or "default_session"

    # Gate 1: Token Budget Cap Check (Task 15)
    within_budget, tokens, err_msg = check_budget_limit(raw_query)
    if not within_budget:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        audit_logger.log_request(
            endpoint="/ask",
            query=raw_query,
            status_code=413,
            latency_ms=latency_ms,
            session_id=session_id,
            trace_id=trace_id,
            guardrail_flags={"budget_exceeded": True, "tokens": tokens},
        )
        raise HTTPException(status_code=413, detail=err_msg)

    # Gate 2: Input Guardrails — PII Masking & Prompt Injection (Task 10)
    is_inj, inj_reason = detect_prompt_injection(raw_query)
    if is_inj:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        audit_logger.log_request(
            endpoint="/ask",
            query=raw_query,
            status_code=400,
            latency_ms=latency_ms,
            session_id=session_id,
            trace_id=trace_id,
            guardrail_flags={"prompt_injection_blocked": True},
        )
        raise HTTPException(status_code=400, detail=inj_reason)

    sanitized_query, was_masked = mask_phone_numbers(raw_query)
    guardrail_flags = {"phone_masked": was_masked}

    # Gate 3: Semantic Response Cache (Task 16)
    cached_result = response_cache.get(sanitized_query)
    if cached_result is not None:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        audit_logger.log_request(
            endpoint="/ask",
            query=raw_query,
            status_code=200,
            latency_ms=latency_ms,
            session_id=session_id,
            trace_id=trace_id,
            cache_hit=True,
            guardrail_flags=guardrail_flags,
        )
        return AskResponse(
            trace_id=trace_id,
            data=cached_result,
            latency_ms=round(latency_ms, 2),
            cache_hit=True,
            guardrail_flags=guardrail_flags,
        )

    # Gate 4: Execution Pipeline — CrewAI Multi-Agent Core (Task 7, 8, 9)
    crew_output = run_support_crew(
        query=sanitized_query,
        session_id=session_id,
        structured=False,
    )

    draft_answer = crew_output["answer"]
    sources = crew_output["sources"]
    ticket_id = crew_output["ticket_id"]
    esc_score = crew_output["escalation_score"]
    grounded = crew_output["grounded"]
    confidence = crew_output["confidence"]

    # Gate 5: Autogen Secondary Review Stage (Task 14)
    verdict = review_support_response(
        query=sanitized_query,
        draft_answer=draft_answer,
        sources=sources,
        grounded=grounded,
        confidence=confidence,
    )

    final_text = verdict.final_answer
    if verdict.redactions_made:
        guardrail_flags["review_redactions_made"] = True

    # Gate 6: Output Guardrail — Groundedness Check (Task 10)
    final_text, is_grounded = verify_groundedness(
        response_text=final_text,
        grounded_flag=grounded,
        confidence=confidence,
    )

    # Gate 7: Structured Output Schema Validation (Task 9)
    support_data = SupportResponse(
        answer=final_text,
        sources=sources,
        ticket_id=ticket_id,
        escalation_score=esc_score,
        grounded=is_grounded,
        confidence=confidence,
    )

    # Store in Cache
    response_cache.set(sanitized_query, support_data)

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    # Gate 8: Audit Logging (Task 12)
    audit_logger.log_request(
        endpoint="/ask",
        query=raw_query,
        status_code=200,
        latency_ms=latency_ms,
        session_id=session_id,
        trace_id=trace_id,
        cache_hit=False,
        guardrail_flags=guardrail_flags,
    )

    return AskResponse(
        trace_id=trace_id,
        data=support_data,
        latency_ms=round(latency_ms, 2),
        cache_hit=False,
        guardrail_flags=guardrail_flags,
    )


@app.post("/add-document", response_model=AddDocumentResponse)
def add_document_endpoint(payload: AddDocumentRequest) -> AddDocumentResponse:
    """Ingests a new policy document, updates vector collections, and invalidates response cache."""
    start_time = time.perf_counter()
    doc_id = payload.doc_id.strip()
    text = payload.text.strip()

    # Step 1: Save to kb/
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb")
    os.makedirs(kb_dir, exist_ok=True)
    file_path = os.path.join(kb_dir, doc_id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Step 2: Index sentence chunks into Chroma
    model = get_embedding_model()
    sentence_col = get_or_create_collection("ola_sentence")
    fixed_col = get_or_create_collection("ola_fixed")

    sentence_chunks = sentence_chunking(text)
    if sentence_chunks:
        embeddings = model.encode(sentence_chunks).tolist()
        sentence_col.upsert(
            ids=[f"{doc_id}_sent_{i}" for i in range(len(sentence_chunks))],
            embeddings=embeddings,
            documents=sentence_chunks,
            metadatas=[{"doc_id": doc_id, "chunk_index": i, "strategy": "sentence"} for i in range(len(sentence_chunks))],
        )

    fixed_chunks = fixed_chunking(text)
    if fixed_chunks:
        f_embeddings = model.encode(fixed_chunks).tolist()
        fixed_col.upsert(
            ids=[f"{doc_id}_fixed_{i}" for i in range(len(fixed_chunks))],
            embeddings=f_embeddings,
            documents=fixed_chunks,
            metadatas=[{"doc_id": doc_id, "chunk_index": i, "strategy": "fixed"} for i in range(len(fixed_chunks))],
        )

    # Step 3: Invalidate Cache
    invalidated_count = response_cache.clear()

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    audit_logger.log_request(
        endpoint="/add-document",
        query=f"Ingested doc {doc_id}",
        status_code=200,
        latency_ms=latency_ms,
        guardrail_flags={"cache_invalidated": invalidated_count},
    )

    return AddDocumentResponse(
        status="indexed",
        doc_id=doc_id,
        chunks_indexed=len(sentence_chunks),
        cache_invalidated_entries=invalidated_count,
    )


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Disconnect-resilient WebSocket for multi-turn customer chat sessions with full governance gating."""
    await websocket.accept()
    session_id = f"ws_{uuid.uuid4().hex[:8]}"

    try:
        while True:
            # Await user message
            user_msg = await websocket.receive_text()
            start_time = time.perf_counter()
            trace_id = f"trc_ws_{uuid.uuid4().hex[:8]}"

            # Gate 1: Token Budget Cap Check (Task 15)
            within_budget, tokens, err_msg = check_budget_limit(user_msg)
            if not within_budget:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    query=user_msg,
                    status_code=413,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    guardrail_flags={"budget_exceeded": True, "tokens": tokens},
                )
                await websocket.send_json({
                    "type": "error",
                    "status_code": 413,
                    "detail": err_msg,
                    "session_id": session_id,
                    "latency_ms": round(latency_ms, 2),
                })
                continue

            # Gate 2: Input Guardrails — Prompt Injection & PII Masking (Task 10)
            is_inj, inj_reason = detect_prompt_injection(user_msg)
            if is_inj:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    query=user_msg,
                    status_code=400,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    guardrail_flags={"prompt_injection_blocked": True},
                )
                await websocket.send_json({
                    "type": "error",
                    "status_code": 400,
                    "detail": inj_reason,
                    "session_id": session_id,
                    "latency_ms": round(latency_ms, 2),
                })
                continue

            sanitized_q, was_masked = mask_phone_numbers(user_msg)
            guardrail_flags = {"phone_masked": was_masked}

            # Gate 3: Semantic Response Cache (Task 16)
            cached_result = response_cache.get(sanitized_q)
            if cached_result is not None:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                audit_logger.log_request(
                    endpoint="/ws/chat",
                    query=user_msg,
                    status_code=200,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                    cache_hit=True,
                    guardrail_flags=guardrail_flags,
                )
                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "data": cached_result.model_dump(),
                    "latency_ms": round(latency_ms, 2),
                    "cache_hit": True,
                })
                continue

            # Gate 4: Execution Pipeline — CrewAI Multi-Agent Core (Tasks 7, 8, 9)
            # Run in thread pool to prevent blocking the asyncio event loop
            crew_output = await asyncio.to_thread(
                run_support_crew,
                query=sanitized_q,
                session_id=session_id,
                structured=False,
            )

            draft_answer = crew_output["answer"]
            sources = crew_output["sources"]
            ticket_id = crew_output["ticket_id"]
            esc_score = crew_output["escalation_score"]
            grounded = crew_output["grounded"]
            confidence = crew_output["confidence"]

            # Gate 5: Autogen Secondary Review Stage (Task 14)
            verdict = await asyncio.to_thread(
                review_support_response,
                query=sanitized_q,
                draft_answer=draft_answer,
                sources=sources,
                grounded=grounded,
                confidence=confidence,
            )

            final_text = verdict.final_answer
            if verdict.redactions_made:
                guardrail_flags["review_redactions_made"] = True

            # Gate 6: Output Guardrail — Groundedness Check (Task 10)
            final_text, is_grounded = verify_groundedness(
                response_text=final_text,
                grounded_flag=grounded,
                confidence=confidence,
            )

            # Gate 7: Structured Output Schema Validation (Task 9)
            support_data = SupportResponse(
                answer=final_text,
                sources=sources,
                ticket_id=ticket_id,
                escalation_score=esc_score,
                grounded=is_grounded,
                confidence=confidence,
            )

            # Store in Cache
            response_cache.set(sanitized_q, support_data)

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # Gate 8: Audit Logging (Task 12)
            audit_logger.log_request(
                endpoint="/ws/chat",
                query=user_msg,
                status_code=200,
                latency_ms=latency_ms,
                session_id=session_id,
                trace_id=trace_id,
                cache_hit=False,
                guardrail_flags=guardrail_flags,
            )

            # Send back validated structured payload
            await websocket.send_json({
                "type": "response",
                "session_id": session_id,
                "trace_id": trace_id,
                "data": support_data.model_dump(),
                "latency_ms": round(latency_ms, 2),
                "cache_hit": False,
            })

    except WebSocketDisconnect:
        # Clean disconnect handling: server remains unaffected and stable
        pass
    except Exception as e:
        # Catch unexpected exceptions, log, and send structured error to client
        try:
            await websocket.send_json({
                "type": "error",
                "status_code": 500,
                "detail": f"Server processing error: {str(e)}",
                "session_id": session_id,
                "latency_ms": 0.0,
            })
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

