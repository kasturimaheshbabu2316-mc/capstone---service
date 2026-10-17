"""Safety and Multi-Tier Guardrails Module (Task 10).

Track: Business Operations / Customer Support (Ola)
Implements:
1. Input Guardrail: mask_pii() for fixed-format Indian phone numbers (+91 98765 43210, 9876543210, 98765-43210).
   Names, addresses, and payment details are acknowledged out of scope per specification.
2. Input Guardrail: detect_prompt_injection() with deterministic pattern signatures.
3. Output Guardrail: check_groundedness() enforcing calibrated similarity threshold (0.3652)
   and content-overlap verification, returning calibrated refusal if ungrounded.
4. GuardrailResult dataclass: {fired, kind, detail, sanitized_text}.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from rag.generate import CALIBRATED_THRESHOLD, FALLBACK_REFUSAL


# ==============================================================================
# 1. GuardrailResult Dataclass
# ==============================================================================
@dataclass
class GuardrailResult:
    """Standardized guardrail outcome result.

    Attributes:
        fired: Boolean flag indicating if the guardrail triggered (blocked or masked).
        kind: Type of guardrail ('pii', 'prompt_injection', 'groundedness', or 'none').
        detail: Explanatory diagnostic detail or rejection reason.
        sanitized_text: Sanitized text safe for downstream propagation or fallback refusal.
    """

    fired: bool
    kind: str
    detail: Optional[str]
    sanitized_text: str


class PIIGuardrailResult(GuardrailResult):
    """GuardrailResult for PII masking supporting tuple unpacking (sanitized_text, was_masked)."""

    def __iter__(self):
        yield self.sanitized_text
        yield self.fired


class InjectionGuardrailResult(GuardrailResult):
    """GuardrailResult for prompt injection supporting tuple unpacking (is_blocked, reason)."""

    def __iter__(self):
        yield self.fired
        yield self.detail


class GroundednessGuardrailResult(GuardrailResult):
    """GuardrailResult for groundedness verification supporting tuple unpacking (sanitized_text, is_grounded)."""

    def __iter__(self):
        yield self.sanitized_text
        yield (not self.fired)


# ==============================================================================
# 2. Input Guardrail: Indian Phone Number PII Masking
# ==============================================================================
# Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9
# Formats: +91 98765 43210, 9876543210, 98765-43210, +91-98765-43210, 09876543210
INDIAN_PHONE_REGEX = re.compile(
    r"(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\b"
)


def mask_pii(text: str) -> PIIGuardrailResult:
    """Masks fixed-format Indian phone numbers with [PHONE_MASKED].

    Scope Note: Names, street addresses, and payment details are acknowledged
    out of scope per project specification. Uses fabricated test numbers only.

    Returns:
        PIIGuardrailResult with (fired, kind='pii', detail, sanitized_text).
        Supports tuple unpacking: sanitized_text, was_masked = mask_pii(text)
    """
    if not text:
        return PIIGuardrailResult(fired=False, kind="pii", detail=None, sanitized_text=text)

    matches = INDIAN_PHONE_REGEX.findall(text)
    if not matches:
        return PIIGuardrailResult(fired=False, kind="pii", detail=None, sanitized_text=text)

    sanitized = INDIAN_PHONE_REGEX.sub("[PHONE_MASKED]", text)
    return PIIGuardrailResult(
        fired=True,
        kind="pii",
        detail=f"Masked {len(matches)} Indian phone number(s).",
        sanitized_text=sanitized,
    )


# Alias for compatibility
mask_phone_numbers = mask_pii


# ==============================================================================
# 3. Input Guardrail: Prompt Injection Defense
# ==============================================================================
INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above) instructions",
    r"reveal (?:the )?system prompt",
    r"system prompt",
    r"you are now",
    r"override security",
    r"bypass restrictions",
    r"jailbreak",
    r"pretend you are",
    r"disregard (?:all )?rules",
    r"act as an unfiltered",
    r"drop table",
    r"delete from",
    r"truncate table",
]


def detect_prompt_injection(text: str) -> InjectionGuardrailResult:
    """Inspects text for prompt injection signatures using a deterministic pattern list.

    Returns:
        InjectionGuardrailResult with (fired, kind='prompt_injection', detail, sanitized_text).
        Supports tuple unpacking: is_blocked, reason = detect_prompt_injection(text)
    """
    if not text:
        return InjectionGuardrailResult(fired=False, kind="prompt_injection", detail=None, sanitized_text=text)

    lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            reason = "Blocked prompt injection: This request was blocked by the safety policy. Please rephrase your question."
            return InjectionGuardrailResult(
                fired=True,
                kind="prompt_injection",
                detail=reason,
                sanitized_text="",
            )

    return InjectionGuardrailResult(fired=False, kind="prompt_injection", detail=None, sanitized_text=text)


# Alias for compatibility
def check_security(text: str) -> Tuple[bool, Optional[str]]:
    res = detect_prompt_injection(text)
    return (not res.fired, res.detail)


def sanitize_and_validate_input(text: str) -> Tuple[str, bool, Optional[str]]:
    """Runs complete input guardrail pipeline: prompt injection check then PII masking."""
    inj_res = detect_prompt_injection(text)
    if inj_res.fired:
        return text, False, inj_res.detail

    pii_res = mask_pii(text)
    return pii_res.sanitized_text, True, None


# ==============================================================================
# 4. Output Guardrail: Groundedness & Content Overlap Verification
# ==============================================================================
STOPWORDS = {
    "what", "when", "where", "which", "how", "why", "who",
    "the", "and", "for", "are", "about", "with", "from", "does", "can",
    "tell", "give", "show", "please", "this", "that", "there", "have", "been",
}


def compute_content_overlap(query: str, context: str) -> int:
    """Computes keyword overlap between query terms and retrieved context."""
    query_tokens = set(re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", query.lower()))
    substantive_tokens = query_tokens - STOPWORDS
    if not substantive_tokens:
        return 0

    context_lower = context.lower()
    matches = sum(1 for token in substantive_tokens if token in context_lower)
    return matches


def check_groundedness(
    query: str,
    retrieved_context: str | list[str] | None = None,
    response_text: str = "",
    similarity: float = 0.0,
    threshold: float = CALIBRATED_THRESHOLD,
    grounded_flag: bool = True,
) -> GroundednessGuardrailResult:
    """Verifies that generated responses are supported by retrieved context.

    Reuses the calibrated similarity threshold (0.3652) plus a content-overlap check.
    Refuses with the exact calibrated fallback string if unsupported.

    Returns:
        GroundednessGuardrailResult with (fired, kind='groundedness', detail, sanitized_text).
        Supports tuple unpacking: sanitized_response, is_grounded = check_groundedness(...)
    """
    # Combine retrieved context chunks into single searchable string
    if isinstance(retrieved_context, list):
        context_str = " ".join(str(c) for c in retrieved_context)
    elif isinstance(retrieved_context, str):
        context_str = retrieved_context
    else:
        context_str = ""

    # Failure Mode 1: Generator already flagged ungrounded or produced fallback refusal
    if not grounded_flag or response_text == FALLBACK_REFUSAL:
        return GroundednessGuardrailResult(
            fired=True,
            kind="groundedness",
            detail=f"Generator flagged ungrounded or returned fallback refusal.",
            sanitized_text=FALLBACK_REFUSAL,
        )

    # Failure Mode 2: Similarity below calibrated threshold
    if similarity < threshold:
        return GroundednessGuardrailResult(
            fired=True,
            kind="groundedness",
            detail=f"Cosine similarity {similarity:.4f} below calibrated threshold {threshold:.4f}.",
            sanitized_text=FALLBACK_REFUSAL,
        )

    # Failure Mode 3: Content overlap check
    overlap_count = compute_content_overlap(query, context_str)
    if context_str and overlap_count == 0:
        return GroundednessGuardrailResult(
            fired=True,
            kind="groundedness",
            detail=f"Zero substantive query terms found in retrieved context.",
            sanitized_text=FALLBACK_REFUSAL,
        )

    return GroundednessGuardrailResult(
        fired=False,
        kind="groundedness",
        detail=None,
        sanitized_text=response_text,
    )


# Alias for backwards compatibility
def verify_groundedness(
    response_text: str,
    grounded_flag: bool,
    confidence: float,
    threshold: float = CALIBRATED_THRESHOLD,
) -> Tuple[str, bool]:
    """Inspects response for groundedness flag and threshold confidence."""
    if not grounded_flag or confidence < threshold or response_text == FALLBACK_REFUSAL:
        return FALLBACK_REFUSAL, False
    return response_text, True


# ==============================================================================
# 5. Re-exported SQL & Token Budget Guardrails
# ==============================================================================
from guardrails import (
    SQLValidationResult,
    strip_markdown_fences,
    validate_sql,
    check_payload_budget,
    check_budget_limit,
)

__all__ = [
    "GuardrailResult",
    "PIIGuardrailResult",
    "InjectionGuardrailResult",
    "GroundednessGuardrailResult",
    "mask_pii",
    "mask_phone_numbers",
    "detect_prompt_injection",
    "check_security",
    "sanitize_and_validate_input",
    "check_groundedness",
    "verify_groundedness",
    "compute_content_overlap",
    "SQLValidationResult",
    "strip_markdown_fences",
    "validate_sql",
    "check_payload_budget",
    "check_budget_limit",
]
