"""Root FastAPI Entrypoint for Ola Customer Support Intelligence System.

Enables running via:
`uvicorn main:app --port 8000`
"""

import os
import sys

# Ensure root workspace is on python sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import (
    app,
    health_check,
    ask_endpoint,
    add_document_endpoint,
    index_endpoint,
)

__all__ = [
    "app",
    "health_check",
    "ask_endpoint",
    "add_document_endpoint",
    "index_endpoint",
]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
