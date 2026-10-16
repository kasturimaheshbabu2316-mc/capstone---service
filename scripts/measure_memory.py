"""Memory measurement script for Ola Support Agent FastAPI service.
Measures peak RSS in MB after startup, after the first /ask call, and after 5 /ask calls.
"""

import gc
import os
import psutil
import time
from fastapi.testclient import TestClient

def get_rss_mb() -> float:
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 2)

def main():
    print("=" * 60)
    print("OLA SUPPORT AGENT - MEMORY USAGE PROFILING (psutil RSS)")
    print("=" * 60)
    
    init_mem = get_rss_mb()
    print(f"Initial process memory: {init_mem:.2f} MB")
    
    # Import app and start TestClient with lifespan
    from api.main import app
    
    with TestClient(app) as client:
        # Give lifespan context a moment to stabilize
        gc.collect()
        startup_mem = get_rss_mb()
        print(f"Peak RSS after startup:           {startup_mem:.2f} MB")
        
        # Health check probe
        health_res = client.get("/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.status_code}"
        
        # 1st /ask call
        q1 = "What is the SLA for a Sev-1 safety incident?"
        t0 = time.time()
        res1 = client.post("/ask", json={"question": q1, "session_id": "mem_test_1"})
        t1 = time.time()
        assert res1.status_code == 200, f"/ask #1 failed: {res1.status_code} - {res1.text}"
        gc.collect()
        first_ask_mem = get_rss_mb()
        print(f"Peak RSS after 1st /ask:          {first_ask_mem:.2f} MB  (took {t1 - t0:.2f}s)")
        
        # 4 more calls (total 5)
        queries = [
            "Under what condition are driver cancellation fees refunded to passengers?",
            "What happens when a customer logs 3 complaints within a 14-day window?",
            "What are the operating hours for driver partner physical onboarding centers?",
            "What is the status of ticket TKT-1001?",
        ]
        
        for idx, q in enumerate(queries, start=2):
            t_start = time.time()
            res = client.post("/ask", json={"question": q, "session_id": f"mem_test_{idx}"})
            t_end = time.time()
            assert res.status_code == 200, f"/ask #{idx} failed: {res.status_code} - {res.text}"
        
        gc.collect()
        five_ask_mem = get_rss_mb()
        print(f"Peak RSS after 5 /ask calls:      {five_ask_mem:.2f} MB")
        print("=" * 60)
        print("SUMMARY TABLE:")
        print(f"  Startup Peak RSS:     {startup_mem:.2f} MB")
        print(f"  After 1st /ask:       {first_ask_mem:.2f} MB")
        print(f"  After 5 /ask calls:   {five_ask_mem:.2f} MB")
        print("=" * 60)
        
        threshold = 450.0
        if first_ask_mem > threshold:
            print(f"ALERT: Peak memory ({first_ask_mem:.2f} MB) EXCEEDS the 450 MB limit for Render's 512 MB free tier!")
        else:
            print(f"SUCCESS: Peak memory ({first_ask_mem:.2f} MB) is safely within the 450 MB limit for Render's 512 MB free tier.")

if __name__ == "__main__":
    main()
