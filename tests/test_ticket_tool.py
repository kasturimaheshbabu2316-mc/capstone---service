"""Unit tests for support ticket lookup tool and escalation formula (Task 6)."""

import pytest
from dataset import SUPPORT_TICKETS
from tools.ticket_tool import (
    W1,
    W2,
    DAYS_80TH_PERCENTILE,
    ESCALATION_THRESHOLD,
    ESCALATION_THRESHOLD_TAU,
    calculate_escalation_score,
    get_escalation_threshold,
    check_support_ticket_status,
)


def test_known_id_lookup():
    """Tests looking up a known valid support ticket ID."""
    res = check_support_ticket_status("TKT-0001")
    assert "error" not in res
    assert res["record_id"] == "TKT-0001"
    assert res["status"] in ["Open", "In Progress", "Escalated", "Resolved", "Closed"]
    assert isinstance(res["resolution_time_hours"], float)
    assert res["resolution_time_hours"] > 0.0
    assert isinstance(res["escalation_score"], float)
    assert 0.0 <= res["escalation_score"] <= 1.0
    assert isinstance(res["recommend_escalation"], bool)
    assert res["category"] in ["Billing", "Technical Issue", "Account Access", "Product Defect", "General Inquiry"]
    assert isinstance(res["days_since_created"], int)
    assert isinstance(res["escalated"], bool)


def test_unknown_id_lookup():
    """Tests looking up an unknown or non-existent ticket ID."""
    for invalid_id in ["TKT-9999", "INVALID-ID", "TKT-0000"]:
        res = check_support_ticket_status(invalid_id)
        assert "error" in res
        assert res["status"] == "Unknown"
        assert res["resolution_time_hours"] is None
        assert res["escalation_score"] is None
        assert res["recommend_escalation"] is False
        assert res["risk_level"] == "Unknown"


def test_score_bounds_across_all_tickets():
    """Verifies that escalation_score is strictly bounded in [0.0, 1.0] for all dataset records."""
    assert len(SUPPORT_TICKETS) == 60
    for record in SUPPORT_TICKETS:
        score = calculate_escalation_score(record)
        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for {record['record_id']}"

        # Test lookup tool response
        lookup_res = check_support_ticket_status(record["record_id"])
        assert "error" not in lookup_res
        assert 0.0 <= lookup_res["escalation_score"] <= 1.0


def test_score_bounds_synthetic_extremes():
    """Tests edge cases and boundary clipping for escalation scoring."""
    # Minimum possible: unescalated, 0 days
    min_rec = {"escalated": False, "days_since_created": 0, "status": "Open"}
    assert calculate_escalation_score(min_rec) == 0.0

    # Maximum possible: escalated, 30 days
    max_rec = {"escalated": True, "days_since_created": 30, "status": "In Progress"}
    assert calculate_escalation_score(max_rec) == 1.0

    # Overflow clipping: > 30 days capped at 1.0 factor
    overflow_rec = {"escalated": True, "days_since_created": 100, "status": "Open"}
    assert calculate_escalation_score(overflow_rec) == 1.0

    # Underflow clipping: < 0 days floored at 0.0 factor
    underflow_rec = {"escalated": False, "days_since_created": -10, "status": "Open"}
    assert calculate_escalation_score(underflow_rec) == 0.0


def test_escalated_ticket():
    """Tests an escalated ticket triggers high score and recommend_escalation=True."""
    # TKT-0002 is an escalated ticket in the dataset (escalated=True, days=18)
    res = check_support_ticket_status("TKT-0002")
    assert "error" not in res
    assert res["escalated"] is True
    assert res["escalation_score"] >= 0.60
    assert res["recommend_escalation"] is True
    assert res["risk_level"] == "High Risk"

    # TKT-0031 is an escalated ticket with 30 days active -> score 1.0
    res_max = check_support_ticket_status("TKT-0031")
    assert res_max["escalated"] is True
    assert res_max["escalation_score"] == 1.0
    assert res_max["recommend_escalation"] is True


def test_old_ticket_aging():
    """Tests aging contribution for active tickets vs closed/resolved tickets."""
    # TKT-0001: Active Open ticket with days_since_created=23 (P80 age)
    # Score = 0.6 * 0 + 0.4 * (23 / 30) = 0.3067
    res_p80 = check_support_ticket_status("TKT-0001")
    assert res_p80["escalated"] is False
    assert res_p80["days_since_created"] == 23
    assert res_p80["status"] == "Open"
    assert res_p80["escalation_score"] == 0.3067
    assert res_p80["recommend_escalation"] is False  # 0.3067 < 0.4400

    # TKT-0016: Active In Progress ticket with days_since_created=30 (max age)
    # Score = 0.6 * 0 + 0.4 * (30 / 30) = 0.4000
    res_max_age = check_support_ticket_status("TKT-0016")
    assert res_max_age["escalated"] is False
    assert res_max_age["days_since_created"] == 30
    assert res_max_age["status"] == "In Progress"
    assert res_max_age["escalation_score"] == 0.4000
    assert res_max_age["recommend_escalation"] is False  # 0.4000 < 0.4400

    # TKT-0007: Closed ticket with days_since_created=23 -> aging zeroed out
    res_closed = check_support_ticket_status("TKT-0007")
    assert res_closed["status"] == "Closed"
    assert res_closed["days_since_created"] == 23
    assert res_closed["escalated"] is False
    assert res_closed["escalation_score"] == 0.0


def test_formula_weights_and_threshold():
    """Validates the frozen weights and empirical 80th-percentile threshold values."""
    assert W1 == 0.6
    assert W2 == 0.4
    assert DAYS_80TH_PERCENTILE == 23.0
    assert ESCALATION_THRESHOLD == 0.4400
    assert ESCALATION_THRESHOLD_TAU == 0.4400

    tau, scores = get_escalation_threshold()
    assert tau == 0.4400
    assert len(scores) == 60
