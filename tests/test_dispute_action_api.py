"""Unit and Integration Tests for Live Dispute Action & Inspector Endpoints.

Validates:
- GET /api/tickets/{ticket_id}/inspector (telematics, receipt, Safe-Harbor Clause 14B)
- POST /api/tickets/{ticket_id}/action (offline execution, overlay state, deterministic transaction ID)
- GET /tickets overlay reflection
- Input validation & safety guardrails (bad formats, non-existent tickets, invalid amounts)
- RAG grounding for Safe-Harbor Clause 14B
"""

from typing import Any
import pytest
from fastapi.testclient import TestClient
from api.main import app, DISPUTE_STATE_OVERLAY


@pytest.fixture(autouse=True)
def clean_dispute_overlay():
    """Ensures test isolation by clearing the dispute state overlay before each test."""
    DISPUTE_STATE_OVERLAY.clear()
    yield
    DISPUTE_STATE_OVERLAY.clear()


@pytest.fixture
def client():
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


def test_get_ticket_inspector_tkt_0007(client: TestClient):
    """Verifies inspector dossier for TKT-0007 returns complete telematics and Safe-Harbor Clause 14B recommendation."""
    response = client.get("/api/tickets/TKT-0007/inspector")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert data["ticket_id"] == "TKT-0007"
    assert data["category"] == "Billing"
    assert data["title"] == "Fastag Toll Surcharge Conflict"
    assert "Trumpet KA-02" in data["telematics"]["toll_plaza"]
    assert data["telematics"]["speed_kmh"] == 74
    assert data["audit_receipt"]["airport_toll_billed"] == 140.0
    assert data["audit_receipt"]["reconciliation_delta"] == 140.0
    assert "Safe-Harbor clause 14B" in data["rover_recommendation"]["text"]
    assert data["rover_recommendation"]["confidence"] >= 0.99
    assert data["action"]["can_execute"] is True


def test_post_ticket_action_execute_refund(client: TestClient):
    """Verifies executing a refund marks ticket as Resolved and generates deterministic wallet transaction."""
    payload = {
        "action": "execute_refund",
        "amount": 140.0,
        "reason": "Dual deduction confirmed at Trumpet KA-02 beacon",
    }
    response = client.post("/api/tickets/TKT-0007/action", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["ticket_id"] == "TKT-0007"
    assert data["status"] == "Resolved"
    assert data["reconciled_status"] == "Reconciled"
    assert data["txn_id"] == "OLA-WL-894214"
    assert data["amount"] == 140.0

    # Verify overlay persisted in memory
    assert "TKT-0007" in DISPUTE_STATE_OVERLAY
    assert DISPUTE_STATE_OVERLAY["TKT-0007"]["status"] == "Resolved"

    # Verify directory endpoint reflects resolved status
    dir_res = client.get("/tickets")
    assert dir_res.status_code == 200
    tickets = dir_res.json()
    tkt_7 = next((t for t in tickets if t.get("ticket_id") == "TKT-0007"), None)
    assert tkt_7 is not None
    assert tkt_7["status"] == "Resolved"

    # Verify inspector reflects Reconciled state and cannot execute duplicate refund
    insp_res = client.get("/api/tickets/TKT-0007/inspector")
    assert insp_res.status_code == 200
    insp_data = insp_res.json()
    assert insp_data["status"] == "Resolved"
    assert insp_data["dispute_status"] == "Reconciled"
    assert insp_data["action"]["can_execute"] is False
    assert insp_data["audit_receipt"]["settlement_txn"] == "OLA-WL-894214"


def test_ticket_inspector_invalid_format(client: TestClient):
    """Verifies that malformed ticket IDs return HTTP 400."""
    response = client.get("/api/tickets/INVALID-ID/inspector")
    assert response.status_code == 400
    assert "Invalid ticket format" in response.json()["detail"]


def test_ticket_inspector_not_found(client: TestClient):
    """Verifies that non-existent ticket IDs return HTTP 404."""
    response = client.get("/api/tickets/TKT-9999/inspector")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_ticket_action_negative_amount_rejected(client: TestClient):
    """Verifies that invalid amounts are rejected by Pydantic validation (HTTP 422)."""
    payload = {
        "action": "execute_refund",
        "amount": -50.0,
    }
    response = client.post("/api/tickets/TKT-0007/action", json=payload)
    assert response.status_code == 422


def test_ask_safe_harbor_clause_14b_grounding(client: TestClient):
    """Verifies POST /ask retrieves Safe-Harbor Clause 14B from refund_compensation_policy."""
    payload = {
        "question": "What is Safe-Harbor Clause 14B for Fastag toll deductions?",
        "session_id": "test_safe_harbor_session",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["grounded"] is True or data.get("guardrail_flags", {}).get("groundedness_pass") is True
    sources = data.get("sources") or data.get("retrieved_sources") or []
    assert any("refund_compensation_policy" in s for s in sources)
    answer_text = (data.get("answer") or data.get("response") or data.get("text") or "").lower()
    assert "safe-harbor" in answer_text or "clause 14b" in answer_text or "fastag" in answer_text or "140" in answer_text
