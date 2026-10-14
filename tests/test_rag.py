"""Unit tests for RAG chunking, indexing, thresholding, and generation (Tasks 3, 4, 5)."""

import pytest
from rag.chunking import (
    fixed_chunking,
    sentence_chunking,
    fixed_size_overlap_chunks,
    sentence_chunks,
)
from rag.index import retrieve, get_or_create_collection
from rag.generate import FALLBACK_REFUSAL, CALIBRATED_THRESHOLD, grounded_generate


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
