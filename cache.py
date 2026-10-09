"""In-Memory Response Cache for Ola Domain Support System.

Track: Business Operations / Customer Support (Ola)
Provides query normalization, thread-safe in-memory caching,
hit/miss statistics, and cache invalidation upon document ingestion.
"""

from typing import Any
import re
import threading


class ResponseCache:
    """Thread-safe normalized response cache with hit/miss telemetry."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, query: str) -> str:
        """Normalizes query string for robust cache key matching."""
        # Lowercase, strip punctuation, collapse whitespace
        clean = re.sub(r"[^\w\s]", "", query.lower())
        return " ".join(clean.split())

    def get(self, query: str) -> Any | None:
        """Retrieves cached response if present, updating stats."""
        key = self._normalize_key(query)
        with self._lock:
            if key in self._cache:
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, query: str, response: Any) -> None:
        """Stores response in cache under normalized key."""
        key = self._normalize_key(query)
        with self._lock:
            self._cache[key] = response

    def clear(self) -> int:
        """Invalidates entire cache (e.g. after knowledge base update).

        Returns number of invalidated entries.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def invalidate_all(self) -> int:
        """Alias for clear()."""
        return self.clear()

    def get_stats(self) -> dict[str, int]:
        """Returns cache telemetry: hits, misses, total entries."""
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(self._hits / (self._hits + self._misses), 4) if (self._hits + self._misses) > 0 else 0.0,
            }


# Global singleton cache instance
response_cache = ResponseCache()
