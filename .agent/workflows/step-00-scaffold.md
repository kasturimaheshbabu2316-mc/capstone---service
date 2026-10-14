---
description: Step 0 - scaffold folders, requirements, env, README skeleton
---
STEP 0 - Scaffold.
1. Create the folder structure from the project rules with empty modules and __init__.py files.
2. requirements.txt with CPU-compatible versions: chromadb, sentence-transformers,
   crewai, langchain-core, langchain, pydantic, fastapi, uvicorn[standard], websockets,
   autogen-agentchat, autogen-ext, python-dotenv, pytest, httpx, numpy.
3. .env.example: MOCK_LLM=true, CREWAI_DISABLE_TELEMETRY=true, OTEL_SDK_DISABLED=true,
   EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2, MAX_REQUEST_TOKENS=1500,
   CHROMA_DIR=./chroma_store, LOG_FILE=./logs/requests.jsonl
4. config.py that loads env with defaults and exposes MOCK_LLM.
5. README.md skeleton. The FIRST LINE must say: "Track completed: Ola (Business
   Operations / Customer Support)". Add empty sections for dataset design choices,
   threshold calibration, chunking comparison, escalation formula, risk level,
   how to run, and a "Telemetry disabled" note.
6. A smoke test that imports every module.
Verify: pip install -r requirements.txt ; pytest -q
