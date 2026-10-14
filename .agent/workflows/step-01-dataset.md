---
description: Step 1 - seeded support-ticket dataset (Task 1)
---
STEP 1 - dataset.py (Task 1).
Write a seeded deterministic generator producing SUPPORT_TICKETS (>= 40, use 60).
Fields: record_id (TKT-0001...), category, status, resolution_time_hours,
days_since_created (int 0-30), escalated (bool).
- Categories: Billing, Technical Issue, Account Access, Product Defect, General Inquiry
  (each >= 3 records). Statuses: Open, In Progress, Escalated, Resolved, Closed
  (each >= 1).
- Use random.Random(SEED) with explicit category and status weights. Choose a realistic
  resolution_time_hours range (e.g. 1-72) and put a one-sentence justification in a
  comment and a constant.
- Make escalated depend on status/category weights so the overall escalated share lands
  between 10% and 30%. Add validate_dataset() that asserts every rule. If it fails, the
  fix is changing SEED or weights, never editing records.
- Add a __main__ block that prints: count per category, count per status, escalated %,
  and the seed, weights, and range used.
Fill the README "dataset design choices" section with the exact SEED, weights, and
range. Save the output to transcripts/01_dataset.txt.
