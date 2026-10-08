"""Unit tests for Governance: Least Autonomy and Token Budgeting (Task 15)."""

import pytest
from governance.least_autonomy import ToolAccessControl, ROLE_PERMISSIONS
from governance.budget import estimate_token_count, check_budget_limit, MAX_TOKEN_BUDGET


def test_least_autonomy_authorized_tools():
    # Retrieval agent can access rag_lookup
    assert ToolAccessControl.verify_agent_tool_access("Policy Retrieval Specialist", "rag_lookup") is True

    # Lookup agent can access check_support_ticket_status
    assert ToolAccessControl.verify_agent_tool_access("Ticket Operations Specialist", "check_support_ticket_status") is True


def test_least_autonomy_unauthorized_tool_raises_permission_error():
    # Response Composer is toolless; binding any tool must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        ToolAccessControl.verify_agent_tool_access("Support Response Composer", "check_support_ticket_status")
    assert "Least Autonomy Violation" in str(exc_info.value)

    # Retrieval Agent cannot access ticket tool
    with pytest.raises(PermissionError) as exc_info2:
        ToolAccessControl.verify_agent_tool_access("Policy Retrieval Specialist", "check_support_ticket_status")
    assert "Least Autonomy Violation" in str(exc_info2.value)


def test_token_budget_estimation():
    text = "Hello world"
    tokens = estimate_token_count(text)
    assert tokens == len(text) // 4


def test_token_budget_enforcement():
    normal_query = "What is the SLA for a Sev-1 incident?"
    within_budget, tokens, err = check_budget_limit(normal_query)
    assert within_budget is True
    assert err is None
    assert tokens <= MAX_TOKEN_BUDGET

    huge_query = "Ola policy question " * 1000  # ~5000 tokens
    within_budget, tokens, err = check_budget_limit(huge_query)
    assert within_budget is False
    assert err is not None
    assert tokens > MAX_TOKEN_BUDGET
    assert "exceeds maximum token budget" in err
