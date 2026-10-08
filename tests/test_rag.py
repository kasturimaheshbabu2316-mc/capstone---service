"""Unit tests for RAG chunking, indexing, thresholding, and generation (Tasks 3, 4, 5)."""

import pytest
from rag.chunking import fixed_chunking, sentence_chunking
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


def test_grounded_generation_in_scope():
    res = grounded_generate("What is the resolution SLA for a Sev-1 safety incident?")
    assert res["grounded"] is True
    assert res["answer"] != FALLBACK_REFUSAL
    assert len(res["sources"]) > 0


def test_grounded_generation_out_of_scope_refusal():
    res = grounded_generate("How do I bake an authentic Italian pizza in Rome?")
    assert res["grounded"] is False
    assert res["answer"] == FALLBACK_REFUSAL
