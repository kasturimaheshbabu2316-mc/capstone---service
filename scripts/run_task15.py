"""Task 15 Runner: Four-Layer Governance & Least Autonomy Enforcement."""

import os
import sys

# Ensure root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from governance.budget import run_governance_demonstration

TRANSCRIPTS_DIR = os.path.join(PROJECT_ROOT, "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def run():
    print("Executing Task 15: Governance, Least Autonomy, and Token Budgeting...")
    run_governance_demonstration()
    txt_path = os.path.join(TRANSCRIPTS_DIR, "15_governance.txt")
    task_path = os.path.join(TRANSCRIPTS_DIR, "task15_least_autonomy.txt")
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    run()
