"""Output Guardrails: Groundedness Verification & Calibrated Refusal.

Track: Business Operations / Customer Support (Ola)
Verifies that generated responses are strictly grounded in policy or ticket facts.
Enforces calibrated refusal if ungrounded.
"""

from typing import Tuple
from rag.generate import FALLBACK_REFUSAL, CALIBRATED_THRESHOLD


def verify_groundedness(
    response_text: str,
    grounded_flag: bool,
    confidence: float,
    threshold: float = CALIBRATED_THRESHOLD,
) -> Tuple[str, bool]:
    """Inspects response for groundedness.

    If grounded_flag is False or confidence is below threshold, returns calibrated refusal.

    Returns:
        (sanitized_response, is_grounded)
    """
    if not grounded_flag or confidence < threshold or response_text == FALLBACK_REFUSAL:
        return FALLBACK_REFUSAL, False

    return response_text, True
