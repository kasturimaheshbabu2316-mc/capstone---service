---
description: Step 10 - FastAPI endpoints, WebSocket and JSON-Lines logging (Tasks 11, 12)
---
STEP 10 - FastAPI deployment and structured logging (Tasks 11, 12).
api/main.py:
1. POST /ask (AskRequest{session_id, question} -> AskResponse = CrewResponse + trace_id
   + latency_ms), POST /add-document (title, text -> chunk, embed, and upsert into the
   recommended collection), GET /health ({status, mock_llm, kb_ready, db_ready}).
   Use a lifespan handler to load the model and index once at startup (never per request).
   Return 400 for a guardrail block, 413 for an oversized payload, 422 for validation, and
   500 with a safe JSON message (never a traceback).
2. @app.websocket("/ws/chat"): multi-turn chat with a per-connection session_id; catch
   WebSocketDisconnect, log it, clean up, and keep the server running for other clients.
   Add a test that connects, sends 2 messages, then disconnects abruptly, then opens a
   second client successfully.
3. api/logging_setup.py: one JSON-Lines entry per request in logs/requests.jsonl with
   trace_id (uuid4), timestamp, endpoint, session_id, masked_question, route, latency_ms,
   status_code. The logged text MUST be the PII-masked text (apply the Step 9 masker
   before logging). Add a test that sends a phone number and asserts the raw number
   never appears in the log file.
Save the output to transcripts/11_api.txt (curl commands and responses).
