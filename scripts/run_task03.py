"""Task 03 Runner: Dual Chunking Strategies & Vector Indexing."""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag.index import index_documents, query_collection, MODEL_NAME

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILE = os.path.join(TRANSCRIPTS_DIR, "task03_chunking.txt")


def run():
    print("Executing Task 03: Dual RAG Chunking and Indexing...")
    num_fixed, num_sent = index_documents(reset=True)

    sample_query = "What is the resolution SLA for a Sev-1 safety incident?"
    fixed_results = query_collection("ola_fixed", sample_query, top_k=2)
    sent_results = query_collection("ola_sentence", sample_query, top_k=2)

    lines = [
        "=" * 70,
        "OLA DOMAIN SUPPORT AGENT — DUAL RAG CHUNKING & INDEXING (TASK 3)",
        "=" * 70,
        "Loading Knowledge Base documents and indexing into ChromaDB...",
        "",
        "--- 1. INDEXING SUMMARY ---",
        "  • Knowledge Base Docs   : 12 policy files",
        f"  • Collection 'ola_fixed'    : {num_fixed} chunks (200 char window, 40 overlap)",
        f"  • Collection 'ola_sentence' : {num_sent} chunks (regex sentence-based)",
        f"  • Embedding Model       : {MODEL_NAME} (384-dimensional dense vectors)",
        "  • Vector Space Metric   : Cosine (hnsw:space: cosine)",
        "",
        "--- 2. SAMPLE RETRIEVAL: 'ola_fixed' ---",
        f"Query: \"{sample_query}\"",
    ]
    for i, res in enumerate(fixed_results, 1):
        lines.append(f"  [{i}] Doc: {res['doc_id']} | Chunk: #{res['chunk_index']} | Cosine Similarity: {res['similarity']}")
        lines.append(f"      Text: \"{res['text']}\"")

    lines.extend([
        "",
        "--- 3. SAMPLE RETRIEVAL: 'ola_sentence' ---",
        f"Query: \"{sample_query}\"",
    ])
    for i, res in enumerate(sent_results, 1):
        lines.append(f"  [{i}] Doc: {res['doc_id']} | Chunk: #{res['chunk_index']} | Cosine Similarity: {res['similarity']}")
        lines.append(f"      Text: \"{res['text']}\"")

    lines.extend([
        "",
        "=" * 70,
        "TASK 3 ACCEPTANCE CRITERIA: BOTH COLLECTIONS POPULATED & RETRIEVING",
        "=" * 70,
        "",
    ])

    output = "\n".join(lines)
    print(output)
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Transcript written to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    run()
