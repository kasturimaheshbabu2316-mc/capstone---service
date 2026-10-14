---
description: Step 6 - check_support_ticket_status with a designed escalation score (Task 6)
---
STEP 6 - check_support_ticket_status (Task 6).
tools/ticket_tool.py: check_support_ticket_status(record_id: str) -> dict with status,
resolution_time_hours, escalation_score in [0, 1], and an error key for unknown IDs.
Design (not a bare OR): escalation_score = w1 * escalated + w2 * (days_since_created /
30), with w1 = 0.6 and w2 = 0.4 (or your own justified weights). Compute the
80th-percentile days_since_created from dataset.py and set ESCALATION_THRESHOLD from
the data (print the distribution and justify the threshold). Return a recommend_escalation
flag. Write the exact formula, weights, and threshold justification to the README.
Add unit tests: known ID, unknown ID, score bounds, an escalated and an old ticket.
Save the output to transcripts/06_ticket_tool.txt.
