"""Test Suite for Router Robustness, Ticket-ID Paraphrasing, and Follow-Up Entity Resolution.

Verifies:
1. extract_ticket_id extracts and normalizes varied paraphrased ticket inputs (tkt 7, ticket no. 0007, etc.).
2. Pronoun and follow-up entity resolution works for conversational triggers (what about that one, and its SLA, etc.).
3. Hybrid inquiries (ticket + policy in one prompt) trigger route 'both'.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from crew.mock_llm import extract_ticket_id
from crew.memory import resolve_pronouns_with_history, extract_last_entities_from_history
from crew.crew import run_support_crew


@pytest.mark.parametrize(
    "input_text,expected_id",
    [
        ("TKT-0007", "TKT-0007"),
        ("tkt-0007", "TKT-0007"),
        ("tkt 7", "TKT-0007"),
        ("ticket no. 0007", "TKT-0007"),
        ("ticket no 7", "TKT-0007"),
        ("ticket 7", "TKT-0007"),
        ("ticket #7", "TKT-0007"),
        ("ticket id: 0007", "TKT-0007"),
        ("what's happening with TKT-0007", "TKT-0007"),
        ("check ticket number 7", "TKT-0007"),
        ("status of tkt 42 please", "TKT-0042"),
        ("ticket: 15", "TKT-0015"),
        ("tkt:7", "TKT-0007"),
        ("TKT0007", "TKT-0007"),
        ("TKT 0007", "TKT-0007"),
    ],
)
def test_paraphrased_ticket_id_extraction(input_text: str, expected_id: str):
    """Validates that extract_ticket_id standardizes diverse ticket phrasings into TKT-XXXX."""
    actual = extract_ticket_id(input_text)
    assert actual == expected_id, f"Failed for '{input_text}': got '{actual}', expected '{expected_id}'"


@pytest.mark.parametrize(
    "followup_query,expected_ticket_in_resolved",
    [
        ("what about that one?", "TKT-0007"),
        ("what about that one", "TKT-0007"),
        ("and its SLA", "TKT-0007"),
        ("what about its SLA?", "TKT-0007"),
        ("is it escalated?", "TKT-0007"),
        ("is it escalated", "TKT-0007"),
        ("same ticket", "TKT-0007"),
        ("is that one at risk of escalation?", "TKT-0007"),
    ],
)
def test_pronoun_followup_resolution(followup_query: str, expected_ticket_in_resolved: str):
    """Validates that conversational follow-up triggers resolve to the previous ticket from history."""
    history = [
        HumanMessage(content="What is the status of TKT-0007?"),
        AIMessage(content="Ticket TKT-0007 is In Progress with an escalation score of 0.35."),
    ]
    resolved, was_resolved, referent_id = resolve_pronouns_with_history(followup_query, history)
    assert was_resolved is True
    assert expected_ticket_in_resolved in resolved
    assert referent_id == expected_ticket_in_resolved


@pytest.mark.parametrize(
    "hybrid_prompt",
    [
        "What is the status of TKT-0007 and what is the SLA policy for this incident?",
        "Check ticket 7 and explain the refund policy for delayed rides",
        "tkt 7 status plus what is the Sev-1 safety incident SLA?",
    ],
)
def test_hybrid_ticket_and_policy_queries(hybrid_prompt: str):
    """Validates that prompts referencing both a ticket and a policy route to 'both'."""
    res = run_support_crew(hybrid_prompt, session_id="test_hybrid_session", structured=True)
    assert res.route == "both"
    assert res.ticket is not None
    assert "TKT-0007" in str(res.ticket)
    assert len(res.sources) > 0
