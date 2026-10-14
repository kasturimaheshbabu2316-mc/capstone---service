---
description: Step 5 - precision/recall comparison of both chunking strategies (Task 5)
---
STEP 5 - Evaluate chunking strategies (Task 5).
rag/evaluate_chunking.py: use the same 5+ queries as Step 4, each with a hand-written
ground-truth list of relevant doc_ids. For EACH collection separately: retrieve top-k,
map chunks to parent doc_ids and dedupe, then compute
precision = |retrieved ∩ relevant| / |retrieved| and
recall = |retrieved ∩ relevant| / |relevant|.
Print per-query arithmetic (e.g. "2/3 = 0.667") for both collections, plus macro
averages. Then generate a 2-3 sentence recommendation that cites those numbers, save it
to rag/recommended.json (the winning collection name), and paste it into the README.
All later steps must use that collection.
Save the output to transcripts/05_chunk_eval.txt.
