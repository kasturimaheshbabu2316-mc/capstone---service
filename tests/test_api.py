"""Unit tests for FastAPI endpoints and WebSocket resilience (Task 11)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_ask_policy_endpoint():
    res = client.post("/ask", json={"query": "What is the SLA for a Sev-1 safety incident?"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["grounded"] is True
    assert len(data["sources"]) > 0


def test_ask_ticket_endpoint():
    res = client.post("/ask", json={"query": "What is the status of TKT-0007?"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["ticket_id"] == "TKT-0007"


def test_ask_budget_cap_endpoint():
    huge_query = "Ola policy question " * 1000
    res = client.post("/ask", json={"query": huge_query})
    assert res.status_code == 413


def test_websocket_chat_and_disconnect():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("What is the SLA for Sev-1?")
        data = ws.receive_json()
        assert data["type"] == "response"
        assert data["data"]["grounded"] is True

    # Confirm second connection succeeds after abrupt disconnect
    with client.websocket_connect("/ws/chat") as ws2:
        ws2.send_text("What is the status of TKT-0001?")
        data2 = ws2.receive_json()
        assert data2["type"] == "response"
        assert data2["data"]["ticket_id"] == "TKT-0001"
