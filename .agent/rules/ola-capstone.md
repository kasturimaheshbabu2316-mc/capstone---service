# Ola Domain Support Agent - Project Rules

You are a Senior AI Engineer building my "Ola Domain Support Agent" final capstone
(Business Operations / Customer Support track). I give you the build in steps, each
available as a /step-XX workflow.

## NON-NEGOTIABLE RULES
- Everything must run under MOCK_LLM (deterministic, zero API keys, zero network).
  A real LLM may exist only behind an env flag; never required.
- Set CREWAI_DISABLE_TELEMETRY=true and OTEL_SDK_DISABLED=true before any crew runs
  (in code and in .env.example).
- Embeddings: SentenceTransformers (local). Vector store: ChromaDB (local).
- No images, PDFs, slides or screenshots anywhere. Only code and text in the repo.
- Deterministic everywhere: fixed seeds, no randomness at runtime.
- One step at a time. For each step: list files you will create or change, write full
  code with docstrings and error handling, then give me the exact command to verify
  it and save its output to transcripts/<step>.txt.
- Do not rename or restructure existing files without asking me.
- Never hand-edit data to satisfy a threshold; change the seed or weights instead.

## TARGET STRUCTURE
ola-support-agent/
  dataset.py
  kb/                      (12+ .md files)
  rag/        chunking.py, index.py, generate.py, calibrate.py, evaluate_chunking.py
  tools/      ticket_tool.py
  crew/       mock_llm.py, crew.py, memory.py, schemas.py
  safety/     guardrails.py
  review/     autogen_review.py
  governance/ budget.py, RISK.md
  cache.py
  api/        main.py, logging_setup.py
  evaluation/ judge.py, test_queries.py, run_eval.py
  transcripts/, tests/, logs/
  requirements.txt, .env.example, Dockerfile, run.bat, README.md

## ENVIRONMENT
- I am on Windows using PowerShell. Use PowerShell syntax only
  (e.g. $env:MOCK_LLM="true", py -m venv .venv, .venv\Scripts\Activate.ps1).
  Never use `export` or `set VAR=`.
- Save verification output with: <command> 2>&1 | Tee-Object transcripts\<step>.txt
- Before using any CrewAI, Autogen, LangChain or ChromaDB API, read the installed
  package source or run `pip show` / `help()` to confirm the real signatures. Do not
  guess APIs from memory.
- Commit to git after each verified step.
