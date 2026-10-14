---
description: Step 15 - run scripts, Dockerfile, GitHub push, Render deployment, checklist
---
STEP 15 - Deployment.
1. run.bat and run.sh: set the env vars, run the ingest/index step, start uvicorn
   (api.main:app --port 8000), and wait for /health.
2. Dockerfile: python:3.11-slim, install CPU-only torch via the PyTorch CPU index, pip
   install -r requirements.txt, pre-download the SentenceTransformer model at build time,
   set MOCK_LLM=true and CREWAI_DISABLE_TELEMETRY=true, EXPOSE 8000, and CMD to uvicorn on
   $PORT.
3. .gitignore (.venv, chroma_store, logs, __pycache__, .env), then give me the git
   commands to push to a PUBLIC GitHub repo.
4. Render deployment steps (Docker web service, env vars, health check path /health).
5. A final submission checklist mapping each of the 16 tasks to the file and transcript
   that proves it.
