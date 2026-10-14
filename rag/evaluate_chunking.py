"""Evaluation of Fixed vs Sentence Chunking Strategies.

Track: Business Operations / Customer Support (Ola)
Compares Precision@k, Recall@k, and Hit-Rate for fixed-size and sentence-based chunking.
"""

from typing import Dict, Any, List
from rag.evaluate import run_comparative_evaluation, evaluate_query_strategy

evaluate_chunking_strategies = run_comparative_evaluation

__all__ = ["evaluate_chunking_strategies", "run_comparative_evaluation", "evaluate_query_strategy"]


if __name__ == "__main__":
    results = evaluate_chunking_strategies()
    print("Chunking Evaluation Complete:", results)
