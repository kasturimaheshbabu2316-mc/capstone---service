"""Unit tests for audit logging & zero PII leakage (Task 12)."""

import os
import json
import pytest
from app.logging_utils import audit_logger, LOG_FILE


def test_audit_log_fields_and_no_raw_phone():
    test_phone = "+91 99887 76655"
    test_query = f"Customer phone {test_phone} requesting SLA details"

    entry = audit_logger.log_request(
        endpoint="/test",
        query=test_query,
        status_code=200,
        latency_ms=45.2,
        session_id="test_session",
    )

    # Check return object
    assert "[PHONE_MASKED]" in entry["masked_query"]
    assert test_phone not in entry["masked_query"]
    assert "trace_id" in entry
    assert "timestamp" in entry

    # Check physical file on disk
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert test_phone not in file_content, f"SECURITY FAILURE: Raw phone {test_phone} leaked into {LOG_FILE}"
