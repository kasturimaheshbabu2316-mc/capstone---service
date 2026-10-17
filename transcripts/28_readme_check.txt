=== COMMAND 1: pytest -q ===
........................................................................ [ 55%]
.........................................................                [100%]
============================== warnings summary ===============================
crew\crew.py:25
  C:\Users\kastu\Desktop\capstone - service\crew\crew.py:25: LangChainDeprecationWarning: RunnableWithMessageHistory is deprecated. Use LangGraph's built-in persistence instead.
    from crew.memory import session_memory, crew_runnable_with_history

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
129 passed, 1 warning in 10.33s

=== COMMAND 2: evaluation/run_eval.py ===
Starting 15-Query Evaluation Benchmark...
[01/15] Evaluating Q01 (sla_by_severity): 'What is the resolution SLA for a Sev-1 safety...'
[02/15] Evaluating Q02 (refund_compensation_policy): 'Under what conditions are driver cancellation...'
[03/15] Evaluating Q03 (vip_customer_policy): 'What are the benefits and response times for ...'
[04/15] Evaluating Q04 (repeat_complaint_handling): 'What happens when a customer logs 3 complaint...'
[05/15] Evaluating Q05 (business_hours_support): 'What are the operating hours for driver partn...'
[06/15] Evaluating Q06 (service_credit_policy): 'What service credit or compensation is provid...'
[07/15] Evaluating Q07 (escalation_matrix): 'Who handles Tier-3 escalations for cases unre...'
[08/15] Evaluating Q08 (ticket_priority_rules): 'How are P1 urgent priority tickets defined un...'
[09/15] Evaluating Q09 (outage_communication): 'How does Ola communicate technical platform o...'
[10/15] Evaluating Q10 (data_retention_policy): 'How long are customer support chat transcript...'
[11/15] Evaluating Q11 (communication_channels): 'What official support channels like in-app ch...'
[12/15] Evaluating Q12 (feedback_collection): 'How is post-ride passenger feedback collected...'
[13/15] Evaluating Q13 (ticket_lookup): 'What is the current status of ticket TKT-0007...'
[14/15] Evaluating Q14 (out_of_scope): 'Can you provide the best authentic recipe for...'
[15/15] Evaluating Q15 (out_of_scope): 'Who won the ICC Cricket World Cup tournament ...'

+-----+----------------------------+----------+-----------+--------------+--------+---------+
| ID  | Topic                      | Accuracy | Grounding | Completeness | Safety | Overall |
+-----+----------------------------+----------+-----------+--------------+--------+---------+
| Q01 | sla_by_severity            |    5     |     5     |      5       |   5    |  5.00   |
| Q02 | refund_compensation_policy |    5     |     5     |      5       |   5    |  5.00   |
| Q03 | vip_customer_policy        |    4     |     5     |      4       |   5    |  4.50   |
| Q04 | repeat_complaint_handling  |    4     |     5     |      2       |   5    |  4.00   |
| Q05 | business_hours_support     |    5     |     5     |      3       |   5    |  4.50   |
| Q06 | service_credit_policy      |    5     |     5     |      5       |   5    |  5.00   |
| Q07 | escalation_matrix          |    5     |     5     |      5       |   5    |  5.00   |
| Q08 | ticket_priority_rules      |    5     |     5     |      5       |   5    |  5.00   |
| Q09 | outage_communication       |    2     |     5     |      3       |   5    |  3.75   |
| Q10 | data_retention_policy      |    5     |     5     |      5       |   5    |  5.00   |
| Q11 | communication_channels     |    5     |     5     |      5       |   5    |  5.00   |
| Q12 | feedback_collection        |    4     |     5     |      3       |   5    |  4.25   |
| Q13 | ticket_lookup              |    5     |     5     |      5       |   5    |  5.00   |
| Q14 | out_of_scope               |    5     |     5     |      5       |   5    |  5.00   |
| Q15 | out_of_scope               |    5     |     5     |      5       |   5    |  5.00   |
+-----+----------------------------+----------+-----------+--------------+--------+---------+
| MACRO AVERAGES                   |   4.60   |   5.00    |     4.33     |  5.00  |  4.73   |
+-----+----------------------------+----------+-----------+--------------+--------+---------+

Evaluation transcript saved to: transcripts/13_eval.txt
Results JSON saved to: evaluation/results.json

=== COMMAND 3: review/autogen_review.py ===
Running AutoGen Review Demo A (Faithful Draft)...
Running AutoGen Review Demo B (Draft with Injected Ungrounded Claim)...

Transcript successfully saved to: C:\Users\kastu\Desktop\capstone - service\transcripts\14_review.txt

=== COMMAND 4: governance/budget.py ===
Governance demonstration report saved to: C:\Users\kastu\Desktop\capstone - service\transcripts\15_governance.txt

=== COMMAND 5: cache.py ===
Cache demonstration report saved to: C:\Users\kastu\Desktop\capstone - service\transcripts\16_cache.txt

=== COMMAND 6: curl.exe http://127.0.0.1:8000/health ===
{"status":"ok","mock_llm":true,"kb_ready":true,"db_ready":true,"service":"ola-support-agent"}

=== COMMAND 7: curl.exe --% POST /ask ===
{"answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","route":"rag","sources":["sla_by_severity"],"ticket":null,"grounded":true,"escalation_recommended":false,"review_status":{"approved":true,"final_answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","reason":"Verified facts against knowledge base. All claims grounded in retrieved context.","feedback":"Verified facts against knowledge base. All claims grounded in retrieved context.","redactions_made":false,"review_notes":"Verified facts against knowledge base. All claims grounded in retrieved context."},"trace_id":"7e97d22f-5444-4445-a9df-545c2a39f1ae","latency_ms":0.09,"data":{"answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","route":"rag","sources":["sla_by_severity"],"ticket":null,"ticket_id":null,"grounded":true,"escalation_recommended":false,"escalation_score":null,"review_status":{"approved":true,"final_answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","reason":"Verified facts against knowledge base. All claims grounded in retrieved context.","feedback":"Verified facts against knowledge base. All claims grounded in retrieved context.","redactions_made":false,"review_notes":"Verified facts against knowledge base. All claims grounded in retrieved context."}},"sql":null,"chart_type":null,"x_col":null,"y_col":null,"retrieved_sources":["sla_by_severity"],"retrieved_snippet":null,"cache_hit":true,"guardrail_flags":{"input_pii_masked":false,"phone_masked":false}}

=== COMMAND 8: Invoke-RestMethod POST /ask ===
{"answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","route":"rag","sources":["sla_by_severity"],"ticket":null,"grounded":true,"escalation_recommended":false,"review_status":{"approved":true,"final_answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","reason":"Verified facts against knowledge base. All claims grounded in retrieved context.","feedback":"Verified facts against knowledge base. All claims grounded in retrieved context.","redactions_made":false,"review_notes":"Verified facts against knowledge base. All claims grounded in retrieved context."},"trace_id":"43b637fc-113e-48d4-87f4-6fb4382c12fe","latency_ms":0.08,"data":{"answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","route":"rag","sources":["sla_by_severity"],"ticket":null,"ticket_id":null,"grounded":true,"escalation_recommended":false,"escalation_score":null,"review_status":{"approved":true,"final_answer":"Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours. Sev-2 high-priority issues require an initial acknowledgement within 1 hour and resolution within 12 hours. Sev-3 standard inquiries mandate response within 4 hours and resolution within 24 hours.","reason":"Verified facts against knowledge base. All claims grounded in retrieved context.","feedback":"Verified facts against knowledge base. All claims grounded in retrieved context.","redactions_made":false,"review_notes":"Verified facts against knowledge base. All claims grounded in retrieved context."}},"sql":null,"chart_type":null,"x_col":null,"y_col":null,"retrieved_sources":["sla_by_severity"],"retrieved_snippet":null,"cache_hit":true,"guardrail_flags":{"input_pii_masked":false,"phone_masked":false}}
