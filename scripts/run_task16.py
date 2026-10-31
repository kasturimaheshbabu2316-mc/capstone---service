"""Task 16 Runner: Semantic Response Cache & Telemetry Tracking."""

import os
import sys

# Ensure root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cache import run_cache_demonstration

TRANSCRIPTS_DIR = os.path.join(PROJECT_ROOT, "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def run():
    print("Executing Task 16: Semantic Response Caching & Invalidation...")
    run_cache_demonstration()
    txt_path = os.path.join(TRANSCRIPTS_DIR, "16_cache.txt")
    task_path = os.path.join(TRANSCRIPTS_DIR, "task16_cache.txt")
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    run()
