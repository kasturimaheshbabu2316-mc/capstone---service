"""
Observability module for Ola Support Intelligence.
Provides Prometheus metrics, structured JSON logging, and distributed tracing hooks.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Context variables for request tracing
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")

# Prometheus Metrics
if PROMETHEUS_AVAILABLE:
    # Request metrics
    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"]
    )

    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )

    http_request_size_bytes = Histogram(
        "http_request_size_bytes",
        "HTTP request size in bytes",
        ["method", "endpoint"],
        buckets=[100, 1000, 10000, 100000, 1000000]
    )

    http_response_size_bytes = Histogram(
        "http_response_size_bytes",
        "HTTP response size in bytes",
        ["method", "endpoint"],
        buckets=[100, 1000, 10000, 100000, 1000000]
    )

    # Business metrics
    ask_requests_total = Counter(
        "ola_ask_requests_total",
        "Total /ask requests",
        ["route", "cache_hit", "grounded", "status"]
    )

    ask_latency_seconds = Histogram(
        "ola_ask_latency_seconds",
        "/ask endpoint latency",
        ["route"],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )

    active_sessions = Gauge(
        "ola_active_sessions",
        "Number of active chat sessions"
    )

    tickets_queried_total = Counter(
        "ola_tickets_queried_total",
        "Total ticket lookups",
        ["ticket_id", "found"]
    )

    kb_ingestions_total = Counter(
        "ola_kb_ingestions_total",
        "Total KB document ingestions",
        ["status"]
    )

    cache_operations_total = Counter(
        "ola_cache_operations_total",
        "Cache operations",
        ["operation", "namespace", "result"]
    )

    guardrail_triggers_total = Counter(
        "ola_guardrail_triggers_total",
        "Guardrail triggers",
        ["type"]
    )

    # System metrics
    chromadb_collections = Gauge(
        "ola_chromadb_collections",
        "Number of ChromaDB collections"
    )

    chromadb_total_chunks = Gauge(
        "ola_chromadb_total_chunks",
        "Total chunks in ChromaDB",
        ["collection"]
    )

    embedding_model_loaded = Gauge(
        "ola_embedding_model_loaded",
        "Whether embedding model is loaded (1) or not (0)"
    )

    mock_llm_active = Gauge(
        "ola_mock_llm_active",
        "Whether mock LLM is active (1) or real LLM (0)"
    )


@dataclass
class StructuredLogRecord:
    """Structured log record for JSON output."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    level: str = "INFO"
    logger: str = ""
    message: str = ""
    trace_id: str = ""
    session_id: str = ""
    user_id: str = ""
    endpoint: str = ""
    method: str = ""
    status_code: int = 0
    latency_ms: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "trace_id": self.trace_id or trace_id_var.get(""),
            "session_id": self.session_id or session_id_var.get(""),
            "user_id": self.user_id or user_id_var.get(""),
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            **self.extra
        }, separators=(",", ":"), ensure_ascii=False)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = StructuredLogRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            trace_id=trace_id_var.get(""),
            session_id=session_id_var.get(""),
            user_id=user_id_var.get(""),
        )

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "getMessage"
            }:
                log_record.extra[key] = value

        return log_record.to_json()


def setup_structured_logging(
    level: str = "INFO",
    json_format: bool = True,
    output_stream: Any = None
) -> logging.Logger:
    """Configure structured JSON logging."""
    logger = logging.getLogger("ola_support_agent")
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    handler = logging.StreamHandler(output_stream or sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ))

    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger with structured output."""
    return logging.getLogger(f"ola_support_agent.{name}")


class MetricsMiddleware:
    """FastAPI middleware for Prometheus metrics collection."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        # Normalize path for metrics (replace dynamic segments)
        normalized_path = self._normalize_path(path)

        request_size = 0
        response_size = 0
        status_code = 500

        async def send_wrapper(message):
            nonlocal response_size, status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        # Read request body size
        if hasattr(scope, "_body"):
            request_size = len(scope["_body"])

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if PROMETHEUS_AVAILABLE:
                duration = time.perf_counter() - start_time

                http_requests_total.labels(
                    method=method,
                    endpoint=normalized_path,
                    status_code=str(status_code)
                ).inc()

                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=normalized_path
                ).observe(duration)

                if request_size:
                    http_request_size_bytes.labels(
                        method=method,
                        endpoint=normalized_path
                    ).observe(request_size)

                if response_size:
                    http_response_size_bytes.labels(
                        method=method,
                        endpoint=normalized_path
                    ).observe(response_size)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics cardinality control."""
        import re
        # Replace UUIDs
        path = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{uuid}", path)
        # Replace ticket IDs
        path = re.sub(r"TKT-\d{4}", "TKT-####", path)
        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)
        return path


def metrics_endpoint():
    """Generate Prometheus metrics output."""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not installed\n", 503, {"Content-Type": "text/plain"}

    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


def record_ask_metrics(
    route: str,
    cache_hit: bool,
    grounded: bool,
    status_code: int,
    latency_ms: float
):
    """Record /ask request metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    ask_requests_total.labels(
        route=route,
        cache_hit=str(cache_hit).lower(),
        grounded=str(grounded).lower(),
        status=str(status_code)
    ).inc()

    ask_latency_seconds.labels(route=route).observe(latency_ms / 1000.0)


def record_ticket_lookup(ticket_id: str, found: bool):
    """Record ticket lookup metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    tickets_queried_total.labels(
        ticket_id=ticket_id,
        found=str(found).lower()
    ).inc()


def record_kb_ingestion(status: str):
    """Record KB ingestion metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    kb_ingestions_total.labels(status=status).inc()


def record_cache_operation(operation: str, namespace: str, result: str):
    """Record cache operation metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    cache_operations_total.labels(
        operation=operation,
        namespace=namespace,
        result=result
    ).inc()


def record_guardrail_trigger(guardrail_type: str):
    """Record guardrail trigger metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    guardrail_triggers_total.labels(type=guardrail_type).inc()


def set_system_metrics(
    chroma_collections: int = 0,
    chroma_chunks: Dict[str, int] = None,
    embedding_loaded: bool = False,
    mock_llm: bool = True
):
    """Set system-level gauge metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    chromadb_collections.set(chroma_collections)
    embedding_model_loaded.set(1 if embedding_loaded else 0)
    mock_llm_active.set(1 if mock_llm else 0)

    if chroma_chunks:
        for collection, count in chroma_chunks.items():
            chromadb_total_chunks.labels(collection=collection).set(count)


def trace_request(func: Callable) -> Callable:
    """Decorator to add trace context to async functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = str(uuid.uuid4())[:8]
        trace_id_var.set(trace_id)

        # Extract session_id from args/kwargs if present
        for arg in args:
            if hasattr(arg, "session_id"):
                session_id_var.set(arg.session_id)
                break
        if "session_id" in kwargs:
            session_id_var.set(kwargs["session_id"])

        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            logger = get_logger("trace")
            logger.info(
                f"Request completed",
                extra={
                    "trace_id": trace_id,
                    "latency_ms": latency_ms,
                    "function": func.__name__
                }
            )
    return wrapper


# Initialize default logger
logger = setup_structured_logging(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    json_format=os.environ.get("LOG_JSON", "true").lower() == "true"
)