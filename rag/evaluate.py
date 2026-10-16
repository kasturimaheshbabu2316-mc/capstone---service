"""Evaluation and Comparison of Chunking Strategies.

Track: Business Operations / Customer Support (Ola)
Evaluates deduplicated parent-document precision and recall across:
- `ola_fixed`: Fixed-size chunks (200 char window, 40 overlap)
- `ola_sentence`: Pure sentence-based chunks
Generates detailed arithmetic comparison tables and empirical recommendation.
"""

from typing import Any
from rag.evaluate_chunking import (
    BENCHMARK_GROUND_TRUTH,
    compare_chunking_strategies,
    evaluate_collection,
    evaluate_query,
    run_comparative_evaluation,
)

# Compatibility aliases
evaluate_query_strategy = evaluate_query
evaluate_chunking_strategies = compare_chunking_strategies

__all__ = [
    "BENCHMARK_GROUND_TRUTH",
    "evaluate_query_strategy",
    "evaluate_collection",
    "compare_chunking_strategies",
    "run_comparative_evaluation",
    "evaluate_chunking_strategies",
]


if __name__ == "__main__":
    from rag.evaluate_chunking import compare_chunking_strategies
    compare_chunking_strategies(save_json=True)

