"""Memory Benchmarking Script for Render Free Web Service Deployment (512 MB RAM limit).

Starts the FastAPI application with TestClient, exercises the lifespan handler,
measures baseline RSS, runs /health and 3 representative /ask queries, and tracks
peak resident set size (RSS) in MB.
"""

from __future__ import annotations

import gc
import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enforce offline mock execution and minimal threading
os.environ["MOCK_LLM"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

try:
    import psutil
except ImportError:
    print("[ERROR] psutil is not installed. Run 'pip install psutil' first.")
    sys.exit(1)

from fastapi.testclient import TestClient


def get_current_rss_mb() -> float:
    """Returns the current process RSS memory in megabytes (MB)."""
    process = psutil.Process(os.getpid())
    # memory_info().rss returns bytes
    return process.memory_info().rss / (1024.0 * 1024.0)


def main():
    print("=" * 70)
    print(" OLA SUPPORT AGENT — MEMORY BENCHMARK (RENDER 512 MB TARGET)")
    print("=" * 70)

    gc.collect()
    baseline_rss = get_current_rss_mb()
    peak_rss = baseline_rss
    print(f"[*] Baseline process RSS (before app import): {baseline_rss:.2f} MB")

    # Import app
    t0 = time.perf_counter()
    from api.main import app
    import_rss = get_current_rss_mb()
    peak_rss = max(peak_rss, import_rss)
    print(f"[*] RSS after importing api.main:            {import_rss:.2f} MB (+{import_rss - baseline_rss:.2f} MB)")

    # Test queries
    test_queries = [
        ("Query 1 (Policy RAG - Sev-1 SLA)", "What is the resolution SLA for a Sev-1 safety incident?"),
        ("Query 2 (Ticket Lookup - TKT-0007)", "What is the status of ticket TKT-0007?"),
        ("Query 3 (Out-of-Scope Fallback)", "What is the recipe for chocolate chip cookies?"),
    ]

    measurements = []

    # Enter lifespan via TestClient
    with TestClient(app) as client:
        gc.collect()
        lifespan_rss = get_current_rss_mb()
        peak_rss = max(peak_rss, lifespan_rss)
        print(f"[*] RSS after FastAPI lifespan startup:     {lifespan_rss:.2f} MB (+{lifespan_rss - baseline_rss:.2f} MB)")

        # 1. Health check
        res_health = client.get("/health")
        assert res_health.status_code == 200, f"/health returned {res_health.status_code}"
        health_rss = get_current_rss_mb()
        peak_rss = max(peak_rss, health_rss)
        print(f"[*] RSS after GET /health:                   {health_rss:.2f} MB (status={res_health.json().get('status')})")

        # 2. Sequential /ask queries
        for idx, (label, q_text) in enumerate(test_queries, 1):
            t_start = time.perf_counter()
            res = client.post("/ask", json={"question": q_text, "session_id": f"bench_{idx}"})
            elapsed = (time.perf_counter() - t_start) * 1000.0
            assert res.status_code == 200, f"/ask failed on {label} with {res.status_code}: {res.text}"

            rss_now = get_current_rss_mb()
            peak_rss = max(peak_rss, rss_now)
            measurements.append({
                "stage": label,
                "status": res.status_code,
                "route": res.json().get("route", "unknown"),
                "latency_ms": round(elapsed, 1),
                "rss_mb": round(rss_now, 2),
            })
            print(f"[*] RSS after {label}: {rss_now:.2f} MB (latency: {elapsed:.1f}ms, route: {res.json().get('route')})")

    gc.collect()
    final_rss = get_current_rss_mb()

    print("\n" + "=" * 70)
    print(" MEMORY BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Phase / Step':<40} {'Status':<10} {'Route':<10} {'Latency':<12} {'RSS (MB)':<10}")
    print("-" * 82)
    print(f"{'Process Baseline':<40} {'OK':<10} {'-':<10} {'-':<12} {baseline_rss:<10.2f}")
    print(f"{'FastAPI Module Import':<40} {'OK':<10} {'-':<10} {'-':<12} {import_rss:<10.2f}")
    print(f"{'Lifespan Startup (Index & Model Preload)':<40} {'OK':<10} {'-':<10} {'-':<12} {lifespan_rss:<10.2f}")
    print(f"{'GET /health':<40} {'200':<10} {'health':<10} {'-':<12} {health_rss:<10.2f}")

    for m in measurements:
        print(f"{m['stage']:<40} {m['status']:<10} {m['route']:<10} {f'{m['latency_ms']}ms':<12} {m['rss_mb']:<10.2f}")

    print("-" * 82)
    print(f"PEAK RESIDENT SET SIZE (RSS):  {peak_rss:.2f} MB")
    print(f"RENDER FREE TIER LIMIT:        512.00 MB")
    headroom = 512.0 - peak_rss
    print(f"REMAINING MEMORY HEADROOM:     {headroom:.2f} MB ({headroom / 512.0 * 100:.1f}%)")
    print("=" * 70)

    if peak_rss > 480.0:
        print(f"[!] WARNING: Peak RSS {peak_rss:.2f} MB exceeds safe 480 MB ceiling for 512 MB Render.")
        sys.exit(2)
    elif peak_rss > 450.0:
        print(f"[!] NOTICE: Peak RSS {peak_rss:.2f} MB is between 450 MB and 480 MB.")
    else:
        print(f"[+] PASS: Peak RSS {peak_rss:.2f} MB is comfortably within the 512 MB memory budget!")


if __name__ == "__main__":
    main()
