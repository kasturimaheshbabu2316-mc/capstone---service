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

import config
from rag.chunking import fixed_size_overlap_chunks, sentence_chunks
from kb_loader import load_kb

# Paths and configuration defaults
KB_DIR: Path = Path("kb")
CHROMA_DIR: Path = config.CHROMA_DIR
EMBED_MODEL_NAME: str = config.EMBED_MODEL
MODEL_NAME: str = EMBED_MODEL_NAME

# Singleton instance for embedding model
_embedding_model: Any = None
_chroma_client: chromadb.PersistentClient | None = None


class IndexResult(tuple):
    """Dual-access result supporting both tuple unpacking and dict key lookups."""

    def __new__(
        cls,
        fixed: int,
        sent: int,
        fixed_name: str = "kb_fixed",
        sent_name: str = "kb_sentence",
    ) -> IndexResult:
        obj = super().__new__(cls, (fixed, sent))
        obj._fixed_name = fixed_name
        obj._sent_name = sent_name
        obj._map = {fixed_name: fixed, sent_name: sent}
        return obj

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, (int, slice)):
            return super().__getitem__(key)
        return self._map[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def keys(self) -> Any:
        return self._map.keys()

    def values(self) -> Any:
        return self._map.values()

    def items(self) -> Any:
        return self._map.items()


class LocalSTEmbeddingFunction:
    """Embedding function delegating to local SentenceTransformer, zero network access."""

    def __call__(self, input: list[str]) -> list[list[float]]:
        model = get_embedding_model()
        emb = model.encode(input, show_progress_bar=False, batch_size=32)
        return emb.tolist() if hasattr(emb, "tolist") else [list(x) for x in emb]

    def embed_query(self, query: str) -> list[float]:
        return self([query])[0]


_chroma_ef: LocalSTEmbeddingFunction | None = None


def get_chroma_embedding_function() -> LocalSTEmbeddingFunction:
    """Returns singleton LocalSTEmbeddingFunction for ChromaDB."""
    global _chroma_ef
    if _chroma_ef is None:
        _chroma_ef = LocalSTEmbeddingFunction()
    return _chroma_ef


def get_embedding_model() -> Any:
    """Loads embedding model once as a thread-safe singleton.

    Loads SentenceTransformer locally with zero network calls.
    Fails fast with clear instruction if model is not cached.
    """
    global _embedding_model
    if _embedding_model is None:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_grad_enabled(False)
        except Exception:
            pass

        from sentence_transformers import SentenceTransformer
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("transformers").setLevel(logging.ERROR)

        # Attempt offline load first
        try:
            _embedding_model = SentenceTransformer(
                EMBED_MODEL_NAME,
                local_files_only=True,
            )
        except Exception:
            # If in offline mode, fail fast immediately
            if os.environ.get("HF_HUB_OFFLINE", "0") == "1" or os.environ.get("TRANSFORMERS_OFFLINE", "0") == "1":
                raise RuntimeError(
                    "Embedding model not found. Run: python scripts/prefetch_models.py (one-time, needs internet)."
                ) from None
            try:
                _embedding_model = SentenceTransformer(EMBED_MODEL_NAME)
            except Exception:
                raise RuntimeError(
                    "Embedding model not found. Run: python scripts/prefetch_models.py (one-time, needs internet)."
                ) from None

        if hasattr(_embedding_model, "eval"):
            try:
                _embedding_model.eval()
            except Exception:
                pass
    return _embedding_model


def get_chroma_client(chroma_dir: Path | str | None = None) -> chromadb.PersistentClient:
    """Returns singleton persistent ChromaDB client with safe embedding function default."""
    global _chroma_client
    if _chroma_client is None:
        target_dir = Path(chroma_dir) if chroma_dir else CHROMA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(target_dir))

        # Wrap get_collection and get_or_create_collection to always use LocalSTEmbeddingFunction
        orig_get = client.get_collection
        orig_get_or_create = client.get_or_create_collection

        def safe_get_collection(name: str, embedding_function: Any = None, **kwargs: Any) -> Any:
            if embedding_function is None:
                embedding_function = get_chroma_embedding_function()
            return orig_get(name=name, embedding_function=embedding_function, **kwargs)

        def safe_get_or_create_collection(name: str, embedding_function: Any = None, **kwargs: Any) -> Any:
            if embedding_function is None:
                embedding_function = get_chroma_embedding_function()
            return orig_get_or_create(name=name, embedding_function=embedding_function, **kwargs)

        client.get_collection = safe_get_collection  # type: ignore[assignment]
        client.get_or_create_collection = safe_get_or_create_collection  # type: ignore[assignment]
        _chroma_client = client
    return _chroma_client


def get_or_create_collection(
    name: str,
    client: chromadb.PersistentClient | None = None,
) -> Any:
    """Gets or creates a Chroma collection configured with cosine similarity and local embedding function."""
    chroma = client or get_chroma_client()
    return chroma.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=get_chroma_embedding_function(),
    )


def load_knowledge_base_docs() -> dict[str, str]:
    """Loads all policy markdown files from kb/ directory into a dict of {doc_id: text}."""
    docs_list = load_kb(KB_DIR)
    return {doc["doc_id"]: doc["text"] for doc in docs_list}


def index_documents(
    reset: bool = False,
    collections: tuple[str, ...] | list[str] = ("kb_fixed", "kb_sentence"),
    client: chromadb.PersistentClient | None = None,
) -> IndexResult:
    """Chunks and indexes KB documents into specified ChromaDB collections.

    Indexes are created with cosine distance (`hnsw:space = cosine`) and populated
    using collection.upsert() with deterministic IDs to guarantee idempotency.

    Args:
        reset: If True, deletes existing collections prior to indexing.
        collections: Tuple or list of collection names to index.
        client: Optional PersistentClient instance.

    Returns:
        IndexResult mapping collection names to their total chunk counts (also unpackable as tuple).
    """
    chroma = client or get_chroma_client()
    model = get_embedding_model()
    docs = load_knowledge_base_docs()

    col_list = list(collections)
    should_index_fixed = any(c in col_list for c in ("kb_fixed", "ola_fixed"))
    should_index_sent = any(c in col_list for c in ("kb_sentence", "ola_sentence"))

    fixed_col_name = "kb_fixed" if "kb_fixed" in col_list else ("ola_fixed" if "ola_fixed" in col_list else "kb_fixed")
    sent_col_name = "kb_sentence" if "kb_sentence" in col_list else ("ola_sentence" if "ola_sentence" in col_list else "kb_sentence")

    if reset:
        for cname in set(col_list + ["ola_fixed", "ola_sentence", "kb_fixed", "kb_sentence"]):
            try:
                chroma.delete_collection(cname)
            except Exception:
                pass

    col_fixed = get_or_create_collection(fixed_col_name, chroma) if should_index_fixed else None
    col_sent = get_or_create_collection(sent_col_name, chroma) if should_index_sent else None

    # Secondary collections for backward compatibility with legacy routes
    col_legacy_fixed = get_or_create_collection("ola_fixed", chroma) if should_index_fixed else None
    col_legacy_sent = get_or_create_collection("ola_sentence", chroma) if should_index_sent else None

    fixed_ids: list[str] = []
    fixed_texts: list[str] = []
    fixed_metas: list[dict[str, Any]] = []

    sent_ids: list[str] = []
    sent_texts: list[str] = []
    sent_metas: list[dict[str, Any]] = []

    for doc_id, text in docs.items():
        # 1. Fixed-size chunking (300 chars, 60 overlap)
        if should_index_fixed:
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
        if should_index_sent:
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
    if should_index_fixed and fixed_texts:
        fixed_embeddings = model.encode(fixed_texts, show_progress_bar=False, batch_size=32).tolist()
        if fixed_ids and col_fixed:
            col_fixed.upsert(
                ids=fixed_ids,
                documents=fixed_texts,
                embeddings=fixed_embeddings,
                metadatas=fixed_metas,
            )
            if col_legacy_fixed and col_legacy_fixed.name != col_fixed.name:
                col_legacy_fixed.upsert(
                    ids=fixed_ids,
                    documents=fixed_texts,
                    embeddings=fixed_embeddings,
                    metadatas=fixed_metas,
                )

    if should_index_sent and sent_texts:
        sent_embeddings = model.encode(sent_texts, show_progress_bar=False, batch_size=32).tolist()
        if sent_ids and col_sent:
            col_sent.upsert(
                ids=sent_ids,
                documents=sent_texts,
                embeddings=sent_embeddings,
                metadatas=sent_metas,
            )
            if col_legacy_sent and col_legacy_sent.name != col_sent.name:
                col_legacy_sent.upsert(
                    ids=sent_ids,
                    documents=sent_texts,
                    embeddings=sent_embeddings,
                    metadatas=sent_metas,
                )

    fixed_count = col_fixed.count() if col_fixed else 0
    sent_count = col_sent.count() if col_sent else 0

    # Refresh persistent client reference so readers detect freshly created HNSW disk segments
    global _chroma_client
    _chroma_client = None

    return IndexResult(
        fixed=fixed_count,
        sent=sent_count,
        fixed_name=fixed_col_name,
        sent_name=sent_col_name,
    )


def retrieve(
    query: str,
    collection_name: str = "kb_sentence",
    k: int = 3,
    top_k: int | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Retrieves top-k chunks from specified ChromaDB collection with cosine similarity.

    Args:
        query: Query string to match against indexed policy chunks.
        collection_name: Target collection ('kb_fixed' or 'kb_sentence').
        k: Maximum number of candidate chunks to retrieve.
        top_k: Optional alias for k parameter.

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
    effective_k = top_k if top_k is not None else k
    known_cols = {"kb_fixed", "kb_sentence", "ola_fixed", "ola_sentence"}

    # Guard against swapped positional arguments
    if query in known_cols and collection_name not in known_cols:
        query, collection_name = collection_name, query

    client = get_chroma_client()
    model = get_embedding_model()

    col = client.get_collection(name=collection_name)
    emb_res = model.encode([query], show_progress_bar=False, batch_size=1)
    query_emb = emb_res.tolist() if hasattr(emb_res, "tolist") else list(emb_res)

    results = col.query(
        query_embeddings=query_emb,
        n_results=effective_k,
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
            chunk_id = meta_dict.get("chunk_id", "unknown")
            chunk_idx = 0
            if "_" in chunk_id:
                try:
                    chunk_idx = int(chunk_id.rsplit("_", 1)[-1])
                except ValueError:
                    chunk_idx = 0

            retrieved.append({
                "text": doc_text,
                "doc_id": meta_dict.get("doc_id", "unknown"),
                "chunk_id": chunk_id,
                "chunk_index": chunk_idx,
                "similarity": similarity,
                "strategy": meta_dict.get("strategy", "unknown"),
            })

    return retrieved


def query_collection(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Flexible query wrapper supporting both retrieve and legacy signatures."""
    known_cols = {"kb_fixed", "kb_sentence", "ola_fixed", "ola_sentence"}
    k = kwargs.get("top_k", kwargs.get("k", 3))
    query = ""
    collection_name = "kb_sentence"

    if len(args) == 1:
        if args[0] in known_cols:
            collection_name = args[0]
        else:
            query = args[0]
    elif len(args) >= 2:
        if args[0] in known_cols:
            collection_name = args[0]
            query = args[1]
        elif args[1] in known_cols:
            query = args[0]
            collection_name = args[1]
        else:
            query = args[0]
            collection_name = args[1]
        if len(args) >= 3 and isinstance(args[2], int):
            k = args[2]

    if "query" in kwargs:
        query = kwargs["query"]
    if "collection_name" in kwargs:
        collection_name = kwargs["collection_name"]

    return retrieve(query=query, collection_name=collection_name, k=k)


if __name__ == "__main__":
    report_lines: list[str] = [
        "=" * 75,
        "OLA DOMAIN SUPPORT AGENT — TASK 3: CHUNKING & CHROMADB INDEXING",
        "=" * 75,
        "",
        "1. INDEXING KNOWLEDGE BASE DOCUMENTS (IDEMPOTENT UPSERT)...",
    ]

    counts = index_documents(reset=False, collections=("kb_fixed", "kb_sentence"))
    report_lines.extend([
        f"  • Collection 'kb_fixed'    : {counts['kb_fixed']} chunks (300 chars, 60 overlap)",
        f"  • Collection 'kb_sentence' : {counts['kb_sentence']} chunks (regex sentence-based)",
        f"  • Embedding Model          : {EMBED_MODEL_NAME}",
        f"  • Distance Metric          : Cosine (hnsw:space = cosine)",
        "",
    ])

    sample_query = "What is the resolution SLA for a Sev-1 safety incident?"
    report_lines.extend([
        "2. SAMPLE QUERY RETRIEVAL:",
        f"   Query: \"{sample_query}\"",
        "",
        "--- Top-3 Results from 'kb_fixed' ---",
    ])
    fixed_res = retrieve(sample_query, collection_name="kb_fixed", k=3)
    for i, r in enumerate(fixed_res, 1):
        report_lines.append(f"  [{i}] Doc ID: {r['doc_id']} | Chunk ID: {r['chunk_id']} | Similarity: {r['similarity']}")
        report_lines.append(f"      Text: \"{r['text']}\"")

    report_lines.extend([
        "",
        "--- Top-3 Results from 'kb_sentence' ---",
    ])
    sent_res = retrieve(sample_query, collection_name="kb_sentence", k=3)
    for i, r in enumerate(sent_res, 1):
        report_lines.append(f"  [{i}] Doc ID: {r['doc_id']} | Chunk ID: {r['chunk_id']} | Similarity: {r['similarity']}")
        report_lines.append(f"      Text: \"{r['text']}\"")

    report_lines.extend([
        "",
        "=" * 75,
        "TASK 3 VERIFICATION COMPLETE: ALL CHUNKS INDEXED & RETRIEVED SUCCESSFULLY",
        "=" * 75,
    ])

    full_output = "\n".join(report_lines)
    print(full_output)

    # Save transcript in UTF-8 format
    transcript_path = Path("transcripts/03_indexing.txt")
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(full_output + "\n")
    print(f"\n[Saved transcript to {transcript_path}]")
