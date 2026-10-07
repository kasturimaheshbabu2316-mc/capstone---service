"""Token Budget Enforcement Module.

Track: Business Operations / Customer Support (Ola)
Enforces maximum input token budget cap of 2,000 estimated tokens.
Rejects oversized payloads to prevent Denial of Service and budget exhaustion.
"""

MAX_TOKEN_BUDGET = 2000


def estimate_token_count(text: str) -> int:
    """Estimates token count using character/4 heuristic."""
    return max(1, len(text) // 4)


def check_budget_limit(text: str) -> tuple[bool, int, str | None]:
    """Checks whether text adheres to the 2,000 token budget limit.

    Returns:
        (is_within_budget, estimated_tokens, error_message)
    """
    tokens = estimate_token_count(text)
    if tokens > MAX_TOKEN_BUDGET:
        return (
            False,
            tokens,
            f"Payload exceeds maximum token budget of {MAX_TOKEN_BUDGET} tokens (estimated {tokens} tokens).",
        )
    return True, tokens, None
