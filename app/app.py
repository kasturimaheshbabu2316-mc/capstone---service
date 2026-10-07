"""FastAPI entrypoint alias for app/app.py.

Exports the core FastAPI application from app.main.
Allows both `uvicorn app.main:app` and `uvicorn app.app:app`.
"""

from app.main import app, ask_endpoint, add_document_endpoint, chat_websocket, health_check

__all__ = ["app", "ask_endpoint", "add_document_endpoint", "chat_websocket", "health_check"]
