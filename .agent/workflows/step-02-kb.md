---
description: Step 2 - write the 12-document knowledge base (Task 2)
---
STEP 2 - Knowledge base (Task 2).
Create 12+ files in kb/, 2-5 sentences each, in my own wording, Ola-specific, no
copied text. One file per topic:
ticket-priority classification rules, SLA-by-severity policy, escalation matrix,
refund/compensation policy, customer-communication-channel policy,
business-hours/holiday-support policy, repeat-complaint-handling policy,
service-credit policy, feedback-collection process, VIP-customer (Ola Select) handling
policy, outage-communication protocol, data-retention policy for tickets.
Rules: each doc is self-contained with a distinctive vocabulary (so retrieval can tell
them apart), and every fact is fabricated but consistent (e.g. Sev-1 first response
15 min, Sev-2 1 hour). Use fabricated examples only. Add a loader kb_loader.py that
returns [{doc_id, title, text}] and a test that checks the 12 topics and sentence
counts.
Verify: pytest tests/test_kb.py
