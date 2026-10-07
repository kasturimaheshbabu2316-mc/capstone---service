"""Evaluation Benchmark Runner for Ola Domain Support System (Task 13).

Track: Business Operations / Customer Support (Ola)
Runs 15 benchmark queries through the agent pipeline, scores them using
the deterministic mock judge across 4 metrics, formats a 15-row table,
and computes summary averages.
"""

import sys
import os
import json

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from eval.test_queries import BENCHMARK_QUERIES
from eval.judge import judge_response
from app.main import ask_endpoint
from app.models import AskRequest
from fastapi import HTTPException

TRANSCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts", "task13_eval.txt")


def run_benchmark():
    results = []
    print("=" * 80)
    print("OLA DOMAIN SUPPORT AGENT — 15-QUERY BENCHMARK EVALUATION (TASK 13)")
    print("=" * 80)

    for item in BENCHMARK_QUERIES:
        qid = item["id"]
        q = item["query"]
        cat = item["category"]

        try:
            req = AskRequest(query=q, session_id=f"eval_{qid}")
            resp = ask_endpoint(req)
            resp_dict = {
                "answer": resp.data.answer,
                "grounded": resp.data.grounded,
                "confidence": resp.data.confidence,
                "sources": resp.data.sources,
                "ticket_id": resp.data.ticket_id,
            }
        except HTTPException as e:
            resp_dict = {
                "answer": f"Blocked: {e.detail}",
                "grounded": False,
                "confidence": 0.0,
                "sources": [],
                "injection_blocked": e.status_code == 400,
            }

        scores = judge_response(item, resp_dict)
        results.append({
            "id": qid,
            "category": cat,
            "topic": item["topic"],
            "query": q,
            "answer": resp_dict["answer"],
            "accuracy": scores["accuracy"],
            "grounding": scores["grounding"],
            "completeness": scores["completeness"],
            "safety": scores["safety"],
        })

    # Summary averages
    avg_acc = sum(r["accuracy"] for r in results) / len(results)
    avg_grd = sum(r["grounding"] for r in results) / len(results)
    avg_cmp = sum(r["completeness"] for r in results) / len(results)
    avg_saf = sum(r["safety"] for r in results) / len(results)

    header = f"{'ID':<5} | {'Category':<12} | {'Topic':<24} | {'Acc':<5} | {'Grd':<5} | {'Cmp':<5} | {'Saf':<5}"
    separator = "-" * len(header)
    rows = [header, separator]

    for r in results:
        row = f"{r['id']:<5} | {r['category']:<12} | {r['topic'][:24]:<24} | {r['accuracy']:<5.1f} | {r['grounding']:<5.1f} | {r['completeness']:<5.1f} | {r['safety']:<5.1f}"
        rows.append(row)

    rows.append(separator)
    avg_row = f"{'AVG':<5} | {'SUMMARY':<12} | {'All 15 Benchmark Queries':<24} | {avg_acc:<5.2f} | {avg_grd:<5.2f} | {avg_cmp:<5.2f} | {avg_saf:<5.2f}"
    rows.append(avg_row)
    rows.append("=" * len(header))

    output_text = "\n".join(rows)
    print("\n" + output_text)

    # Detailed query-by-query log
    detail_lines = ["\n\n--- DETAILED QUERY-BY-QUERY BREAKDOWN ---"]
    for r in results:
        detail_lines.append(f"\n[{r['id']}] ({r['category']}) Query: {r['query']}")
        detail_lines.append(f"  • Answer: {r['answer']}")
        detail_lines.append(f"  • Scores: Accuracy={r['accuracy']:.1f}, Grounding={r['grounding']:.1f}, Completeness={r['completeness']:.1f}, Safety={r['safety']:.1f}")

    full_transcript = (
        "=" * 80 + "\n"
        "OLA DOMAIN SUPPORT AGENT — 15-QUERY BENCHMARK EVALUATION (TASK 13)\n"
        "=" * 80 + "\n\n"
        + output_text + "\n"
        + "\n".join(detail_lines) + "\n\n"
        "TASK 13 ACCEPTANCE CRITERIA: 15 QUERIES EVALUATED WITH 4 METRICS AND SUMMARY AVERAGES\n"
    )

    os.makedirs(os.path.dirname(TRANSCRIPT_PATH), exist_ok=True)
    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    print(f"\nSaved evaluation transcript to: {TRANSCRIPT_PATH}")


if __name__ == "__main__":
    run_benchmark()
