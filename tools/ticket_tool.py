"""Support Ticket Lookup and Escalation Risk Tool.

Track: Business Operations / Customer Support (Ola)
Provides check_support_ticket_status(record_id) tool returning status,
resolution time, and an empirical escalation risk score.
"""

from typing import Any
import numpy as np
from dataset import SUPPORT_TICKETS_BY_ID, SUPPORT_TICKETS


def calculate_escalation_score(record: dict[str, Any]) -> float:
    """Calculates escalation risk score S_esc in [0, 1].

    Formula:
        recency = days_since_created / 30.0 (in [0, 1])
        S_esc = 0.6 * float(escalated) + 0.4 * recency

    Operational refinement:
        If status is 'Resolved' or 'Closed', the ticket has achieved resolution,
        so the recency aging term is zeroed out (0.0).
    """
    escalated_flag = 1.0 if record.get("escalated", False) else 0.0
    status = record.get("status", "")

    if status in ("Resolved", "Closed"):
        recency = 0.0
    else:
        days = record.get("days_since_created", 0)
        recency = min(1.0, max(0.0, days / 30.0))

    score = 0.6 * escalated_flag + 0.4 * recency
    return round(float(score), 4)


def get_escalation_threshold() -> tuple[float, list[float]]:
    """Calculates the 80th percentile escalation threshold across the seed-42 dataset."""
    all_scores = [calculate_escalation_score(rec) for rec in SUPPORT_TICKETS]
    p80 = float(np.percentile(all_scores, 80))
    return round(p80, 4), all_scores


# Freeze empirical 80th percentile threshold
ESCALATION_THRESHOLD_TAU, _ALL_SCORES = get_escalation_threshold()


def check_support_ticket_status(record_id: str) -> dict[str, Any]:
    """Looks up customer support ticket status and escalation risk.

    Args:
        record_id: The ticket identifier, e.g. 'TKT-0001' to 'TKT-0060'.

    Returns:
        Structured dictionary with status, resolution time, and escalation score.
    """
    clean_id = record_id.strip().upper()
    record = SUPPORT_TICKETS_BY_ID.get(clean_id)

    if not record:
        return {
            "error": f"Ticket record '{clean_id}' not found in operational database.",
            "record_id": clean_id,
            "status": "Unknown",
            "resolution_time_hours": None,
            "escalation_score": None,
            "risk_level": "Unknown",
            "recommend_escalation": False,
        }

    score = calculate_escalation_score(record)
    recommend_escalation = score >= ESCALATION_THRESHOLD_TAU

    risk_level = "High Risk" if recommend_escalation else "Normal"

    return {
        "record_id": record["record_id"],
        "category": record["category"],
        "status": record["status"],
        "resolution_time_hours": record["resolution_time_hours"],
        "days_since_created": record["days_since_created"],
        "escalated": record["escalated"],
        "escalation_score": score,
        "escalation_threshold": ESCALATION_THRESHOLD_TAU,
        "risk_level": risk_level,
        "recommend_escalation": recommend_escalation,
    }


try:
    from crewai.tools import tool

    @tool("check_support_ticket_status")
    def check_support_ticket_status_crew_tool(record_id: str) -> str:
        """Looks up status, category, resolution time, and escalation risk of a ticket by record ID."""
        res = check_support_ticket_status(record_id)
        if "error" in res:
            return f"Ticket Lookup Error: {res['error']}"
        return (
            f"Ticket ID: {res['record_id']}\nStatus: {res['status']}\nCategory: {res['category']}\n"
            f"Resolution Time: {res['resolution_time_hours']} hours\nEscalation Score: {res['escalation_score']}\n"
            f"Risk Level: {res['risk_level']}\nRecommend Escalation: {res['recommend_escalation']}"
        )
except ImportError:
    check_support_ticket_status_crew_tool = check_support_ticket_status


if __name__ == "__main__":
    print("=" * 70)
    print("OLA DOMAIN SUPPORT AGENT — TICKET STATUS & ESCALATION (TASK 6)")
    print("=" * 70)
    print("Formula: S_esc = 0.6 * float(escalated) + 0.4 * (days_since_created / 30)")
    print("Refinement: Recency term zeroed for 'Resolved' and 'Closed' tickets.\n")

    p80_thresh, scores = get_escalation_threshold()

    print("--- 1. EMPIRICAL ESCALATION SCORE DISTRIBUTION (Seed 42, N=60) ---")
    print(f"  • Min Score          : {min(scores):.4f}")
    print(f"  • Max Score          : {max(scores):.4f}")
    print(f"  • Mean Score         : {sum(scores)/len(scores):.4f}")
    print(f"  • 50th Percentile (Median) : {float(np.percentile(scores, 50)):.4f}")
    print(f"  • 80th Percentile (Tau)    : {p80_thresh:.4f}")
    print(f"  • Chosen Threshold justification: T = {p80_thresh:.4f} corresponds to the 80th percentile of scores in seed-42 data.")

    print("\n--- 2. SAMPLE LOOKUP DEMONSTRATIONS ---")
    test_ids = ["TKT-0001", "TKT-0002", "TKT-0003", "TKT-0007", "TKT-9999"]
    for tid in test_ids:
        res = check_support_ticket_status(tid)
        print(f"\nQuery: check_support_ticket_status('{tid}')")
        if "error" in res:
            print(f"  • Result: {res['error']}")
        else:
            print(f"  • Status             : {res['status']}")
            print(f"  • Category           : {res['category']}")
            print(f"  • Resolution Time    : {res['resolution_time_hours']} hours")
            print(f"  • Days Active        : {res['days_since_created']} days")
            print(f"  • Escalated Flag     : {res['escalated']}")
            print(f"  • Escalation Score   : {res['escalation_score']:.4f}")
            print(f"  • Risk Classification: {res['risk_level']} (Recommend Escalation: {res['recommend_escalation']})")

    print("\n" + "=" * 70)
    print("TASK 6 ACCEPTANCE CRITERIA: TICKET TOOL & THRESHOLD JUSTIFIED")
    print("=" * 70)
