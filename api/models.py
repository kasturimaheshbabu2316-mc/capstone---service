"""FastAPI Pydantic Schemas for Ola Domain Support Service (Task 11).

Track: Business Operations / Customer Support (Ola)
Provides request/response schemas for REST and WebSocket interactions.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from crew.schemas import CrewResponse, SupportResponse


class AskRequest(BaseModel):
    """Payload for POST /ask endpoint."""

    question: str | None = Field(default=None, max_length=20000, description="Customer question or operational inquiry.")
    query: str | None = Field(default=None, max_length=20000, description="Backwards-compatible alias for question.")
    session_id: str | None = Field(default="default_session", description="Conversation session ID.")

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
    data: Any | None = Field(default=None, description="Legacy structured data object.")
    sql: str | None = Field(default=None, description="Optional generated SQL query.")
    chart_type: str | None = Field(default=None, description="Optional visualization chart type.")
    x_col: str | None = Field(default=None, description="Optional x-axis column.")
    y_col: str | None = Field(default=None, description="Optional y-axis column.")
    retrieved_sources: list[str] = Field(default_factory=list, description="Direct list of retrieved sources.")
    source_titles: list[str] = Field(default_factory=list, description="Unique list of titles extracted from sources metadata or titles.")
    retrieved_snippet: str | None = Field(default=None, description="Direct excerpt snippet.")
    review_status: dict[str, Any] | None = Field(default_factory=dict, description="Secondary review stage metadata.")
    cache_hit: bool = Field(default=False, description="Flag indicating if served from semantic cache.")
    guardrail_flags: dict[str, Any] = Field(default_factory=dict, description="Safety guardrail audit flags.")


class AddDocumentRequest(BaseModel):
    """Payload for POST /add-document endpoint."""

    title: str | None = Field(default=None, description="Title or document identifier.")
    doc_id: str | None = Field(default=None, description="Document identifier (alias for title).")
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

    status: str = Field(default="ok", description="Service health state.")
    mock_llm: bool = Field(default=True, description="Flag indicating offline deterministic mock LLM execution.")
    kb_ready: bool = Field(default=True, description="Flag indicating knowledge base vector store availability.")
    db_ready: bool = Field(default=True, description="Flag indicating operational ticket database readiness.")
    service: str | None = Field(default="ola-support-agent", description="Service identifier.")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error: str | None = Field(default="Error", description="High-level error classification.")
    detail: str = Field(..., description="Safe human-readable error description.")
    status_code: int = Field(..., description="HTTP status code.")
    trace_id: str | None = Field(default=None, description="Request trace ID if applicable.")


class FeedbackRequest(BaseModel):
    """Payload for POST /feedback endpoint."""

    session_id: str | None = Field(default="default_session", description="Conversation session ID.")
    ticket_id: str | None = Field(default=None, description="Optional associated ticket ID.")
    question: str | None = Field(default=None, description="User's original query.")
    answer: str | None = Field(default=None, description="Assistant's response text.")
    rating: int = Field(..., ge=1, le=5, description="Customer rating from 1 to 5 stars.")
    suggestion: str | None = Field(default=None, description="Optional feedback suggestion or comment.")
    timestamp: str | None = Field(default=None, description="ISO timestamp of submission.")


class FeedbackRecord(BaseModel):
    """Structured feedback record stored and retrieved."""

    id: str = Field(..., description="Unique feedback ID.")
    timestamp: str = Field(..., description="ISO submission timestamp.")
    rating: int = Field(..., ge=1, le=5, description="Star rating.")
    ticket_id: str | None = Field(default=None, description="Associated ticket ID if any.")
    question: str | None = Field(default=None, description="User query.")
    answer: str | None = Field(default=None, description="AI answer.")
    suggestion: str | None = Field(default=None, description="User suggestion.")


class FeedbackResponse(BaseModel):
    """Response returned upon feedback submission."""

    status: str = Field(default="recorded", description="Submission status.")
    message: str = Field(..., description="Polite confirmation message.")
    feedback_id: str = Field(..., description="Generated feedback ID.")
    has_suggestion: bool = Field(default=False, description="Flag indicating if suggestion was provided.")


class TicketActionRequest(BaseModel):
    """Payload for POST /api/tickets/{ticket_id}/action endpoint."""

    action: Literal["execute_refund", "issue_voucher", "reset_auth", "close_ticket"] = Field(
        default="execute_refund", description="Action to perform on ticket dispute."
    )
    amount: float = Field(default=140.0, ge=0.0, le=5000.0, description="Refund or credit amount in INR.")
    reason: str | None = Field(default="Dual deduction confirmed", max_length=256, description="Audit reconciliation note.")


class TicketActionResponse(BaseModel):
    """Response payload for ticket action."""

    success: bool = Field(default=True, description="Whether action succeeded.")
    ticket_id: str = Field(..., description="Target ticket ID.")
    status: str = Field(..., description="Updated ticket status, e.g. Resolved.")
    reconciled_status: str = Field(default="Reconciled", description="Audit dispute status.")
    txn_id: str = Field(..., description="Unique settlement transaction reference.")
    amount: float = Field(..., description="Reconciled amount in INR.")
    message: str = Field(..., description="Human-readable audit confirmation.")


__all__ = [
    "AddDocumentRequest",
    "AddDocumentResponse",
    "AskRequest",
    "AskResponse",
    "CrewResponse",
    "ErrorResponse",
    "FeedbackRecord",
    "FeedbackRequest",
    "FeedbackResponse",
    "HealthResponse",
    "SupportResponse",
    "TicketActionRequest",
    "TicketActionResponse",
]
