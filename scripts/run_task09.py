"""Task 09 Runner: Structured Pydantic Output Schema Validation."""

import os
import sys
import json
from pydantic import ValidationError

# Suppress telemetry prior to CrewAI imports
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crew.crew import run_support_crew
from crew.schemas import CrewResponse, validate_crew_response

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
FILE_09 = os.path.join(TRANSCRIPTS_DIR, "09_schema.txt")
FILE_TASK09 = os.path.join(TRANSCRIPTS_DIR, "task09_structured_output.txt")


def run():
    print("Executing Task 09: Structured CrewResponse Pydantic Validation...")

    # 1. RAG Policy Query Response Validation
    policy_res = run_support_crew(
        query="What is the SLA for a Sev-1 safety incident?",
        session_id="task09_policy_session",
        structured=True,
    )
    validated_policy = CrewResponse.model_validate(policy_res)

    # 2. Ticket Lookup Query Response Validation
    ticket_res = run_support_crew(
        query="Check status of TKT-0002",
        session_id="task09_ticket_session",
        structured=True,
    )
    validated_ticket = CrewResponse.model_validate(ticket_res)

    # 3. Validation Mismatch Demonstration (Negative Test)
    mismatch_caught = False
    mismatch_error_str = ""
    try:
        # Invalid route and missing required answer field
        invalid_payload = {
            "route": "invalid_engine_route",
            "sources": [],
            "grounded": True,
            "escalation_recommended": False,
        }
        CrewResponse.model_validate(invalid_payload)
    except (ValidationError, ValueError) as exc:
        mismatch_caught = True
        mismatch_error_str = str(exc)

    lines = [
        "=" * 80,
        "OLA DOMAIN SUPPORT AGENT — STRUCTURED CREWRESPONSE VALIDATION (TASK 9)",
        "=" * 80,
        "",
        "--- 1. PYDANTIC MODEL SCHEMA: CrewResponse ---",
        json.dumps(CrewResponse.model_json_schema(), indent=2),
        "",
        "--- 2. VALIDATED POLICY INSTANCE (route='rag') ---",
        json.dumps(validated_policy.model_dump(), indent=2),
        "",
        "--- 3. VALIDATED TICKET LOOKUP INSTANCE (route='lookup') ---",
        json.dumps(validated_ticket.model_dump(), indent=2),
        "",
        "--- 4. SCHEMA MISMATCH REJECTION TEST ---",
        f"Mismatch Caught Successfully : {mismatch_caught}",
        f"Validation Error Output      :\n{mismatch_error_str}",
        "",
        "=" * 80,
        "TASK 9 ACCEPTANCE CRITERIA: CREWRESPONSE ENFORCED & VALIDATED VIA model_validate",
        "=" * 80,
    ]

    output_text = "\n".join(lines)
    print(output_text)

    for path in (FILE_09, FILE_TASK09):
        with open(path, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
        print(f"Transcript written to: {path}")


if __name__ == "__main__":
    run()
