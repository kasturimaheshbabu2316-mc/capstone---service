"""FastAPI Pydantic Schemas for Ola Domain Support Service.

Track: Business Operations / Customer Support (Ola)
Provides request/response schemas for REST and WebSocket interactions.
"""

from typing import Any
from pydantic import BaseModel, Field
from crew.schema import SupportResponse


class AskRequest(BaseModel):
    """Payload for POST /ask."""

    query: str = Field(..., min_length=1, description="Customer question or ticket status query.")
    session_id: str | None = Field(default="default_session", description="Optional conversation session ID.")


class AskResponse(BaseModel):
    """Response payload for POST /ask."""

    trace_id: str = Field(..., description="Unique UUID trace identifier.")
    data: SupportResponse = Field(..., description="Grounded agent answer and metadata.")
    latency_ms: float = Field(..., description="Request processing time in milliseconds.")
    cache_hit: bool = Field(default=False, description="True if served directly from response cache.")
    guardrail_flags: dict[str, Any] = Field(default_factory=dict, description="Flags for PII masking and safety checks.")


class AddDocumentRequest(BaseModel):
    """Payload for POST /add-document."""

    doc_id: str = Field(..., min_length=1, description="Identifier for new policy document, e.g. cancellation_faq.md.")
    text: str = Field(..., min_length=10, description="Full policy document text.")


class AddDocumentResponse(BaseModel):
    """Response payload for POST /add-document."""

    status: str = Field(default="indexed", description="Ingestion status.")
    doc_id: str = Field(..., description="Document ID.")
    chunks_indexed: int = Field(..., description="Number of text chunks created and indexed into Chroma.")
    cache_invalidated_entries: int = Field(..., description="Number of cleared cache entries.")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    detail: str = Field(..., description="Error message details.")
    trace_id: str | None = Field(default=None, description="Request trace ID if generated.")
