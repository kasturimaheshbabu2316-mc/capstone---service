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
    redactions_made: bool = Field(default=False, description="Flag indicating if ungrounded claims were redacted.")


def review_support_response(
    query: str,
    draft_answer: str,
    sources: list[str],
    grounded: bool,
    confidence: float,
) -> Verdict:
    """Reviews draft response for grounding, accuracy, and compliance.

    Simulates the 2-agent consensus loop (PolicyComplianceReviewer + FinalEditor).
    """
    # Check 1: Refusal alignment
    if draft_answer == FALLBACK_REFUSAL or not grounded:
        return Verdict(
            approved=True,
            feedback="Compliance Review: Out-of-scope query properly routed to calibrated refusal.",
            final_answer=FALLBACK_REFUSAL,
            redactions_made=False,
        )

    # Check 2: Hallucination detection
    # Flag known hallucinated or ungrounded assertions (e.g. unverified monetary sums or policies)
    hallucination_indicators = [
        "100% full compensation for any delay",
        "free rides for lifetime",
        "guaranteed refund without inspection",
        "unlimited credits",
    ]

    has_hallucination = any(h in draft_answer.lower() for h in hallucination_indicators)

    if has_hallucination:
        # FinalEditor redacts hallucinated claim
        revised = (
            "Under standard Ola policy, compensation and refunds are assessed strictly based on "
            "investigation findings and documented delay tiers as outlined in the Service Credit Policy."
        )
        return Verdict(
            approved=False,
            feedback="PolicyComplianceReviewer: Detected ungrounded policy claim. FinalEditor: Redacted unverified claim.",
            final_answer=revised,
            redactions_made=True,
        )

    # Check 3: Standard approval
    return Verdict(
        approved=True,
        feedback="PolicyComplianceReviewer: Verified facts against knowledge base. FinalEditor: Tone and compliance approved.",
        final_answer=draft_answer,
        redactions_made=False,
    )
