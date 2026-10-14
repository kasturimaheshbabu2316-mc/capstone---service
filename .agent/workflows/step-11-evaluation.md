---
description: Step 11 - 15-query evaluation with a mock LLM-as-judge (Task 13)
---
STEP 11 - Evaluation (Task 13).
1. evaluation/test_queries.py: 15 queries, one per required KB topic (12) plus 2+
   out-of-scope or edge-case queries, plus 1 ticket-lookup query. Include expected topic
   and a reference answer for each.
2. evaluation/judge.py: a deterministic MOCK LLM-as-judge. Write the judge prompt
   (Accuracy, Grounding, Completeness, Safety, each 1-5) and implement the mock judge with
   transparent rules (accuracy = keyword overlap with the reference; grounding = share of
   answer sentences supported by the retrieved chunks; completeness = coverage of
   reference key points; safety = no PII leaked or injected content followed).
3. evaluation/run_eval.py: run all 15 queries through the crew, print a table of the
   four scores per query and the four averages, and save it to transcripts/13_eval.txt
   and evaluation/results.json. Put a short interpretation in the README.
