"""RAG Chunking Strategies Module for Ola Support Policy Knowledge Base.

Track: Business Operations / Customer Support (Ola)
Implements two chunking strategies:
1. Fixed-size chunking with sliding character window overlap (300 chars, 60 overlap).
2. Sentence-based chunking using pure regex boundary splitting (zero external dependencies).

Every chunk dictionary preserves metadata: `doc_id`, `chunk_id`, and `strategy`.
"""

from __future__ import annotations

import re
from typing import Any


def fixed_size_overlap_chunks(
    text: str,
    size: int = 300,
    overlap: int = 60,
    doc_id: str = "doc",
) -> list[dict[str, Any]]:
    """Chunks text into fixed character windows with sliding overlap.

    Args:
        text: Source text string to chunk.
        size: Target character length per window (default: 300).
        overlap: Character overlap between consecutive windows (default: 60).
        doc_id: Identifier of the parent source document.

    Returns:
        List of chunk dicts with keys: `text`, `doc_id`, `chunk_id`, `strategy`.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= size:
        return [
            {
                "text": clean_text,
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_fixed_0",
                "strategy": "fixed",
            }
        ]

    chunks: list[dict[str, Any]] = []
    step = size - overlap
    if step <= 0:
        raise ValueError(f"Chunk size ({size}) must be strictly greater than overlap ({overlap}).")

    start = 0
    chunk_idx = 0

    while start < len(clean_text):
        end = start + size
        chunk_content = clean_text[start:end].strip()
        if chunk_content:
            chunks.append(
                {
                    "text": chunk_content,
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_fixed_{chunk_idx}",
                    "strategy": "fixed",
                }
            )
            chunk_idx += 1
        if end >= len(clean_text):
            break
        start += step

    return chunks


def sentence_chunks(
    text: str,
    doc_id: str = "doc",
) -> list[dict[str, Any]]:
    """Splits text into individual sentence chunks using pure regex boundary detection.

    Zero external NLTK/spacy dependency to ensure 100% offline determinism.

    Args:
        text: Source text string to chunk.
        doc_id: Identifier of the parent source document.

    Returns:
        List of chunk dicts with keys: `text`, `doc_id`, `chunk_id`, `strategy`.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    # Strip out standalone markdown heading lines so headings don't pollute sentence chunks
    lines = [
        line.strip()
        for line in clean_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    body = " ".join(lines).strip()
    if not body:
        return []

    # Regex splits on whitespace following sentence terminator (. ! ?)
    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", body)
        if s.strip()
    ]

    chunks: list[dict[str, Any]] = []
    for idx, sentence in enumerate(raw_sentences):
        chunks.append(
            {
                "text": sentence,
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_sent_{idx}",
                "strategy": "sentence",
            }
        )

    return chunks


# ---------------------------------------------------------------------------
# Backward Compatibility Helpers (used by legacy app routes / tests)
# ---------------------------------------------------------------------------


def fixed_chunking(
    text: str,
    chunk_size: int = 200,
    overlap: int = 40,
) -> list[str]:
    """Legacy helper returning plain strings for fixed chunking."""
    dict_chunks = fixed_size_overlap_chunks(
        text=text,
        size=chunk_size,
        overlap=overlap,
        doc_id="legacy",
    )
    return [c["text"] for c in dict_chunks]


def sentence_chunking(text: str) -> list[str]:
    """Legacy helper returning plain strings for sentence chunking."""
    dict_chunks = sentence_chunks(text=text, doc_id="legacy")
    return [c["text"] for c in dict_chunks]
