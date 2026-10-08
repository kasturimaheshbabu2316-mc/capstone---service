"""Unit tests for support ticket lookup tool and escalation formula (Task 6)."""

import pytest
from tools.ticket_tool import (
    calculate_escalation_score,
    get_escalation_threshold,
    check_support_ticket_status,
    ESCALATION_THRESHOLD_TAU,
)


def test_escalation_score_formula_active_ticket():
    # Active ticket with escalated=True, days=30 -> 0.6 * 1.0 + 0.4 * 1.0 = 1.0
    rec = {"escalated": True, "days_since_created": 30, "status": "In Progress"}
    assert calculate_escalation_score(rec) == 1.0

    # Active ticket with escalated=False, days=15 -> 0.6 * 0.0 + 0.4 * 0.5 = 0.2
    rec2 = {"escalated": False, "days_since_created": 15, "status": "Open"}
    assert calculate_escalation_score(rec2) == 0.2


def test_escalation_score_formula_closed_resolved_recency_zeroed():
    # Closed ticket: recency term zeroed -> only 0.6 * escalated
    rec_closed = {"escalated": False, "days_since_created": 25, "status": "Closed"}
    assert calculate_escalation_score(rec_closed) == 0.0

    rec_resolved = {"escalated": True, "days_since_created": 28, "status": "Resolved"}
    assert calculate_escalation_score(rec_resolved) == 0.6


def test_escalation_threshold_empirically_valid():
    tau, scores = get_escalation_threshold()
    assert 0.0 <= tau <= 1.0
    assert len(scores) == 60


def test_check_support_ticket_status_lookup():
    # Valid record
    res = check_support_ticket_status("TKT-0001")
    assert res["record_id"] == "TKT-0001"
    assert res["status"] in ["Open", "In Progress", "Escalated", "Resolved", "Closed"]
    assert res["escalation_score"] is not None

    # Invalid record
    res_err = check_support_ticket_status("TKT-9999")
    assert "error" in res_err
    assert res_err["status"] == "Unknown"
