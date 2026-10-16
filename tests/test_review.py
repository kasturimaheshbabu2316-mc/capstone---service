"""Unit tests for AutoGen secondary review stage (Task 14).

Track: Business Operations / Customer Support (Ola)
Verifies:
1. ReviewVerdict schema (approved, final_answer, reason) + legacy aliases.
2. Two AssistantAgents: Policy_Compliance_Reviewer and Final_Editor (output_content_type=ReviewVerdict).
3. RoundRobinGroupChat team setup (max_turns=2, custom_message_types=[StructuredMessage[ReviewVerdict]]).
4. Demo A: unchanged draft -> approved=True, same text.
5. Demo B: injected ungrounded claim -> approved=False, claim removed.
6. Pipeline integration: run_support_crew surfaces review_status in CrewResponse.
7. Verification that transcripts/14_review.txt is generated and populated.
"""

from pathlib import Path
import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat

from crew.crew import run_support_crew
from crew.schemas import CrewResponse
from rag.generate import FALLBACK_REFUSAL
from review.autogen_review import (
    ReviewVerdict,
    Verdict,
    build_review_team,
    review_support_response,
    run_autogen_review_sync,
    run_review_demos,
)


def test_review_verdict_schema():
    """Validates ReviewVerdict field constraints and compatibility aliasing."""
    v = ReviewVerdict(
        approved=True,
        final_answer="Standard resolution is 4 hours.",
        reason="Verified against knowledge base.",
    )
    assert v.approved is True
    assert v.final_answer == "Standard resolution is 4 hours."
    assert v.reason == "Verified against knowledge base."
    assert v.feedback == "Verified against knowledge base."
    assert v.redactions_made is False

    # Backwards compatibility alias
    assert issubclass(Verdict, ReviewVerdict) or Verdict is ReviewVerdict


def test_autogen_team_structure():
    """Verifies that the review team instantiates 2 AssistantAgents in a RoundRobinGroupChat."""
    team = build_review_team()
    assert isinstance(team, RoundRobinGroupChat)
    assert len(team._participants) == 2

    reviewer = team._participants[0]
    editor = team._participants[1]
    assert isinstance(reviewer, AssistantAgent)
    assert isinstance(editor, AssistantAgent)
    assert reviewer.name == "Policy_Compliance_Reviewer"
    assert editor.name == "Final_Editor"
    assert editor._output_content_type is ReviewVerdict
    assert team._max_turns == 2


def test_demo_a_unchanged_faithful_draft():
    """Demo A: A faithful grounded draft is approved as-is with identical text."""
    context = "Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours."
    draft = "Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours."

    verdict, msgs = run_autogen_review_sync(draft, context)
    assert verdict.approved is True
    assert verdict.final_answer == draft
    assert verdict.redactions_made is False
    assert "Verified facts against knowledge base" in verdict.reason
    assert len(msgs) == 3  # task, reviewer, editor


def test_demo_b_injected_ungrounded_claim():
    """Demo B: Draft with deliberately injected ungrounded claim is rejected and redacted."""
    context = "Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours."
    draft = "Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. In addition, refunds are instant for all riders."

    verdict, msgs = run_autogen_review_sync(draft, context)
    assert verdict.approved is False
    assert "refunds are instant for all riders" not in verdict.final_answer
    assert "Sev-1 safety incidents require" in verdict.final_answer
    assert verdict.redactions_made is True
    assert "flagged ungrounded claims" in verdict.reason.lower()


def test_review_approves_faithful_response():
    """Verifies standard pipeline interface approves faithful draft."""
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


def test_review_revises_hallucinated_claims():
    """Verifies standard pipeline interface redacts unsupported compensation claim."""
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


def test_review_handles_refusal_unaffected():
    """Verifies that calibrated fallback refusals pass through unaffected."""
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


def test_pipeline_integration_surfaces_review_status():
    """Verifies that run_support_crew wires review stage and surfaces review_status in CrewResponse."""
    res = run_support_crew("What is the resolution SLA for a Sev-1 safety incident?", structured=True)
    assert isinstance(res, CrewResponse)
    assert res.review_status is not None
    assert "approved" in res.review_status
    assert "final_answer" in res.review_status
    assert "reason" in res.review_status
    assert res.review_status["approved"] is True


def test_transcript_file_exists():
    """Verifies transcripts/14_review.txt is present and contains Demo A & Demo B traces."""
    transcript_path = Path(__file__).resolve().parent.parent / "transcripts" / "14_review.txt"
    assert transcript_path.exists(), "transcripts/14_review.txt must exist."
    content = transcript_path.read_text(encoding="utf-8")
    assert "DEMO A: UNCHANGED FAITHFUL DRAFT" in content
    assert "DEMO B: DRAFT WITH INJECTED UNGROUNDED CLAIM" in content
    assert "RoundRobinGroupChat" in content
    assert "ReviewVerdict" in content
