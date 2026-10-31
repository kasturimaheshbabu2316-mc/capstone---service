"""PyTest Global Configuration, Offline Guard, and Clean Teardown.

Track: Business Operations / Customer Support (Ola)
Patches socket.socket.connect and socket.create_connection to block all non-loopback
network access across the entire test session.
"""

from __future__ import annotations

import contextlib
import os
import socket
import sys
import warnings

# Enforce 100% offline execution and telemetry suppression
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["MOCK_LLM"] = "true"

# Suppress deprecation warnings during testing
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*InMemoryChatMessageHistory was deprecated.*")

# ---------------------------------------------------------------------------
# Strict Offline Network Guard (blocks non-loopback network connections)
# ---------------------------------------------------------------------------

_orig_socket_connect = socket.socket.connect
_orig_create_connection = socket.create_connection


def _is_loopback(host: object) -> bool:
    """Returns True if the destination host is loopback or local."""
    if host is None:
        return True
    if not isinstance(host, str):
        return False
    h = host.strip().lower()
    return h in ("127.0.0.1", "localhost", "::1", "0.0.0.0", "testserver") or h.startswith("127.")


def _guarded_connect(self: socket.socket, address: object) -> None:
    """Blocks any socket connect to a non-loopback address."""
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = address[0]
        if not _is_loopback(host):
            raise RuntimeError(f"network access attempted to non-loopback host: {host}")
    elif isinstance(address, str):
        # AF_UNIX or named pipe
        pass
    _orig_socket_connect(self, address)  # type: ignore[arg-type]


def _guarded_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
    """Blocks any socket create_connection to a non-loopback address."""
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = address[0]
        if not _is_loopback(host):
            raise RuntimeError(f"network access attempted to non-loopback host: {host}")
    return _orig_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]


socket.socket.connect = _guarded_connect  # type: ignore[assignment]
socket.create_connection = _guarded_create_connection  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Teardown Cleanup
# ---------------------------------------------------------------------------

try:
    import colorama

    _orig_reset_all = colorama.initialise.reset_all

    def _safe_reset_all():
        with contextlib.suppress(Exception):
            if sys.stdout and not sys.stdout.closed and hasattr(sys.stdout, "isatty"):
                _orig_reset_all()

    colorama.initialise.reset_all = _safe_reset_all
except ImportError:
    pass


import pytest
import uuid
from pathlib import Path


@pytest.fixture
def isolated_kb_and_chroma(tmp_path, monkeypatch):
    """Isolates KB_DIR and winning_collection to a temporary directory and collection."""
    temp_kb = tmp_path / "temp_kb"
    temp_kb.mkdir(parents=True, exist_ok=True)
    temp_col = f"test_temp_{uuid.uuid4().hex[:8]}"

    monkeypatch.setenv("KB_DIR", str(temp_kb))
    monkeypatch.setenv("WINNING_COLLECTION", temp_col)

    yield {"kb_dir": temp_kb, "collection": temp_col}

    try:
        from rag.index import get_chroma_client
        chroma = get_chroma_client()
        chroma.delete_collection(temp_col)
    except Exception:
        pass

