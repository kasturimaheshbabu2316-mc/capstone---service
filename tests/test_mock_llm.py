"""Unit tests for deterministic MockLLM and ReAct loop (Task 7)."""

import pytest
from llm.mock_llm import MockLLM
from tools.rag_tool import rag_lookup
from tools.ticket_tool import check_support_ticket_status


def test_mock_llm_ticket_dispatch():
    llm = MockLLM()
    # Simulate Call 1 with lookup tool
    resp = llm.call(
        messages="Please check the current status of TKT-0007",
        from_agent=type("Agent", (), {"role": "Ticket Operations Specialist", "tools": [check_support_ticket_status]})(),
    )
    assert "Action: check_support_ticket_status" in resp
    assert "TKT-0007" in resp


def test_mock_llm_rag_dispatch():
    llm = MockLLM()
    resp = llm.call(
        messages="What is the SLA for a Sev-1 safety incident?",
        from_agent=type("Agent", (), {"role": "Policy Retrieval Specialist", "tools": [rag_lookup]})(),
    )
    assert "Action: rag_lookup" in resp


def test_mock_llm_avoids_template_contamination():
    llm = MockLLM()
    # Prompt containing CrewAI system template placeholder
    template_msg = (
        "You are an assistant.\n"
        "Observation: the result of the action\n"
        "User question: Check status of TKT-0001"
    )
    resp = llm.call(
        messages=template_msg,
        from_agent=type("Agent", (), {"role": "Ticket Operations Specialist", "tools": [check_support_ticket_status]})(),
    )
    # Pitfall 1: Must NOT treat placeholder template as a real observation
    assert "Action: check_support_ticket_status" in resp
