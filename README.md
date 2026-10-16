# Track completed: Ola (Business Operations / Customer Support)

## Ola Domain Support Agent — Operational Intelligence & Support System

## 1. Dataset Design Choices

- **Deterministic Random Seed**: `SEED = 42` (yielding byte-identical output across repeated runs).
- **Total Ticket Volume**: `TOTAL_RECORDS = 60` (satisfying the `≥ 40` requirement).
- **Category Weights**:
  - `Billing`: 0.25 (Yield: 22 records, `≥ 3` threshold met)
  - `Technical Issue`: 0.25 (Yield: 8 records, `≥ 3` threshold met)
  - `Account Access`: 0.20 (Yield: 8 records, `≥ 3` threshold met)
  - `Product Defect`: 0.15 (Yield: 9 records, `≥ 3` threshold met)
  - `General Inquiry`: 0.15 (Yield: 13 records, `≥ 3` threshold met)
- **Status Weights**:
  - `Open`: 0.20 (Yield: 11 records, `≥ 1` threshold met)
  - `In Progress`: 0.20 (Yield: 15 records, `≥ 1` threshold met)
  - `Escalated`: 0.15 (Yield: 9 records, `≥ 1` threshold met)
  - `Resolved`: 0.25 (Yield: 12 records, `≥ 1` threshold met)
  - `Closed`: 0.20 (Yield: 13 records, `≥ 1` threshold met)
- **Resolution Time Range & Distribution**: `[1.0, 72.0]` hours using log-normal distribution (`μ = 2.2`, `σ = 0.8`).
  - *Observed Values*: Min 1.7 hours, Max 48.6 hours, Mean 11.5 hours.
  - *Justification*: Support ticket resolution times range from 1.0 to 72.0 hours, reflecting rapid first-tier billing corrections through to maximum multi-day technical and safety escalations.
- **Escalation Coupling & Invariant**:
  - Escalation probability is conditioned on operational status: `P(escalated | status = 'Escalated') = 0.85` vs `P(escalated | other) = 0.08`.
  - *Overall Escalation Rate*: Exactly **20.00%** (12 / 60 tickets), landing strictly within the mandated `[10%, 30%]` compliance band.

## 2. Threshold Calibration

To prevent hallucinations while ensuring valid operational policy queries are never falsely rejected, the retrieval threshold $T$ is empirically calibrated rather than assigned an arbitrary default (e.g. 0.5/0.6/0.7). Top-1 cosine similarity scores are measured across in-scope and deliberately out-of-scope query clusters:

### In-Scope Query Cluster ($\ge 4$ queries)

| Query | Top-1 Doc ID | Cosine Similarity |
| --- | --- | :---: |
| "When does Ola provide monetary refunds for driver cancellations?" | `refund_compensation_policy` | 0.7153 |
| "How does Ola handle repeat chronic complaints from passengers?" | `repeat_complaint_handling` | 0.6884 |
| "What is the resolution SLA for a Sev-1 safety incident?" | `sla_by_severity` | 0.6299 |
| "What compensation is provided for ride delays exceeding 20 minutes?" | `test_cancellation_clause` | 0.5726 |
| "What are the benefits and response times for VIP Ola Select customers?" | `vip_customer_policy` | 0.5325 |
| **Cluster Minimum ($\min(S_{\text{in}}))** | | **0.5325** |

### Out-of-Scope Distractor Cluster ($\ge 3$ queries)

| Query | Top-1 Doc ID | Cosine Similarity |
| --- | --- | :---: |
| "How do I book an international flight to London with British Airways?" | `communication_channels` | 0.1979 |
| "What is the current stock price of Tesla on NASDAQ?" | `business_hours_support` | 0.1449 |
| "Who won the cricket world cup?" | `feedback_collection` | 0.1158 |
| "What is the best authentic Italian pizza recipe?" | `ticket_priority_rules` | 0.0794 |
| **Cluster Maximum ($\max(S_{\text{out}}))** | | **0.1979** |

### Midpoint Formulation & Decision Rule

$$T = \frac{\min(S_{\text{in}}) + \max(S_{\text{out}})}{2} = \frac{0.5325 + 0.1979}{2} = \mathbf{0.3652}$$

- **Symmetric Safety Margin**: $\Delta = \frac{0.5325 - 0.1979}{2} = \mathbf{0.1673}$ above the highest out-of-scope query and below the lowest in-scope query.
- **Decision Rule**:
  $$\text{Action} = \begin{cases} \text{Extractive Answer (MOCK\_LLM)} & \text{if } \text{similarity} \ge 0.3652 \\ \text{"I don't know based on the available policy documents."} & \text{if } \text{similarity} < 0.3652 \end{cases}$$
- **Artifact**: Full calibration data is preserved in [`rag/threshold.json`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/threshold.json).

## 3. Chunking Comparison

Both chunking strategies were evaluated against the 6 benchmark support queries using deduplicated parent document retrieval ($k=3$):

- **Precision**: $\frac{|\text{retrieved} \cap \text{relevant}|}{|\text{retrieved}|}$
- **Recall**: $\frac{|\text{retrieved} \cap \text{relevant}|}{|\text{relevant}|}$

### Comparative Evaluation Metrics

| Query ID | Benchmark Query | Relevant Doc | `kb_fixed` (P / R) | `kb_sentence` (P / R) |
| :---: | --- | --- | :---: | :---: |
| **Q1** | What is the resolution SLA for a Sev-1 safety incident? | `sla_by_severity` | $1/2 = 0.500$ / $1/1 = 1.000$ | $1/1 = \mathbf{1.000}$ / $1/1 = \mathbf{1.000}$ |
| **Q2** | Under what condition are driver cancellation fees refunded? | `refund_compensation_policy` | $1/2 = 0.500$ / $1/1 = 1.000$ | $1/2 = 0.500$ / $1/1 = 1.000$ |
| **Q3** | What happens when a customer logs 3 complaints within 14 days? | `repeat_complaint_handling` | $1/2 = 0.500$ / $1/1 = 1.000$ | $1/2 = 0.500$ / $1/1 = 1.000$ |
| **Q4** | Operating hours for driver partner physical onboarding centers? | `business_hours_support` | $1/2 = 0.500$ / $1/1 = 1.000$ | $1/2 = 0.500$ / $1/1 = 1.000$ |
| **Q5** | Service credit for ride delays exceeding 20 minutes? | `service_credit_policy` | $1/3 = 0.333$ / $1/1 = 1.000$ | $1/2 = \mathbf{0.500}$ / $1/1 = 1.000$ |
| **Q6** | Benefits and response times for VIP Ola Select customers? | `vip_customer_policy` | $1/2 = 0.500$ / $1/1 = 1.000$ | $1/1 = \mathbf{1.000}$ / $1/1 = \mathbf{1.000}$ |
| **Macro Average** | | | **P: 47.2% \| R: 100.0%** | **P: 66.7% \| R: 100.0%** |

### Empirical Recommendation & Production Decision
>
> **Recommendation:**  
> Across the benchmark evaluation queries, sentence-based chunking (`kb_sentence`) achieved a macro-averaged precision of **66.7%** and recall of **100.0%**, significantly outperforming fixed-size chunking (`kb_fixed`) which scored **47.2%** precision. Fixed-size chunking frequently splits operational policy rules across arbitrary character windows and introduces irrelevant cross-document neighbors. Consequently, `kb_sentence` is designated as the winning collection and primary index for all downstream grounded generation and agent workflows.

- **Artifact**: Saved in [`rag/recommended.json`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/rag/recommended.json) and [`transcripts/05_chunk_eval.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/05_chunk_eval.txt).

## 4. Escalation Formula & Threshold Justification

To prevent arbitrary heuristic escalation decisions and avoid bare Boolean OR logic (`escalated or days > 14`), escalation risk is quantified as a continuous metric $S_{\text{esc}} \in [0.0, 1.0]$ evaluated by `check_support_ticket_status(record_id)` in [`tools/ticket_tool.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/tools/ticket_tool.py).

### Exact Mathematical Formula & Weight Justification

$$S_{\text{esc}} = w_1 \cdot \text{escalated} + w_2 \cdot \left(\frac{\text{days\_since\_created}}{30}\right)$$

Where:

- $\text{escalated} \in \{0.0, 1.0\}$: Binary indicator whether customer support has flagged the ticket for managerial escalation.
- $\text{days\_since\_created} \in [0, 30]$: Operational days elapsed since ticket ingestion (clipped to $[0, 30]$).
- **Weight Assignments**:
  - $w_1 = \mathbf{0.60}$: Heavy priority placed on confirmed operational escalations (safety, high financial dispute, repeated failure).
  - $w_2 = \mathbf{0.40}$: Linear aging penalty scaled across a standard 30-day resolution horizon.
  - Normalization constraint: $w_1 + w_2 = 1.00$, strictly bounding $S_{\text{esc}} \in [0.0, 1.0]$.
- **Lifecycle Refinement (Recency Zeroing)**:
  - When ticket `status \in {"Resolved", "Closed"}`, the support interaction is completed. Aging recency is zeroed out ($\text{recency} = 0.0$), ensuring resolved historical cases do not falsely accumulate escalation risk.

### Empirical Distribution Analysis ($N=60$, Seed 42)

The baseline operational dataset ([`dataset.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/dataset.py)) yields the following empirical parameter distributions:

| Metric | `days_since_created` (Days) | `escalation_score` ($S_{\text{esc}}$) | Operational Meaning |
| :--- | :---: | :---: | :--- |
| **Minimum** | 0.00 | 0.0000 | Fresh unescalated ticket (or resolved ticket) |
| **Maximum** | 30.00 | 1.0000 | Confirmed escalation at maximum lifecycle staleness |
| **Mean ($\mu$)** | 14.90 | 0.2416 | Fleet average operational workload |
| **50th Percentile (Median)** | 15.00 | 0.1267 | Routine ticket operational baseline |
| **80th Percentile ($P_{80}$)** | **23.00** | **0.4400** | Calibrated escalation threshold ($\tau = 0.4400$) |

### Threshold Justification ($\tau = 0.4400$)

The escalation decision rule is defined as:
$$\text{recommend\_escalation} = \begin{cases} \mathbf{True} & \text{if } S_{\text{esc}} \ge \mathbf{0.4400} \\ \mathbf{False} & \text{if } S_{\text{esc}} < \mathbf{0.4400} \end{cases}$$

1. **Empirical 80th-Percentile Cutoff**: Setting $\tau = 0.4400$ isolates the top 20% highest-risk support cases for supervisor intervention and proactive re-assignment.
2. **Deterministic Trigger for Active Escalations**: Because $w_1 = 0.60 \ge \tau = 0.4400$, **any** ticket with `escalated = True` immediately exceeds the threshold regardless of recency ($S_{\text{esc}} \ge 0.60$).
3. **Noise Suppression for Aging Routine Tickets**: An unescalated active ticket at the 80th-percentile age ($23.0\text{ days}$) yields:
   $$S_{\text{esc}} = 0.6 \cdot 0 + 0.4 \cdot \left(\frac{23.0}{30}\right) = \mathbf{0.3067} < 0.4400$$
   Even an active unescalated ticket at maximum age ($30\text{ days}$) scores $0.4000 < 0.4400$. Normal aging alone never causes false alarms without compounding operational escalation.
4. **Tool API Contract**:
   - Known ticket lookup: Returns `status`, `resolution_time_hours`, `escalation_score`, `recommend_escalation`, `risk_level`, and `category`.
   - Unknown ticket lookup: Returns explicit `error` key with safe defaults (`status="Unknown"`, `escalation_score=None`, `recommend_escalation=False`).
   - Saved execution run output: [`transcripts/06_ticket_tool.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/06_ticket_tool.txt).

## 5. FastAPI Service Architecture & Structured Audit Logging

The production backend is deployed using FastAPI ([`api/main.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/api/main.py)) with lifespan-managed model caching and thread-safe structured audit logging ([`api/logging_setup.py`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/api/logging_setup.py)).

### 1. Lifespan Resource Management

- **One-Time Startup Loading**: The `lifespan` context manager preloads the `SentenceTransformer("all-MiniLM-L6-v2")` embedding model and opens the winning ChromaDB collection (`kb_sentence`) once at server boot, attaching them to `app.state`.
- **Zero Per-Request Overhead**: Requests utilize preloaded singleton handles, avoiding repeated disk IO or model deserialization.

### 2. API Endpoints & Status Code Contracts

| Endpoint | Method | Request / Payload | Response Schema | Status Code Behaviors |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | `GET` | None | `HealthResponse` | `200 OK` (`{status: "healthy", mock_llm: true, kb_ready: true, db_ready: true}`) |
| `/ask` | `POST` | `AskRequest{question, session_id}` | `AskResponse` (`CrewResponse` + `trace_id` + `latency_ms`) | `200 OK`; `400 Bad Request` (prompt injection block); `413 Payload Too Large` (token budget exceeded); `422 Unprocessable Entity` (Pydantic validation); `500 Internal Server Error` (safe JSON, no traceback) |
| `/add-document` | `POST` | `AddDocumentRequest{title, text}` | `AddDocumentResponse` | `200 OK` (sentence-chunks, embeds, and upserts into `kb_sentence`, invalidating semantic cache) |
| `/ws/chat` | `WebSocket` | Multi-turn text stream | `{"type": "response", "data": CrewResponse, ...}` | Clean `WebSocketDisconnect` recovery without crashing server |

### 3. Structured Audit Logging & Zero-PII Guarantee

Every incoming request appends a single JSON-Lines record to [`logs/requests.jsonl`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/logs/requests.jsonl) adhering to the strict schema:

```json
{
  "trace_id": "40f2c3d3-e800-49ca-95d0-c4a04a2015e1",
  "timestamp": "2026-10-15T08:48:17.575660+00:00",
  "endpoint": "/ws/chat",
  "session_id": "ws_d3dcbd98",
  "masked_question": "What is the SLA for a Sev-1 safety incident?",
  "route": "rag",
  "latency_ms": 229.92,
  "status_code": 200,
  "cache_hit": false,
  "guardrail_flags": {
    "phone_masked": false,
    "grounded": true
  }
}
```

- **Strict PII Redaction Before Persistence**: The Step 9 `mask_pii()` filter is executed prior to appending to the file stream. Raw phone numbers (`+91 98765 43210`, `9876543210`, `98765-43210`) are replaced with `[PHONE_MASKED]`, guaranteeing zero raw phone numbers appear in disk logs.
- **Trace Transcript**: All curl requests and responses are recorded in [`transcripts/11_api.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/transcripts/11_api.txt).

## 6. How to Run

### Run the FastAPI Backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run the Complete Test Suite

```bash
pytest -v
```

### Telemetry Disabled Note

> **Telemetry Disabled Notice:**  
> All OpenTelemetry and CrewAI telemetry tracking are strictly disabled by default (`CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true`). The system operates 100% offline with zero external network tracking or third-party telemetry calls.
