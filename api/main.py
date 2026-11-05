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
import gc
import hmac
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anyio
import anyio.to_thread

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.logging_setup import audit_logger
from api.models import (
    AddDocumentRequest,
    AddDocumentResponse,
    AskRequest,
    AskResponse,
    HealthResponse,
)
from cache import response_cache
from crew.schemas import CrewResponse
from rag.chunking import sentence_chunks
from rag.index import (
    get_chroma_client,
    get_embedding_model,
    get_or_create_collection,
)
from kb_loader import load_kb
from safety.guardrails import (
    check_groundedness,
    detect_prompt_injection,
    mask_pii,
)
from tools.ticket_tool import get_all_tickets
from review.autogen_review import review_support_response, _resolve_context_text

logger = logging.getLogger("ola_domain_agent.api")


def run_support_crew(*args: Any, **kwargs: Any) -> Any:
    """Wrapper function to allow lazy loading of crewai while preserving mockability in tests."""
    from crew.crew import run_support_crew as _run
    return _run(*args, **kwargs)


def _read_winning_collection() -> str:
    """Reads winning collection from recommended.json synchronously."""
    rec_path = PROJECT_ROOT / "rag" / "recommended.json"
    if rec_path.exists():
        try:
            with open(rec_path, "r", encoding="utf-8") as rf:
                rec_data = json.load(rf)
                return (
                    rec_data.get("winning_collection")
                    or rec_data.get("recommended_collection")
                    or "kb_sentence"
                )
        except (OSError, ValueError, TypeError):
            return "kb_sentence"
    return "kb_sentence"


# ==============================================================================
# Lifespan Handler: Preload Model & Chroma Index ONCE at startup
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads SentenceTransformer model, ChromaDB index, and validates ticket dataset readiness."""
    logger.info("Initializing API Lifespan: Preloading SentenceTransformer and ChromaDB collections...")
    app.state.kb_ready = False
    app.state.db_ready = False

    try:
        # Preload embedding model singleton once
        embedding_model = get_embedding_model()
        chroma_client = get_chroma_client()

        # Check DB readiness
        try:
            from dataset import SUPPORT_TICKETS
            app.state.db_ready = len(SUPPORT_TICKETS) > 0
        except Exception as exc:
            logger.exception("Lifespan: Ticket dataset failed to load: %s", exc)
            app.state.db_ready = False

        # Identify winning collection from rag/recommended.json (default: kb_sentence)
        winning_col = _read_winning_collection()
        if winning_col in ("ola_sentence", "ola_fixed"):
            winning_col = "kb_sentence"

        collection = get_or_create_collection(winning_col, chroma_client)

        # Build ChromaDB index if missing or empty
        if collection.count() == 0:
            logger.info("ChromaDB '%s' is empty. Indexing knowledge base collections at startup...", winning_col)
            from rag.index import index_documents
            index_documents(reset=False, collections=("kb_fixed", "kb_sentence"), client=chroma_client)
            collection = get_or_create_collection(winning_col, chroma_client)

        app.state.embedding_model = embedding_model
        app.state.chroma_client = chroma_client
        app.state.collection = collection
        app.state.winning_collection = winning_col
        app.state.kb_ready = collection.count() > 0
        logger.info("Lifespan: SentenceTransformer and '%s' collection ready (count=%d).", winning_col, collection.count())

        # Pre-warm CrewAI agents and crews once in lifespan
        try:
            from crew.crew import get_policy_crew, get_ticket_crew
            get_policy_crew()
            get_ticket_crew()
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.info("Crew pre-warm: %s", exc)

        try:
            from review.autogen_review import get_shared_review_pool
            get_shared_review_pool()
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.info("AutoGen pool pre-warm: %s", exc)

        # Reclaim temporary import memory for 512MB RAM budget
        gc.collect()
    except Exception as exc:
        logger.exception("Lifespan initialization failure: %s", exc)

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

# CORS Middleware (configurable allow_origins from env)
cors_origins_env = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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
    if isinstance(exc.detail, dict):
        content = {
            "error": exc.detail.get("error", "HTTP Error"),
            "detail": exc.detail.get("detail", exc.detail.get("message", "HTTP Error")),
            "status_code": exc.status_code,
            **exc.detail,
        }
        return JSONResponse(status_code=exc.status_code, content=content)
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
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc)
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
@app.get("/app")
@app.get("/desk")
def index_endpoint():
    """Serves the interactive Glassmorphism UI or JSON status."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(
            str(index_file),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Ola Domain Support Agent API", "status": "running"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon_endpoint():
    """Returns 204 No Content for browser favicon requests to prevent 404 noise."""
    return Response(status_code=204)


def check_readiness() -> tuple[bool, bool]:
    """Checks whether the KB collection and ticket DB are ready."""
    kb_ready = getattr(app.state, "kb_ready", None)
    db_ready = getattr(app.state, "db_ready", None)
    if kb_ready is None or db_ready is None:
        try:
            t = get_all_tickets()
            db_ready = bool(t and len(t) > 0)
        except Exception:
            db_ready = False
        try:
            col = get_or_create_collection("kb_sentence")
            cnt = col.count() if hasattr(col, "count") else 0
            kb_ready = cnt > 0
        except Exception:
            kb_ready = False
        app.state.kb_ready = kb_ready
        app.state.db_ready = db_ready
    return bool(kb_ready), bool(db_ready)


def format_human_source_title(raw_title: str) -> str:
    """Formats human source title in sentence case while preserving uppercase acronyms (SLA, VIP, KB)."""
    if not raw_title:
        return ""
    if raw_title in ("dataset.py", "dataset", "Ola Operational Records"):
        return "Ticket records"
    acronyms = {"SLA", "VIP", "KB", "CSAT"}
    clean = raw_title.replace("_", " ").replace(".md", "")
    words = clean.strip().split()
    if not words:
        return ""
    result = []
    for i, w in enumerate(words):
        upper_w = w.upper()
        if upper_w in acronyms:
            result.append(upper_w)
        elif i == 0:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


def _resolve_source_titles(sources: list[str] | None) -> list[str]:
    """Resolves raw source identifiers or filenames to human-readable document titles."""
    if not sources:
        return []
    titles: list[str] = []
    kb_dir = Path(os.environ.get("KB_DIR", str(PROJECT_ROOT / "kb"))).resolve()
    doc_title_map: dict[str, str] = {}
    try:
        if kb_dir.exists():
            for doc in load_kb(kb_dir):
                doc_title_map[doc["doc_id"]] = doc["title"]
                doc_title_map[f"{doc['doc_id']}.md"] = doc["title"]
    except Exception:
        pass

    for s in sources:
        clean_s = str(s).strip()
        stem = Path(clean_s).stem
        if clean_s in ("dataset.py", "dataset") or stem == "dataset":
            titles.append("Ticket records")
        elif clean_s in doc_title_map:
            titles.append(format_human_source_title(doc_title_map[clean_s]))
        elif stem in doc_title_map:
            titles.append(format_human_source_title(doc_title_map[stem]))
        else:
            titles.append(format_human_source_title(clean_s))
    return list(dict.fromkeys(titles))


@app.get("/health", response_model=HealthResponse)
@app.head("/health")
def health_check() -> HealthResponse:
    """Service health state and readiness status."""
    kb_ready, db_ready = check_readiness()
    return HealthResponse(
        status="ok" if (kb_ready and db_ready) else "warming_up",
        mock_llm=os.environ.get("MOCK_LLM", "true").lower() == "true",
        kb_ready=kb_ready,
        db_ready=db_ready,
        service="ola-support-agent",
    )


def run_unified_pipeline(
    raw_question: str,
    session_id: str,
    endpoint: str = "/ask",
    trace_id: str | None = None,
    is_admin: bool = False,
) -> AskResponse:
    """One unified pipeline function executing the full governance and multi-agent lifecycle:

    1. Readiness check: Verifies KB and DB are ready (HTTP 503 if warming up).
    2. Length cap check: Max length 20,000 chars (HTTP 422).
    3. Budget check: MAX_REQUEST_TOKENS enforcement (HTTP 413).
    4. Input Guardrails: Prompt-injection defense (HTTP 400).
    5. PII masking: Mask phone, email, credentials.
    6. Session resolution: Pronoun & follow-up rewriting.
    7. Cache: Partitioned namespace lookup (policy vs session-scoped ticket).
    8. Crew: Multi-agent execution (RAG / ticket lookup).
    9. Output groundedness & Autogen review.
    10. Schema validation & structured logging.
    """
    start_time = time.perf_counter()
    trace_id = trace_id or str(uuid.uuid4())

    try:
        # 0. Readiness Check (HTTP 503 if warming up)
        kb_ready, db_ready = check_readiness()
        if not (kb_ready and db_ready):
            raise HTTPException(
                status_code=503,
                detail="Service is warming up and not yet ready to process requests. Please try again shortly.",
            )

        # 1. Length Cap Check (HTTP 422)
        if len(raw_question) > 20000:
            raise HTTPException(
                status_code=422,
                detail="Question exceeds maximum allowed length of 20,000 characters.",
            )

        # 2. Token Budget Check (HTTP 413 on oversized payload)
        from governance.budget import check_payload_budget, MAX_REQUEST_TOKENS
        within_budget, tokens, err_msg = check_payload_budget(raw_question)
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
                detail=f"Your question is too long. Keep it under {MAX_REQUEST_TOKENS:,} tokens (estimated {tokens:,} tokens).",
            )

        # 3. Prompt Injection Check (HTTP 400)
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
                guardrail_flags={"prompt_injection_blocked": True, "detail": "guardrail_blocked"},
            )
            safe_guardrail_msg = "This request was blocked by the safety policy. Please rephrase your question."
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "guardrail_blocked",
                    "message": safe_guardrail_msg,
                    "detail": safe_guardrail_msg,
                },
            )

        # 4. Input Guardrails (PII Masking)
        pii_res = mask_pii(raw_question)
        sanitized_question = pii_res.sanitized_text
        guardrail_flags: dict[str, Any] = {"input_pii_masked": pii_res.fired, "phone_masked": pii_res.fired}

        # 3. Resolve follow-up query through session memory BEFORE the cache check
        from crew.memory import session_memory
        resolved_question, was_resolved = session_memory.resolve_query(session_id, sanitized_question)

        # If query was rewritten from history (pronoun resolution) or contains a ticket ID,
        # use the session-scoped ticket namespace; only history-free policy questions use the global cache.
        from crew.mock_llm import extract_ticket_id
        ticket_id_found = extract_ticket_id(resolved_question)
        is_ticket_or_history = was_resolved or bool(ticket_id_found)

        if is_ticket_or_history:
            cache_namespace = "ticket"
            cache_session_id = session_id
            cache_query_key = resolved_question
        else:
            cache_namespace = "policy"
            cache_session_id = None
            cache_query_key = sanitized_question

        # Response Cache Check (Policy queries cached globally; ticket/history queries strictly session-scoped)
        cached_result = response_cache.get(
            cache_query_key,
            namespace=cache_namespace,
            session_id=cache_session_id,
        )
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

            source_titles = _resolve_source_titles(cached_result.sources)

            raw_review = getattr(cached_result, "review_status", None) or {}
            is_revised = bool(
                raw_review.get("redactions_made", False)
                or (
                    raw_review.get("final_answer")
                    and raw_review.get("final_answer").strip() != cached_result.answer.strip()
                )
            )
            if is_admin:
                resp_review = dict(raw_review)
                resp_review["revised"] = is_revised
            else:
                resp_review = {
                    "approved": bool(raw_review.get("approved", True)),
                    "revised": is_revised,
                }

            data_obj = {
                "answer": cached_result.answer,
                "route": route_name,
                "sources": cached_result.sources,
                "source_titles": source_titles,
                "ticket": ticket_payload,
                "ticket_id": ticket_id_val,
                "grounded": cached_result.grounded,
                "escalation_recommended": cached_result.escalation_recommended,
                "escalation_score": ticket_payload.get("escalation_score") if ticket_payload else None,
                "review_status": resp_review,
            }

            return AskResponse(
                answer=cached_result.answer,
                route=route_name,
                sources=cached_result.sources,
                source_titles=source_titles,
                ticket=ticket_payload,
                grounded=cached_result.grounded,
                escalation_recommended=cached_result.escalation_recommended,
                trace_id=trace_id,
                latency_ms=round(latency_ms, 2),
                data=data_obj,
                retrieved_sources=cached_result.sources,
                review_status=resp_review,
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
            context_text = _resolve_context_text(crew_output.sources) or crew_output.answer
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
            review_context = _resolve_context_text(crew_output.sources) or crew_output.answer
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
        else:
            if crew_output.review_status.get("approved") is False:
                crew_output.grounded = False

        # 7. Schema Validation & Cache Store
        from crew.schemas import validate_crew_response
        validated_crew = validate_crew_response(crew_output)

        # Dynamic tickets without session are never cached globally
        if cache_namespace == "policy" or (cache_namespace == "ticket" and cache_session_id):
            response_cache.set(
                cache_query_key,
                validated_crew,
                namespace=cache_namespace,
                session_id=cache_session_id,
            )

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

        source_titles = _resolve_source_titles(validated_crew.sources)

        raw_review = validated_crew.review_status or {}
        is_revised = bool(
            raw_review.get("redactions_made", False)
            or (
                raw_review.get("final_answer")
                and raw_review.get("final_answer").strip() != validated_crew.answer.strip()
            )
        )
        if is_admin:
            resp_review = dict(raw_review)
            resp_review["revised"] = is_revised
        else:
            resp_review = {
                "approved": bool(raw_review.get("approved", True)),
                "revised": is_revised,
            }

        data_obj = {
            "answer": validated_crew.answer,
            "route": validated_crew.route,
            "sources": validated_crew.sources,
            "source_titles": source_titles,
            "ticket": validated_crew.ticket,
            "ticket_id": ticket_id_val,
            "grounded": validated_crew.grounded,
            "escalation_recommended": validated_crew.escalation_recommended,
            "escalation_score": validated_crew.ticket.get("escalation_score") if validated_crew.ticket else None,
            "review_status": resp_review,
        }

        return AskResponse(
            answer=validated_crew.answer,
            route=validated_crew.route,
            sources=validated_crew.sources,
            source_titles=source_titles,
            ticket=validated_crew.ticket,
            grounded=validated_crew.grounded,
            escalation_recommended=validated_crew.escalation_recommended,
            trace_id=trace_id,
            latency_ms=round(latency_ms, 2),
            data=data_obj,
            retrieved_sources=validated_crew.sources,
            review_status=resp_review,
            cache_hit=False,
            guardrail_flags=guardrail_flags,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Internal processing error in run_unified_pipeline.")
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred while processing your request. Please try again later.",
        )


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(
    payload: AskRequest,
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> AskResponse:
    """Processes customer inquiries via the unified pipeline in an AnyIO worker thread without event loop blocking."""
    raw_question = payload.question or payload.query or ""
    session_id = payload.session_id or "default_session"
    server_token = os.environ.get("ADMIN_TOKEN")
    is_admin = bool(
        server_token
        and server_token.strip()
        and x_admin_token
        and hmac.compare_digest(x_admin_token.strip(), server_token.strip())
    )
    return await anyio.to_thread.run_sync(
        run_unified_pipeline,
        raw_question,
        session_id,
        "/ask",
        None,
        is_admin,
    )


def verify_admin_token(x_admin_token: str | None = Header(None, alias="X-Admin-Token")) -> str:
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


def _sync_add_document(doc_title: str, doc_text: str) -> AddDocumentResponse:
    """Synchronous core ingestion pipeline executed in background worker thread.

    - Validates document title matches ^[A-Za-z0-9_-]{1,64}$ (stripping trailing .md).
    - Checks target path resides inside KB directory to prevent path traversal.
    - Chunks with sentence_chunks and indexes into kb_sentence.
    - Invalidates the policy response cache.
    """
    start_time = time.perf_counter()

    # 1. Title validation: strip a trailing .md and validate regex
    clean_title = doc_title[:-3] if doc_title.endswith(".md") else doc_title
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", clean_title):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid document title '{clean_title}'. Titles must match ^[A-Za-z0-9_-]{{1,64}}$ (letters, numbers, underscores, hyphens up to 64 characters).",
        )

    # 2. Path resolution & Path Traversal Guard
    kb_dir = Path(os.environ.get("KB_DIR", str(PROJECT_ROOT / "kb"))).resolve()
    kb_dir.mkdir(parents=True, exist_ok=True)
    file_path = (kb_dir / f"{clean_title}.md").resolve()

    try:
        file_path.relative_to(kb_dir)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Path traversal detected. Document target must reside inside the KB directory.",
        )

    try:
        # 3. Save document to kb/ directory
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_text)

        # 4. Chunk using the recommended strategy (sentence chunking for kb_sentence)
        chunks = sentence_chunks(doc_text, doc_id=clean_title)
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Document '{clean_title}' contains no valid text sentences for indexing.",
            )

        # 5. Embed & upsert into winning collection ('kb_sentence')
        target_collection = os.environ.get("WINNING_COLLECTION", "kb_sentence")
        model = getattr(app.state, "embedding_model", None) or get_embedding_model()
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

        # 6. Invalidate policy response cache (isolated from ticket caches)
        invalidated_count = response_cache.clear(namespace="policy")

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        trace_id = str(uuid.uuid4())

        audit_logger.log_request(
            endpoint="/add-document",
            question=f"Ingested document: {clean_title}",
            status_code=200,
            latency_ms=latency_ms,
            session_id="system",
            trace_id=trace_id,
            route="system",
            guardrail_flags={"cache_invalidated": invalidated_count},
        )

        return AddDocumentResponse(
            status="indexed",
            title=clean_title,
            doc_id=clean_title,
            collection=target_collection,
            chunks_indexed=len(chunks),
            cache_invalidated_entries=invalidated_count,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Internal processing error in add_document_endpoint.")
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred while adding the document.",
        )


@app.post("/add-document", response_model=AddDocumentResponse)
async def add_document_endpoint(
    payload: AddDocumentRequest,
    admin_token: str = Depends(verify_admin_token),
) -> AddDocumentResponse:
    """Ingests a markdown document, sentence-chunks, embeds, and upserts in an AnyIO worker thread."""
    doc_title = (payload.title or payload.doc_id or "document").strip()
    doc_text = payload.text.strip()
    return await anyio.to_thread.run_sync(_sync_add_document, doc_title, doc_text)


@app.post("/clear-cache")
def clear_cache_endpoint(admin_token: str = Depends(verify_admin_token)) -> dict[str, Any]:
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
                # Execute through the single unified pipeline function in AnyIO worker thread
                ask_res = await anyio.to_thread.run_sync(
                    run_unified_pipeline,
                    user_msg,
                    session_id,
                    "/ws/chat",
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
    except Exception:
        logger.exception("Unexpected WebSocket exception for session %s", session_id)
        try:
            await websocket.send_json({
                "type": "error",
                "status_code": 500,
                "detail": "An unexpected server processing error occurred.",
                "session_id": session_id,
                "latency_ms": 0.0,
            })
            await websocket.close()
        except (RuntimeError, OSError) as close_exc:
            logger.debug("Clean WebSocket close skipped: %s", close_exc)
    finally:
        logger.info("WebSocket connection finalized for session %s.", session_id)


@app.get("/tickets")
def get_tickets_endpoint() -> list[dict[str, Any]]:
    """Returns directory of support tickets for the dispatch desk."""
    return get_all_tickets()


# Mount static files directory at root AFTER all API routes so no API route is shadowed
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="site")


# Direct execution entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
