# Engineering Standards, Governance Rules & Operational Invariants

## Ola Domain Support Agent (Business Operations & Customer Support Track)

---

## 1. Non-Negotiable System Invariants

### 1.1 Zero-Network & Offline Execution

- The system must operate with zero active internet access and zero paid third-party API keys.
- All embedding inference is performed locally using pre-cached `sentence-transformers/all-MiniLM-L6-v2`.
- Offline environment variables must be enforced across all execution scripts:

  ```ini
  MOCK_LLM=true
  HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1
  ```

### 1.2 Telemetry Suppression

- CrewAI and OpenTelemetry telemetry collection must be explicitly disabled prior to launching any crew execution:

  ```ini
  CREWAI_DISABLE_TELEMETRY=true
  OTEL_SDK_DISABLED=true
  ```

- This configuration must be documented and verified in the repository `README.md`.

### 1.3 Documentation Directory Boundary

- All project Markdown documentation files must reside strictly inside the [`doc/`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/doc/) directory.
- The only permitted exceptions outside `doc/` are:
  - Repository root [`README.md`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/README.md)
  - Governance classification document [`governance/RISK_CLASSIFICATION.md`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/governance/RISK_CLASSIFICATION.md)
- No duplicate documentation files may be created in the repository root.

### 1.4 Absolute Media Asset Prohibition

- No image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`), PDF files (`.pdf`), presentations (`.ppt`, `.pptx`), audio (`.mp3`, `.wav`), or video files (`.mp4`, `.mov`) are permitted anywhere in the repository.
- All system architectures, component topologies, and sequence flows must be represented strictly using Mermaid markdown diagrams or ASCII tables.

---

## 2. Governance & Security Rules

### 2.1 Principle of Least Autonomy (Application Layer)

- Tools must only be bound to explicitly authorized agent roles:
  - `rag_lookup` $\to$ Permitted only for **Retrieval Agent**.
  - `check_support_ticket_status` $\to$ Permitted only for **Lookup Agent**.
  - **Response Composer** $\to$ Granted zero tools.
- Any attempt to wire an unauthorized tool to an agent must immediately raise a runtime `PermissionError`.

### 2.2 Runtime Token Budgeting (Runtime Layer)

- Every incoming query must undergo token budget estimation:
  $$\text{estimated\_tokens} = \left\lceil \frac{\text{len}(\text{raw\_text})}{4} \right\rceil$$
- If $\text{estimated\_tokens} > 2,000$ (e.g., payloads $> 8\text{ KB}$), the gateway must reject the request with HTTP 413 (Payload Too Large) or HTTP 422.
- The system must never silently truncate or execute oversized requests.

### 2.3 PII Sanitization & Zero-Leakage Invariant

- Indian telephone numbers matching the regex `(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b` must be replaced with `[PHONE_MASKED]` prior to downstream agent dispatch and audit logging.
- An automated unit test in `tests/test_logging.py` must assert zero occurrences of raw phone numbers in `logs/requests.jsonl`.
- Customer names, residential addresses, and payment details are explicitly out of scope for masking.

### 2.4 Groundedness & Calibrated Fallbacks

- Policy answers must be derived strictly from retrieved knowledge base chunks.
- If top-1 chunk cosine similarity is below the empirically calibrated threshold $T$, the system must return the exact calibrated refusal:
  `"I don't know based on the provided policies."`

---

## 3. Data & Determinism Rules

### 3.1 Dataset Generation Rules

- The synthetic dataset generator (`dataset.py`) must use a fixed random seed (`seed = 42`).
- Dataset records must never be manually altered or hand-edited to meet rubric bands.
- Invariants:
  - Total records: $N = 60$.
  - All 5 categories must contain $\ge 3$ records.
  - All 5 statuses must contain $\ge 1$ record.
  - Escalation percentage must fall strictly between $10\%$ and $30\%$.

### 3.2 Evaluation & Scoring Determinism

- The 15-query evaluation benchmark (`eval/run_eval.py`) and mock judge (`eval/judge.py`) must be fully rule-based and deterministic.
- Multiple runs of the evaluation suite must produce identical numerical scores across Accuracy, Grounding, Completeness, and Safety.

---

## 4. Engineering & Code Quality Rules

1. **Strict Dependency Pinning:** Dependencies must be declared in [`requirements.txt`](file:///c:/Users/kastu/Desktop/capstone%20-%20service/requirements.txt) with semantic version boundaries compatible with Python 3.12.
2. **Standard Output Discipline:** Execution logs must be written to `logs/requests.jsonl` using JSON-Lines format. Console outputs must remain deterministic and reproducible.
3. **Standalone Transcript Verification:** Each task must have a dedicated runner script in `scripts/` generating its verification transcript in `transcripts/taskNN_*.txt`.
