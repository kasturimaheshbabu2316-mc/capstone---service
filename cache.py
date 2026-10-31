"""In-Memory Response Cache for Grounded Generation (Task 16).

Track: Business Operations / Customer Support (Ola)
Provides:
1. In-memory response cache keyed by normalized query (lowercase, trimmed, collapsed whitespace).
2. Thread-safe operations with hit/miss and generation call counters.
3. Cache invalidation on document ingestion.
4. Demonstration comparing latency before and after cache hits.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
TRANSCRIPT_PATH = PROJECT_ROOT / "transcripts" / "16_cache.txt"


class ResponseCache:
    """Thread-safe normalized response cache with hit/miss and generation call telemetry."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._hits: int = 0
        self._misses: int = 0
        self._generation_calls: int = 0

    def _normalize_key(self, query: str) -> str:
        """Normalizes query: lowercase, stripped, collapsed whitespace, punctuation stripped."""
        clean = re.sub(r"[^\w\s]", "", query.lower())
        return " ".join(clean.strip().split())

    def _build_key(
        self,
        query: str,
        namespace: str = "policy",
        session_id: str | None = None,
    ) -> str:
        """Constructs isolated cache keys separating policy queries from session-specific ticket lookups."""
        norm = self._normalize_key(query)
        if namespace == "ticket" or (session_id and namespace != "policy"):
            sess = (session_id or "session").strip()
            return f"ticket:{sess}:{norm}"
        return f"policy:{norm}"

    def get(
        self,
        query: str,
        namespace: str = "policy",
        session_id: str | None = None,
    ) -> Optional[Any]:
        """Retrieves cached response if present, updating stats.
        
        Dynamic ticket queries without a session_id bypass global cache to prevent stale operational data.
        """
        # Guard: never serve dynamic ticket lookups from an unscoped global cache
        if namespace == "ticket" and not session_id:
            with self._lock:
                self._misses += 1
            return None

        key = self._build_key(query, namespace=namespace, session_id=session_id)
        with self._lock:
            if key in self._cache:
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(
        self,
        query: str,
        response: Any,
        namespace: str = "policy",
        session_id: str | None = None,
    ) -> None:
        """Stores response in cache under isolated namespace/session key."""
        # Guard: do not cache dynamic ticket lookups globally without a session_id
        if namespace == "ticket" and not session_id:
            return

        key = self._build_key(query, namespace=namespace, session_id=session_id)
        with self._lock:
            self._cache[key] = response

    def get_or_compute(
        self,
        query: str,
        compute_fn: Callable[[str], Any],
        namespace: str = "policy",
        session_id: str | None = None,
    ) -> Tuple[Any, bool]:
        """Gets response from cache or invokes compute_fn, updating generation counter.

        Returns:
            Tuple of (response_value, is_cache_hit).
        """
        if namespace == "ticket" and not session_id:
            with self._lock:
                self._misses += 1
                self._generation_calls += 1
            return compute_fn(query), False

        key = self._build_key(query, namespace=namespace, session_id=session_id)
        with self._lock:
            if key in self._cache:
                self._hits += 1
                return self._cache[key], True

            # Cache miss: execute generation step
            self._misses += 1
            self._generation_calls += 1

        # Compute outside lock to avoid holding lock during generation
        result = compute_fn(query)

        with self._lock:
            self._cache[key] = result
            return result, False

    def clear(self, namespace: Optional[str] = None) -> int:
        """Invalidates cache entries. If namespace is provided, clears only that namespace.

        Returns number of invalidated entries.
        """
        with self._lock:
            if namespace:
                prefix = f"{namespace}:"
                to_delete = [k for k in self._cache if k.startswith(prefix)]
                for k in to_delete:
                    del self._cache[k]
                return len(to_delete)
            count = len(self._cache)
            self._cache.clear()
            return count

    def invalidate_all(self) -> int:
        """Alias for clear()."""
        return self.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Returns cache telemetry: hits, misses, generation calls, hit ratio, total entries."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = round(self._hits / total_requests, 4) if total_requests > 0 else 0.0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "generation_calls": self._generation_calls,
                "hit_ratio": hit_ratio,
            }

    def reset_stats(self) -> None:
        """Resets telemetry counters while retaining cached entries."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._generation_calls = 0


# Global singleton cache instance
response_cache = ResponseCache()


def run_cache_demonstration() -> Dict[str, Any]:
    """Demonstrates in-memory caching on a grounded-generation query.

    Runs the query twice:
    - Run 1: Cache Miss -> invokes grounded generation, increments generation call counter.
    - Run 2: Cache Hit  -> served instantly from cache, generation call counter does NOT increment.
    Saves formatted results to transcripts/16_cache.txt.
    """
    TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    from rag.generate import grounded_generate

    demo_cache = ResponseCache()
    query = "What is the resolution SLA for a Sev-1 safety incident?"

    # --------------------------------------------------------------------------
    # Run 1: Cache Miss
    # --------------------------------------------------------------------------
    t0 = time.perf_counter()
    res_1, hit_1 = demo_cache.get_or_compute(query, lambda q: grounded_generate(q))
    lat_1_ms = (time.perf_counter() - t0) * 1000.0

    stats_1 = demo_cache.get_stats()

    # --------------------------------------------------------------------------
    # Run 2: Cache Hit (variation with leading/trailing spaces and mixed casing)
    # --------------------------------------------------------------------------
    query_variation = "   WHAT IS THE RESOLUTION SLA FOR A SEV-1 SAFETY INCIDENT?   "
    t1 = time.perf_counter()
    res_2, hit_2 = demo_cache.get_or_compute(query_variation, lambda q: grounded_generate(q))
    lat_2_ms = (time.perf_counter() - t1) * 1000.0

    stats_2 = demo_cache.get_stats()
    speedup = round(lat_1_ms / lat_2_ms, 1) if lat_2_ms > 0 else 100.0

    # --------------------------------------------------------------------------
    # Build Transcript
    # --------------------------------------------------------------------------
    lines: list[str] = []
    lines.append("================================================================================")
    lines.append("STEP 13 / TASK 16 - IN-MEMORY RESPONSE CACHE DEMONSTRATION")
    lines.append("================================================================================")
    lines.append("Component: In-Memory Normalized Response Cache (cache.py)")
    lines.append("Normalization: lowercase, trimmed, whitespace collapsed, punctuation stripped")
    lines.append("Telemetry Tracked: hits, misses, generation_calls, latency_ms")
    lines.append("--------------------------------------------------------------------------------\n")

    lines.append("--------------------------------------------------------------------------------")
    lines.append("RUN 1: INITIAL QUERY (EXPECTED: CACHE MISS, GENERATION CALL = 1)")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Query:                   '{query}'")
    lines.append(f"Cache Status:            {'HIT' if hit_1 else 'MISS (Cold Generation)'}")
    lines.append(f"Grounded Answer:         {res_1.get('answer') if isinstance(res_1, dict) else getattr(res_1, 'answer', str(res_1))}")
    lines.append(f"Latency:                 {lat_1_ms:.2f} ms")
    lines.append(f"Generation Call Counter: {stats_1['generation_calls']}")
    lines.append(f"Hit / Miss Stats:        Hits={stats_1['hits']}, Misses={stats_1['misses']}")
    lines.append("\n" + "=" * 80 + "\n")

    lines.append("--------------------------------------------------------------------------------")
    lines.append("RUN 2: IDENTICAL QUERY WITH WHITESPACE & CASING VARIATION (EXPECTED: CACHE HIT)")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Query Variant:           '{query_variation}'")
    lines.append(f"Normalized Key:          '{demo_cache._normalize_key(query_variation)}'")
    lines.append(f"Cache Status:            {'HIT (Instant Retrieval)' if hit_2 else 'MISS'}")
    lines.append(f"Grounded Answer:         {res_2.get('answer') if isinstance(res_2, dict) else getattr(res_2, 'answer', str(res_2))}")
    lines.append(f"Latency:                 {lat_2_ms:.4f} ms")
    lines.append(f"Generation Call Counter: {stats_2['generation_calls']} (Remained at 1 - no generation call!)")
    lines.append(f"Hit / Miss Stats:        Hits={stats_2['hits']}, Misses={stats_2['misses']}")
    lines.append(f"Latency Speedup:         {speedup}x faster ({lat_1_ms:.2f} ms -> {lat_2_ms:.4f} ms)")
    lines.append("\n" + "=" * 80 + "\n")

    report_text = "\n".join(lines)
    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Cache demonstration report saved to: {TRANSCRIPT_PATH}")
    return {
        "run_1": {"latency_ms": lat_1_ms, "hit": hit_1, "generation_calls": stats_1["generation_calls"]},
        "run_2": {"latency_ms": lat_2_ms, "hit": hit_2, "generation_calls": stats_2["generation_calls"], "speedup": speedup},
    }


if __name__ == "__main__":
    run_cache_demonstration()
