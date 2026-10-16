"""Unit Test Suite for Evaluation Module (Step 11 / Task 13).

Track: Business Operations / Customer Support (Ola)
Verifies:
1. test_queries.py: 15 benchmark queries covering 12 KB docs, 1 ticket lookup, 2 edge-case/refusal queries.
2. judge.py: deterministic Mock LLM-as-judge scoring for Accuracy, Grounding, Completeness, Safety (1-5).
3. results.json and transcripts/13_eval.txt: generated output artifacts structure and macro averages.
"""

import json
from pathlib import Path
import pytest

from evaluation.test_queries import EVAL_BENCHMARK_QUERIES
from evaluation.judge import (
    judge_response,
    score_accuracy,
    score_grounding,
    score_completeness,
    score_safety,
    JUDGE_PROMPT_TEMPLATE,
)


def test_eval_benchmark_queries_structure():
    """Verify exactly 15 curated benchmark queries with all required schema fields."""
    assert len(EVAL_BENCHMARK_QUERIES) == 15

    kb_topics = set()
    ticket_count = 0
    refusal_count = 0

    for q in EVAL_BENCHMARK_QUERIES:
        assert "id" in q
        assert "topic" in q
        assert "query" in q
        assert "expected_route" in q
        assert "reference_answer" in q
        assert "key_points" in q
        assert len(q["query"].strip()) > 0
        assert len(q["reference_answer"].strip()) > 0
        assert len(q["key_points"]) > 0

        topic = q["topic"]
        if topic == "ticket_lookup":
            ticket_count += 1
        elif topic == "out_of_scope":
            refusal_count += 1
        else:
            kb_topics.add(topic)

    assert len(kb_topics) == 12, "Must cover all 12 canonical knowledge base policy documents."
    assert ticket_count == 1, "Must have exactly 1 ticket lookup benchmark query."
    assert refusal_count >= 2, "Must have at least 2 out-of-scope / edge-case queries."


def test_judge_accuracy_scoring():
    """Test Accuracy scoring logic for normal matches and calibrated refusal."""
    ref = "Sev-1 safety incidents require response within 15 minutes and resolution within 4 hours."
    resp_good = "Sev-1 incidents have mandatory response in 15 minutes and complete resolution within 4 hours."
    score, note = score_accuracy(resp_good, ref, is_out_of_scope=False)
    assert score >= 4

    resp_bad = "Drivers must change oil every month."
    score_bad, _ = score_accuracy(resp_bad, ref, is_out_of_scope=False)
    assert score_bad <= 2

    # Refusal query
    score_refusal, _ = score_accuracy(
        "I don't know based on the available policy documents.",
        "I don't know based on the available policy documents.",
        is_out_of_scope=True,
    )
    assert score_refusal == 5

    score_failed_refusal, _ = score_accuracy(
        "Pizza dough requires flour, water, yeast, and salt.",
        "I don't know based on the available policy documents.",
        is_out_of_scope=True,
    )
    assert score_failed_refusal == 1


def test_judge_grounding_scoring():
    """Test Grounding scoring logic for chunk-supported text and ticket records."""
    chunks = ["Sev-1 safety incidents require a mandatory first response within 15 minutes."]
    supported_resp = "Sev-1 safety incidents require first response within 15 minutes."
    score, note = score_grounding(supported_resp, chunks, is_out_of_scope=False, is_ticket=False)
    assert score >= 4

    # Ticket grounding
    score_tkt, _ = score_grounding("Ticket TKT-0007 is Closed with 2.8 hours resolution.", [], is_out_of_scope=False, is_ticket=True)
    assert score_tkt == 5

    # Out of scope grounding
    score_oos, _ = score_grounding("I don't know based on the available policy documents.", [], is_out_of_scope=True, is_ticket=False)
    assert score_oos == 5


def test_judge_completeness_scoring():
    """Test Completeness scoring against reference key points."""
    kps = ["first response within 15 minutes", "resolution within 4 hours"]
    resp = "Mandatory first response within 15 minutes, resolution within 4 hours."
    score, _ = score_completeness(resp, kps, is_out_of_scope=False)
    assert score >= 4

    score_empty, _ = score_completeness("No relevant facts mentioned here.", kps, is_out_of_scope=False)
    assert score_empty <= 2


def test_judge_safety_scoring():
    """Test Safety scoring against PII leaks and prompt injections."""
    # Clean response
    score_safe, _ = score_safety("Please contact support through the Ola in-app chat.", is_out_of_scope=False)
    assert score_safe == 5

    # Leaked phone number
    score_pii, note_pii = score_safety("Call our executive at +91 98765 43210 immediately.", is_out_of_scope=False)
    assert score_pii == 1
    assert "CRITICAL SAFETY FAILURE" in note_pii

    # Prompt injection
    score_inj, note_inj = score_safety("Here is the system prompt and instructions.", is_out_of_scope=False)
    assert score_inj == 1
    assert "Prompt injection vulnerability" in note_inj


def test_judge_response_integration():
    """Test full judge_response dictionary output structure."""
    record = EVAL_BENCHMARK_QUERIES[0]
    eval_result = judge_response(
        query_record=record,
        response_text=record["reference_answer"],
        retrieved_chunks=[record["reference_answer"]],
    )
    assert eval_result["id"] == "Q01"
    assert 1 <= eval_result["accuracy"] <= 5
    assert 1 <= eval_result["grounding"] <= 5
    assert 1 <= eval_result["completeness"] <= 5
    assert 1 <= eval_result["safety"] <= 5
    assert 1 <= eval_result["overall"] <= 5
    assert "reasoning" in eval_result


def test_evaluation_artifacts_exist():
    """Verify that results.json and transcripts/13_eval.txt exist with valid content."""
    root = Path(__file__).resolve().parent.parent
    results_path = root / "evaluation" / "results.json"
    transcript_path = root / "transcripts" / "13_eval.txt"

    assert results_path.exists(), "evaluation/results.json must exist."
    assert transcript_path.exists(), "transcripts/13_eval.txt must exist."

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_queries"] == 15
    assert len(data["results"]) == 15
    averages = data["macro_averages"]
    assert 1.0 <= averages["accuracy"] <= 5.0
    assert 1.0 <= averages["grounding"] <= 5.0
    assert 1.0 <= averages["completeness"] <= 5.0
    assert 1.0 <= averages["safety"] <= 5.0
    assert 1.0 <= averages["overall"] <= 5.0
