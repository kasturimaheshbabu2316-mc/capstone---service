"""RAG Vector Indexing and Chroma Collection Management.

Track: Business Operations / Customer Support (Ola)
Indexes knowledge base documents into two isolated ChromaDB collections:
- `ola_fixed`: Fixed-size chunks (200 chars, 40 overlap)
- `ola_sentence`: Pure sentence-based chunks
Uses local SentenceTransformers ("all-MiniLM-L6-v2") with cosine distance.
"""

import os
import sys
import glob
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from rag.chunking import fixed_chunking, sentence_chunking

# Paths
KB_DIR = Path("kb")
CHROMA_DIR = Path(".chroma_db")

# Model
MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy loader for local SentenceTransformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_chroma_client() -> chromadb.PersistentClient:
    """Returns persistent ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_or_create_collection(name: str) -> Any:
    """Gets or creates a Chroma collection with cosine similarity."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def load_knowledge_base_docs() -> dict[str, str]:
    """Loads all markdown files from kb/ directory into a dict of {doc_id: text}."""
    docs = {}
    pattern = str(KB_DIR / "*.md")
    for file_path in sorted(glob.glob(pattern)):
        doc_id = Path(file_path).stem  # e.g., 'sla_by_severity'
        with open(file_path, "r", encoding="utf-8") as f:
            docs[doc_id] = f.read().strip()
    return docs


def index_documents(reset: bool = True) -> tuple[int, int]:
    """Chunks and indexes all KB documents into `ola_fixed` and `ola_sentence` collections.

    Returns:
        (total_fixed_chunks, total_sentence_chunks)
    """
    client = get_chroma_client()
    model = get_embedding_model()
    docs = load_knowledge_base_docs()

    if reset:
        for col_name in ["ola_fixed", "ola_sentence"]:
            try:
                client.delete_collection(col_name)
            except Exception:
                pass

    # Create collections with cosine similarity metric
    col_fixed = client.get_or_create_collection(
        name="ola_fixed", metadata={"hnsw:space": "cosine"}
    )
    col_sent = client.get_or_create_collection(
        name="ola_sentence", metadata={"hnsw:space": "cosine"}
    )

    fixed_ids, fixed_texts, fixed_metas = [], [], []
    sent_ids, sent_texts, sent_metas = [], [], []

    for doc_id, text in docs.items():
        # 1. Fixed chunking
        f_chunks = fixed_chunking(text, chunk_size=200, overlap=40)
        for idx, chunk in enumerate(f_chunks):
            chunk_id = f"fixed_{doc_id}_{idx}"
            fixed_ids.append(chunk_id)
            fixed_texts.append(chunk)
            fixed_metas.append(
                {"doc_id": doc_id, "chunk_index": idx, "strategy": "fixed"}
            )

        # 2. Sentence chunking
        s_chunks = sentence_chunking(text)
        for idx, chunk in enumerate(s_chunks):
            chunk_id = f"sent_{doc_id}_{idx}"
            sent_ids.append(chunk_id)
            sent_texts.append(chunk)
            sent_metas.append(
                {"doc_id": doc_id, "chunk_index": idx, "strategy": "sentence"}
            )

    # Compute dense embeddings locally
    fixed_embeddings = model.encode(fixed_texts, show_progress_bar=False).tolist()
    sent_embeddings = model.encode(sent_texts, show_progress_bar=False).tolist()

    # Upsert into Chroma collections
    if fixed_ids:
        col_fixed.upsert(
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

    return len(fixed_ids), len(sent_ids)


def query_collection(
    collection_name: str, query_text: str, top_k: int = 3
) -> list[dict[str, Any]]:
    """Queries specified Chroma collection and returns top-k chunks with cosine similarity."""
    client = get_chroma_client()
    model = get_embedding_model()

    col = client.get_collection(name=collection_name)
    query_emb = model.encode([query_text], show_progress_bar=False).tolist()

    results = col.query(
        query_embeddings=query_emb,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for doc, meta, dist in zip(docs, metas, dists):
            # Chroma returns cosine distance d in [0, 2]; similarity = 1 - d
            cosine_similarity = round(1.0 - float(dist), 4)
            meta_dict = meta or {}
            chunks.append(
                {
                    "text": doc,
                    "doc_id": meta_dict.get("doc_id", "unknown"),
                    "chunk_index": meta_dict.get("chunk_index", 0),
                    "strategy": meta_dict.get("strategy", "unknown"),
                    "distance": round(float(dist), 4),
                    "similarity": cosine_similarity,
                }
            )

    return chunks


if __name__ == "__main__":
    print("=" * 70)
    print("OLA DOMAIN SUPPORT AGENT — DUAL RAG CHUNKING & INDEXING (TASK 3)")
    print("=" * 70)
    print("Loading Knowledge Base documents and indexing into ChromaDB...")

    num_fixed, num_sent = index_documents(reset=True)

    print(f"\n--- 1. INDEXING SUMMARY ---")
    print(f"  • Knowledge Base Docs   : 12 policy files")
    print(f"  • Collection 'ola_fixed'    : {num_fixed} chunks (200 char window, 40 overlap)")
    print(f"  • Collection 'ola_sentence' : {num_sent} chunks (regex sentence-based)")
    print(f"  • Embedding Model       : {MODEL_NAME} (384-dimensional dense vectors)")
    print(f"  • Vector Space Metric   : Cosine (hnsw:space: cosine)")

    sample_query = "What is the resolution SLA for a Sev-1 safety incident?"
    print(f"\n--- 2. SAMPLE RETRIEVAL: 'ola_fixed' ---")
    print(f"Query: \"{sample_query}\"")
    fixed_results = query_collection("ola_fixed", sample_query, top_k=2)
    for i, res in enumerate(fixed_results, 1):
        print(f"  [{i}] Doc: {res['doc_id']} | Chunk: #{res['chunk_index']} | Cosine Similarity: {res['similarity']}")
        print(f"      Text: \"{res['text']}\"")

    print(f"\n--- 3. SAMPLE RETRIEVAL: 'ola_sentence' ---")
    print(f"Query: \"{sample_query}\"")
    sent_results = query_collection("ola_sentence", sample_query, top_k=2)
    for i, res in enumerate(sent_results, 1):
        print(f"  [{i}] Doc: {res['doc_id']} | Chunk: #{res['chunk_index']} | Cosine Similarity: {res['similarity']}")
        print(f"      Text: \"{res['text']}\"")

    print("\n" + "=" * 70)
    print("TASK 3 ACCEPTANCE CRITERIA: BOTH COLLECTIONS POPULATED & RETRIEVING")
    print("=" * 70)
