"""Strict Offline Runner Wrapper for Ola Domain Support Intelligence System.

Track: Business Operations / Customer Support (Ola)
Enforces:
1. Environment variables: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1,
   CREWAI_DISABLE_TELEMETRY=true, OTEL_SDK_DISABLED=true, MOCK_LLM=true.
2. Socket guard blocking all non-loopback network connections (socket.connect and create_connection).
3. Executes target module or all four core verification stages:
   - evaluation/run_eval.py
   - review/autogen_review.py
   - governance/budget.py
   - cache.py
"""

from __future__ import annotations

import os
import runpy
import socket
import sys
import time
from pathlib import Path

# Enforce offline flags prior to any third-party imports
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["MOCK_LLM"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Strict Offline Network Guard
# ---------------------------------------------------------------------------

_orig_socket_connect = socket.socket.connect
_orig_create_connection = socket.create_connection


def _is_loopback(host: object) -> bool:
    if host is None:
        return True
    if not isinstance(host, str):
        return False
    h = host.strip().lower()
    if h in ("127.0.0.1", "localhost", "::1", "0.0.0.0", "testserver"):
        return True
    if h.startswith("127."):
        return True
    return False


def _guarded_connect(self: socket.socket, address: object) -> None:
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = address[0]
        if not _is_loopback(host):
            raise RuntimeError(f"network access attempted to non-loopback host: {host}")
    _orig_socket_connect(self, address)  # type: ignore[arg-type]


def _guarded_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = address[0]
        if not _is_loopback(host):
            raise RuntimeError(f"network access attempted to non-loopback host: {host}")
    return _orig_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]


socket.socket.connect = _guarded_connect  # type: ignore[assignment]
socket.create_connection = _guarded_create_connection  # type: ignore[assignment]


def run_target(script_rel_path: str) -> bool:
    full_path = PROJECT_ROOT / script_rel_path
    if not full_path.exists():
        print(f"[!] Target script not found: {full_path}", file=sys.stderr)
        return False

    print("\n" + "=" * 80)
    print(f"OFFLINE EXECUTION: {script_rel_path}")
    print(f"Socket Guard: ACTIVE (Non-loopback blocked) | HF_HUB_OFFLINE=1 | MOCK_LLM=true")
    print("=" * 80)

    t0 = time.perf_counter()
    try:
        runpy.run_path(str(full_path), run_name="__main__")
        elapsed = time.perf_counter() - t0
        print(f"\n[+] COMPLETED: {script_rel_path} in {elapsed:.2f}s (PASS)")
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"\n[-] FAILED: {script_rel_path} in {elapsed:.2f}s: {exc}", file=sys.stderr)
        return False


def main() -> None:
    targets = sys.argv[1:]
    if not targets or targets == ["--all"]:
        targets = [
            "evaluation/run_eval.py",
            "review/autogen_review.py",
            "governance/budget.py",
            "cache.py",
        ]

    print("=" * 80)
    print("OLA SUPPORT INTELLIGENCE — STRICT OFFLINE VERIFICATION RUNNER")
    print(f"Total targets: {len(targets)}")
    print("=" * 80)

    all_passed = True
    for target in targets:
        success = run_target(target)
        if not success:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("ALL TARGETS PASSED STRICT OFFLINE VERIFICATION (ZERO EXTERNAL NETWORK ACCESS)!")
    else:
        print("SOME TARGETS FAILED DURING OFFLINE RUN.")
    print("=" * 80)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
