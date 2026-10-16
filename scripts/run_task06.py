"""Task 06 Runner: Ticket Status Tool & Escalation Risk Scoring."""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.ticket_tool import generate_report

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
FILE_06 = os.path.join(TRANSCRIPTS_DIR, "06_ticket_tool.txt")
FILE_TASK06 = os.path.join(TRANSCRIPTS_DIR, "task06_ticket_tool.txt")


def run():
    print("Executing Task 06: Ticket Status Tool and Escalation Formula Evaluation...")
    output = generate_report()
    print(output)

    for path in (FILE_06, FILE_TASK06):
        with open(path, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Transcript written to: {path}")


if __name__ == "__main__":
    run()
