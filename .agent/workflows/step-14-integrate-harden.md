---
description: Step 14 - integrate the full pipeline, full test suite, final README
---
STEP 14 - Integrate and harden.
1. One pipeline function that runs: guardrails (input) -> budget check -> cache ->
   crew (RAG / lookup) -> output groundedness check -> Autogen review -> schema
   validation -> structured log. Make /ask and the WebSocket both call it.
2. pytest suite covering every task: dataset thresholds, KB topics, both indexes,
   fallback, precision/recall math, escalation score, crew tool invocation (not
   placeholder), memory present vs fresh, schema validation, each guardrail, API
   endpoints, WebSocket disconnect, no raw PII in logs, review approve and revise,
   least autonomy, budget rejection, cache hit.
3. Finish the README: track statement on line 1, dataset choices, calibration numbers,
   chunking comparison and recommendation, the escalation formula, the risk level, the
   telemetry note, how to run everything under MOCK_LLM with zero API keys, and links to
   each transcript.
4. Run the whole thing offline (disconnect the network or block it) and confirm it still
   passes.
Verify: pytest -q
