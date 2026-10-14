---
description: Step 4 - grounded generation with an empirically calibrated threshold (Task 4)
---
STEP 4 - Grounded generation and calibrated "I don't know" threshold (Task 4).
1. rag/calibrate.py: measure top-1 cosine similarity on >= 4 in-scope queries and >= 3
   deliberately out-of-scope queries (e.g. "who won the cricket world cup", "best pizza
   recipe"). Print both clusters, then pick the threshold between them (midpoint of
   max(out-of-scope) and min(in-scope), or justify another choice). Write the measured
   values and the chosen threshold to rag/threshold.json and to the README.
   Do NOT use 0.5/0.6/0.7 defaults.
2. rag/generate.py: grounded_answer(query, k=3, collection="recommended"):
   retrieve top-k; if top-1 similarity < threshold return the exact fallback "I don't
   know based on the available policy documents."; else call the generator.
3. The MOCK generator (MOCK_LLM) must be deterministic and extractive: compose the
   answer only from retrieved chunk text (e.g. select the most relevant sentences),
   returning {answer, sources, top_similarity, grounded}.
4. Demo on 5+ in-scope queries and 1 out-of-scope query that triggers the fallback.
Save the output to transcripts/04_grounded.txt.
