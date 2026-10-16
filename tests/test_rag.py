"""Unit tests for RAG chunking, indexing, thresholding, and generation (Tasks 3, 4, 5)."""

import pytest
from rag.chunking import (
    fixed_chunking,
    sentence_chunking,
    fixed_size_overlap_chunks,
    sentence_chunks,
)
from rag.index import retrieve, get_or_create_collection
from rag.generate import (
    FALLBACK_REFUSAL,
    CALIBRATED_THRESHOLD,
    grounded_generate,
    grounded_answer,
)
import json
from pathlib import Path


def test_fixed_chunking_size_and_overlap():
    text = "A" * 300
    chunks = fixed_chunking(text, chunk_size=200, overlap=40)
    assert len(chunks) == 2
    assert len(chunks[0]) == 200


def test_sentence_chunking_regex_boundary():
    text = "First sentence. Second sentence! Third sentence? All done."
    chunks = sentence_chunking(text)
    assert len(chunks) == 4
    assert chunks[0] == "First sentence."
    assert chunks[1] == "Second sentence!"
    assert chunks[2] == "Third sentence?"
    assert chunks[3] == "All done."


def test_fixed_size_overlap_chunks_metadata():
    text = "Ola maintains 24/7 safety response teams. " * 15
    chunks = fixed_size_overlap_chunks(text, size=300, overlap=60, doc_id="sample_doc")
    assert len(chunks) >= 2
    for chunk in chunks:
        assert "text" in chunk and isinstance(chunk["text"], str)
        assert chunk["doc_id"] == "sample_doc"
        assert chunk["strategy"] == "fixed"
        assert chunk["chunk_id"].startswith("sample_doc_fixed_")


def test_sentence_chunks_metadata():
    text = "Ola Select offers white-glove support. Escalation response is within 15 minutes! Contact support@olacabs.com."
    chunks = sentence_chunks(text, doc_id="vip_doc")
    assert len(chunks) == 3
    for chunk in chunks:
        assert "text" in chunk and isinstance(chunk["text"], str)
        assert chunk["doc_id"] == "vip_doc"
        assert chunk["strategy"] == "sentence"
        assert chunk["chunk_id"].startswith("vip_doc_sent_")


def test_retrieve_kb_collections():
    # Test retrieval from kb_sentence
    sent_res = retrieve("What is the resolution SLA for Sev-1 safety incident?", collection_name="kb_sentence", k=3)
    assert len(sent_res) == 3
    for r in sent_res:
        assert "text" in r
        assert "doc_id" in r
        assert "chunk_id" in r
        assert "similarity" in r
        assert 0.0 <= r["similarity"] <= 1.0

    # Test retrieval from kb_fixed
    fixed_res = retrieve("What is the resolution SLA for Sev-1 safety incident?", collection_name="kb_fixed", k=3)
    assert len(fixed_res) == 3
    for r in fixed_res:
        assert "text" in r
        assert "doc_id" in r
        assert "chunk_id" in r
        assert "similarity" in r
        assert 0.0 <= r["similarity"] <= 1.0


def test_grounded_generation_in_scope():
    res = grounded_generate("What is the resolution SLA for a Sev-1 safety incident?")
    assert res["grounded"] is True
    assert res["answer"] != FALLBACK_REFUSAL
    assert len(res["sources"]) > 0


def test_grounded_generation_out_of_scope_refusal():
    res = grounded_generate("How do I bake an authentic Italian pizza in Rome?")
    assert res["grounded"] is False
    assert res["answer"] == FALLBACK_REFUSAL


def test_grounded_answer_structure_and_fallback():
    # In-scope
    in_res = grounded_answer("When does Ola provide monetary refunds for driver cancellations?", k=3, collection="recommended")
    assert in_res["grounded"] is True
    assert in_res["answer"] != "I don't know based on the available policy documents."
    assert "refund_compensation_policy" in in_res["sources"]
    assert in_res["top_similarity"] > 0.3652

    # Out-of-scope exact fallback
    out_res = grounded_answer("Who won the cricket world cup?", k=3, collection="recommended")
    assert out_res["grounded"] is False
    assert out_res["answer"] == "I don't know based on the available policy documents."
    assert out_res["top_similarity"] < 0.3652


def test_threshold_json_file():
    threshold_file = Path("rag/threshold.json")
    assert threshold_file.exists(), "rag/threshold.json must exist."
    with open(threshold_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "threshold" in data
    assert data["threshold"] not in (0.5, 0.6, 0.7)
    assert len(data.get("in_scope_queries", [])) >= 4
    assert len(data.get("out_of_scope_queries", [])) >= 3
    assert data["min_in_scope"] > data["max_out_scope"]


def test_recommended_json_and_evaluation():
    rec_file = Path("rag/recommended.json")
    assert rec_file.exists(), "rag/recommended.json must exist."
    with open(rec_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["winning_collection"] == "kb_sentence"
    assert data["recommended_collection"] == "kb_sentence"
    assert data["macro_precision_sentence"] > data["macro_precision_fixed"]
    assert data["macro_recall_sentence"] >= 0.99
    assert len(data.get("recommendation", "")) > 50


