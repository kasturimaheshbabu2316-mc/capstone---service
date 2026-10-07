"""Input Guardrails: PII Phone Masking & Prompt Injection Defense.

Track: Business Operations / Customer Support (Ola)
Masks Indian phone numbers with [PHONE_MASKED] and rejects prompt injection attempts.
"""

import re
from typing import Tuple

# Indian mobile phone numbers: 10 digits starting with 6, 7, 8, or 9, optional +91/0 prefix, optional hyphen/space
INDIAN_PHONE_REGEX = re.compile(
    r"(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b"
)

# Common prompt injection signatures
INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above) instructions",
    r"system prompt",
    r"you are now",
    r"override security",
    r"bypass restrictions",
    r"jailbreak",
    r"pretend you are",
    r"disregard (?:all )?rules",
    r"act as an unfiltered",
]


def mask_phone_numbers(text: str) -> Tuple[str, bool]:
    """Replaces any Indian phone numbers in the text with [PHONE_MASKED].

    Returns:
        (sanitized_text, was_masked)
    """
    matches = INDIAN_PHONE_REGEX.findall(text)
    if not matches:
        return text, False

    sanitized = INDIAN_PHONE_REGEX.sub("[PHONE_MASKED]", text)
    return sanitized, True


def detect_prompt_injection(text: str) -> Tuple[bool, str | None]:
    """Inspects text for prompt injection patterns.

    Returns:
        (is_injection, reason)
    """
    lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True, f"Blocked prompt injection pattern: '{pattern}'"
    return False, None


def sanitize_and_validate_input(text: str) -> Tuple[str, bool, str | None]:
    """Runs complete input guardrail pipeline.

    Returns:
        (sanitized_text, is_valid, rejection_reason)
    """
    is_inj, reason = detect_prompt_injection(text)
    if is_inj:
        return text, False, reason

    sanitized, _ = mask_phone_numbers(text)
    return sanitized, True, None
