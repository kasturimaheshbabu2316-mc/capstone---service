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


def test_session_isolation_and_policy_cache_hit():
    """Session A asks about TKT-0007, then 'what about its SLA?'; session B asks only
    'what about its SLA?' and must not receive A's answer; a repeated policy question
    produces a cache hit with generation counter unchanged.
    """
    from api.main import run_unified_pipeline
    from crew.memory import session_memory
    from cache import response_cache

    session_memory.clear()
    response_cache.clear()
    response_cache.reset_stats()

    # 1. Session A asks about TKT-0007
    resp_a1 = run_unified_pipeline(
        raw_question="What is the status of TKT-0007?",
        session_id="session_A_test",
    )
    assert resp_a1.ticket is not None
    assert resp_a1.ticket["record_id"] == "TKT-0007"

    # 2. Session A follow-up: "what about its SLA?" -> resolves to TKT-0007
    resp_a2 = run_unified_pipeline(
        raw_question="what about its SLA?",
        session_id="session_A_test",
    )
    assert "TKT-0007" in resp_a2.answer or (resp_a2.ticket and resp_a2.ticket.get("record_id") == "TKT-0007")

    # 3. Session B asks only "what about its SLA?" -> must NOT receive Session A's TKT-0007 answer
    resp_b1 = run_unified_pipeline(
        raw_question="what about its SLA?",
        session_id="session_B_test",
    )
    assert "TKT-0007" not in resp_b1.answer
    assert resp_b1.ticket is None or resp_b1.ticket.get("record_id") != "TKT-0007"

    # 4. Repeated policy question produces cache hit with generation counter unchanged
    policy_q = "What is the resolution SLA for a Sev-1 safety incident?"

    # First call: cache miss
    resp_p1 = run_unified_pipeline(
        raw_question=policy_q,
        session_id="session_P1",
    )
    assert resp_p1.cache_hit is False

    stats_mid = response_cache.get_stats()
    gen_before = stats_mid["generation_calls"]

    # Second call (same or different session for policy query): cache hit
    resp_p2 = run_unified_pipeline(
        raw_question=policy_q,
        session_id="session_P2",
    )
    assert resp_p2.cache_hit is True
    assert resp_p2.answer == resp_p1.answer
    gen_after = response_cache.get_stats()["generation_calls"]
    assert gen_after == gen_before  # Generation counter unchanged


def test_interaction_recorded_in_history_exactly_once():
    """Interaction recorded in history exactly once (2 messages: Human + AI)."""
    from crew.crew import run_support_crew
    from crew.memory import session_memory, get_session_history

    session_memory.clear("single_record_sess")
    res = run_support_crew("Check status of TKT-0007", session_id="single_record_sess")
    hist = get_session_history("single_record_sess")
    assert len(hist.messages) == 2


def test_session_memory_caps_and_lru():
    """Verifies per-session message cap and LRU session eviction."""
    from crew.memory import session_memory, get_session_history, MAX_MESSAGES_PER_SESSION, MAX_SESSIONS, SESSION_STORE

    session_memory.clear()

    # Message cap test
    sess = "cap_test_sess"
    for i in range(MAX_MESSAGES_PER_SESSION + 5):
        session_memory.record_interaction(sess, f"Q{i}", f"A{i}")
    hist = get_session_history(sess)
    assert len(hist.messages) <= MAX_MESSAGES_PER_SESSION

    # LRU eviction test
    session_memory.clear()
    for i in range(MAX_SESSIONS + 10):
        get_session_history(f"sess_{i}")
    assert len(SESSION_STORE) <= MAX_SESSIONS
    assert "sess_0" not in SESSION_STORE
    assert f"sess_{MAX_SESSIONS + 9}" in SESSION_STORE

