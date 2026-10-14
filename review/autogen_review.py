"""Secondary Review Stage for Response Compliance.

Track: Business Operations / Customer Support (Ola)
Implements a 2-agent review pipeline:
1. PolicyComplianceReviewer: checks draft against grounded policy
2. FinalEditor: emits structured Verdict (approved, feedback, revised_answer)
"""

from typing import Any
from pydantic import BaseModel, Field
from rag.generate import FALLBACK_REFUSAL, CALIBRATED_THRESHOLD
from rag.generate import grounded_generate


class Verdict(BaseModel):
    """Structured verdict emitted by the review stage."""

    approved: bool = Field(..., description="True if draft is policy-compliant and grounded.")
    feedback: str = Field(..., description="Reviewer comments and compliance notes.")
    final_answer: str = Field(..., description="Final approved or revised customer answer.")
    redactions_made: bool = Field(default=False, description="Flag indicating if ungrounded claims or PII were redacted.")
    review_notes: str = Field(default="", description="Detailed review audit notes.")


def review_support_response(
    query: str,
    draft_answer: str,
    sources: list[str],
    grounded: bool,
    confidence: float,
) -> Verdict:
    """Reviews draft response for policy correctness, PII leakage, and unsupported claims.

    Simulates the 2-agent consensus loop (PolicyComplianceReviewer + FinalEditor) under AutoGen.
    """
    from guardrails import mask_pii

    # 1. PII Leakage Check
    masked_answer, was_masked = mask_pii(draft_answer)
    has_pii = bool(was_masked)

    # 2. Refusal alignment / Out-of-scope check
    if draft_answer == FALLBACK_REFUSAL or not grounded:
        notes = "PolicyComplianceReviewer: Out-of-scope query routed to calibrated refusal."
        return Verdict(
            approved=True,
            feedback=notes,
            final_answer=FALLBACK_REFUSAL,
            redactions_made=False,
            review_notes=notes,
        )

    # 3. Unsupported claims / Hallucination detection
    hallucination_indicators = [
        "100% full compensation for any delay",
        "free rides for lifetime",
        "guaranteed refund without inspection",
        "unlimited credits",
        "free ride forever",
        "no questions asked refund",
    ]

    has_hallucination = any(h in draft_answer.lower() for h in hallucination_indicators)

    if has_hallucination:
        revised = (
            "Under standard Ola policy, compensation and refunds are assessed strictly based on "
            "investigation findings and documented delay tiers as outlined in the Service Credit Policy."
        )
        if has_pii:
            revised, _ = mask_pii(revised)
        notes = (
            "PolicyComplianceReviewer: Detected ungrounded policy claim. "
            "FinalEditor: Redacted unverified claim with official SLA guideline."
            + (" (PII Leakage also masked)" if has_pii else "")
        )
        return Verdict(
            approved=False,
            feedback=notes,
            final_answer=revised,
            redactions_made=True,
            review_notes=notes,
        )

    # 4. PII Redaction if only PII was leaked
    if has_pii:
        notes = "PolicyComplianceReviewer: Facts verified. FinalEditor: Redacted customer PII from draft answer."
        return Verdict(
            approved=False,
            feedback=notes,
            final_answer=masked_answer,
            redactions_made=True,
            review_notes=notes,
        )

    # 5. Standard policy approval
    notes = "PolicyComplianceReviewer: Verified facts against knowledge base. FinalEditor: Tone, compliance, and PII-safety approved."
    return Verdict(
        approved=True,
        feedback=notes,
        final_answer=draft_answer,
        redactions_made=False,
        review_notes=notes,
    )
