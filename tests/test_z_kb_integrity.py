"""Integrity test verifying canonical KB directory and ChromaDB index remain unpolluted.

Track: Business Operations / Customer Support (Ola)
Verifies that:
1. Canonical kb/ directory contains exactly the 12 official policy markdown files.
2. Canonical ChromaDB collection ('kb_sentence') chunk metadatas contain only those 12 doc_ids.
"""

from __future__ import annotations

import os
from pathlib import Path
import config
from rag.index import get_or_create_collection

OFFICIAL_12_DOCS = sorted([
    "business_hours_support",
    "communication_channels",
    "data_retention_policy",
    "escalation_matrix",
    "feedback_collection",
    "outage_communication",
    "refund_compensation_policy",
    "repeat_complaint_handling",
    "service_credit_policy",
    "sla_by_severity",
    "ticket_priority_rules",
    "vip_customer_policy",
])


def test_canonical_kb_directory_has_exactly_12_official_files():
    """Asserts kb/ contains exactly the 12 official files and no stray test files."""
    canonical_kb = config.PROJECT_ROOT / "kb"
    assert canonical_kb.exists(), f"Canonical KB directory does not exist: {canonical_kb}"

    kb_files = sorted([f.name for f in canonical_kb.glob("*.md")])
    expected_files = [f"{doc_id}.md" for doc_id in OFFICIAL_12_DOCS]

    assert len(kb_files) == 12, f"Expected exactly 12 files in kb/, but found {len(kb_files)}: {kb_files}"
    assert kb_files == expected_files, f"KB file mismatch. Found {kb_files}, expected {expected_files}"


def test_canonical_collection_contains_only_12_official_doc_ids():
    """Asserts the production ChromaDB collection has chunks belonging only to the 12 official doc_ids."""
    col = get_or_create_collection("kb_sentence")
    data = col.get()
    metas = data.get("metadatas") or []

    assert len(metas) > 0, "Production collection 'kb_sentence' is empty"

    present_doc_ids = sorted(set(m["doc_id"] for m in metas if isinstance(m, dict) and "doc_id" in m))
    assert present_doc_ids == OFFICIAL_12_DOCS, (
        f"Production collection contains unexpected doc_ids: {set(present_doc_ids) ^ set(OFFICIAL_12_DOCS)}"
    )

