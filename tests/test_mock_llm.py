"""Unit tests for deterministic MockLLM, ReAct loop, and Crew execution (Task 7)."""

import pytest
from pydantic import BaseModel, Field
from crew.mock_llm import MockLLM, get_tool_arg_names, check_for_real_observation
from crew.crew import run_support_crew
from tools.rag_tool import rag_lookup_crew_tool
from tools.ticket_tool import check_support_ticket_status_crew_tool

PLACEHOLDER_SUBSTRINGS = [
    "placeholder",
    "todo",
    "dummy",
    "lorem ipsum",
    "sample text",
    "replace me",
    "insert here",
    "unimplemented",
]


def test_mock_llm_ticket_dispatch():
    """Simulates Turn 1 with lookup tool; asserts correct Action and ticket ID in Action Input."""
    llm = MockLLM()
    resp = llm.call(
        messages="Please check the current status of TKT-0007",
        from_agent=type("Agent", (), {"role": "Ticket Operations Specialist", "tools": [check_support_ticket_status_crew_tool]})(),
    )
    assert "Thought:" in resp
    assert "Action: check_support_ticket_status" in resp
    assert '"record_id": "TKT-0007"' in resp or '"record_id":"TKT-0007"' in resp.replace(" ", "")


def test_mock_llm_rag_dispatch():
    """Simulates Turn 1 with RAG tool; asserts correct Action and query in Action Input."""
    llm = MockLLM()
    resp = llm.call(
        messages="What is the SLA for a Sev-1 safety incident?",
        from_agent=type("Agent", (), {"role": "Policy Retrieval Specialist", "tools": [rag_lookup_crew_tool]})(),
    )
    assert "Thought:" in resp
    assert "Action: rag_lookup" in resp
    assert "Action Input:" in resp


def test_mock_llm_avoids_template_contamination_pitfall_a():
    """Pitfall A: Verifies that MockLLM ignores CrewAI template text 'Observation: the result of the action'."""
    llm = MockLLM()
    template_msg = (
        "You are an assistant.\n"
        "Observation: the result of the action\n"
        "User question: Check status of TKT-0001"
    )
    resp = llm.call(
        messages=template_msg,
        from_agent=type("Agent", (), {"role": "Ticket Operations Specialist", "tools": [check_support_ticket_status_crew_tool]})(),
    )
    # Must NOT emit Final Answer prematurely on Turn 1
    assert "Action: check_support_ticket_status" in resp
    assert "Final Answer:" not in resp


def test_mock_llm_dispatches_by_declared_args_schema_pitfall_b():
    """Pitfall B: Verifies that tool dispatch is governed by declared schema ('record_id' vs 'query'), NOT by tool name."""
    class CustomRagSchema(BaseModel):
        query: str = Field(..., description="Query text")

    class CustomTicketSchema(BaseModel):
        record_id: str = Field(..., description="Record ID")

    # Create dummy tools with deliberately arbitrary names
    dummy_rag = type("CustomTool", (), {
        "name": "arbitrary_search_engine_99",
        "args_schema": CustomRagSchema,
    })()
    dummy_ticket = type("CustomTool", (), {
        "name": "arbitrary_fetcher_engine_42",
        "args_schema": CustomTicketSchema,
    })()

    llm = MockLLM()

    # Query with ticket tool available
    resp_ticket = llm.call(
        messages="Check ticket TKT-0002",
        from_agent=type("Agent", (), {"role": "Operations", "tools": [dummy_ticket]})(),
    )
    assert "Action: arbitrary_fetcher_engine_42" in resp_ticket
    assert "TKT-0002" in resp_ticket

    # Query with rag tool available
    resp_rag = llm.call(
        messages="What is the refund rule?",
        from_agent=type("Agent", (), {"role": "Support", "tools": [dummy_rag]})(),
    )
    assert "Action: arbitrary_search_engine_99" in resp_rag


def test_mock_llm_react_two_turn_sequence():
    """Verifies complete 2-turn ReAct cycle: Action turn -> Observation turn -> Final Answer."""
    llm = MockLLM()
    agent = type("Agent", (), {"role": "Ticket Operations Specialist", "tools": [check_support_ticket_status_crew_tool]})()

    # Turn 1: Model emits Action
    t1_resp = llm.call(messages="Status of TKT-0002", from_agent=agent)
    assert "Action: check_support_ticket_status" in t1_resp

    # Turn 2: CrewAI provides history with Observation
    turn2_history = (
        "Status of TKT-0002\n"
        "Action: check_support_ticket_status\n"
        'Action Input: {"record_id": "TKT-0002"}\n'
        "Observation: Ticket ID: TKT-0002\nStatus: Escalated\nResolution Time: 15.8 hours\n"
    )
    t2_resp = llm.call(messages=turn2_history, from_agent=agent)
    assert "Thought: I now know the final answer" in t2_resp
    assert "Final Answer:" in t2_resp
    assert "TKT-0002" in t2_resp


def test_no_placeholder_in_policy_response():
    """Fails if the final answer of a policy query contains placeholder text."""
    query = "What is the SLA for a Sev-1 safety incident?"
    res = run_support_crew(query, session_id="test_mock_policy_nonplaceholder")

    ans = res["answer"]
    assert ans is not None and len(ans.strip()) > 20, "Answer is suspiciously empty"

    ans_lower = ans.lower()
    for placeholder in PLACEHOLDER_SUBSTRINGS:
        assert placeholder not in ans_lower, f"Found placeholder text '{placeholder}' in policy answer: {ans}"

    # Verify domain-specific grounded facts
    assert any(term in ans for term in ["15 minutes", "4 hours", "Sev-1", "safety incident"]), (
        f"Answer lacks domain policy content: {ans}"
    )
    assert res["grounded"] is True
    assert len(res["sources"]) > 0
    assert res["tool_invoked"] == "rag_lookup"


def test_no_placeholder_in_ticket_status_response():
    """Fails if the final answer of a ticket status query contains placeholder text."""
    query = "status of TKT-0007"
    res = run_support_crew(query, session_id="test_mock_ticket_nonplaceholder")

    ans = res["answer"]
    assert ans is not None and len(ans.strip()) > 20, "Answer is suspiciously empty"

    ans_lower = ans.lower()
    for placeholder in PLACEHOLDER_SUBSTRINGS:
        assert placeholder not in ans_lower, f"Found placeholder text '{placeholder}' in ticket answer: {ans}"

    # Verify domain-specific operational data for TKT-0007
    assert "TKT-0007" in ans
    assert "Closed" in ans
    assert "2.8" in ans  # Resolution time for TKT-0007
    assert res["ticket_id"] == "TKT-0007"
    assert res["tool_invoked"] == "check_support_ticket_status"
