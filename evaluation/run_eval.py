"""Comprehensive Evaluation Benchmark Suite & Evaluation Reporter (Task 13 + Extended Suite).

Track: Business Operations / Customer Support (Ola)
Supports:
- Canonical 15-query benchmark (for Task 13 compliance)
- Extended 50-query benchmark across all 5 operational categories:
  * Policy Inquiries (20 queries covering all 12 KB topics)
  * Ticket Lookups (10 queries: valid, invalid, missing)
  * Hybrid Inquiries (6 queries)
  * Out-of-Scope (8 queries testing calibrated refusal)
  * Adversarial & Guardrails (6 queries)
- Reports macro averages, per-category scores, refusal precision/recall, and groundedness rate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crew.crew import run_support_crew
from crew.schemas import CrewResponse
from evaluation.judge import JUDGE_NAME, JUDGE_PROMPT_TEMPLATE, judge_response
from evaluation.queries import EVAL_BENCHMARK_QUERIES
from evaluation.extended_queries import EXTENDED_EVAL_QUERIES_50
from rag.generate import FALLBACK_REFUSAL
from rag.index import retrieve

RESULTS_JSON_PATH = PROJECT_ROOT / "evaluation" / "results.json"
TRANSCRIPT_TXT_PATH = PROJECT_ROOT / "transcripts" / "13_eval.txt"
TRANSCRIPT_TASK_PATH = PROJECT_ROOT / "transcripts" / "task13_eval.txt"


def evaluate_query_list(
    query_list: List[Dict[str, Any]],
    use_llm_judge: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Runs a list of benchmark queries through the pipeline and scores them."""
    evaluated_records = []
    total_q = len(query_list)

    if verbose:
        print(f"Evaluating {total_q} queries using '{JUDGE_NAME}' (use_llm_judge={use_llm_judge})...")

    for i, item in enumerate(query_list, 1):
        q_id = item["id"]
        topic = item.get("topic", "policy")
        category = item.get("category", "policy")
        query_text = item["query"]
        session_id = f"eval_{q_id}"

        if verbose:
            print(f"[{i:02d}/{total_q}] ({category}/{topic}) '{query_text[:45]}...'")

        # 1. Run through support crew
        crew_res = run_support_crew(query=query_text, session_id=session_id, structured=True)
        if not isinstance(crew_res, CrewResponse):
            crew_res = CrewResponse.model_validate(crew_res)

        # 2. Retrieve context chunks for groundedness evaluation
        retrieved_texts: List[str] = []
        if crew_res.route in ("rag", "both"):
            try:
                chunks = retrieve(query_text, collection_name="kb_sentence", k=6)
                retrieved_texts = [c["text"] for c in chunks]
                if crew_res.sources:
                    from kb_loader import get_doc_by_id
                    for s in crew_res.sources:
                        doc_obj = get_doc_by_id(s)
                        if doc_obj and "text" in doc_obj:
                            retrieved_texts.append(doc_obj["text"])
            except Exception:
                retrieved_texts = crew_res.sources

        # 3. Score with judge
        eval_score = judge_response(
            query_record=item,
            response_text=crew_res.answer,
            retrieved_chunks=retrieved_texts,
            use_llm_judge=use_llm_judge,
        )

        record = {
            "id": q_id,
            "category": category,
            "topic": topic,
            "query": query_text,
            "expected_route": item["expected_route"],
            "actual_route": crew_res.route,
            "agent_response": crew_res.answer,
            "reference_answer": item["reference_answer"],
            "sources": crew_res.sources,
            "grounded_flag": crew_res.grounded,
            "scores": {
                "accuracy": eval_score["accuracy"],
                "grounding": eval_score["grounding"],
                "completeness": eval_score["completeness"],
                "safety": eval_score["safety"],
                "overall": eval_score["overall"],
            },
            "reasoning": eval_score["reasoning"],
        }
        evaluated_records.append(record)

    # 4. Macro averages
    avg_acc = sum(r["scores"]["accuracy"] for r in evaluated_records) / total_q
    avg_grd = sum(r["scores"]["grounding"] for r in evaluated_records) / total_q
    avg_cmp = sum(r["scores"]["completeness"] for r in evaluated_records) / total_q
    avg_sft = sum(r["scores"]["safety"] for r in evaluated_records) / total_q
    avg_ovr = sum(r["scores"]["overall"] for r in evaluated_records) / total_q

    averages = {
        "accuracy": round(avg_acc, 2),
        "grounding": round(avg_grd, 2),
        "completeness": round(avg_cmp, 2),
        "safety": round(avg_sft, 2),
        "overall": round(avg_ovr, 2),
    }

    # 5. Per-category scores
    categories = sorted(list(set(r.get("category", "policy") for r in evaluated_records)))
    per_category = {}
    for cat in categories:
        cat_records = [r for r in evaluated_records if r.get("category") == cat]
        cat_len = len(cat_records)
        if cat_len > 0:
            per_category[cat] = {
                "count": cat_len,
                "accuracy": round(sum(r["scores"]["accuracy"] for r in cat_records) / cat_len, 2),
                "grounding": round(sum(r["scores"]["grounding"] for r in cat_records) / cat_len, 2),
                "completeness": round(sum(r["scores"]["completeness"] for r in cat_records) / cat_len, 2),
                "safety": round(sum(r["scores"]["safety"] for r in cat_records) / cat_len, 2),
                "overall": round(sum(r["scores"]["overall"] for r in cat_records) / cat_len, 2),
            }

    # 6. Refusal Precision & Recall and Groundedness Rate
    expected_refusals = 0
    actual_refusals = 0
    correct_refusals = 0
    total_grounded_eligible = 0
    actual_grounded = 0

    for r in evaluated_records:
        resp = r["agent_response"].lower()
        is_refusal = (
            FALLBACK_REFUSAL.lower() in resp
            or "i don't know" in resp
            or "blocked" in resp
            or "safety policy" in resp
        )
        should_refuse = r["expected_route"] in ("out_of_scope", "blocked")

        if should_refuse:
            expected_refusals += 1
        if is_refusal:
            actual_refusals += 1
            if should_refuse:
                correct_refusals += 1

        if r["expected_route"] in ("rag", "both"):
            total_grounded_eligible += 1
            if r["grounded_flag"]:
                actual_grounded += 1

    refusal_precision = round(correct_refusals / max(actual_refusals, 1), 3)
    refusal_recall = round(correct_refusals / max(expected_refusals, 1), 3)
    groundedness_rate = round(actual_grounded / max(total_grounded_eligible, 1), 3)

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "judge_name": JUDGE_NAME,
        "total_queries": total_q,
        "macro_averages": averages,
        "per_category": per_category,
        "refusal_metrics": {
            "expected_refusals": expected_refusals,
            "actual_refusals": actual_refusals,
            "correct_refusals": correct_refusals,
            "precision": refusal_precision,
            "recall": refusal_recall,
        },
        "groundedness_rate": groundedness_rate,
        "results": evaluated_records,
    }


def run_benchmark_evaluation(use_llm_judge: bool = False, suite: str = "all") -> Dict[str, Any]:
    """Runs evaluation benchmark suite and saves results to results.json and transcripts."""
    TRANSCRIPT_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Run canonical 15 queries (for Task 13 compliance transcript)
    res_15 = evaluate_query_list(EVAL_BENCHMARK_QUERIES, use_llm_judge=use_llm_judge, verbose=False)

    # 2. Run extended 50 queries (for quality review)
    res_50 = evaluate_query_list(EXTENDED_EVAL_QUERIES_50, use_llm_judge=use_llm_judge, verbose=True)

    # Format 15-query transcript for Task 13 graduation criteria
    table_lines = [
        "+-----+----------------------------+----------+-----------+--------------+--------+---------+",
        f"| {'ID':<3} | {'Topic':<26} | {'Accuracy':<8} | {'Grounding':<9} | {'Completeness':<12} | {'Safety':<6} | {'Overall':<7} |",
        "+-----+----------------------------+----------+-----------+--------------+--------+---------+",
    ]
    for r in res_15["results"]:
        s = r["scores"]
        table_lines.append(
            f"| {r['id']:<3} | {r['topic'][:26]:<26} | {s['accuracy']:^8} | {s['grounding']:^9} | {s['completeness']:^12} | {s['safety']:^6} | {s['overall']:^7.2f} |"
        )
    table_lines.append("+-----+----------------------------+----------+-----------+--------------+--------+---------+")
    table_lines.append(
        f"| {'MACRO AVERAGES':<32} | {res_15['macro_averages']['accuracy']:^8.2f} | {res_15['macro_averages']['grounding']:^9.2f} | {res_15['macro_averages']['completeness']:^12.2f} | {res_15['macro_averages']['safety']:^6.2f} | {res_15['macro_averages']['overall']:^7.2f} |"
    )
    table_lines.append("+-----+----------------------------+----------+-----------+--------------+--------+---------+")
    table_text = "\n".join(table_lines)

    report_lines = [
        "================================================================================",
        "STEP 11 / TASK 13 - EVALUATION BENCHMARK REPORT (15 QUERIES)",
        "================================================================================\n",
        "EVALUATOR:",
        JUDGE_NAME,
        "\nJUDGE PROMPT SPECIFICATION:",
        "--------------------------------------------------------------------------------",
        JUDGE_PROMPT_TEMPLATE.strip(),
        "\n--------------------------------------------------------------------------------",
        "EVALUATION RESULTS TABLE (1-5 Scale per Criterion):",
        "--------------------------------------------------------------------------------",
        table_text,
        "\n--------------------------------------------------------------------------------",
        "DETAILED PER-QUERY EVALUATION TRACE:",
        "--------------------------------------------------------------------------------\n",
    ]
    for r in res_15["results"]:
        s = r["scores"]
        report_lines.append(f"[{r['id']}] Topic: {r['topic']}")
        report_lines.append(f"Query:            {r['query']}")
        report_lines.append(f"Route:            {r['actual_route']} (Expected: {r['expected_route']})")
        report_lines.append(f"Reference Answer: {r['reference_answer']}")
        report_lines.append(f"Agent Response:   {r['agent_response']}")
        report_lines.append(f"Scores:           Accuracy={s['accuracy']}/5, Grounding={s['grounding']}/5, Completeness={s['completeness']}/5, Safety={s['safety']}/5 -> Overall={s['overall']:.2f}/5")
        report_lines.append(f"Reasoning:        {r['reasoning']['accuracy']}")
        report_lines.append(f"                  {r['reasoning']['grounding']}")
        report_lines.append(f"                  {r['reasoning']['completeness']}")
        report_lines.append(f"                  {r['reasoning']['safety']}")
        report_lines.append("-" * 80 + "\n")

    full_transcript = "\n".join(report_lines)
    with open(TRANSCRIPT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(full_transcript)
    with open(TRANSCRIPT_TASK_PATH, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    # Master results.json preserves Task 13 15-query root contract and embeds extended 50-query suite
    combined_results = {
        "timestamp": res_50["timestamp"],
        "judge_name": JUDGE_NAME,
        "total_queries": res_15["total_queries"],
        "macro_averages": res_15["macro_averages"],
        "results": res_15["results"],
        "extended_evaluation_50": {
            "total_queries": res_50["total_queries"],
            "macro_averages": res_50["macro_averages"],
            "per_category": res_50["per_category"],
            "refusal_metrics": res_50["refusal_metrics"],
            "groundedness_rate": res_50["groundedness_rate"],
            "results": res_50["results"],
        },
    }

    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_results, f, indent=2)

    # Print summary console view
    print("\n" + "=" * 78)
    print("50-QUERY BENCHMARK SUMMARY (BY CATEGORY)")
    print("=" * 78)
    print(f"{'Category':<16} | {'Count':<5} | {'Accuracy':<8} | {'Grounding':<9} | {'Completeness':<12} | {'Safety':<6} | {'Overall':<7}")
    print("-" * 78)
    for cat, metrics in res_50["per_category"].items():
        print(f"{cat:<16} | {metrics['count']:<5} | {metrics['accuracy']:^8.2f} | {metrics['grounding']:^9.2f} | {metrics['completeness']:^12.2f} | {metrics['safety']:^6.2f} | {metrics['overall']:^7.2f}")
    print("-" * 78)
    print(f"{'OVERALL MACRO':<16} | {res_50['total_queries']:<5} | {res_50['macro_averages']['accuracy']:^8.2f} | {res_50['macro_averages']['grounding']:^9.2f} | {res_50['macro_averages']['completeness']:^12.2f} | {res_50['macro_averages']['safety']:^6.2f} | {res_50['macro_averages']['overall']:^7.2f}")
    print("=" * 78)
    print(f"Refusal Precision : {res_50['refusal_metrics']['precision']:.1%}")
    print(f"Refusal Recall    : {res_50['refusal_metrics']['recall']:.1%}")
    print(f"Groundedness Rate : {res_50['groundedness_rate']:.1%}")
    print(f"\nTranscripts saved to: transcripts/task13_eval.txt and 13_eval.txt")
    print(f"Master results saved to: evaluation/results.json")

    return combined_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ola Domain Support Evaluation Suite")
    parser.add_argument("--use-llm-judge", action="store_true", default=False, help="Enable optional LLM judge")
    parser.add_argument("--suite", choices=["15", "50", "all"], default="all", help="Evaluation suite to execute")
    args = parser.parse_args()
    run_benchmark_evaluation(use_llm_judge=args.use_llm_judge, suite=args.suite)
