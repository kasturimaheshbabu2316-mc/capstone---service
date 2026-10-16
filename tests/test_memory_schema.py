"""Unit tests for Session Memory (Task 8) and CrewResponse Schema Validation (Task 9)."""

import pytest
from pydantic import ValidationError
from crew.memory import (
    InMemoryChatMessageHistory,
    RunnableWithMessageHistory,
    get_session_history,
    resolve_pronouns_with_history,
    session_memory,
)
from crew.schemas import CrewResponse, validate_crew_response
from crew.crew import run_support_crew


def test_in_memory_history_and_session_store():
    """Validates InMemoryChatMessageHistory creation and message retention across sessions."""
    session_memory.clear()
    hist_1 = get_session_history("test_sess_1")
    assert isinstance(hist_1, InMemoryChatMessageHistory)

    session_memory.record_interaction("test_sess_1", "Check TKT-0007", "Ticket TKT-0007 is closed.")
    assert len(hist_1.messages) == 2

    # Verify session 2 is isolated
    hist_2 = get_session_history("test_sess_2")
    assert len(hist_2.messages) == 0


def test_multi_turn_pronoun_resolution_session_a():
    """Turn 2 depends on Turn 1: 'that one' and 'its SLA' resolve to TKT-0007."""
    session_memory.clear("session_a_test")

    # Turn 1: Explicit mention
    res1 = run_support_crew("Check the status of TKT-0007", session_id="session_a_test")
    assert res1["ticket_id"] == "TKT-0007"

    # Turn 2: Follow-up using pronouns
    res2 = run_support_crew("What about its SLA and is that one at risk of escalation?", session_id="session_a_test")
    assert res2["was_resolved"] is True
    assert "TKT-0007" in res2["resolved_query"]
    assert res2["ticket_id"] == "TKT-0007"
    assert res2["route"] in ("lookup", "both")


def test_session_b_fresh_isolation_fails_reset():
    """Fresh session with zero prior history: pronoun cannot resolve and resets/fails."""
    session_memory.clear("session_b_test")

    # Follow-up query executed directly in a fresh session
    res = run_support_crew("What about its SLA and is that one at risk of escalation?", session_id="session_b_test")
    assert res["was_resolved"] is False
    assert res["ticket_id"] is None


def test_crew_response_schema_validation_valid():
    """Validates CrewResponse instances with rag, lookup, and both routes."""
    # RAG route
    rag_data = {
        "answer": "Sev-1 first response is 15 minutes.",
        "route": "rag",
        "sources": ["sla_by_severity.md"],
        "ticket": None,
        "grounded": True,
        "escalation_recommended": False,
    }
    validated_rag = CrewResponse.model_validate(rag_data)
    assert validated_rag.route == "rag"
    assert validated_rag.grounded is True

    # Lookup route
    lookup_data = {
        "answer": "Ticket TKT-0002 is escalated.",
        "route": "lookup",
        "sources": ["dataset.py"],
        "ticket": {"record_id": "TKT-0002", "status": "Escalated"},
        "grounded": True,
        "escalation_recommended": True,
    }
    validated_lookup = CrewResponse.model_validate(lookup_data)
    assert validated_lookup.route == "lookup"
    assert validated_lookup.escalation_recommended is True

    # Both route
    both_data = {
        "answer": "Ticket TKT-0002 status and general refund policy.",
        "route": "both",
        "sources": ["dataset.py", "refund_policy.md"],
        "ticket": {"record_id": "TKT-0002"},
        "grounded": True,
        "escalation_recommended": True,
    }
    validated_both = CrewResponse.model_validate(both_data)
    assert validated_both.route == "both"


def test_crew_response_schema_validation_mismatch_raises_error():
    """Demonstrates that CrewResponse.model_validate raises ValidationError on invalid data."""
    # Missing required 'answer'
    with pytest.raises(ValidationError):
        CrewResponse.model_validate({
            "route": "rag",
            "sources": [],
            "grounded": True,
            "escalation_recommended": False,
        })

    # Invalid route string ('unsupported_route')
    with pytest.raises(ValidationError):
        CrewResponse.model_validate({
            "answer": "Some answer",
            "route": "unsupported_route",
            "sources": [],
            "grounded": True,
            "escalation_recommended": False,
        })

    # Helper function raises ValueError on mismatch
    with pytest.raises(ValueError) as excinfo:
        validate_crew_response({"route": "invalid"})
    assert "CrewResponse schema mismatch error" in str(excinfo.value)


def test_run_support_crew_structured_output_returns_crew_response():
    """Verifies that run_support_crew(structured=True) returns a validated CrewResponse."""
    res = run_support_crew("What is the SLA for a Sev-1 safety incident?", structured=True)
    assert isinstance(res, CrewResponse)
    assert res.route == "rag"
    assert res.grounded is True
    assert len(res.sources) > 0
    assert "15 minutes" in res.answer or "4 hours" in res.answer
