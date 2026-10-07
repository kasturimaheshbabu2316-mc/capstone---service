# AI System Risk Classification: Ola Domain Support Agent

**System:** Ola Domain Support Agent (`ola-support-agent`)  
**Domain Track:** Business Operations & Customer Support (Ola)  
**Governance Standard:** ISO/IEC 42001 & EU AI Act Risk Alignment  

---

## 1. System Risk Classification: Medium Risk

The Ola Domain Support Agent is classified as a **Medium Risk (Tier 2)** AI application.

### Justification & Trust Boundary Analysis

1. **Direct Operational Impact Without Direct Safety Execution:**  
   The agent interacts directly with external riders, driver-partners, and internal operations staff to provide policy guidance, SLA definitions, monetary refund conditions, and ticket status lookups. While it provides critical operational information, it does not directly control physical vehicle navigation, execute automated payments without human confirmation, or handle dispatch safety commands.

2. **Customer Trust & Financial Rights:**  
   Inaccurate responses regarding cancellation refunds, service credits, or escalation matrices can impact customer rights, driver earnings, and corporate compliance. Consequently, groundedness verification, dual-index cosine thresholding ($T = 0.3652$), and secondary compliance review are strictly enforced.

3. **PII and Data Exposure:**  
   The system processes customer queries which may inadvertently contain personal identifiers such as Indian mobile phone numbers. The input guardrail enforces automatic regex-based masking (`[PHONE_MASKED]`) before queries reach any agent, model, or persistent audit log.

4. **Autonomy Guardrails:**  
   The system enforces Least Autonomy at the application layer: the Response Composer agent is strictly toolless, and the Retrieval and Lookup agents have partitioned, non-overlapping tool registries. Requests exceeding 2,000 estimated tokens are rejected at the gateway.
