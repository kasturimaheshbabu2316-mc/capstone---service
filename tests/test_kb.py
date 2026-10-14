"""Unit tests for Ola Support Knowledge Base files and kb_loader.py.

Verifies Task 2 requirements:
- At least 12 distinct policy files in kb/
- All 12 mandated operational support topics are covered
- Sentence count for every document is between 2 and 5 sentences
- Documents contain distinctive Ola-specific vocabulary and fabricated facts
- kb_loader.load_kb returns correctly formatted dictionaries [{doc_id, title, text}]
"""

from __future__ import annotations

from pathlib import Path
import pytest

from kb_loader import (
    REQUIRED_TOPIC_IDS,
    count_sentences,
    get_doc_by_id,
    load_kb,
    validate_kb,
)

KB_DIR = Path("kb")


def test_kb_directory_exists():
    """Knowledge base directory must exist and be accessible."""
    assert KB_DIR.exists() and KB_DIR.is_dir(), "Directory 'kb/' must exist."


def test_kb_file_count():
    """Knowledge base must contain at least 12 distinct documents."""
    docs = load_kb(KB_DIR)
    assert len(docs) >= 12, f"Expected >= 12 KB files, found {len(docs)}"


def test_kb_all_required_topics_present():
    """All 12 mandatory operational topics must have a corresponding document."""
    docs = load_kb(KB_DIR)
    found_ids = {d["doc_id"] for d in docs}

    for topic_id in REQUIRED_TOPIC_IDS:
        assert topic_id in found_ids, f"Mandatory topic '{topic_id}' missing from kb/."


def test_kb_document_structure():
    """Every loaded document must have non-empty doc_id, title, and text fields."""
    docs = load_kb(KB_DIR)
    for doc in docs:
        assert "doc_id" in doc and isinstance(doc["doc_id"], str) and len(doc["doc_id"]) > 0
        assert "title" in doc and isinstance(doc["title"], str) and len(doc["title"]) > 0
        assert "text" in doc and isinstance(doc["text"], str) and len(doc["text"]) > 0


def test_kb_sentence_counts():
    """Every knowledge base document body must contain between 2 and 5 sentences."""
    docs = load_kb(KB_DIR)
    for doc in docs:
        sc = count_sentences(doc["text"])
        assert 2 <= sc <= 5, (
            f"Document '{doc['doc_id']}' has {sc} sentences. Must be between 2 and 5."
        )


def test_kb_ola_specific_vocabulary():
    """Documents must contain Ola-specific domain vocabulary."""
    docs = load_kb(KB_DIR)
    ola_mentions = [d for d in docs if "ola" in d["text"].lower() or "ola" in d["title"].lower()]
    # Overwhelming majority of documents must explicitly reference Ola operations
    assert len(ola_mentions) >= 10, "Expected at least 10 documents to explicitly reference Ola."


def test_kb_fabricated_facts_consistency():
    """Fabricated operational SLAs and policy numbers must remain internally consistent."""
    # Check SLA by severity numbers
    sla_doc = get_doc_by_id("sla_by_severity", KB_DIR)
    assert sla_doc is not None
    assert "15 minutes" in sla_doc["text"]  # Sev-1 response
    assert "1 hour" in sla_doc["text"]       # Sev-2 response
    assert "4 hours" in sla_doc["text"]      # Sev-3 response

    # Check VIP customer policy
    vip_doc = get_doc_by_id("vip_customer_policy", KB_DIR)
    assert vip_doc is not None
    assert "Ola Select" in vip_doc["text"] or "Ola Select" in vip_doc["title"]
    assert "15 minutes" in vip_doc["text"]  # VIP SLA response

    # Check cancellation refund consistency
    refund_doc = get_doc_by_id("refund_compensation_policy", KB_DIR)
    assert refund_doc is not None
    assert "5 minutes" in refund_doc["text"]

    # Check escalation matrix tiers
    esc_doc = get_doc_by_id("escalation_matrix", KB_DIR)
    assert esc_doc is not None
    assert "Tier-1" in esc_doc["text"]
    assert "Tier-2" in esc_doc["text"]
    assert "Tier-3" in esc_doc["text"]


def test_kb_get_doc_by_id():
    """get_doc_by_id must return the specific document or None for unknown IDs."""
    doc = get_doc_by_id("sla_by_severity", KB_DIR)
    assert doc is not None
    assert doc["doc_id"] == "sla_by_severity"

    missing = get_doc_by_id("non_existent_policy_xyz", KB_DIR)
    assert missing is None


def test_kb_validation_summary_passes():
    """validate_kb() must return passed=True with zero missing or invalid docs."""
    summary = validate_kb(KB_DIR)
    assert summary["passed"] is True
    assert len(summary["missing_topics"]) == 0
    assert len(summary["invalid_sentence_docs"]) == 0
