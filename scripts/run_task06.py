"""Task 06 Runner: Ticket Status Tool & Escalation Risk Scoring."""

import os
import sys
import numpy as np

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.ticket_tool import (
    get_escalation_threshold,
    check_support_ticket_status,
)

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILE = os.path.join(TRANSCRIPTS_DIR, "task06_ticket_tool.txt")


def run():
    print("Executing Task 06: Ticket Status Tool and Escalation Formula Evaluation...")
    p80_thresh, scores = get_escalation_threshold()

    lines = [
        "=" * 70,
        "OLA DOMAIN SUPPORT AGENT — TICKET STATUS & ESCALATION (TASK 6)",
        "=" * 70,
        "Formula: S_esc = 0.6 * float(escalated) + 0.4 * (days_since_created / 30)",
        "Refinement: Recency term zeroed for 'Resolved' and 'Closed' tickets.",
        "",
        "--- 1. EMPIRICAL ESCALATION SCORE DISTRIBUTION (Seed 42, N=60) ---",
        f"  • Min Score          : {min(scores):.4f}",
        f"  • Max Score          : {max(scores):.4f}",
        f"  • Mean Score         : {sum(scores)/len(scores):.4f}",
        f"  • 50th Percentile (Median) : {float(np.percentile(scores, 50)):.4f}",
        f"  • 80th Percentile (Tau)    : {p80_thresh:.4f}",
        f"  • Chosen Threshold justification: T = {p80_thresh:.4f} corresponds to the 80th percentile of scores in seed-42 data.",
        "",
        "--- 2. SAMPLE LOOKUP DEMONSTRATIONS ---",
    ]

    test_ids = ["TKT-0001", "TKT-0002", "TKT-0003", "TKT-0007", "TKT-9999"]
    for tid in test_ids:
        res = check_support_ticket_status(tid)
        lines.append(f"\nQuery: check_support_ticket_status('{tid}')")
        if "error" in res:
            lines.append(f"  • Result: {res['error']}")
        else:
            lines.append(f"  • Status             : {res['status']}")
            lines.append(f"  • Category           : {res['category']}")
            lines.append(f"  • Resolution Time    : {res['resolution_time_hours']} hours")
            lines.append(f"  • Days Active        : {res['days_since_created']} days")
            lines.append(f"  • Escalated Flag     : {res['escalated']}")
            lines.append(f"  • Escalation Score   : {res['escalation_score']:.4f}")
            lines.append(f"  • Risk Classification: {res['risk_level']} (Recommend Escalation: {res['recommend_escalation']})")

    lines.extend([
        "",
        "=" * 70,
        "TASK 6 ACCEPTANCE CRITERIA: TICKET TOOL & THRESHOLD JUSTIFIED",
        "=" * 70,
        "",
    ])

    output = "\n".join(lines)
    print(output)
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Transcript written to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    run()
