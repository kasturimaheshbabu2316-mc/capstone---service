"""Empirical Cosine Similarity Calibration Module.

Track: Business Operations / Customer Support (Ola)
Calibrates the similarity threshold between in-scope and out-of-scope customer queries.
Writes calibration results and threshold to rag/threshold.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from rag.index import retrieve

# Configuration Paths
THRESHOLD_JSON_PATH = Path(__file__).resolve().parent / "threshold.json"

# In-Scope Ola Policy Queries (>= 4 queries)
IN_SCOPE_QUERIES = [
    "What is the resolution SLA for a Sev-1 safety incident?",
    "When does Ola provide monetary refunds for driver cancellations?",
    "How does Ola handle repeat chronic complaints from passengers?",
    "What are the benefits and response times for VIP Ola Select customers?",
    "What compensation is provided for ride delays exceeding 20 minutes?",
]

# Out-of-Scope Distractor Queries (>= 3 queries)
OUT_OF_SCOPE_QUERIES = [
    "Who won the cricket world cup?",
    "What is the best authentic Italian pizza recipe?",
    "How do I book an international flight to London with British Airways?",
    "What is the current stock price of Tesla on NASDAQ?",
]


def calibrate_threshold(
    collection_name: str = "kb_sentence",
    save_json: bool = True,
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]]]:
    """Measures top-1 cosine similarity for in-scope and out-of-scope query clusters.

    Derives empirical threshold T = (min(in-scope) + max(out-of-scope)) / 2.

    Args:
        collection_name: Target ChromaDB collection (default: 'kb_sentence').
        save_json: Whether to persist results to rag/threshold.json.

    Returns:
        Tuple of (calibrated_threshold, in_scope_metrics, out_scope_metrics).
    """
    in_scope_results: list[dict[str, Any]] = []
    for q in IN_SCOPE_QUERIES:
        chunks = retrieve(q, collection_name=collection_name, k=1)
        sim = chunks[0]["similarity"] if chunks else 0.0
        doc = chunks[0]["doc_id"] if chunks else "none"
        in_scope_results.append({
            "query": q,
            "similarity": sim,
            "top_doc": doc,
        })

    out_scope_results: list[dict[str, Any]] = []
    for q in OUT_OF_SCOPE_QUERIES:
        chunks = retrieve(q, collection_name=collection_name, k=1)
        sim = chunks[0]["similarity"] if chunks else 0.0
        doc = chunks[0]["doc_id"] if chunks else "none"
        out_scope_results.append({
            "query": q,
            "similarity": sim,
            "top_doc": doc,
        })

    min_in_scope = min(r["similarity"] for r in in_scope_results)
    max_out_scope = max(r["similarity"] for r in out_scope_results)

    # Threshold chosen as exact midpoint between clusters
    calibrated_threshold = round((min_in_scope + max_out_scope) / 2.0, 4)
    margin = round((min_in_scope - max_out_scope) / 2.0, 4)

    if save_json:
        data = {
            "threshold": calibrated_threshold,
            "min_in_scope": min_in_scope,
            "max_out_scope": max_out_scope,
            "margin": margin,
            "collection": collection_name,
            "metric": "cosine_similarity",
            "justification": (
                f"Midpoint between lowest in-scope similarity ({min_in_scope:.4f}) and "
                f"highest out-of-scope similarity ({max_out_scope:.4f}) yields T = {calibrated_threshold:.4f}, "
                f"providing a symmetric buffer margin of {margin:.4f} against false refusals and hallucinations."
            ),
            "in_scope_queries": in_scope_results,
            "out_of_scope_queries": out_scope_results,
        }
        with open(THRESHOLD_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    return calibrated_threshold, in_scope_results, out_scope_results


# Default calibrated threshold constant
CALIBRATED_THRESHOLD = 0.3652


def load_threshold() -> float:
    """Loads calibrated threshold from threshold.json or falls back to constant."""
    if THRESHOLD_JSON_PATH.exists():
        try:
            with open(THRESHOLD_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("threshold", CALIBRATED_THRESHOLD))
        except Exception:
            pass
    return CALIBRATED_THRESHOLD


if __name__ == "__main__":
    print("=" * 75)
    print("OLA DOMAIN SUPPORT AGENT — TASK 4: EMPIRICAL THRESHOLD CALIBRATION")
    print("=" * 75)

    col = "kb_sentence"
    T, in_res, out_res = calibrate_threshold(collection_name=col, save_json=True)

    print(f"\n1. IN-SCOPE QUERIES (>= 4 queries):")
    for r in in_res:
        print(f"  • Sim: {r['similarity']:.4f} | Top Doc: {r['top_doc']:<26} | Q: \"{r['query']}\"")

    print(f"\n2. OUT-OF-SCOPE QUERIES (>= 3 queries):")
    for r in out_res:
        print(f"  • Sim: {r['similarity']:.4f} | Top Doc: {r['top_doc']:<26} | Q: \"{r['query']}\"")

    min_in = min(r["similarity"] for r in in_res)
    max_out = max(r["similarity"] for r in out_res)
    print(f"\n3. CLUSTER SEPARATION & CALIBRATION METRICS:")
    print(f"  • Lowest In-Scope Similarity  (min_in) : {min_in:.4f}")
    print(f"  • Highest Out-of-Scope Sim   (max_out): {max_out:.4f}")
    print(f"  • Derived Midpoint Threshold (T)      : {T:.4f}")
    print(f"  • Buffer Margin                        : {(min_in - max_out) / 2.0:.4f}")
    print(f"  • Threshold JSON saved to              : {THRESHOLD_JSON_PATH}")
    print("=" * 75)
