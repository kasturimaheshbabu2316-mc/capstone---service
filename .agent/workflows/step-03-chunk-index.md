---
description: Step 3 - two chunking strategies in two ChromaDB collections (Task 3)
---
STEP 3 - Chunking and ChromaDB indexing (Task 3).
- rag/chunking.py: (a) fixed_size_overlap_chunks(text, size=300 chars, overlap=60),
  (b) sentence_chunks(text) (regex sentence splitter, no external download). Every chunk
  keeps metadata: doc_id, chunk_id, strategy.
- rag/index.py: load SentenceTransformer(EMBED_MODEL) once, embed all chunks of each
  strategy, and index them into TWO separate persistent ChromaDB collections:
  "kb_fixed" and "kb_sentence", using collection.upsert() with cosine distance
  (hnsw:space = cosine). Make indexing idempotent.
- retrieve(query, collection_name, k) returns [{text, doc_id, chunk_id, similarity}]
  where similarity = 1 - cosine distance.
- Print chunk counts per collection and top-3 results for one sample query from each.
Save the output to transcripts/03_indexing.txt.
