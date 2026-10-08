"""Unit tests for AutoGen secondary review stage (Task 14)."""

import pytest
from review.autogen_review import review_support_response, Verdict
from rag.generate import FALLBACK_REFUSAL


def test_review_approves_faithful_response():
    verdict = review_support_response(
        query="What is the SLA for Sev-1 incidents?",
        draft_answer="Sev-1 safety incidents require mandatory resolution within 4 hours.",
        sources=["sla_by_severity"],
        grounded=True,
        confidence=0.92,
    )
    assert verdict.approved is True
    assert verdict.redactions_made is False
    assert "Sev-1" in verdict.final_answer
    assert "Verified facts against knowledge base" in verdict.feedback


def test_review_revises_hallucinated_claims():
    verdict = review_support_response(
        query="What is the compensation for delay?",
        draft_answer="Ola provides 100% full compensation for any delay with unlimited credits.",
        sources=["service_credit_policy"],
        grounded=True,
        confidence=0.85,
    )
    assert verdict.approved is False
    assert verdict.redactions_made is True
    assert "100% full compensation" not in verdict.final_answer
    assert "unlimited credits" not in verdict.final_answer
    assert "Redacted unverified claim" in verdict.feedback


def test_review_handles_refusal_unaffected():
    verdict = review_support_response(
        query="Where to travel in Paris?",
        draft_answer=FALLBACK_REFUSAL,
        sources=[],
        grounded=False,
        confidence=0.15,
    )
    assert verdict.approved is True
    assert verdict.final_answer == FALLBACK_REFUSAL
    assert verdict.redactions_made is False
