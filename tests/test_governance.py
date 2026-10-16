"""Unit tests for Governance: Least Autonomy and Token Budgeting (Task 15).

Track: Business Operations / Customer Support (Ola)
Verifies:
1. Least Autonomy registry and tool guard wrapper:
   - TOOL_PERMISSIONS = {"check_support_ticket_status": ["Lookup Agent"]}
   - Composer Agent or Retrieval Agent calling the tool is blocked with PermissionError.
   - Lookup Agent calling the tool succeeds.
2. Token budget estimation and MAX_REQUEST_TOKENS enforcement.
3. Transcripts verification for Task 15.
"""

from pathlib import Path
import pytest
from governance.least_autonomy import ToolAccessControl, ROLE_PERMISSIONS
from governance.budget import (
    estimate_token_count,
    check_budget_limit,
    MAX_REQUEST_TOKENS,
    MAX_TOKEN_BUDGET,
    run_governance_demonstration,
)
from tools.ticket_tool import (
    check_support_ticket_status,
    TOOL_PERMISSIONS,
)


def test_least_autonomy_authorized_tools():
    """Retrieval and Lookup agents can access their respective designated tools."""
    assert ToolAccessControl.verify_agent_tool_access("Policy Retrieval Specialist", "rag_lookup") is True
    assert ToolAccessControl.verify_agent_tool_access("Ticket Operations Specialist", "check_support_ticket_status") is True


def test_least_autonomy_unauthorized_tool_raises_permission_error():
    """Toolless or mismatched agent roles raise PermissionError at initialization."""
    with pytest.raises(PermissionError) as exc_info:
        ToolAccessControl.verify_agent_tool_access("Support Response Composer", "check_support_ticket_status")
    assert "Least Autonomy Violation" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info2:
        ToolAccessControl.verify_agent_tool_access("Policy Retrieval Specialist", "check_support_ticket_status")
    assert "Least Autonomy Violation" in str(exc_info2.value)


def test_tool_guard_wrapper_blocks_composer_and_retrieval():
    """Guard wrapper inside check_support_ticket_status blocks Composer/Retrieval and permits Lookup Agent."""
    # 1. Verify TOOL_PERMISSIONS registry contains check_support_ticket_status
    assert "check_support_ticket_status" in TOOL_PERMISSIONS
    assert any("Lookup Agent" in r or "Ticket Operations" in r for r in TOOL_PERMISSIONS["check_support_ticket_status"])

    # 2. Composer agent call is blocked
    with pytest.raises(PermissionError) as exc_composer:
        check_support_ticket_status("TKT-0001", caller_role="Support Response Composer")
    assert "Least Autonomy Violation" in str(exc_composer.value)

    # 3. Retrieval agent call is blocked
    with pytest.raises(PermissionError) as exc_retrieval:
        check_support_ticket_status("TKT-0001", caller_role="Policy Retrieval Specialist")
    assert "Least Autonomy Violation" in str(exc_retrieval.value)

    # 4. Lookup agent succeeds
    result = check_support_ticket_status("TKT-0001", caller_role="Lookup Agent")
    assert result["record_id"] == "TKT-0001"
    assert result["status"] == "Open"
    assert "escalation_score" in result


def test_token_budget_estimation():
    """Verifies token count estimation using character/4 heuristic."""
    text = "Hello world"
    tokens = estimate_token_count(text)
    assert tokens == len(text) // 4

    tokens_with_context = estimate_token_count("Hello", context="World1234")
    assert tokens_with_context == (len("Hello") + len("World1234")) // 4


def test_token_budget_enforcement():
    """Verifies request acceptance within budget and rejection when oversized."""
    normal_query = "What is the SLA for a Sev-1 incident?"
    within_budget, tokens, err = check_budget_limit(normal_query)
    assert within_budget is True
    assert err is None
    assert tokens <= MAX_REQUEST_TOKENS

    huge_query = "Ola policy question " * 1000  # ~5000 tokens
    within_budget, tokens, err = check_budget_limit(huge_query)
    assert within_budget is False
    assert err is not None
    assert tokens > MAX_REQUEST_TOKENS
    assert "exceeds maximum token budget" in err


def test_governance_transcript_file_exists():
    """Verifies transcripts/15_governance.txt exists with expected sections."""
    transcript_path = Path(__file__).resolve().parent.parent / "transcripts" / "15_governance.txt"
    assert transcript_path.exists(), "transcripts/15_governance.txt must exist."
    content = transcript_path.read_text(encoding="utf-8")
    assert "LEAST AUTONOMY TOOL PERMISSIONS REGISTRY" in content
    assert "SYSTEM RISK CLASSIFICATION (MEDIUM RISK)" in content
    assert "RUNTIME TOKEN BUDGET ENFORCEMENT" in content
