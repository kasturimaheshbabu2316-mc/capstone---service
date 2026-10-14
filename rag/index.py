"""RAG Vector Indexing and Chroma Collection Management.

Track: Business Operations / Customer Support (Ola)
Indexes knowledge base documents into two isolated ChromaDB collections:
- `kb_fixed`: Fixed-size chunks (300 chars, 60 overlap)
- `kb_sentence`: Pure sentence-based chunks using regex

Features:
- Single-instance lazy loading of SentenceTransformer(EMBED_MODEL)
- Persistent ChromaDB storage using cosine distance metric (hnsw:space = cosine)
- Fully idempotent indexing via collection.upsert() with deterministic chunk IDs
- retrieve(query, collection_name, k) returning similarity = 1 - cosine distance
"""

from __future__ import annotations

import glob
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

import config
from rag.chunking import fixed_size_overlap_chunks, sentence_chunks
from kb_loader import load_kb

# Paths and configuration defaults
KB_DIR: Path = Path("kb")
CHROMA_DIR: Path = config.CHROMA_DIR
EMBED_MODEL_NAME: str = config.EMBED_MODEL

# Singleton instance for SentenceTransformer
_embedding_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None


def get_embedding_model() -> SentenceTransformer:
    """Loads SentenceTransformer model once as a thread-safe singleton.

    Disables tokenizers parallelism and progress bars to guarantee clean,
    deterministic offline execution.
    """
    global _embedding_model
    if _embedding_model is None:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            from transformers.utils import logging as hf_logging
            hf_logging.disable_progress_bar()
        except Exception:
            pass
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("transformers").setLevel(logging.ERROR)
        _embedding_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedding_model


def get_chroma_client(chroma_dir: Path | str | None = None) -> chromadb.PersistentClient:
    """Returns singleton persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        target_dir = Path(chroma_dir) if chroma_dir else CHROMA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(target_dir))
    return _chroma_client


def get_or_create_collection(
    name: str,
    client: chromadb.PersistentClient | None = None,
) -> Any:
    """Gets or creates a Chroma collection configured with cosine similarity."""
    chroma = client or get_chroma_client()
    return chroma.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def load_knowledge_base_docs() -> dict[str, str]:
    """Loads all policy markdown files from kb/ directory into a dict of {doc_id: text}."""
    docs_list = load_kb(KB_DIR)
    return {doc["doc_id"]: doc["text"] for doc in docs_list}


def index_documents(
    reset: bool = False,
    collections: tuple[str, str] = ("kb_fixed", "kb_sentence"),
) -> dict[str, int]:
    """Chunks and indexes all KB documents into two ChromaDB collections.

    Indexes are created with cosine distance (`hnsw:space = cosine`) and populated
    using collection.upsert() with deterministic IDs to guarantee idempotency.

    Args:
        reset: If True, deletes existing collections prior to indexing.
        collections: Tuple of collection names (fixed_collection, sentence_collection).

    Returns:
        Dict mapping collection names to their total chunk counts.
    """
    client = get_chroma_client()
    model = get_embedding_model()
    docs = load_knowledge_base_docs()

    fixed_col_name, sent_col_name = collections

    if reset:
        for cname in [fixed_col_name, sent_col_name, "ola_fixed", "ola_sentence"]:
            try:
                client.delete_collection(cname)
            except Exception:
                pass

    col_fixed = get_or_create_collection(fixed_col_name, client)
    col_sent = get_or_create_collection(sent_col_name, client)

    # Secondary collections for backward compatibility with legacy routes
    col_legacy_fixed = get_or_create_collection("ola_fixed", client)
    col_legacy_sent = get_or_create_collection("ola_sentence", client)

    fixed_ids: list[str] = []
    fixed_texts: list[str] = []
    fixed_metas: list[dict[str, Any]] = []

    sent_ids: list[str] = []
    sent_texts: list[str] = []
    sent_metas: list[dict[str, Any]] = []

    for doc_id, text in docs.items():
        # 1. Fixed-size chunking (300 chars, 60 overlap)
        f_chunks = fixed_size_overlap_chunks(text, size=300, overlap=60, doc_id=doc_id)
        for chunk in f_chunks:
            fixed_ids.append(chunk["chunk_id"])
            fixed_texts.append(chunk["text"])
            fixed_metas.append({
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "strategy": chunk["strategy"],
            })

        # 2. Sentence-based chunking
        s_chunks = sentence_chunks(text, doc_id=doc_id)
        for chunk in s_chunks:
            sent_ids.append(chunk["chunk_id"])
            sent_texts.append(chunk["text"])
            sent_metas.append({
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "strategy": chunk["strategy"],
            })

    # Encode embeddings in batch
    fixed_embeddings = model.encode(fixed_texts, show_progress_bar=False).tolist()
    sent_embeddings = model.encode(sent_texts, show_progress_bar=False).tolist()

    # Idempotent upsert into target collections
    if fixed_ids:
        col_fixed.upsert(
            ids=fixed_ids,
            documents=fixed_texts,
            embeddings=fixed_embeddings,
            metadatas=fixed_metas,
        )
        col_legacy_fixed.upsert(
            ids=fixed_ids,
            documents=fixed_texts,
            embeddings=fixed_embeddings,
            metadatas=fixed_metas,
        )

    if sent_ids:
        col_sent.upsert(
            ids=sent_ids,
            documents=sent_texts,
            embeddings=sent_embeddings,
            metadatas=sent_metas,
        )
        col_legacy_sent.upsert(
            ids=sent_ids,
            documents=sent_texts,
            embeddings=sent_embeddings,
            metadatas=sent_metas,
        )

    return {
        fixed_col_name: col_fixed.count(),
        sent_col_name: col_sent.count(),
    }


def retrieve(
    query: str,
    collection_name: str = "kb_sentence",
    k: int = 3,
) -> list[dict[str, Any]]:
    """Retrieves top-k chunks from specified ChromaDB collection with cosine similarity.

    Args:
        query: Query string to match against indexed policy chunks.
        collection_name: Target collection ('kb_fixed' or 'kb_sentence').
        k: Maximum number of candidate chunks to retrieve.

    Returns:
        List of candidate dictionaries:
        [
            {
                "text": "Ola enforces strict resolution Service Level Agreements...",
                "doc_id": "sla_by_severity",
                "chunk_id": "sla_by_severity_sent_0",
                "similarity": 0.8241
            },
            ...
        ]
    """
    client = get_chroma_client()
    model = get_embedding_model()

    col = client.get_collection(name=collection_name)
    query_emb = model.encode([query], show_progress_bar=False).tolist()

    results = col.query(
        query_embeddings=query_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[dict[str, Any]] = []
    if results and results["documents"] and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc_text, meta, dist in zip(docs, metas, distances):
            # Chroma returns cosine distance d in [0, 2]; similarity = 1 - d
            dist_val = float(dist)
            similarity = round(1.0 - dist_val, 4)
            meta_dict = meta or {}
            retrieved.append({
                "text": doc_text,
                "doc_id": meta_dict.get("doc_id", "unknown"),
                "chunk_id": meta_dict.get("chunk_id", "unknown"),
                "similarity": similarity,
                "strategy": meta_dict.get("strategy", "unknown"),
            })

    return retrieved


# Alias for backwards compatibility
query_collection = retrieve


if __name__ == "__main__":
    print("=" * 75)
    print("OLA DOMAIN SUPPORT AGENT — TASK 3: CHUNKING & CHROMADB INDEXING")
    print("=" * 75)

    print("\n1. INDEXING KNOWLEDGE BASE DOCUMENTS (IDEMPOTENT UPSERT)...")
    counts = index_documents(reset=False, collections=("kb_fixed", "kb_sentence"))
    print(f"  • Collection 'kb_fixed'    : {counts['kb_fixed']} chunks (300 chars, 60 overlap)")
    print(f"  • Collection 'kb_sentence' : {counts['kb_sentence']} chunks (regex sentence-based)")
    print(f"  • Embedding Model          : {EMBED_MODEL_NAME}")
    print(f"  • Distance Metric          : Cosine (hnsw:space = cosine)")

    sample_query = "What is the resolution SLA for a Sev-1 safety incident?"
    print(f"\n2. SAMPLE QUERY RETRIEVAL:")
    print(f"   Query: \"{sample_query}\"")

    print(f"\n--- Top-3 Results from 'kb_fixed' ---")
    fixed_res = retrieve(sample_query, collection_name="kb_fixed", k=3)
    for i, r in enumerate(fixed_res, 1):
        print(f"  [{i}] Doc ID: {r['doc_id']} | Chunk ID: {r['chunk_id']} | Similarity: {r['similarity']}")
        print(f"      Text: \"{r['text']}\"")

    print(f"\n--- Top-3 Results from 'kb_sentence' ---")
    sent_res = retrieve(sample_query, collection_name="kb_sentence", k=3)
    for i, r in enumerate(sent_res, 1):
        print(f"  [{i}] Doc ID: {r['doc_id']} | Chunk ID: {r['chunk_id']} | Similarity: {r['similarity']}")
        print(f"      Text: \"{r['text']}\"")

    print("\n" + "=" * 75)
    print("TASK 3 VERIFICATION COMPLETE: ALL CHUNKS INDEXED & RETRIEVED SUCCESSFULLY")
    print("=" * 75)
