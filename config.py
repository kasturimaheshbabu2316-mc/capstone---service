"""Central Configuration Module for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Loads environment variables with robust fallback defaults.
Guarantees MOCK_LLM=True and telemetry disabled by default.
All paths are root-relative using Path(__file__).resolve().parent.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if present
load_dotenv(override=False)

PROJECT_ROOT = Path(__file__).resolve().parent

# Core Execution Flags
MOCK_LLM: bool = os.environ.get("MOCK_LLM", "true").lower() == "true"
CREWAI_DISABLE_TELEMETRY: bool = os.environ.get("CREWAI_DISABLE_TELEMETRY", "true").lower() == "true"
OTEL_SDK_DISABLED: bool = os.environ.get("OTEL_SDK_DISABLED", "true").lower() == "true"

# Enforce telemetry suppression and single-thread execution for memory efficiency
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true" if CREWAI_DISABLE_TELEMETRY else "false"
os.environ["OTEL_SDK_DISABLED"] = "true" if OTEL_SDK_DISABLED else "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# Single Source of Truth for Token Budget from governance/budget.py
from governance.budget import MAX_REQUEST_TOKENS, MAX_TOKEN_BUDGET
MAX_QUERY_TOKENS: int = MAX_REQUEST_TOKENS

# Model & Storage Settings (all root-relative and env-configurable)
EMBED_MODEL: str = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
KB_DIR: Path = Path(os.environ.get("KB_DIR", str(PROJECT_ROOT / "kb"))).resolve()
CHROMA_DIR: Path = Path(os.environ.get("CHROMA_DIR", str(PROJECT_ROOT / "chroma_store"))).resolve()
DATABASE_URL: str = os.environ.get("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'support.db'}")
BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
LOG_DIR: Path = Path(os.environ.get("LOG_DIR", str(PROJECT_ROOT / "logs"))).resolve()
LOG_FILE: Path = Path(os.environ.get("LOG_FILE", str(LOG_DIR / "requests.jsonl"))).resolve()

try:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
