---
description: Step 13 - least autonomy, risk level, token budget, response cache (Tasks 15, 16)
---
STEP 13 - Governance and caching (Tasks 15, 16).
1. Application layer, least autonomy: make the tool assignment explicit in one registry
   (TOOL_PERMISSIONS = {"check_support_ticket_status": ["Lookup Agent"]}). Add a guard
   wrapper inside the tool that checks the calling agent's role and raises
   PermissionError for anyone else. Demonstrate: a Composer or Retrieval agent attempting
   the call is blocked, and the Lookup Agent succeeds. Add a test.
2. governance/RISK.md: classify this system as MEDIUM risk (customer support tickets)
   using the Low/Medium/High scheme and justify it in one paragraph; copy it into the
   README.
3. Runtime layer: governance/budget.py estimates tokens per request (len(text)/4 plus
   retrieved context) and enforces MAX_REQUEST_TOKENS. A deliberately oversized request is
   rejected with a clear message (HTTP 413 in the API), and a normal one passes. Show both.
4. cache.py: in-memory cache keyed by normalized query (lowercase, trimmed,
   collapsed whitespace) for the grounded-generation step, with hit/miss counters. Demo:
   run the same query twice and show the generation call counter incrementing once, plus
   before/after timing.
Save the output to transcripts/15_governance.txt and transcripts/16_cache.txt.
