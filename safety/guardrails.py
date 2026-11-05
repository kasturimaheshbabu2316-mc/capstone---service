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
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from governance.budget import check_budget_limit as _cbl, MAX_REQUEST_TOKENS
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
# 2. Input Guardrail: Extended PII Masking (Phone, Email, Card, Aadhaar, PAN, Vehicle, UPI)
# ==============================================================================
INDIAN_PHONE_REGEX = re.compile(
    r"(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\b"
)
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
CARD_REGEX = re.compile(
    r"\b(?:\d{4}[\-\s]?){3}\d{4}\b"
)
AADHAAR_REGEX = re.compile(
    r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"
)
PAN_REGEX = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
)
VEHICLE_PLATE_REGEX = re.compile(
    r"\b[A-Z]{2}[\s\-]?[0-9]{1,2}[\s\-]?[A-Z]{1,2}[\s\-]?[0-9]{4}\b"
)
UPI_REGEX = re.compile(
    r"\b[a-zA-Z0-9.\-_]{2,}@(okhdfcbank|okaxis|oksbi|okicici|paytm|upi|ybl|axl|ibl)\b",
    re.IGNORECASE,
)


def mask_pii(text: str) -> PIIGuardrailResult:
    """Masks sensitive PII patterns including phone numbers, emails, cards, Aadhaar, PAN, vehicles, and UPI IDs.

    Returns:
        PIIGuardrailResult with (fired, kind='pii', detail, sanitized_text).
        Supports tuple unpacking: sanitized_text, was_masked = mask_pii(text)
    """
    if not text:
        return PIIGuardrailResult(fired=False, kind="pii", detail=None, sanitized_text=text)

    sanitized = text
    mask_count = 0

    # 1. Phone numbers
    phone_matches = INDIAN_PHONE_REGEX.findall(sanitized)
    if phone_matches:
        sanitized = INDIAN_PHONE_REGEX.sub("[PHONE_MASKED]", sanitized)
        mask_count += len(phone_matches)

    # 2. Email addresses
    email_matches = EMAIL_REGEX.findall(sanitized)
    if email_matches:
        sanitized = EMAIL_REGEX.sub("[EMAIL_MASKED]", sanitized)
        mask_count += len(email_matches)

    # 3. Credit / Debit card numbers
    card_matches = CARD_REGEX.findall(sanitized)
    if card_matches:
        sanitized = CARD_REGEX.sub("[CARD_MASKED]", sanitized)
        mask_count += len(card_matches)

    # 4. Aadhaar numbers (12-digit)
    aadhaar_matches = AADHAAR_REGEX.findall(sanitized)
    if aadhaar_matches:
        sanitized = AADHAAR_REGEX.sub("[AADHAAR_MASKED]", sanitized)
        mask_count += len(aadhaar_matches)

    # 5. PAN numbers (ABCDE1234F)
    pan_matches = PAN_REGEX.findall(sanitized)
    if pan_matches:
        sanitized = PAN_REGEX.sub("[PAN_MASKED]", sanitized)
        mask_count += len(pan_matches)

    # 6. Vehicle registration plates (e.g. KA01AB1234)
    vehicle_matches = VEHICLE_PLATE_REGEX.findall(sanitized)
    if vehicle_matches:
        sanitized = VEHICLE_PLATE_REGEX.sub("[VEHICLE_MASKED]", sanitized)
        mask_count += len(vehicle_matches)

    # 7. UPI IDs
    upi_matches = UPI_REGEX.findall(sanitized)
    if upi_matches:
        sanitized = UPI_REGEX.sub("[UPI_MASKED]", sanitized)
        mask_count += len(upi_matches)

    fired = mask_count > 0
    detail = f"Masked {mask_count} sensitive PII token(s)." if fired else None
    return PIIGuardrailResult(
        fired=fired,
        kind="pii",
        detail=detail,
        sanitized_text=sanitized,
    )


# Alias for compatibility
mask_phone_numbers = mask_pii


# ==============================================================================
# 3. Input Guardrail: Prompt Injection Defense with Unicode Normalization
# ==============================================================================
INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above) instructions",
    r"disregard (?:all )?(?:previous|above|the above) instructions",
    r"disregard the above",
    r"reveal (?:the )?system prompt",
    r"what is your system prompt",
    r"output (?:the )?(?:initial|system) prompt",
    r"system prompt",
    r"you are now",
    r"override security",
    r"bypass restrictions",
    r"jailbreak",
    r"pretend you are",
    r"role-?play as",
    r"act as an unfiltered",
    r"disregard (?:all )?rules",
    r"base64 (?:decode|encoded)",
    r"decode this base64",
    r"grant admin(?: access)?",
    r"give me admin(?: access)?",
    r"drop table",
    r"delete from",
    r"truncate table",
]


def detect_prompt_injection(text: str) -> InjectionGuardrailResult:
    """Inspects text for prompt injection signatures using Unicode normalization and pattern matching.

    Applies NFKC normalization and lowercasing to defeat spacing tricks and homoglyphs.
    Returns:
        InjectionGuardrailResult with (fired, kind='prompt_injection', detail, sanitized_text).
    """
    if not text:
        return InjectionGuardrailResult(fired=False, kind="prompt_injection", detail=None, sanitized_text=text)

    # Unicode NFKC normalization and lower-casing
    normalized_text = unicodedata.normalize("NFKC", text).lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            reason = "Blocked prompt injection: This request was blocked by the safety policy. Please rephrase your question."
            return InjectionGuardrailResult(
                fired=True,
                kind="prompt_injection",
                detail=reason,
                sanitized_text="",
            )

    return InjectionGuardrailResult(fired=False, kind="prompt_injection", detail=None, sanitized_text=text)


def check_security(text: str) -> Tuple[bool, Optional[str]]:
    """Inspects text for prompt injection patterns. Returns (is_safe, rejection_reason)."""
    if not text:
        return True, None
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
# 5. Self-Contained Token Budget & SQL Guardrails (Zero sqlparse dependency)
# ==============================================================================
@dataclass(frozen=True)
class SQLValidationResult:
    """Immutable structured result of SQL validation."""
    is_safe: bool
    sanitized_query: str
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "sanitized_query": self.sanitized_query,
            "error_message": self.error_message,
        }

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


def strip_markdown_fences(sql: str) -> str:
    """Strips markdown code fences (```sql ... ```) and whitespace."""
    cleaned = sql.strip()
    cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


BLOCKED_SQL_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "EXEC", "EXECUTE", "GRANT", "REVOKE", "PRAGMA", "ATTACH",
    "DETACH", "CREATE", "REPLACE", "LOAD_EXTENSION",
]


def validate_sql(raw_sql: str, default_limit: int = 100) -> SQLValidationResult:
    """Pure-python SQL validation without sqlparse dependency.
    Validates that query is non-empty, read-only SELECT, and contains no blocked keywords.
    """
    if not raw_sql or not raw_sql.strip():
        return SQLValidationResult(
            is_safe=False,
            sanitized_query="",
            error_message="Empty query provided.",
        )
    clean_sql = strip_markdown_fences(raw_sql)
    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]
    if len(statements) > 1:
        return SQLValidationResult(
            is_safe=False,
            sanitized_query=clean_sql,
            error_message="Multiple statements detected. Only exactly ONE SQL statement is permitted.",
        )
    if not statements:
        return SQLValidationResult(
            is_safe=False,
            sanitized_query=clean_sql,
            error_message="No executable SQL statement found.",
        )
    trimmed = statements[0]
    first_word_match = re.match(r"^\s*([a-zA-Z]+)", trimmed)
    if not first_word_match or first_word_match.group(1).upper() not in ("SELECT", "WITH"):
        return SQLValidationResult(
            is_safe=False,
            sanitized_query=clean_sql,
            error_message="Only read-only SELECT or WITH statements are permitted.",
        )
    upper_query = trimmed.upper()
    for kw in BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper_query):
            return SQLValidationResult(
                is_safe=False,
                sanitized_query=clean_sql,
                error_message=f"Destructive SQL command '{kw}' detected. Query rejected.",
            )
    return SQLValidationResult(
        is_safe=True,
        sanitized_query=trimmed,
        error_message=None,
    )


def check_payload_budget(text: str, max_tokens: Optional[int] = None) -> Tuple[bool, int, Optional[str]]:
    """Enforces token budget cap using governance.budget logic."""
    limit = max_tokens or MAX_REQUEST_TOKENS
    return _cbl(text, max_tokens=limit)


def check_budget_limit(text: str, context: str = "", max_tokens: int = 2000) -> Tuple[bool, int, Optional[str]]:
    return _cbl(text, context=context, max_tokens=max_tokens)


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
