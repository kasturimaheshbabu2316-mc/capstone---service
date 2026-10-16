"""Unit tests for audit logging & zero PII leakage (Task 12)."""

import json
import os
import pytest
from api.logging_setup import audit_logger, LOG_FILE


def test_audit_log_fields_and_no_raw_phone():
    test_phone = "+91 99887 76655"
    test_question = f"Customer phone {test_phone} requesting SLA details"

    entry = audit_logger.log_request(
        endpoint="/test",
        question=test_question,
        status_code=200,
        latency_ms=45.2,
        session_id="test_session",
        route="rag",
    )

    # Check returned object schema requirements
    assert "trace_id" in entry
    assert "timestamp" in entry
    assert "endpoint" in entry
    assert "session_id" in entry
    assert "masked_question" in entry
    assert "route" in entry
    assert "latency_ms" in entry
    assert "status_code" in entry

    assert "[PHONE_MASKED]" in entry["masked_question"]
    assert test_phone not in entry["masked_question"]
    assert entry["route"] == "rag"
    assert entry["status_code"] == 200

    # Check physical file on disk: raw number must NEVER appear
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert test_phone not in file_content, f"SECURITY FAILURE: Raw phone {test_phone} leaked into {LOG_FILE}"


def test_audit_log_format_multiple_formats():
    test_phones = ["9876543210", "98765-43210", "+91 98765 43210"]
    for ph in test_phones:
        raw_msg = f"User contact number is {ph}"
        entry = audit_logger.log_request(
            endpoint="/ask",
            question=raw_msg,
            status_code=200,
            latency_ms=12.5,
            session_id="sess_multi",
            route="lookup",
        )
        assert "[PHONE_MASKED]" in entry["masked_question"]
        assert ph not in entry["masked_question"]

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        file_content = f.read()

    for ph in test_phones:
        assert ph not in file_content, f"Raw phone {ph} leaked into log file"
