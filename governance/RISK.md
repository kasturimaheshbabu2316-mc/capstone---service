# Enterprise AI Risk Classification & Governance

**Track:** Ola (Business Operations / Customer Support)  
**System:** Ola Domain Support Agent  
**Risk Classification:** **MEDIUM Risk** (Customer Support Tickets)

## 1. System Risk Classification & Justification

Under the enterprise AI Low / Medium / High governance taxonomy, this system is classified as **MEDIUM Risk (Customer Support Tickets)**. Customer support operations interact directly with end passengers and driver partners, handling sensitive operational inquiries, private ticket identifiers, operational resolution timelines, and policy-governed escalation determinations. While the system does not possess autonomous financial execution authority (refund disbursements require human-in-the-loop sign-off) and tool permissions are strictly read-only, erroneous policy advice or flawed escalation assessments can cause direct customer frustration, financial disputes, and operational SLA breaches. To mitigate these risks, the application enforces least autonomy tool binding (only the Lookup Agent may execute ticket status queries), strict input/output PII phone masking (`[PHONE_MASKED]`), a 2,000-token request budget, deterministic multi-agent secondary consensus review under AutoGen, and cosine similarity-calibrated refusals on out-of-scope prompts.

## 2. Operation-Level Risk Tier Matrix

| Operation | Risk Level | Description | Mitigation Strategy |
| :--- | :---: | :--- | :--- |
| **Policy FAQ Retrieval** | Low | Reading published customer guidelines and operational SLAs | Cosine similarity thresholding ($\tau = 0.3652$) with calibrated fallback |
| **Ticket Status Lookup** | Medium | Reading customer ticket status, category, and escalation score | Explicit least-autonomy tool permission, read-only SELECT, PII redaction |
| **Database Analytics** | Medium | Aggregating fleet resolution times and ticket volumes | SQL safety guardrails, read-only validation, mandatory `LIMIT 100` |
| **Financial Compensation** | High | Credit voucher issuance and driver fee reversals | Human-in-the-loop escalation recommendation; zero autonomous payout tools |

## 3. Least Autonomy Tool Permissions Registry

- **Retrieval Agent**: Bound strictly to `rag_lookup` (read-only policy store).
- **Lookup Agent**: Bound strictly to `check_support_ticket_status` (read-only ticket database).
- **Composer Agent**: Zero tool bindings (`tools=[]`), precluding autonomous state modification.
- **Reviewer Agents**: Zero tool bindings; secondary compliance audit and redaction under AutoGen.

## 4. Privacy & Telemetry Boundary

All external telemetry tracking is disabled (`CREWAI_DISABLE_TELEMETRY=true`, `OTEL_SDK_DISABLED=true`). Zero unmasked phone numbers appear in disk audit logs.
