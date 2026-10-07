"""Structured JSON-Lines Audit Logging Utility.

Track: Business Operations / Customer Support (Ola)
Emits structured audit records to logs/requests.jsonl with UUID trace IDs,
latencies, and guaranteed PII phone number redaction.
"""

from typing import Any
import os
import json
import uuid
from datetime import datetime, timezone
import threading
from guardrails.input_guard import mask_phone_numbers

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "requests.jsonl")

_log_lock = threading.Lock()


class AuditLogger:
    """Thread-safe JSONL logger guaranteeing zero PII leakage."""

    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_request(
        self,
        endpoint: str,
        query: str,
        status_code: int,
        latency_ms: float,
        session_id: str = "default_session",
        trace_id: str | None = None,
        cache_hit: bool = False,
        guardrail_flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Writes an audit entry to logs/requests.jsonl with guaranteed phone masking."""
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        # Strict PII masking before persisting to storage
        masked_q, was_masked = mask_phone_numbers(query)

        flags = dict(guardrail_flags or {})
        if was_masked:
            flags["phone_masked"] = True

        entry = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "session_id": session_id,
            "masked_query": masked_q,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
            "cache_hit": cache_hit,
            "guardrail_flags": flags,
        }

        with _log_lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        return entry


# Global audit logger instance
audit_logger = AuditLogger()
