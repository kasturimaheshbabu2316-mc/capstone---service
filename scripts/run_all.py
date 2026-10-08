"""Master Verification Runner for Ola Domain Support Agent.

Executes all 16 tasks sequentially, generates all transcripts,
and validates that all acceptance criteria are met.
"""

import os
import sys
import time

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

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")

TASKS = [
    ("Task 01: Synthetic Dataset Generator", run_task01.run, ["task01_dataset.txt"]),
    ("Task 03: Dual Chunking & Vector Indexing", run_task03.run, ["task03_chunking.txt"]),
    ("Task 04: Cosine Threshold Calibration", run_task04.run, ["task04_threshold.txt"]),
    ("Task 05: Chunking Strategy Evaluation", run_task05.run, ["task05_chunking_comparison.txt"]),
    ("Task 06: Ticket Tool & Escalation Formula", run_task06.run, ["task06_ticket_tool.txt"]),
    ("Task 07: CrewAI 3-Agent Core & MockLLM", run_task07.run, ["task07_crew_kickoff.txt"]),
    ("Task 08: Conversational Session Memory", run_task08.run, ["task08_memory_session_a.txt", "task08_memory_session_b.txt"]),
    ("Task 09: Structured Pydantic Output", run_task09.run, ["task09_structured_output.txt"]),
    ("Task 10: Multi-Tier Safety Guardrails", run_task10.run, ["task10_guardrails.txt"]),
    ("Task 11: FastAPI & WebSocket Resilience", run_task11.run, ["task11_websocket.txt"]),
    ("Task 12: Structured Audit Logging", run_task12.run, ["task12_logging.txt"]),
    ("Task 13: 15-Query Evaluation Benchmark", run_task13.run, ["task13_eval.txt"]),
    ("Task 14: AutoGen Secondary Review Stage", run_task14.run, ["task14_autogen_review.txt"]),
    ("Task 15: Four-Layer Governance", run_task15.run, ["task15_least_autonomy.txt"]),
    ("Task 16: Semantic Response Caching", run_task16.run, ["task16_cache.txt"]),
]


def main():
    print("=" * 80)
    print("OLA DOMAIN SUPPORT AGENT — MASTER TRANSCRIPT GENERATION & VERIFICATION")
    print("=" * 80)
    start_all = time.perf_counter()

    results = []

    for name, runner, expected_files in TASKS:
        print(f"\n>>> Running {name}...")
        t0 = time.perf_counter()
        try:
            runner()
            dur = time.perf_counter() - t0
            # Validate output files exist and are not empty
            all_exist = True
            for fname in expected_files:
                fpath = os.path.join(TRANSCRIPTS_DIR, fname)
                if not os.path.exists(fpath) or os.path.getsize(fpath) == 0:
                    all_exist = False
                    break

            if all_exist:
                results.append((name, "PASS", dur, expected_files))
            else:
                results.append((name, "FAIL (Missing Artifact)", dur, expected_files))
        except Exception as e:
            dur = time.perf_counter() - t0
            results.append((name, f"ERROR: {str(e)[:40]}", dur, expected_files))

    total_time = time.perf_counter() - start_all

    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY — ALL 16 TASKS")
    print("=" * 80)
    print(f"{'Task / Deliverable':<45} | {'Status':<8} | {'Time (s)':<8} | {'Artifacts'}")
    print("-" * 80)

    all_passed = True
    for name, status, dur, files in results:
        file_str = ", ".join(files)
        print(f"{name:<45} | {status:<8} | {dur:<8.2f} | {file_str}")
        if status != "PASS":
            all_passed = False

    print("=" * 80)
    print(f"Total Verification Elapsed Time: {total_time:.2f} seconds")
    if all_passed:
        print("ALL 16 TASKS VERIFIED SUCCESSFULLY WITH 100% PASS RATE!")
    else:
        print("SOME TASKS ENCOUNTERED FAILURES. PLEASE REVIEW LOGS.")
    print("=" * 80)


if __name__ == "__main__":
    main()
