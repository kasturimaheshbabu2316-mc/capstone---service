---
description: Step 16 (optional) - reconnect the existing Streamlit UI to the new FastAPI backend
---
STEP 16 (optional) - Point my existing Streamlit app at the new FastAPI /ask.
Read the backend URL from BACKEND_URL (default http://127.0.0.1:8000), call GET /health
at startup and show "Backend offline - start it with: uvicorn api.main:app --port 8000"
instead of a raw ConnectionError, use timeouts, handle 400/413 with friendly messages,
and truncate very long repeated text in the chat display. Keep my existing Quick Action
buttons working.
