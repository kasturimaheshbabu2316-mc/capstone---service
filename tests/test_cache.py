"""Unit tests for semantic response cache (Task 16).

Track: Business Operations / Customer Support (Ola)
Verifies:
1. Normalized query key matching (lowercase, trimmed, collapsed whitespace).
2. Hit, miss, and generation call telemetry counters.
3. Cache invalidation on clear().
4. Verification that transcripts/16_cache.txt is generated and populated.
"""

from pathlib import Path
import pytest
from cache import ResponseCache, response_cache


def test_cache_set_and_get():
    c = ResponseCache()
    c.set("What is the SLA for Sev-1?", "Resolution is 4 hours.")

    # Exact match
    res = c.get("What is the SLA for Sev-1?")
    assert res == "Resolution is 4 hours."

    # Normalized match (different case, extra spaces, punctuation)
    res_norm = c.get("  what is the sla for sev-1?  ")
    assert res_norm == "Resolution is 4 hours."


def test_cache_miss_and_stats():
    c = ResponseCache()
    assert c.get("Unknown question?") is None

    stats = c.get_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    c.set("Known question", "Known answer")
    assert c.get("Known question") == "Known answer"

    stats2 = c.get_stats()
    assert stats2["hits"] == 1
    assert stats2["misses"] == 1
    assert stats2["size"] == 1


def test_cache_get_or_compute_and_generation_counter():
    """Verifies that calling get_or_compute on the same query twice only increments generation call counter once."""
    c = ResponseCache()
    call_tracker = {"compute_invocations": 0}

    def sample_generation(q: str) -> str:
        call_tracker["compute_invocations"] += 1
        return f"Generated answer for {q}"

    query = "What are the operating hours?"

    # First call: Cache miss -> calls generation function
    res_1, hit_1 = c.get_or_compute(query, sample_generation)
    assert hit_1 is False
    assert call_tracker["compute_invocations"] == 1
    stats_1 = c.get_stats()
    assert stats_1["generation_calls"] == 1
    assert stats_1["misses"] == 1
    assert stats_1["hits"] == 0

    # Second call (with varied whitespace/casing): Cache hit -> does NOT call generation function
    query_variant = "   what   are   the OPERATING   hours?   "
    res_2, hit_2 = c.get_or_compute(query_variant, sample_generation)
    assert hit_2 is True
    assert res_2 == res_1
    assert call_tracker["compute_invocations"] == 1  # Unchanged
    stats_2 = c.get_stats()
    assert stats_2["generation_calls"] == 1  # Still 1
    assert stats_2["hits"] == 1
    assert stats_2["misses"] == 1


def test_cache_clear_invalidation():
    c = ResponseCache()
    c.set("Q1", "A1")
    c.set("Q2", "A2")

    cleared_count = c.clear()
    assert cleared_count == 2
    assert c.get("Q1") is None
    assert c.get_stats()["size"] == 0


def test_cache_transcript_file_exists():
    """Verifies transcripts/16_cache.txt exists and has valid demonstration trace."""
    transcript_path = Path(__file__).resolve().parent.parent / "transcripts" / "16_cache.txt"
    assert transcript_path.exists(), "transcripts/16_cache.txt must exist."
    content = transcript_path.read_text(encoding="utf-8")
    assert "RUN 1: INITIAL QUERY" in content
    assert "RUN 2: IDENTICAL QUERY WITH WHITESPACE & CASING VARIATION" in content
    assert "Generation Call Counter" in content
    assert "Latency Speedup" in content
