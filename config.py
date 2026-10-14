"""Central Configuration Module for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Loads environment variables with robust fallback defaults.
Guarantees MOCK_LLM=True and telemetry disabled by default.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if present
load_dotenv(override=False)

# Core Execution Flags
MOCK_LLM: bool = os.environ.get("MOCK_LLM", "true").lower() == "true"
CREWAI_DISABLE_TELEMETRY: bool = os.environ.get("CREWAI_DISABLE_TELEMETRY", "true").lower() == "true"
OTEL_SDK_DISABLED: bool = os.environ.get("OTEL_SDK_DISABLED", "true").lower() == "true"

# Enforce telemetry suppression immediately in runtime environment
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true" if CREWAI_DISABLE_TELEMETRY else "false"
os.environ["OTEL_SDK_DISABLED"] = "true" if OTEL_SDK_DISABLED else "false"

# Model & Storage Settings
EMBED_MODEL: str = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_REQUEST_TOKENS: int = int(os.environ.get("MAX_REQUEST_TOKENS", "1500"))
MAX_QUERY_TOKENS: int = int(os.environ.get("MAX_QUERY_TOKENS", "2000"))
CHROMA_DIR: Path = Path(os.environ.get("CHROMA_DIR", "./chroma_store"))
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./data/support.db")
BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
LOG_FILE: Path = Path(os.environ.get("LOG_FILE", "./logs/requests.jsonl"))

# Ensure directory structures exist
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
Path("./transcripts").mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)
Path("./tests").mkdir(parents=True, exist_ok=True)
