"""Unit tests for semantic response cache (Task 16)."""

import pytest
from cache import ResponseCache


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


def test_cache_clear_invalidation():
    c = ResponseCache()
    c.set("Q1", "A1")
    c.set("Q2", "A2")

    cleared_count = c.clear()
    assert cleared_count == 2
    assert c.get("Q1") is None
    assert c.get_stats()["size"] == 0
