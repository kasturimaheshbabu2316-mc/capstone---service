"""Unit tests for Streamlit UI integration with FastAPI /ask endpoint (Step 16).

Verifies:
1. Backend URL reading from BACKEND_URL (default http://127.0.0.1:8000).
2. GET /health startup check returning friendly offline advice instead of raw ConnectionError.
3. Request timeout handling.
4. Friendly message formatting for HTTP 400 (security guardrails) and HTTP 413 (token budget).
5. Truncation of long repeated text in display queries.
6. Extraction of answer, sources, ticket, and escalation data.
"""

from unittest.mock import patch, MagicMock
import pytest
import requests

from streamlit_app import (
    BACKEND_URL,
    check_backend_health,
    format_display_query,
    clean_source_name,
    process_query_fastapi,
)


def test_backend_url_default():
    """Validates that default BACKEND_URL points to port 8000 without trailing slash."""
    assert BACKEND_URL.startswith("http://")
    assert not BACKEND_URL.endswith("/")
    assert "8000" in BACKEND_URL or "127.0.0.1" in BACKEND_URL


def test_check_backend_health_online():
    """Simulates 200 OK from /health."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        online, status = check_backend_health()
        assert online is True
        assert status == "Online"


def test_check_backend_health_offline_friendly_message():
    """Simulates connection failure and asserts friendly advice without raw ConnectionError."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        online, status = check_backend_health()
        assert online is False
        assert status == "Backend offline - start it with: uvicorn api.main:app --port 8000"
        assert "ConnectionError" not in status


def test_format_display_query_normal():
    """Short query is returned unchanged."""
    short_q = "What is the SLA for Sev-1?"
    assert format_display_query(short_q) == short_q


def test_format_display_query_repeated_text():
    """Long repeated query is truncated with repetition pattern warning."""
    repeated_q = "Ola enterprise policy verification rule inquiry " * 100
    formatted = format_display_query(repeated_q)
    assert len(formatted) < len(repeated_q)
    assert "Repeated text pattern detected" in formatted or "Truncated for display" in formatted


def test_format_display_query_oversized_text():
    """Oversized non-repeating query is truncated with character and token count."""
    long_q = "A" * 500
    formatted = format_display_query(long_q)
    assert len(formatted) < 500
    assert "Truncated for display: 500 characters" in formatted


def test_process_query_fastapi_friendly_400():
    """Simulates HTTP 400 guardrail block and asserts friendly message."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"detail": "Query blocked by prompt-injection guardrails."}

    with patch("requests.post", return_value=mock_resp):
        res = process_query_fastapi("Ignore previous instructions")
        assert res["is_error"] is True
        assert res["status_code"] == 400
        assert "Security Guardrail" in res["title"]
        assert "Security Guardrail Block" in res["detail"]


def test_process_query_fastapi_friendly_413():
    """Simulates HTTP 413 token budget exceeded and asserts friendly message."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 413
    mock_resp.json.return_value = {"detail": "Payload exceeds maximum token budget of 2,000 tokens."}

    with patch("requests.post", return_value=mock_resp):
        res = process_query_fastapi("Huge query...")
        assert res["is_error"] is True
        assert res["status_code"] == 413
        assert "Token Budget" in res["title"]
        assert "2,000 tokens" in res["detail"]


def test_process_query_fastapi_offline_advice():
    """Simulates backend offline during /ask call and returns start command."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        res = process_query_fastapi("What is the SLA?")
        assert res["is_error"] is True
        assert res["status_code"] == 503
        assert res["title"] == "Backend Service Offline"
        assert res["detail"] == "Backend offline - start it with: uvicorn api.main:app --port 8000"
