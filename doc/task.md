# Task Breakdown & Work Breakdown Structure (WBS)

## Ola Domain Support Agent (Business Operations & Customer Support Track)

---

## 1. Overview & Marks Distribution

The implementation of the **Ola Domain Support Agent** is divided into 16 discrete, sequentially verifiable tasks mapped across 4 project parts totaling 100 marks:

| Part | Description | Scope | Marks |
| :--- | :--- | :--- | :---: |
| **Part 1** | Dataset Design & RAG Core | Tasks 1 – 5 | 30 |
| **Part 2** | CrewAI Orchestration, Tools, Memory & Guardrails | Tasks 6 – 10 | 30 |
| **Part 3** | FastAPI, Audit Logging & Evaluation Suite | Tasks 11 – 13 | 20 |
| **Part 4** | Resilience, Autogen Review & Governance | Tasks 14 – 16 | 20 |
| **Total** | **Full System Delivery** | **16 Tasks** | **100** |

---

## 2. Part 1 — Dataset Design & RAG Core (30 Marks)

### Task 1: Synthetic Dataset Generator

- **Module:** [`dataset.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/dataset.py)
- **Objective:** Generate $N = 60$ realistic support ticket records deterministically using `seed = 42`.
- **Fields:** `record_id`, `category`, `status`, `resolution_time_hours`, `days_since_created`, `escalated`.
- **Validation Criteria:**
  - Category counts: All 5 categories $\ge 3$ records each.
  - Status counts: All 5 statuses $\ge 1$ record each.
  - Escalation band: Strictly within $10\%\text{--}30\%$.
  - Determinism: Two consecutive runs produce byte-identical outputs.
- **Transcript File:** `transcripts/task01_dataset.txt`
- **Runner Command:** `python dataset.py > transcripts/task01_dataset.txt`

---

### Task 2: Knowledge Base Authoring

- **Module:** [`kb/*.md`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/kb/)
- **Objective:** Author 12 distinct Markdown policy documents (2–5 sentences each) with quantitative numbers, SLA hours, and distinct vocabulary boundaries:
  1. `ticket_priority_rules.md`
  2. `sla_by_severity.md`
  3. `escalation_matrix.md`
  4. `refund_compensation_policy.md`
  5. `communication_channels.md`
  6. `business_hours_support.md`
  7. `repeat_complaint_handling.md`
  8. `service_credit_policy.md`
  9. `feedback_collection.md`
  10. `vip_customer_policy.md`
  11. `outage_communication.md`
  12. `data_retention_policy.md`
- **Validation Criteria:** Exactly 12 required files covering all policy topics with zero placeholder text.

---

### Task 3: Dual Chunking Strategies & Vector Indexing

- **Modules:** [`rag/chunking.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/chunking.py), [`rag/index.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/index.py)
- **Objective:** Implement two chunking strategies (fixed 200 char/40 overlap and regex sentence-based) and index chunks into isolated ChromaDB collections (`ola_fixed` and `ola_sentence`).
- **Validation Criteria:** Successful upsert with metadata (`doc_id`, `chunk_index`, `strategy`) and sample retrieval demonstrated for both collections.
- **Transcript File:** `transcripts/task03_chunking.txt`

---

### Task 4: Grounded Generation & Empirical Threshold Calibration

- **Module:** [`rag/generate.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/generate.py)
- **Objective:** Calibrate cosine similarity cutoff $T$ empirically using $\ge 3$ in-scope and $\ge 2$ out-of-scope queries. Formulate threshold $T = \frac{S_{in} + S_{out}}{2}$.
- **Validation Criteria:** Print similarity distributions, document $T$, and demonstrate 5 in-scope answers plus 1 out-of-scope fallback (`"I don't know based on the provided policies."`).
- **Transcript File:** `transcripts/task04_threshold.txt`

---

### Task 5: Strategy Comparison & Evaluation

- **Module:** [`rag/evaluate.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/evaluate.py)
- **Objective:** Evaluate both chunking collections across 5 queries using deduplicated parent document precision and recall arithmetic.
- **Validation Criteria:** Arithmetic table printed for both collections accompanied by a 3-sentence recommendation citing empirical metrics.
- **Transcript File:** `transcripts/task05_chunking_comparison.txt`

---

## 3. Part 2 — CrewAI Orchestration, Tools, Memory & Guardrails (30 Marks)

### Task 6: Ticket Status Tool & Escalation Formula

- **Module:** [`tools/ticket_tool.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/tools/ticket_tool.py)
- **Objective:** Implement `check_support_ticket_status(record_id)` with escalation formula:
  $$S_{esc} = 0.6 \cdot \mathbf{1}_{\{\text{escalated}\}} + 0.4 \cdot \left(\frac{\text{days\_since\_created}}{30}\right)$$
  *(Recency weight zeroed for `Resolved` and `Closed` tickets).*
- **Validation Criteria:** Justify threshold $\tau_{esc}$ against the empirical 80th percentile of dataset scores; print distribution.
- **Transcript File:** `transcripts/task06_ticket_tool.txt`

---

### Task 7: CrewAI 3-Agent Core & Deterministic `MockLLM`

- **Modules:** [`crew/agents.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/crew/agents.py), [`crew/crew.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/crew/crew.py), [`llm/mock_llm.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/llm/mock_llm.py)
- **Objective:** Assemble a 3-agent crew (`RetrievalAgent`, `LookupAgent`, `ResponseComposer`) running under a deterministic `MockLLM` inheriting from `BaseLLM`.
- **Validation Criteria:**
  - Emulate ReAct loop deterministically.
  - Mitigate template contamination (no system prompt leaks).
  - Mitigate tool dispatch bugs (schema-driven routing).
  - Demonstrate both RAG tool and lookup tool invocation.
- **Transcript File:** `transcripts/task07_crew_kickoff.txt`

---

### Task 8: Conversational Session Memory & Pronoun Resolution

- **Module:** [`crew/memory.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/crew/memory.py)
- **Objective:** Implement LangChain `InMemoryChatMessageHistory` with `RunnableWithMessageHistory` to resolve multi-turn pronoun references across turns.
- **Validation Criteria:**
  - Transcript A: Resolves "that one" to `TKT-0007` in multi-turn conversation.
  - Transcript B: Fresh session shows state absence and prompts user for ticket ID.
- **Transcript Files:** `transcripts/task08_memory_session_a.txt` and `transcripts/task08_memory_session_b.txt`

---

### Task 9: Structured Pydantic Output Validation

- **Module:** [`crew/schema.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/crew/schema.py)
- **Objective:** Enforce structured `SupportResponse` Pydantic model validation on all crew outputs.
- **Validation Criteria:** Validated JSON output emitted and checked via `SupportResponse.model_validate()`.
- **Transcript File:** `transcripts/task09_structured_output.txt`

---

### Task 10: Multi-Tier Guardrails

- **Modules:** [`guardrails/input_guard.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/guardrails/input_guard.py), [`guardrails/output_guard.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/guardrails/output_guard.py)
- **Objective:** Implement phone masking (`[PHONE_MASKED]`), adversarial prompt injection detection, and output groundedness refusal gates.
- **Validation Criteria:** Demonstrate each guardrail triggering appropriately.
- **Transcript File:** `transcripts/task10_guardrails.txt`

---

## 4. Part 3 — FastAPI, Audit Logging & Evaluation Suite (20 Marks)

### Task 11: FastAPI Endpoints & WebSocket Resilience

- **Module:** [`api/main.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/api/main.py)
- **Objective:** Implement `POST /ask`, `POST /add-document`, and `WS /ws/chat`. Handle `WebSocketDisconnect` cleanly.
- **Validation Criteria:** Demonstrate HTTP endpoints and test WebSocket disconnection mid-session confirming server stability.
- **Transcript File:** `transcripts/task11_websocket.txt`

---

### Task 12: Structured JSON-Lines Audit Logging

- **Module:** [`api/logging_utils.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/api/logging_utils.py)
- **Objective:** Emit append-only JSONL logs to `logs/requests.jsonl` with `trace_id`, execution duration, and pre-sanitized queries.
- **Validation Criteria:** Automated test greps `logs/requests.jsonl` asserting zero occurrences of raw phone numbers.
- **Transcript File:** `transcripts/task12_logging.txt`

---

### Task 13: 15-Query Evaluation Benchmark

- **Modules:** [`eval/test_queries.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/eval/test_queries.py), [`eval/judge.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/eval/judge.py), [`eval/run_eval.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/eval/run_eval.py)
- **Objective:** Benchmark the agent across 15 queries (12 policy topics, 1 ticket lookup, 2 adversarial/out-of-scope cases) evaluated on 4 metrics (Accuracy, Grounding, Completeness, Safety) by a deterministic mock judge.
- **Validation Criteria:** Format 15-row table with individual scores and 4 summary averages.
- **Transcript File:** `transcripts/task13_eval.txt`

---

## 5. Part 4 — Resilience, Autogen Review & Governance (20 Marks)

### Task 14: Autogen Secondary Review Stage

- **Module:** [`review/autogen_review.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/review/autogen_review.py)
- **Objective:** Implement a 2-agent `RoundRobinGroupChat` (`PolicyComplianceReviewer` + `FinalEditor`) emitting `StructuredMessage[Verdict]`.
- **Validation Criteria:**
  - Demo 1 (Approve): Faithful response $\to$ `approved = True`, `final_answer == draft`.
  - Demo 2 (Revise): Injected hallucination $\to$ `approved = False`, ungrounded claim redacted.
- **Transcript File:** `transcripts/task14_autogen_review.txt`

---

### Task 15: Four-Layer Governance

- **Modules:** [`governance/least_autonomy.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/governance/least_autonomy.py), [`governance/budget.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/governance/budget.py), [`governance/RISK_CLASSIFICATION.md`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/governance/RISK_CLASSIFICATION.md)
- **Objective:** Enforce application least autonomy raising `PermissionError`, document Medium risk classification, and reject queries $> 2,000$ estimated tokens with HTTP 413.
- **Validation Criteria:** Demonstrate blocked unauthorized tool wiring and rejected oversized payloads.
- **Transcript File:** `transcripts/task15_least_autonomy.txt`

---

### Task 16: Semantic Response Caching

- **Module:** [`cache.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/cache.py)
- **Objective:** Implement an in-memory normalized query cache for policy responses with call counters and invalidation upon `POST /add-document`.
- **Validation Criteria:** Demonstrate cold cache vs warm cache latency reduction and counter stability (`llm_calls = 1`, `cache_hits = 1`).
- **Transcript File:** `transcripts/task16_cache.txt`
