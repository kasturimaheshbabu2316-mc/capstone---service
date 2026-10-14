# Risk Assessment & Autonomy Matrix

**Track:** Ola (Business Operations / Customer Support)  
**System:** Ola Domain Support Agent  

## 1. Risk Tier Analysis

| Operation | Risk Level | Description | Mitigation Strategy |
| --- | --- | --- | --- |
| Policy FAQ Retrieval | Low | Reading public policy documents | RAG cosine threshold filtering (T=0.3652) |
| Ticket Status Lookup | Medium | Reading customer ticket status and escalation score | PII masking on input/output, read-only SELECT |
| Database Analytics | Medium | Aggregating resolution times and ticket volumes | SQL guardrails, read-only SELECT, mandatory LIMIT 100 |
| Financial Refund Action | High | Driver cancellation compensation | Human-in-the-loop review, zero tool execution rights |

## 2. Least Autonomy Tool Binding

- **Retrieval Agent:** Bound strictly to `rag_lookup` (read-only policy store).
- **Lookup Agent:** Bound strictly to `check_support_ticket_status` (read-only ticket database).
- **Composer Agent:** Zero tool bindings (`tools=[]`), ensuring no autonomous state mutations.
- **Reviewer Agent:** Zero tool bindings; secondary audit validation under AutoGen.

## 3. Telemetry & Privacy Notice

All external OpenTelemetry and CrewAI telemetry tracking are explicitly disabled (`CREWAI_DISABLE_TELEMETRY=true`, `OTEL_SDK_DISABLED=true`). Customer PII is masked at input and response boundaries.
