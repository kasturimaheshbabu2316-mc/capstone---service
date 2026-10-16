"""15 Curated Evaluation Benchmark Queries (Task 13).

Track: Business Operations / Customer Support (Ola)
Includes:
- 12 in-scope policy queries (one for each canonical knowledge base document)
- 1 operational ticket lookup query (TKT-0007)
- 2 out-of-scope / edge-case queries testing calibrated refusal

Each query record specifies:
- id: Identifier (Q01 - Q15)
- query: User query text
- topic: Associated KB document or operational route
- expected_route: 'rag', 'lookup', or 'out_of_scope'
- reference_answer: Canonical factual reference answer
- key_points: Essential factual assertions required for completeness
"""

from __future__ import annotations

from typing import Any, Dict, List

EVAL_BENCHMARK_QUERIES: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. 12 Canonical Knowledge Base Topics
    # --------------------------------------------------------------------------
    {
        "id": "Q01",
        "topic": "sla_by_severity",
        "query": "What is the resolution SLA for a Sev-1 safety incident?",
        "expected_route": "rag",
        "reference_answer": "Sev-1 safety incidents require a mandatory first response within 15 minutes and complete operational resolution within 4 hours.",
        "key_points": [
            "first response within 15 minutes",
            "resolution within 4 hours",
        ],
    },
    {
        "id": "Q02",
        "topic": "refund_compensation_policy",
        "query": "Under what conditions are driver cancellation fees refunded to passengers?",
        "expected_route": "rag",
        "reference_answer": "Driver cancellation fees are unconditionally reversed if the driver remained stationary for more than 5 minutes or failed to arrive at the pickup spot.",
        "key_points": [
            "unconditionally reversed",
            "driver stationary for more than 5 minutes",
            "failed to arrive at pickup spot",
        ],
    },
    {
        "id": "Q03",
        "topic": "vip_customer_policy",
        "query": "What are the benefits and response times for VIP Ola Select customers?",
        "expected_route": "rag",
        "reference_answer": "VIP support tickets assign directly to Senior Relationship Managers with a 15-minute first-response SLA across all severities and resolution within 6 hours. Vehicle breakdowns receive a replacement Prime luxury cab within 10 minutes at zero fare.",
        "key_points": [
            "Senior Relationship Managers",
            "15-minute first-response SLA",
            "resolution within 6 hours",
            "replacement Prime luxury cab within 10 minutes",
        ],
    },
    {
        "id": "Q04",
        "topic": "repeat_complaint_handling",
        "query": "What happens when a customer logs 3 complaints within a 14-day rolling window?",
        "expected_route": "rag",
        "reference_answer": "When a customer logs three or more complaints within a 14-day rolling window, the system flags the ticket as a Chronic Repeat Defect, routing to a Senior Quality Supervisor within 2 hours for outbound telephonic review and fleet audit within 24 hours.",
        "key_points": [
            "Chronic Repeat Defect",
            "Senior Quality Supervisor within 2 hours",
            "outbound telephonic review",
            "fleet audit within 24 hours",
        ],
    },
    {
        "id": "Q05",
        "topic": "business_hours_support",
        "query": "What are the operating hours for driver partner physical onboarding centers and emergency desks?",
        "expected_route": "rag",
        "reference_answer": "Driver partner physical onboarding centers operate Monday through Saturday from 09:00 to 18:00 Indian Standard Time. Passenger emergency support desks operate 24/7/365 without interruption.",
        "key_points": [
            "Monday through Saturday",
            "09:00 to 18:00 IST",
            "emergency support operates 24/7/365",
        ],
    },
    {
        "id": "Q06",
        "topic": "service_credit_policy",
        "query": "What service credit or compensation is provided for ride delays exceeding 20 minutes?",
        "expected_route": "rag",
        "reference_answer": "Delays exceeding 20 minutes attributable to dispatch errors qualify for a ₹50 service voucher valid for 30 days, deposited into the wallet within 24 hours.",
        "key_points": [
            "delays exceeding 20 minutes",
            "₹50 service voucher",
            "valid for 30 days",
            "deposited within 24 hours",
        ],
    },
    {
        "id": "Q07",
        "topic": "escalation_matrix",
        "query": "Who handles Tier-3 escalations for cases unresolved after 8 hours?",
        "expected_route": "rag",
        "reference_answer": "Cases remaining unresolved after 8 hours or involving legal liability escalate directly to the Tier-3 City Operations Head for final executive determination.",
        "key_points": [
            "unresolved after 8 hours",
            "legal liability",
            "Tier-3 City Operations Head",
        ],
    },
    {
        "id": "Q08",
        "topic": "ticket_priority_rules",
        "query": "How are P1 urgent priority tickets defined under Ola operational guidelines?",
        "expected_route": "rag",
        "reference_answer": "P1 Critical tickets are strictly reserved for active passenger safety incidents, medical emergencies, and vehicular accidents occurring during a ride.",
        "key_points": [
            "active passenger safety incidents",
            "medical emergencies",
            "vehicular accidents",
        ],
    },
    {
        "id": "Q09",
        "topic": "outage_communication",
        "query": "How does Ola communicate technical platform outages via in-app banners and push notifications?",
        "expected_route": "rag",
        "reference_answer": "When an outage affects more than 5 percent of active bookings, incident status alerts initiate within 15 minutes via in-app banners, push notifications, and broadcast SMS, with post-mortem reports published within 48 hours.",
        "key_points": [
            "affects more than 5 percent",
            "alerts within 15 minutes",
            "in-app banners, push notifications, and SMS",
            "post-mortem within 48 hours",
        ],
    },
    {
        "id": "Q10",
        "topic": "data_retention_policy",
        "query": "How long are customer support chat transcripts and audit logs retained in live stores and cold storage?",
        "expected_route": "rag",
        "reference_answer": "Active customer tickets and chat transcripts are retained in live production stores for 180 days following ticket resolution, then PII is redacted and records are archived in encrypted cold storage for 3 years.",
        "key_points": [
            "live production stores for 180 days",
            "PII redacted",
            "encrypted cold storage for 3 years",
        ],
    },
    {
        "id": "Q11",
        "topic": "communication_channels",
        "query": "What official support channels like in-app chat, SOS hotline, and email are available for riders?",
        "expected_route": "rag",
        "reference_answer": "Riders and drivers can engage Ola support via real-time in-app chat for trip assistance, a 24/7 SOS emergency telephone hotline connecting within 30 seconds, and formal email to support@olacabs.com.",
        "key_points": [
            "real-time in-app chat",
            "24/7 SOS emergency hotline within 30 seconds",
            "support@olacabs.com",
        ],
    },
    {
        "id": "Q12",
        "topic": "feedback_collection",
        "query": "How is post-ride passenger feedback collected via star ratings and evaluated?",
        "expected_route": "rag",
        "reference_answer": "Within 60 seconds of trip completion, riders receive an in-app prompt to submit a 1-to-5 star rating; ratings of 1 or 2 stars trigger an automated customer care callback inquiry within 4 hours.",
        "key_points": [
            "within 60 seconds of trip completion",
            "1-to-5 star rating",
            "1 or 2 stars trigger callback within 4 hours",
        ],
    },
    # --------------------------------------------------------------------------
    # 2. Operational Ticket Lookup Query
    # --------------------------------------------------------------------------
    {
        "id": "Q13",
        "topic": "ticket_lookup",
        "query": "What is the current status of ticket TKT-0007?",
        "expected_route": "lookup",
        "reference_answer": "Ticket TKT-0007 (Billing) is currently Closed with a resolution time of 2.8 hours. Escalation risk score is 0.0000 (Normal).",
        "key_points": [
            "TKT-0007",
            "Closed",
            "resolution time of 2.8 hours",
            "Escalation risk score",
        ],
    },
    # --------------------------------------------------------------------------
    # 3. Out-of-Scope / Edge-Case Queries (Calibrated Refusal)
    # --------------------------------------------------------------------------
    {
        "id": "Q14",
        "topic": "out_of_scope",
        "query": "Can you provide the best authentic recipe for baking Neapolitan pizza dough?",
        "expected_route": "rag",
        "reference_answer": "I don't know based on the available policy documents.",
        "key_points": [
            "I don't know based on the available policy documents.",
        ],
    },
    {
        "id": "Q15",
        "topic": "out_of_scope",
        "query": "Who won the ICC Cricket World Cup tournament final in 2011?",
        "expected_route": "rag",
        "reference_answer": "I don't know based on the available policy documents.",
        "key_points": [
            "I don't know based on the available policy documents.",
        ],
    },
]

__all__ = ["EVAL_BENCHMARK_QUERIES"]
