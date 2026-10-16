"""Executes the 15-query evaluation benchmark suite under MOCK LLM-as-judge (Task 13).

Track: Business Operations / Customer Support (Ola)
Runs all 15 benchmark queries through the CrewAI pipeline, evaluates each response
across Accuracy, Grounding, Completeness, and Safety, computes averages,
and outputs to transcripts/13_eval.txt and evaluation/results.json.
"""

from __future__ import annotations

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
from evaluation.judge import judge_response, JUDGE_PROMPT_TEMPLATE
from evaluation.test_queries import EVAL_BENCHMARK_QUERIES
from rag.index import retrieve

RESULTS_JSON_PATH = PROJECT_ROOT / "evaluation" / "results.json"
TRANSCRIPT_TXT_PATH = PROJECT_ROOT / "transcripts" / "13_eval.txt"


def run_benchmark_evaluation() -> Dict[str, Any]:
    """Runs all 15 benchmark queries through the support crew and evaluates them with MOCK LLM-as-judge."""
    TRANSCRIPT_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    evaluated_records = []
    print("Starting 15-Query Evaluation Benchmark...")

    for i, item in enumerate(EVAL_BENCHMARK_QUERIES, 1):
        q_id = item["id"]
        topic = item["topic"]
        query_text = item["query"]
        session_id = f"eval_sess_{q_id}"

        print(f"[{i:02d}/15] Evaluating {q_id} ({topic}): '{query_text[:45]}...'")

        # 1. Run through support crew
        crew_res = run_support_crew(query=query_text, session_id=session_id, structured=True)
        if not isinstance(crew_res, CrewResponse):
            crew_res = CrewResponse.model_validate(crew_res)

        # 2. Retrieve context chunks for groundedness evaluation if RAG route
        retrieved_texts: List[str] = []
        if crew_res.route in ("rag", "both"):
            try:
                chunks = retrieve(query_text, collection_name="kb_sentence", k=3)
                retrieved_texts = [c["text"] for c in chunks]
            except Exception:
                retrieved_texts = crew_res.sources

        # 3. Score with deterministic MOCK LLM-as-Judge
        eval_score = judge_response(
            query_record=item,
            response_text=crew_res.answer,
            retrieved_chunks=retrieved_texts,
        )

        record = {
            "id": q_id,
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

    # 4. Compute macro averages
    total_q = len(evaluated_records)
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

    # 5. Build ASCII Table
    table_lines = []
    header_sep = "+-----+----------------------------+----------+-----------+--------------+--------+---------+"
    table_lines.append(header_sep)
    table_lines.append(f"| {'ID':<3} | {'Topic':<26} | {'Accuracy':<8} | {'Grounding':<9} | {'Completeness':<12} | {'Safety':<6} | {'Overall':<7} |")
    table_lines.append(header_sep)

    for r in evaluated_records:
        s = r["scores"]
        table_lines.append(
            f"| {r['id']:<3} | {r['topic'][:26]:<26} | {s['accuracy']:^8} | {s['grounding']:^9} | {s['completeness']:^12} | {s['safety']:^6} | {s['overall']:^7.2f} |"
        )

    table_lines.append(header_sep)
    table_lines.append(
        f"| {'MACRO AVERAGES':<32} | {averages['accuracy']:^8.2f} | {averages['grounding']:^9.2f} | {averages['completeness']:^12.2f} | {averages['safety']:^6.2f} | {averages['overall']:^7.2f} |"
    )
    table_lines.append(header_sep)

    table_text = "\n".join(table_lines)

    # 6. Format full report for transcripts/13_eval.txt
    report_lines = []
    report_lines.append("================================================================================")
    report_lines.append("STEP 11 / TASK 13 - EVALUATION BENCHMARK REPORT (15 QUERIES)")
    report_lines.append("================================================================================\n")
    report_lines.append("JUDGE PROMPT SPECIFICATION:")
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(JUDGE_PROMPT_TEMPLATE.strip())
    report_lines.append("\n--------------------------------------------------------------------------------")
    report_lines.append("EVALUATION RESULTS TABLE (1-5 Scale per Criterion):")
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(table_text)
    report_lines.append("\n--------------------------------------------------------------------------------")
    report_lines.append("DETAILED PER-QUERY EVALUATION TRACE:")
    report_lines.append("--------------------------------------------------------------------------------\n")

    for r in evaluated_records:
        report_lines.append(f"[{r['id']}] Topic: {r['topic']}")
        report_lines.append(f"Query:            {r['query']}")
        report_lines.append(f"Route:            {r['actual_route']} (Expected: {r['expected_route']})")
        report_lines.append(f"Reference Answer: {r['reference_answer']}")
        report_lines.append(f"Agent Response:   {r['agent_response']}")
        s = r["scores"]
        report_lines.append(f"Scores:           Accuracy={s['accuracy']}/5, Grounding={s['grounding']}/5, Completeness={s['completeness']}/5, Safety={s['safety']}/5 -> Overall={s['overall']:.2f}/5")
        report_lines.append(f"Reasoning:        {r['reasoning']['accuracy']}")
        report_lines.append(f"                  {r['reasoning']['grounding']}")
        report_lines.append(f"                  {r['reasoning']['completeness']}")
        report_lines.append(f"                  {r['reasoning']['safety']}")
        report_lines.append("-" * 80 + "\n")

    full_transcript = "\n".join(report_lines)

    # Save transcript
    with open(TRANSCRIPT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    # Save JSON results
    output_json_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_queries": total_q,
        "macro_averages": averages,
        "results": evaluated_records,
    }
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_json_data, f, indent=2)

    print("\n" + table_text)
    print(f"\nEvaluation transcript saved to: {TRANSCRIPT_TXT_PATH}")
    print(f"Results JSON saved to: {RESULTS_JSON_PATH}")

    return output_json_data


if __name__ == "__main__":
    run_benchmark_evaluation()
