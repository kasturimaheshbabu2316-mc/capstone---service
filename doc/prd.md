# Product Requirements Document (PRD)

## Ola Domain Support Agent (Business Operations & Customer Support Track)

---

## 1. Product Overview & Strategic Rationale

The **Ola Domain Support Agent** is an enterprise multi-agent support platform engineered for Ola's customer and business operations. It provides instant, consistent, and policy-grounded assistance to riders, driver partners, and internal customer support representatives across two operational intents:

1. **Policy Questions:** Providing authoritative answers to operational and procedural questions (e.g., ticket priority classification, SLA response times, driver cancellation fees, refund turnaround timelines) strictly derived from an internal knowledge base via Retrieval-Augmented Generation (RAG).
2. **Ticket Status Inquiries:** Providing automated lookups for customer support tickets (e.g., status, resolution time, escalation risk) against a validated operational dataset using structured tool execution.

### Key Operating Constraints

- **100% Deterministic & Offline:** Runs under a deterministic `MOCK_LLM` with zero paid API keys, zero external network calls, and pre-cached local embeddings.
- **Production Governance:** Adheres to the principle of least autonomy, strict token budget caps, Indian PII telephone masking, and transparent JSON-Lines audit logging.
- **Dual-Team Architecture:** Combines a primary CrewAI execution crew with an independent secondary Autogen review team to enforce compliance and eliminate hallucinations.

---

## 2. Target Personas & User Journeys

### Persona 1: Ola Rider (Passenger)

- **Role:** Everyday commuter using Ola ride-hailing services.
- **Goals:** Check refund timelines for canceled rides, understand fare dispute procedures, and check the resolution status of open complaints.
- **Pain Point:** Frustration with vague policy answers or ungrounded commitments regarding compensation.

### Persona 2: Driver Partner

- **Role:** Independent driver operating on the Ola mobility network.
- **Goals:** Inquire about partner support hub hours, understand repeat complaint review criteria, and verify ticket escalation status for vehicle-related disputes.
- **Pain Point:** Lack of transparent communication on escalation timelines and partner support processes.

### Persona 3: Internal Operations Support Lead

- **Role:** Operations manager overseeing support queues, SLA adherence, and team escalation paths.
- **Goals:** Ensure support teams follow the escalation matrix, monitor tickets exceeding resolution thresholds, and maintain consistent policy adherence.
- **Pain Point:** Inconsistent agent interpretation of policy SLAs and delayed escalation of chronic complaints.

### Persona 4: Platform Compliance & AI Governance Auditor

- **Role:** Enterprise risk officer ensuring data protection and responsible AI operation.
- **Goals:** Verify that rider contact numbers are never logged in plain text, agents do not execute unauthorized tools, and responses are auditable via trace IDs.
- **Pain Point:** Silent prompt injection vulnerabilities, data leakage, and unmonitored agent autonomy.

---

## 3. Functional Requirements (FR)

### Part 1: Dataset & RAG Core

- **FR1 (Synthetic Operational Dataset):** Generate a deterministic dataset (`SUPPORT_TICKETS`) of $N = 60$ records using `seed = 42`. The dataset must contain all 5 categories ($\ge 3$ records each), all 5 statuses ($\ge 1$ record each), log-normal resolution times ($0.5\text{--}72.0\text{ hours}$), and an escalation percentage strictly within the $10\%\text{--}30\%$ validation band.
- **FR2 (Knowledge Base Authoring):** Maintain $\ge 12$ distinct Markdown policy documents in `kb/` (2–5 sentences each) with quantitative numbers, SLA hours, and distinct vocabulary boundaries.
- **FR3 (Dual Vector Indexing):** Implement two chunking strategies (fixed $200\text{ char} / 40\text{ overlap}$ and sentence-based regex) indexed into isolated ChromaDB collections (`ola_fixed` and `ola_sentence`) using local `sentence-transformers/all-MiniLM-L6-v2`.
- **FR4 (Empirical Threshold Calibration):** Derive an empirical cosine similarity cutoff $T$ positioned between in-scope ($S_{in}$) and out-of-scope ($S_{out}$) query clusters. Queries below $T$ must return the calibrated fallback `"I don't know based on the provided policies."`.
- **FR5 (Strategy Comparison):** Compute deduplicated parent document precision and recall arithmetic across both collections for $\ge 5$ queries and provide a numbers-cited recommendation.

### Part 2: CrewAI Orchestration, Memory & Guardrails

- **FR6 (Ticket Status & Escalation Tool):** Implement `check_support_ticket_status(record_id: str)` returning status, resolution time, and an escalation risk score:
  $$S_{esc} = 0.6 \cdot \mathbf{1}_{\{\text{escalated}\}} + 0.4 \cdot \left(\frac{\text{days\_since\_created}}{30}\right)$$
  Flagging high risk above the empirical 80th percentile threshold $\tau_{esc}$.
- **FR7 (CrewAI Multi-Agent Core):** Assemble a 3-agent crew (`RetrievalAgent`, `LookupAgent`, `ResponseComposer`) powered by a deterministic `MockLLM` with regression protections for template contamination and schema-based tool routing.
- **FR8 (Conversational Session Memory):** Implement LangChain `InMemoryChatMessageHistory` with `RunnableWithMessageHistory` to resolve multi-turn pronouns ("that one" $\to$ ticket ID) while ensuring cross-session state isolation.
- **FR9 (Structured Output Validation):** Enforce and validate all responses against the Pydantic `SupportResponse` schema.
- **FR10 (Safety Guardrails):** Implement input masking for Indian phone numbers (`[PHONE_MASKED]`), rule-based prompt injection detection, and output groundedness refusal gates.

### Part 3: FastAPI, Logging & Evaluation

- **FR11 (API & Streaming Protocol):** Implement FastAPI endpoints `POST /ask`, `POST /add-document`, and `WS /ws/chat` with structured `WebSocketDisconnect` recovery.
- **FR12 (Structured Audit Logging):** Write append-only JSON-Lines records to `logs/requests.jsonl` containing `trace_id`, execution duration, and pre-masked queries, verified by automated zero-PII leakage tests.
- **FR13 (15-Query Evaluation Benchmark):** Benchmark the agent across 15 queries (12 policy topics, 1 ticket inquiry, 2 adversarial/out-of-scope cases) evaluated on 4 metrics (Accuracy, Grounding, Completeness, Safety) by a deterministic mock judge.

### Part 4: Resilience & Governance

- **FR14 (Autogen Secondary Review):** Route draft responses through a 2-agent `RoundRobinGroupChat` (`PolicyComplianceReviewer` + `FinalEditor`) emitting `StructuredMessage[Verdict]` covering approval and ungrounded claim redaction.
- **FR15 (Four-Layer Governance):** Implement application-layer least autonomy raising `PermissionError` on unauthorized tool wiring, document Medium risk classification, and enforce a 2,000 estimated token budget cap.
- **FR16 (Semantic Response Cache):** Implement an in-memory query cache for grounded policy answers with telemetry tracking and cache invalidation on `POST /add-document`.

---

## 4. Non-Functional Requirements (NFR)

- **NFR1 (Deterministic Offline Execution):** The system must execute without live network access after initial local embedding caching. Environment flags `MOCK_LLM=true`, `CREWAI_DISABLE_TELEMETRY=true`, and `OTEL_SDK_DISABLED=true` must be enforced.
- **NFR2 (Zero Media Assets):** No images, PDFs, videos, or external slides anywhere in the repository. All architectural diagrams must use Markdown/Mermaid.
- **NFR3 (Auditability):** Every request must be traceable via a unique UUIDv4 `trace_id` recorded in `logs/requests.jsonl`.
- **NFR4 (Reproducibility):** Every task must produce a standalone transcript in `transcripts/taskNN_*.txt` reproducible via automated runner scripts.
