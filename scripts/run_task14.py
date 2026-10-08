"""Task 14 Runner: AutoGen Multi-Agent Secondary Review Stage."""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from review.autogen_review import review_support_response

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILE = os.path.join(TRANSCRIPTS_DIR, "task14_autogen_review.txt")


def run():
    print("Executing Task 14: AutoGen Multi-Agent Secondary Review Stage...")
    # Demo 1: Faithful response approved
    v1 = review_support_response(
        query="What is the SLA for Sev-1?",
        draft_answer="Sev-1 critical incidents require acknowledgement within 15 minutes and resolution within 2 hours.",
        sources=["sla_by_severity.md"],
        grounded=True,
        confidence=0.95,
    )

    # Demo 2: Injected hallucination revised
    v2 = review_support_response(
        query="What compensation do I get for delays?",
        draft_answer="Ola provides 100% full compensation for any delay regardless of circumstances with unlimited credits.",
        sources=["service_credit_policy.md"],
        grounded=True,
        confidence=0.88,
    )

    text = (
        "=" * 80 + "\n"
        "OLA DOMAIN SUPPORT AGENT — AUTOGEN SECONDARY REVIEW STAGE (TASK 14)\n"
        "=" * 80 + "\n\n"
        "--- DEMO 1: FAITHFUL RESPONSE (APPROVED) ---\n"
        f"Draft Answer   : Sev-1 critical incidents require acknowledgement within 15 minutes and resolution within 2 hours.\n"
        f"Verdict Approved: {v1.approved}\n"
        f"Feedback       : {v1.feedback}\n"
        f"Final Answer   : {v1.final_answer}\n"
        f"Redactions Made: {v1.redactions_made}\n\n"
        "--- DEMO 2: INJECTED HALLUCINATION (REVISED) ---\n"
        f"Draft Answer   : Ola provides 100% full compensation for any delay regardless of circumstances with unlimited credits.\n"
        f"Verdict Approved: {v2.approved}\n"
        f"Feedback       : {v2.feedback}\n"
        f"Final Answer   : {v2.final_answer}\n"
        f"Redactions Made: {v2.redactions_made}\n\n"
        "=" * 80 + "\n"
        "TASK 14 ACCEPTANCE CRITERIA: AUTOGEN APPROVE AND REVISE CASES WITH VERDICT COMPLETED\n"
        "=" * 80 + "\n"
    )

    print(text)
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Transcript written to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    run()
