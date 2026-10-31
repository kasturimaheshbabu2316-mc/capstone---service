"""Task 14 Runner: AutoGen Multi-Agent Secondary Review Stage."""

import os
import sys

# Ensure root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from review.autogen_review import run_review_demos

TRANSCRIPTS_DIR = os.path.join(PROJECT_ROOT, "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def run():
    print("Executing Task 14: AutoGen Multi-Agent Secondary Review Stage...")
    run_review_demos()
    txt_path = os.path.join(TRANSCRIPTS_DIR, "14_review.txt")
    task_path = os.path.join(TRANSCRIPTS_DIR, "task14_autogen_review.txt")
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    run()
