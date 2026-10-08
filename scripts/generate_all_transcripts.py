"""Master Transcript Generation Pipeline for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Generates verified transcripts for all 16 tasks:
- Task 01: task01_dataset.txt
- Task 03: task03_chunking.txt
- Task 04: task04_threshold.txt
- Task 05: task05_chunking_comparison.txt
- Task 06: task06_ticket_tool.txt
- Task 07: task07_crew_kickoff.txt
- Task 08: task08_memory_session_a.txt & task08_memory_session_b.txt
- Task 09: task09_structured_output.txt
- Task 10: task10_guardrails.txt
- Task 11: task11_websocket.txt
- Task 12: task12_logging.txt
- Task 13: task13_eval.txt
- Task 14: task14_autogen_review.txt
- Task 15: task15_least_autonomy.txt
- Task 16: task16_cache.txt
"""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts import (
    run_task01,
    run_task03,
    run_task04,
    run_task05,
    run_task06,
    run_task07,
    run_task08,
    run_task09,
    run_task10,
    run_task11,
    run_task12,
    run_task13,
    run_task14,
    run_task15,
    run_task16,
)


def generate_all():
    print("=" * 80)
    print("REGENERATING ALL 16 TRANSCRIPTS FOR OLA DOMAIN SUPPORT AGENT")
    print("=" * 80)

    run_task01.run()
    run_task03.run()
    run_task04.run()
    run_task05.run()
    run_task06.run()
    run_task07.run()
    run_task08.run()
    run_task09.run()
    run_task10.run()
    run_task11.run()
    run_task12.run()
    run_task13.run()
    run_task14.run()
    run_task15.run()
    run_task16.run()

    print("\n" + "=" * 80)
    print("ALL 16 TASK TRANSCRIPTS SUCCESSFULLY GENERATED & VERIFIED!")
    print("=" * 80)


if __name__ == "__main__":
    generate_all()
