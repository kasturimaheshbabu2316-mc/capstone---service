"""FastAPI Service for Ola Domain Support Intelligence Agent.

Re-exports the application and route handlers from api.main for unified architecture.
"""

from api.main import (
    app,
    index_endpoint,
    health_check,
    ask_endpoint,
    add_document_endpoint,
    chat_websocket,
    lifespan,
    run_unified_pipeline,
)

__all__ = [
    "app",
    "index_endpoint",
    "health_check",
    "ask_endpoint",
    "add_document_endpoint",
    "chat_websocket",
    "lifespan",
    "run_unified_pipeline",
]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
