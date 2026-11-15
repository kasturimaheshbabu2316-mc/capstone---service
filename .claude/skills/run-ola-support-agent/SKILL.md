---
name: run-ola-support-agent
description: Run the Ola Domain Support Intelligence platform — FastAPI backend with enterprise Glassmorphism web UI, Streamlit fallback console, and full multi-agent CrewAI pipeline (offline MOCK_LLM mode)
---

# Ola Domain Support Agent — Run Skill

**App type**: Python FastAPI service + Static Web UI + Streamlit fallback  
**Drive method**: Background server + `curl` smoke tests / browser automation via `chromium-cli`  
**Key paths**: `api/main.py` (FastAPI), `static/index.html` (Web UI), `streamlit_app.py` (Streamlit)

---

## Prerequisites (verified on this container)

```bash
# System: Python 3.11 or 3.12 (3.13+ not supported by crewai/langchain stack)
# This container has Python 3.14 - use C:/Python314/python.exe for testing
# One-time model download (needs internet):
python scripts/prefetch_models.py
```

**Core dependencies** (pinned in `requirements.txt`):
- `fastapi==0.162.0`, `uvicorn[standard]==0.54.0`
- `crewai==1.15.33`, `langchain==1.4.7`, `langchain-core==1.7.3`
- `autogen-agentchat==0.7.5`, `autogen-ext==0.7.5`
- `chromadb==1.5.9`, `sentence-transformers==6.2.0`
- `numpy==2.4.6`, `pydantic==2.12.5`
- `python-dotenv==1.2.4`, `pytest==9.2.0`, `pytest-asyncio==1.4.1`

---

## Build & Setup (verified commands)

```bash
# 1. Create venv (Python 3.11/3.12 required for crewai compat)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# 2. Install pinned deps
pip install -r requirements.txt

# 3. Copy environment config
cp .env.example .env

# 4. One-time model prefetch (downloads all-MiniLM-L6-v2 to HF cache)
python scripts/prefetch_models.py

# 5. Run ingestion & ChromaDB indexing
python rag/index.py
```

---

## Run (Agent Path — Primary)

### Option A: FastAPI + Web UI (port 8000)

```bash
# Export env vars (match run.sh / run.bat)
export MOCK_LLM=true
export CREWAI_DISABLE_TELEMETRY=true
export OTEL_SDK_DISABLED=true
export ADMIN_TOKEN=change-me-demo-token

# Start uvicorn (lifespan preloads embedding model + ChromaDB kb_sentence)
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Verify health
curl -s http://127.0.0.1:8000/health
# {"status":"ok","mock_llm":true,"kb_ready":true,"db_ready":true,"service":"ola-support-agent"}

# Open web UI
# http://127.0.0.1:8000        # Enterprise Glassmorphism Dispatch Desk
# http://127.0.0.1:8000/docs   # Swagger API docs
```

**Web UI features** (served from `static/index.html`):
- 3-zone layout: sticky glass navbar, main chat stage, collapsible settings drawer
- 7 interactive quick-action starter cards (Sev-1 SLA, Ticket TKT-0007, Refunds, VIP SLA, PII test, Guardrail test, Budget test)
- Live ticket directory with telematics inspector, KPI cards, category spectrum
- Policy explorer, ratings & reviews, system telemetry stage
- Zero external deps — system fonts, inline SVGs, client-side PII masking

### Option B: Streamlit Fallback Console (port 8501)

```bash
# Requires backend running on 8000
BACKEND_URL=http://127.0.0.1:8000 streamlit run streamlit_app.py --server.port 8501
# http://localhost:8501
```

---

## Smoke Test Commands (verified)

```bash
# Health
curl -s http://127.0.0.1:8000/health

# Policy query (RAG)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the resolution SLA for a Sev-1 safety incident?", "session_id": "demo"}'

# Ticket lookup
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the status of TKT-0007?", "session_id": "demo"}'

# Ticket directory
curl -s "http://127.0.0.1:8000/tickets?limit=3"

# Admin: ingest document (needs X-Admin-Token)
curl -s -X POST http://127.0.0.1:8000/add-document \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me-demo-token" \
  -d '{"title": "test_policy", "text": "Test policy content."}'

# Admin: clear cache
curl -s -X POST http://127.0.0.1:8000/clear-cache \
  -H "X-Admin-Token: change-me-demo-token"

# WebSocket chat (Python)
python -c "
import asyncio, websockets, json
async def chat():
    async with websockets.connect('ws://127.0.0.1:8000/ws/chat') as ws:
        await ws.send('What is the SLA for Sev-1?')
        print(json.loads(await ws.recv()))
asyncio.run(chat())
"
```

---

## Test Suite (verified)

```bash
# Full test suite (~133 tests)
pytest -q

# Evaluation benchmark (15 queries)
python evaluation/run_eval.py

# AutoGen review demo
python review/autogen_review.py

# Offline proof (socket guard)
python scripts/run_offline.py

# Clean clone verification
python scripts/verify_clean_clone.py
```

---

## Gotchas (battle scars)

| Issue | Workaround |
|-------|------------|
| **Python 3.13+ incompatible** with `crewai`/`langchain` | Use Python 3.11 or 3.12. This container has 3.14 — core API (`/health`, `/tickets`, static UI) works but CrewAI pipeline fails. |
| **CrewAI 1.15.33 requires `langchain<0.2.0`** but README says 1.4.7 | Pin `langchain==0.1.20`, `langchain-core==0.2.0` for Python 3.12 compat. |
| **`pydantic` v1/v2 mixing** breaks `langchain_core` | Keep `pydantic==2.12.5` + `pydantic-core==2.41.5`; avoid v1. |
| **Model not cached** → `RuntimeError` on startup | Run `python scripts/prefetch_models.py` once with internet. |
| **ChromaDB empty on first run** | `rag/index.py` auto-indexes on startup via lifespan; or run manually. |
| **Port 8000 in use** | Change `PORT` in `.env` or `--port` flag. |
| **WebSocket disconnects crash server** | Fixed in `api/main.py:1113-1130` — catches `WebSocketDisconnect`, logs, cleans up. |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: langchain.agents.agent` | Downgrade `langchain==0.1.20`, `langchain-core==0.2.0` |
| `ModuleNotFoundError: langchain_core.pydantic_v1` | Use `pydantic==2.12.5` + `pydantic-core==2.41.5` |
| `RuntimeError: Embedding model not found` | `python scripts/prefetch_models.py` |
| `HTTP 500 on /ask` | Check server logs — usually CrewAI import chain broken by version mismatch |
| `WebSocket 404` | Ensure `/ws/chat` route registered before static file mount (`api/main.py:1400`) |
| `CORS errors` | Set `CORS_ORIGINS` env var (default: `http://127.0.0.1:8000,http://localhost:8000`) |

---

## Architecture Notes (for driver authors)

- **Lifespan** (`api/main.py:114-176`): Preloads `SentenceTransformer` + ChromaDB `kb_sentence` collection once at startup → `app.state`
- **Unified pipeline** (`run_unified_pipeline`): 10-step governance chain (readiness → length → budget → prompt-injection → PII → session resolve → cache → CrewAI → groundedness → AutoGen review → cache/store → audit log)
- **Cache**: Thread-safe normalized LRU in `cache.py` — policy namespace global, ticket namespace session-scoped
- **Audit log**: JSONL to `logs/requests.jsonl` with pre-persistence PII masking (`[PHONE_MASKED]`)
- **Mock LLM**: `crew/mock_llm.py` deterministic ReAct executor — subclasses `crewai.llms.base_llm.BaseLLM`
- **Static UI**: Served from `static/` via `StaticFiles` mount at `/` (after API routes)
- **Streamlit**: Separate process, proxies to `BACKEND_URL` env var