"""Task 02 Runner: Knowledge Base Validation & Transcript Generation."""

import os
import sys

# Ensure root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from kb_loader import load_kb, count_sentences, validate_kb

TRANSCRIPTS_DIR = os.path.join(PROJECT_ROOT, "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILES = [
    os.path.join(TRANSCRIPTS_DIR, "02_kb.txt"),
    os.path.join(TRANSCRIPTS_DIR, "task02_kb.txt"),
]


def run():
    print("Executing Task 02: Validating Knowledge Base...")
    kb_dir = os.path.join(PROJECT_ROOT, "kb")
    docs = sorted(load_kb(kb_dir), key=lambda d: d["doc_id"])

    lines = [
        "=" * 70,
        "OLA SUPPORT KNOWLEDGE BASE — SUMMARY & VALIDATION",
        "=" * 70,
        f"Total documents loaded: {len(docs)}",
        "-" * 70,
        f"{'Doc ID':<30} | {'Sentences':<9} | {'Title'}",
        "-" * 70,
    ]

    for d in docs:
        sc = count_sentences(d["text"])
        lines.append(f"{d['doc_id']:<30} | {sc:<9} | {d['title']}")

    lines.append("-" * 70)
    summary = validate_kb(kb_dir)
    passed_str = "PASSED" if summary["passed"] else "FAILED"
    lines.append(f"Validation Result: {passed_str}")
    lines.append("=" * 70)

    output = "\n".join(lines) + "\n"
    print(output)

    for tf in TRANSCRIPT_FILES:
        with open(tf, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Transcript written to: {tf}")


if __name__ == "__main__":
    run()

