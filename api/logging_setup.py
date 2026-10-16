"""Audit Logging and Structured JSON-Lines Logger Setup (Task 12).

Track: Business Operations / Customer Support (Ola)
Provides thread-safe structured logging to logs/requests.jsonl with:
- trace_id (uuid4)
- timestamp (ISO-8601 UTC)
- endpoint
- session_id
- masked_question (guaranteed Step 9 PII phone masking applied before writing)
- route
- latency_ms
- status_code
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from safety.guardrails import mask_pii

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.environ.get("LOG_DIR", str(PROJECT_ROOT / "logs")))
LOG_FILE = Path(os.environ.get("LOG_FILE", str(LOG_DIR / "requests.jsonl")))
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

_log_lock = threading.Lock()
logger = logging.getLogger("ola_domain_agent.audit")


class AuditLogger:
    """Thread-safe JSONL logger guaranteeing zero PII leakage into audit logs."""

    def __init__(self, log_path: Path | str = LOG_FILE):
        self.log_path = Path(log_path)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.logger = logger

    def log_request(
        self,
        endpoint: str,
        question: Optional[str] = None,
        status_code: int = 200,
        latency_ms: float = 0.0,
        session_id: str = "default_session",
        trace_id: Optional[str] = None,
        route: str = "none",
        cache_hit: bool = False,
        guardrail_flags: Optional[dict[str, Any]] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Writes one JSON-Lines record to logs/requests.jsonl.

        Guarantees that the Step 9 mask_pii() is applied to the input question
        so no raw phone numbers are ever persisted to disk.
        """
        raw_text = question if question is not None else (query or "")

        # Strictly apply Step 9 PII masking before writing to disk
        pii_res = mask_pii(raw_text)
        masked_text = pii_res.sanitized_text

        if trace_id is None:
            trace_id = str(uuid.uuid4())

        flags = dict(guardrail_flags or {})
        if pii_res.fired:
            flags["phone_masked"] = True

        entry = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "session_id": session_id,
            "masked_question": masked_text,
            "masked_query": masked_text,  # alias for backwards compatibility
            "route": route,
            "latency_ms": round(latency_ms, 2),
            "status_code": status_code,
            "cache_hit": cache_hit,
            "guardrail_flags": flags,
        }

        # Include any extra kwargs
        for k, v in kwargs.items():
            if k not in entry:
                entry[k] = v

        with _log_lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        return entry


# Singleton audit logger instance
audit_logger = AuditLogger()
RequestAuditLogger = AuditLogger

__all__ = ["audit_logger", "AuditLogger", "RequestAuditLogger", "LOG_FILE", "LOG_DIR"]
