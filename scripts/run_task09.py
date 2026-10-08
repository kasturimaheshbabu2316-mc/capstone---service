"""Task 09 Runner: Structured Pydantic Output Schema Validation."""

import os
import sys
import json

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crew.crew import run_support_crew
from crew.schema import SupportResponse

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILE = os.path.join(TRANSCRIPTS_DIR, "task09_structured_output.txt")


def run():
    print("Executing Task 09: Structured Pydantic Output Validation...")
    structured_res = run_support_crew(
        query="What is the SLA for a Sev-1 safety incident?",
        session_id="task09_pydantic_session",
        structured=True,
    )

    validated = SupportResponse.model_validate(structured_res)
    json_output = json.dumps(validated.model_dump(), indent=2)

    text = (
        "=" * 80 + "\n"
        "OLA DOMAIN SUPPORT AGENT — STRUCTURED PYDANTIC OUTPUT VALIDATION (TASK 9)\n"
        "=" * 80 + "\n\n"
        "--- PYDANTIC MODEL SCHEMA: SupportResponse ---\n"
        + json.dumps(SupportResponse.model_json_schema(), indent=2) + "\n\n"
        "--- VALIDATED CREW RESPONSE INSTANCE ---\n"
        f"{json_output}\n\n"
        "Validation Check: SupportResponse.model_validate(data) passed with 100% type safety.\n\n"
        "=" * 80 + "\n"
        "TASK 9 ACCEPTANCE CRITERIA: STRUCTURED PYDANTIC OUTPUT ENFORCED\n"
        "=" * 80 + "\n"
    )

    print(text)
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Transcript written to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    run()
