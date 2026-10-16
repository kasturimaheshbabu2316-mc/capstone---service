"""FastAPI Pydantic Schemas for Ola Domain Support Service.

Re-exports schemas from api.models for full backwards compatibility.
"""

from api.models import (
    AskRequest,
    AskResponse,
    AddDocumentRequest,
    AddDocumentResponse,
    HealthResponse,
    ErrorResponse,
    CrewResponse,
    SupportResponse,
)

__all__ = [
    "AskRequest",
    "AskResponse",
    "AddDocumentRequest",
    "AddDocumentResponse",
    "HealthResponse",
    "ErrorResponse",
    "CrewResponse",
    "SupportResponse",
]
