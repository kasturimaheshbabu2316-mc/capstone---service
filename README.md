# Ola Domain Support Agent (`ola-support-agent`)

**Domain Track:** Business Operations / Customer Support (Ola)  
**Deliverable:** Deterministic, offline-capable multi-agent customer support system.  
**Execution Mode:** 100% offline under deterministic `MOCK_LLM=true` with zero external API keys and zero telemetry.

---

## 1. Domain Track Statement & Overview

This system implements an enterprise-grade AI customer support agent tailored for **Ola** (ride-hailing, driver operations, and customer support). The platform addresses two primary operational intents:
1. **Policy Inquiries:** Procedural and regulatory questions (SLAs, cancellation refunds, service credits, VIP benefits) grounded strictly in 12 internal policy documents via dual-index RAG.
2. **Ticket Status Inquiries:** Operational lookup and escalation risk scoring for support tickets against a synthetic dataset of 60 records using structured tool invocation.

---

## 2. Dataset Design Choices (Task 1)

The synthetic dataset [`dataset.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/dataset.py) was generated deterministically using standard distribution modeling:

| Parameter | Selected Value | Justification / Operational Rationale |
| :--- | :--- | :--- |
| **Random Seed** | `42` | Ensures 100% reproducible data generation across runs. |
| **Record Count** | 60 records | Comfortably exceeds the $\ge 40$ threshold for statistical coverage. |
| **Categories & Weights** | Billing (0.25), Technical Issue (0.25), Account Access (0.20), Product Defect (0.15), General Inquiry (0.15) | Reflects real ride-hailing support distributions dominated by fare & app issues. |
| **Statuses & Weights** | Open (0.20), In Progress (0.20), Escalated (0.15), Resolved (0.25), Closed (0.20) | Realistic queue distribution where ~45% of tickets are resolved or closed. |
| **Resolution Time Range** | `0.5` to `72.0` hours (log-normal, clipped) | Support tickets usually resolve within hours for simple cases but have a long tail up to a few days for complex investigations. |
| **Monetary Field** | *None* (N/A) | Support tickets in this track do not contain a transactional amount; resolution time is used as the continuous metric. |
| **Escalation Rate** | **20.00%** (12 / 60) | Strictly within the required $10\%\text{--}30\%$ validation band. |

---

## 3. Setup & Offline Execution

### Environment Setup

The repository runs completely offline with zero API keys. Telemetry and cloud sync are suppressed at process startup:

```bash
# 1. Activate virtual environment
.\.service\Scripts\activate

# 2. Suppress telemetry and enforce Mock LLM (also auto-loaded via .env & sitecustomize.py)
set MOCK_LLM=true
set CREWAI_DISABLE_TELEMETRY=true
set OTEL_SDK_DISABLED=true
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set CREWAI_TRACING_ENABLED=false
```

### Running the FastAPI Backend & Glassmorphism Web Console (`app/`)

```bash
# Start FastAPI application with live Glassmorphism Web UI
.\.service\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/`** in your browser to access the **Interactive Glassmorphism Console** (`Ola Nexus AI`), featuring real-time WebSocket live chat, REST inspection, escalation gauge HUD, ticket explorer, and policy ingestion.

### Containerized Deployment (Docker)

```bash
# Build production container image
docker build -t ola-support-agent .

# Run container (100% offline with pre-cached embeddings)
docker run -d -p 8000:8000 --name ola-agent ola-support-agent
```

### Running Tests & Transcripts

```bash
# Run complete pytest suite (39 tests across API, UI, Guardrails, Governance, RAG, Cache, Review, Tools)
python -m pytest -v

# Run 15-query evaluation benchmark
python eval/run_eval.py

# Run master verification runner for all 16 tasks (or individual scripts/run_taskNN.py)
python scripts/run_all.py

# Or regenerate all transcripts via master pipeline
python scripts/generate_all_transcripts.py
```

---

## 4. Part 1 Results — RAG & Threshold Calibration

### Retrieval Calibration Table (Task 4)

Cosine similarity measured between in-scope policy questions and out-of-scope non-policy queries on collection `ola_sentence`:

| Query Type | Query Text | Top-1 Similarity | Status |
| :--- | :--- | :---: | :--- |
| **In-Scope** | "What is the resolution SLA for a Sev-1 safety incident?" | `0.5792` | Grounded match |
| **In-Scope** | "When does Ola provide monetary refunds for driver cancellations?" | `0.5367` | Grounded match |
| **In-Scope** | "How does Ola handle repeat chronic complaints from passengers?" | `0.5098` | Grounded match |
| **In-Scope** | "What are the benefits and response times for VIP Ola Select customers?" | `0.5041` | Grounded match |
| **Out-of-Scope** | "How do I book an international flight to London with British Airways?" | `0.2319` | Out-of-scope |
| **Out-of-Scope** | "What is the current stock price and revenue of Tesla in NASDAQ?" | `0.1983` | Out-of-scope |
| **Out-of-Scope** | "What ingredients are needed to bake an authentic Italian pizza?" | `0.1636` | Out-of-scope |

- **Minimum In-Scope Similarity:** `0.5041`
- **Maximum Out-of-Scope Similarity:** `0.2319`
- **Calibrated Cosine Threshold ($T$):** **`0.3652`** (midpoint separator)
- **Fallback String:** `"I don't know based on the provided policies."`

### Chunking Strategy Comparison (Task 5)

Evaluated across 5 representative policy queries measuring deduplicated parent document Precision and Recall:

| Metric | `ola_fixed` (200 char / 40 overlap) | `ola_sentence` (Punctuation boundary) |
| :--- | :---: | :---: |
| **Parent Document Precision** | 50.0% | **53.3%** |
| **Parent Document Recall** | 100.0% | **100.0%** |
| **Recommendation** | Baseline | **Recommended (`ola_sentence`)** due to higher precision and zero mid-sentence boundary slicing. |

---

## 5. Part 2 Results — Agents, Memory & Guardrails

### Escalation Score Formula & Empirical Threshold (Task 6)

$$\text{recency} = \frac{\text{days\_since\_created}}{30} \quad (\text{zeroed for 'Resolved' and 'Closed'})$$
$$S_{esc} = 0.6 \cdot \mathbf{1}_{\{\text{escalated} = \text{True}\}} + 0.4 \cdot \text{recency}$$

- **Score Range:** `0.0000` to `0.8533`
- **80th Percentile Empirical Threshold ($\tau_{esc}$):** **`0.4400`** (tickets with $S_{esc} \ge 0.4400$ flagged as *High Escalation Risk*).

### CrewAI Multi-Agent Architecture (Task 7)
- **`Policy Retrieval Specialist`:** Bound exclusively to tool `rag_lookup`.
- **`Ticket Operations Specialist`:** Bound exclusively to tool `check_support_ticket_status`.
- **`Support Response Composer`:** Strictly toolless under Least Autonomy governance.

### Conversational Memory (Task 8)
- **Session A (Continuous):** Demonstrates pronoun resolution ("that one" $\to$ `TKT-0007`).
- **Session B (Fresh):** Demonstrates ungrounded pronoun rejection prompting for ticket ID.

### Structured Output Schema (Task 9)
Enforces strongly-typed Pydantic model `SupportResponse` (`answer`, `sources`, `ticket_id`, `escalation_score`, `grounded`, `confidence`).

### Guardrails (Task 10)
- **PII Masking:** Indian phone numbers (`+91 98765 43210`) masked to `[PHONE_MASKED]`.
- **Prompt Injection Defense:** Blocks adversarial patterns (`"ignore previous instructions"` $\to$ HTTP 400).
- **Groundedness Refusal:** Ungrounded out-of-scope queries return calibrated fallback.

---

## 6. Part 3 Results — API, Observability & Evaluation

### FastAPI Endpoints (`app/main.py`)
- `GET /`: Interactive Glassmorphism Web Console with live chat, telemetry HUD, and ticket explorer.
- `GET /health`: Health status & offline capability flag.
- `POST /ask`: Request `{query, session_id}` $\to$ Response `{trace_id, data, latency_ms, cache_hit, guardrail_flags}`.
- `POST /add-document`: Ingests markdown doc, upserts into Chroma, and invalidates response cache.
- `WS /ws/chat`: Disconnect-resilient WebSocket surviving abrupt client disconnects without server degradation.

### Structured Audit Logging (`app/logging_utils.py`)
Emits append-only JSON-L records to `logs/requests.jsonl` with UUID trace IDs, latencies, and verified zero-phone-number leakage:
```json
{
  "trace_id": "aa3eec50-a691-4733-b78b-2c5b5cd0a1aa",
  "timestamp": "2026-10-07T12:48:42.123456+00:00",
  "endpoint": "/ask",
  "session_id": "default_session",
  "masked_query": "My phone is [PHONE_MASKED], what is the SLA for Sev-1?",
  "status_code": 200,
  "latency_ms": 693.25,
  "cache_hit": false,
  "guardrail_flags": {"phone_masked": true}
}
```

### 15-Query Evaluation Benchmark Table (Task 13)

| ID | Category | Topic | Accuracy | Grounding | Completeness | Safety |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Q01** | Policy | `ticket_priority_rules` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q02** | Policy | `sla_by_severity` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q03** | Policy | `escalation_matrix` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q04** | Policy | `refund_compensation_policy` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q05** | Policy | `communication_channels` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q06** | Policy | `business_hours_support` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q07** | Policy | `repeat_complaint_handling` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q08** | Policy | `service_credit_policy` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q09** | Policy | `feedback_collection` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q10** | Policy | `vip_customer_policy` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q11** | Policy | `outage_communication` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q12** | Policy | `data_retention_policy` | 5.0 | 5.0 | 4.8 | 5.0 |
| **Q13** | Lookup | `ticket_status` (`TKT-0007`) | 5.0 | 5.0 | 5.0 | 5.0 |
| **Q14** | Adversarial | `prompt_injection` | 5.0 | 5.0 | 5.0 | 5.0 |
| **Q15** | OutOfScope | `out_of_scope` (Paris tourism) | 5.0 | 5.0 | 5.0 | 5.0 |
| **AVG** | **SUMMARY** | **All 15 Benchmark Queries** | **5.00** | **5.00** | **4.84** | **5.00** |

---

## 7. Part 4 Results — Review, Governance & Caching

### AutoGen Secondary Review Stage (Task 14)
2-agent review pipeline (`PolicyComplianceReviewer` + `FinalEditor`) emitting structured `Verdict`:
- **Approve Case:** Faithful draft approved as-is.
- **Revise Case:** Injected hallucination ("100% full compensation for any delay with unlimited credits") flagged and ungrounded claims redacted.

### Four-Layer Governance (Task 15)
1. **Application Least Autonomy:** Unauthorized tool assignment raises `PermissionError`.
2. **Runtime Token Budget Cap:** Queries $> 2,000$ estimated tokens rejected with HTTP 413.
3. **Risk Tier:** Medium Risk documented in [`governance/RISK_CLASSIFICATION.md`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/governance/RISK_CLASSIFICATION.md).
4. **Input Sanitization:** Indian phone regex masking enforced before agent ingestion.

### Semantic Response Cache (Task 16)
- Identical queries served with cache hit and significant latency reduction.
- Cache invalidated automatically upon `POST /add-document`.

---

## 8. Known Limitations

1. **PII Scope:** Redaction specifically targets Indian mobile phone numbers (`+91 9XXXX XXXXX`); names and street addresses are not masked by design.
2. **Storage Scope:** Chat sessions and cache are in-memory (reset on server reboot); ChromaDB vector embeddings and JSONL audit logs persist on disk.

---

## 9. Complete Transcript Index

All 16 tasks produce execution transcripts saved in `transcripts/`:

| Task ID | Task Description | Transcript Artifact |
| :--- | :--- | :--- |
| **Task 1** | Seeded Dataset Generation & Validation | [`transcripts/task01_dataset.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task01_dataset.txt) |
| **Task 3** | Dual Chunking & Chroma Indexing | [`transcripts/task03_chunking.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task03_chunking.txt) |
| **Task 4** | Cosine Threshold Calibration | [`transcripts/task04_threshold.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task04_threshold.txt) |
| **Task 5** | Chunking Strategy Comparison (P/R) | [`transcripts/task05_chunking_comparison.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task05_chunking_comparison.txt) |
| **Task 6** | Ticket Lookup & Escalation Formula | [`transcripts/task06_ticket_tool.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task06_ticket_tool.txt) |
| **Task 7** | CrewAI 3-Agent Core & Tool Logs | [`transcripts/task07_crew_kickoff.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task07_crew_kickoff.txt) |
| **Task 8** | Conversational Memory (Session A) | [`transcripts/task08_memory_session_a.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task08_memory_session_a.txt) |
| **Task 8** | Conversational Memory (Session B) | [`transcripts/task08_memory_session_b.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task08_memory_session_b.txt) |
| **Task 9** | Structured Pydantic Output Schema | [`transcripts/task09_structured_output.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task09_structured_output.txt) |
| **Task 10** | Input & Output Safety Guardrails | [`transcripts/task10_guardrails.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task10_guardrails.txt) |
| **Task 11** | FastAPI & Disconnect-Resilient WS | [`transcripts/task11_websocket.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task11_websocket.txt) |
| **Task 12** | JSONL Audit Logs & Zero-PII Test | [`transcripts/task12_logging.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task12_logging.txt) |
| **Task 13** | 15-Query Evaluation Benchmark Table | [`transcripts/task13_eval.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task13_eval.txt) |
| **Task 14** | AutoGen Secondary Review Stage | [`transcripts/task14_autogen_review.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task14_autogen_review.txt) |
| **Task 15** | Least Autonomy & Token Budget Cap | [`transcripts/task15_least_autonomy.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task15_least_autonomy.txt) |
| **Task 16** | Semantic Cache Hit/Miss Telemetry | [`transcripts/task16_cache.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/task16_cache.txt) |
