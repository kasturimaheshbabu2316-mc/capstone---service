"""FastAPI Pydantic Schemas for Ola Domain Support Service (Task 11).

Track: Business Operations / Customer Support (Ola)
Provides request/response schemas for REST and WebSocket interactions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from crew.schemas import CrewResponse, SupportResponse


class AskRequest(BaseModel):
    """Payload for POST /ask endpoint."""

    question: Optional[str] = Field(default=None, description="Customer question or operational inquiry.")
    query: Optional[str] = Field(default=None, description="Backwards-compatible alias for question.")
    session_id: Optional[str] = Field(default="default_session", description="Conversation session ID.")

    @model_validator(mode="after")
    def validate_and_sync_question(self) -> AskRequest:
        if not self.question and not self.query:
            raise ValueError("Field 'question' is required.")
        if not self.question and self.query:
            self.question = self.query
        elif not self.query and self.question:
            self.query = self.question
        return self


class AskResponse(CrewResponse):
    """Response payload for POST /ask (AskResponse = CrewResponse + trace_id + latency_ms)."""

    trace_id: str = Field(..., description="Unique UUID trace identifier.")
    latency_ms: float = Field(..., description="Total request processing time in milliseconds.")

    # Backwards compatibility attributes for UI and legacy tests
    data: Optional[Any] = Field(default=None, description="Legacy structured data object.")
    sql: Optional[str] = Field(default=None, description="Optional generated SQL query.")
    chart_type: Optional[str] = Field(default=None, description="Optional visualization chart type.")
    x_col: Optional[str] = Field(default=None, description="Optional x-axis column.")
    y_col: Optional[str] = Field(default=None, description="Optional y-axis column.")
    retrieved_sources: List[str] = Field(default_factory=list, description="Direct list of retrieved sources.")
    retrieved_snippet: Optional[str] = Field(default=None, description="Direct excerpt snippet.")
    review_status: Dict[str, Any] = Field(default_factory=dict, description="Secondary review stage metadata.")
    cache_hit: bool = Field(default=False, description="Flag indicating if served from semantic cache.")
    guardrail_flags: Dict[str, Any] = Field(default_factory=dict, description="Safety guardrail audit flags.")


class AddDocumentRequest(BaseModel):
    """Payload for POST /add-document endpoint."""

    title: Optional[str] = Field(default=None, description="Title or document identifier.")
    doc_id: Optional[str] = Field(default=None, description="Document identifier (alias for title).")
    text: str = Field(..., min_length=1, description="Full policy text to chunk, embed, and upsert.")

    @model_validator(mode="after")
    def sync_title_and_doc_id(self) -> AddDocumentRequest:
        if not self.title and not self.doc_id:
            raise ValueError("Either 'title' or 'doc_id' must be provided.")
        if not self.title and self.doc_id:
            self.title = self.doc_id
        elif not self.doc_id and self.title:
            self.doc_id = self.title
        return self


class AddDocumentResponse(BaseModel):
    """Response payload for POST /add-document."""

    status: str = Field(default="indexed", description="Ingestion outcome status.")
    title: str = Field(..., description="Document title.")
    doc_id: str = Field(..., description="Document ID.")
    collection: str = Field(default="kb_sentence", description="Target Chroma collection name.")
    chunks_indexed: int = Field(..., description="Number of text chunks created and indexed.")
    cache_invalidated_entries: int = Field(default=0, description="Number of invalidated cache entries.")


class HealthResponse(BaseModel):
    """Response payload for GET /health."""

    status: str = Field(default="healthy", description="Service health state.")
    mock_llm: bool = Field(default=True, description="Flag indicating offline deterministic mock LLM execution.")
    kb_ready: bool = Field(default=True, description="Flag indicating knowledge base vector store availability.")
    db_ready: bool = Field(default=True, description="Flag indicating operational ticket database readiness.")
    service: Optional[str] = Field(default="ola-support-agent", description="Service identifier.")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error: Optional[str] = Field(default="Error", description="High-level error classification.")
    detail: str = Field(..., description="Safe human-readable error description.")
    status_code: int = Field(..., description="HTTP status code.")
    trace_id: Optional[str] = Field(default=None, description="Request trace ID if applicable.")


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
