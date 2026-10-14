---
description: Step 9 - PII masking, prompt-injection and groundedness guardrails (Task 10)
---
STEP 9 - Guardrails (Task 10).
safety/guardrails.py:
1. Input: mask_pii() for fixed-format phone numbers (Indian formats: +91 98765 43210,
   9876543210, 98765-43210) -> "[PHONE_MASKED]". Do NOT attempt names, addresses or
   payment details (acknowledged out of scope). Use fabricated numbers only.
2. Input: detect_prompt_injection() using a deterministic pattern list ("ignore previous
   instructions", "reveal system prompt", "you are now", etc.) returning blocked + reason.
3. Output: groundedness check that refuses when retrieved context does not support the
   question (reuse the calibrated similarity threshold plus a content-overlap check).
4. A GuardrailResult dataclass: {fired, kind, detail, sanitized_text}.
5. Demo one deliberate case per guardrail, and show the masked text being what the crew
   receives. Add tests.
Save the output to transcripts/10_guardrails.txt.
