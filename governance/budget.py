"""Token Budget Enforcement & Runtime Governance Module (Task 15).

Track: Business Operations / Customer Support (Ola)
Enforces maximum input token budget cap (MAX_REQUEST_TOKENS = 2000).
Estimates tokens per request: (len(text) / 4 + retrieved context).
Rejects oversized payloads (HTTP 413) to protect inference pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple

MAX_REQUEST_TOKENS: int = 2000
MAX_TOKEN_BUDGET: int = MAX_REQUEST_TOKENS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT_PATH = PROJECT_ROOT / "transcripts" / "15_governance.txt"


def estimate_token_count(text: str, context: str = "") -> int:
    """Estimates token count per request: (len(text) + len(context)) // 4 heuristic."""
    total_chars = len(text) + len(context)
    return max(1, total_chars // 4)


def check_budget_limit(
    text: str,
    context: str = "",
    max_tokens: int = MAX_REQUEST_TOKENS,
) -> Tuple[bool, int, str | None]:
    """Checks whether the request payload conforms to MAX_REQUEST_TOKENS.

    Returns:
        (is_within_budget, estimated_tokens, error_message)
    """
    tokens = estimate_token_count(text, context)
    if tokens > max_tokens:
        err_msg = (
            f"Payload exceeds maximum token budget of {max_tokens} tokens "
            f"(estimated {tokens:,} tokens)."
        )
        return False, tokens, err_msg
    return True, tokens, None


def run_governance_demonstration() -> Dict[str, Any]:
    """Executes least autonomy, risk tier, and token budget demonstrations.

    Saves formatted output report to transcripts/15_governance.txt.
    """
    TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    from tools.ticket_tool import check_support_ticket_status, TOOL_PERMISSIONS

    lines: list[str] = []
    lines.append("================================================================================")
    lines.append("STEP 13 / TASK 15 - ENTERPRISE GOVERNANCE DEMONSTRATION TRANSCRIPT")
    lines.append("================================================================================")
    lines.append("System: Ola Domain Support Agent")
    lines.append("Governance Pillars:")
    lines.append("  1. Application Layer: Least Autonomy Tool Permissions Registry")
    lines.append("  2. System Layer: Enterprise Risk Classification (MEDIUM Risk)")
    lines.append("  3. Runtime Layer: Request Token Budget Enforcement (MAX_REQUEST_TOKENS = 2000)")
    lines.append("--------------------------------------------------------------------------------\n")

    # --------------------------------------------------------------------------
    # 1. Least Autonomy Tool Permissions Registry & Guard Demonstration
    # --------------------------------------------------------------------------
    lines.append("--------------------------------------------------------------------------------")
    lines.append("1. LEAST AUTONOMY TOOL PERMISSIONS REGISTRY")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Explicit Permissions Registry:\n  {TOOL_PERMISSIONS}\n")

    # Case A: Composer Agent attempts ticket lookup
    composer_blocked = False
    composer_err = ""
    try:
        check_support_ticket_status("TKT-0001", caller_role="Support Response Composer")
    except PermissionError as e:
        composer_blocked = True
        composer_err = str(e)

    lines.append("Demo 1A: Calling check_support_ticket_status as 'Support Response Composer' (or 'Composer Agent'):")
    lines.append(f"  • Authorization Result: {'BLOCKED (PermissionError raised)' if composer_blocked else 'UNEXPECTED SUCCESS'}")
    lines.append(f"  • Exception Message:    {composer_err}")

    # Case B: Retrieval Agent attempts ticket lookup
    retrieval_blocked = False
    retrieval_err = ""
    try:
        check_support_ticket_status("TKT-0001", caller_role="Policy Retrieval Specialist")
    except PermissionError as e:
        retrieval_blocked = True
        retrieval_err = str(e)

    lines.append("\nDemo 1B: Calling check_support_ticket_status as 'Policy Retrieval Specialist' (or 'Retrieval Agent'):")
    lines.append(f"  • Authorization Result: {'BLOCKED (PermissionError raised)' if retrieval_blocked else 'UNEXPECTED SUCCESS'}")
    lines.append(f"  • Exception Message:    {retrieval_err}")

    # Case C: Lookup Agent attempts ticket lookup
    lookup_success = False
    lookup_result: dict[str, Any] = {}
    try:
        lookup_result = check_support_ticket_status("TKT-0001", caller_role="Lookup Agent")
        lookup_success = True
    except Exception as e:
        lookup_success = False

    lines.append("\nDemo 1C: Calling check_support_ticket_status as 'Lookup Agent':")
    lines.append(f"  • Authorization Result: {'SUCCESS' if lookup_success else 'FAILED'}")
    lines.append(f"  • Returned Record ID:   {lookup_result.get('record_id')}")
    lines.append(f"  • Ticket Status:        {lookup_result.get('status')}")
    lines.append(f"  • Escalation Score:     {lookup_result.get('escalation_score')}")
    lines.append("\n" + "=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # 2. Risk Classification Summary
    # --------------------------------------------------------------------------
    lines.append("--------------------------------------------------------------------------------")
    lines.append("2. SYSTEM RISK CLASSIFICATION (MEDIUM RISK)")
    lines.append("--------------------------------------------------------------------------------")
    risk_summary = (
        "Under the enterprise AI Low / Medium / High governance taxonomy, this system is classified as "
        "MEDIUM Risk (Customer Support Tickets). Customer support operations interact directly with end "
        "passengers and driver partners, handling sensitive operational inquiries, private ticket identifiers, "
        "operational resolution timelines, and policy-governed escalation determinations. While the system does "
        "not possess autonomous financial execution authority (refund disbursements require human-in-the-loop "
        "sign-off) and tool permissions are strictly read-only, erroneous policy advice or flawed escalation "
        "assessments can cause direct customer frustration, financial disputes, and operational SLA breaches. "
        "To mitigate these risks, the application enforces least autonomy tool binding (only the Lookup Agent "
        "may execute ticket status queries), strict input/output PII phone masking ([PHONE_MASKED]), a 2,000-token "
        "request budget, deterministic multi-agent secondary consensus review under AutoGen, and cosine "
        "similarity-calibrated refusals on out-of-scope prompts."
    )
    lines.append(f"{risk_summary}\n")
    lines.append("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # 3. Token Budget Enforcement (Normal vs Oversized Request)
    # --------------------------------------------------------------------------
    lines.append("--------------------------------------------------------------------------------")
    lines.append("3. RUNTIME TOKEN BUDGET ENFORCEMENT (MAX_REQUEST_TOKENS = 2000)")
    lines.append("--------------------------------------------------------------------------------")

    normal_query = "What is the resolution SLA for a Sev-1 safety incident?"
    n_ok, n_tokens, n_err = check_budget_limit(normal_query)
    lines.append("Demo 3A: Normal In-Scope Request:")
    lines.append(f"  • Query:            '{normal_query}'")
    lines.append(f"  • Estimated Tokens: {n_tokens} / {MAX_REQUEST_TOKENS}")
    lines.append(f"  • Gate Outcome:     {'PASSED (Status 200 OK)' if n_ok else 'REJECTED'}")
    lines.append(f"  • Error Message:    {n_err}")

    oversized_query = "Ola operational support policy inquiry with repeated payload characters. " * 300
    o_ok, o_tokens, o_err = check_budget_limit(oversized_query)
    lines.append("\nDemo 3B: Deliberately Oversized Request:")
    lines.append(f"  • Query Length:     {len(oversized_query):,} characters")
    lines.append(f"  • Estimated Tokens: {o_tokens:,} / {MAX_REQUEST_TOKENS}")
    lines.append(f"  • Gate Outcome:     {'PASSED' if o_ok else 'REJECTED (HTTP 413 Payload Too Large)'}")
    lines.append(f"  • Error Message:    {o_err}")
    lines.append("\n" + "=" * 80 + "\n")

    report_text = "\n".join(lines)
    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Governance demonstration report saved to: {TRANSCRIPT_PATH}")
    return {
        "least_autonomy": {
            "composer_blocked": composer_blocked,
            "retrieval_blocked": retrieval_blocked,
            "lookup_success": lookup_success,
        },
        "budget": {
            "normal_passed": n_ok,
            "normal_tokens": n_tokens,
            "oversized_rejected": not o_ok,
            "oversized_tokens": o_tokens,
        },
    }


if __name__ == "__main__":
    run_governance_demonstration()
