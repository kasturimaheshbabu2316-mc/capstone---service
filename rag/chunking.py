"""RAG Chunking Strategies Module.

Implements two chunking strategies:
1. Fixed-size with overlap (e.g. 200 characters, 40 character overlap).
2. Sentence-based chunking using pure regex (no external NLTK dependencies).
"""

import re


def fixed_chunking(
    text: str, chunk_size: int = 200, overlap: int = 40
) -> list[str]:
    """Chunks text into fixed character windows with sliding overlap.

    Args:
        text: Source text string.
        chunk_size: Target character length per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_size:
        return [clean_text]

    chunks = []
    step = chunk_size - overlap
    start = 0

    while start < len(clean_text):
        end = start + chunk_size
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean_text):
            break
        start += step

    return chunks


def sentence_chunking(text: str) -> list[str]:
    """Splits text into individual sentence chunks using regex punctuation boundary detection.

    Zero external NLTK/spacy dependency to ensure offline determinism.

    Args:
        text: Source text string.

    Returns:
        List of complete sentence chunks.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    # Regex splits on whitespace following sentence terminator (. ! ?)
    raw_sentences = re.split(r"(?<=[.!?])\s+", clean_text)
    return [s.strip() for s in raw_sentences if s.strip()]
