"""Pydantic Structured Output Schema for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Enforces strongly-typed contract for all agent responses.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class CrewResponse(BaseModel):
    """Canonical structured response format for CrewAI support agent workflows.

    Attributes:
        answer: Grounded response text to the user query.
        route: Query routing classification ('rag' | 'lookup' | 'both').
        sources: List of source policy documents or operational references.
        ticket: Optional ticket data dictionary if lookup route.
        grounded: Flag indicating whether response is grounded in policy or data.
        escalation_recommended: Boolean flag indicating if ticket escalation is recommended.
    """

    answer: str = Field(..., description="Grounded response text to the user query.")
    route: Literal["rag", "lookup", "both"] = Field(..., description="Inquiry routing classification.")
    sources: list[str] = Field(default_factory=list, description="List of source policy files or data references.")
    ticket: Optional[dict[str, Any]] = Field(default=None, description="Operational ticket data if ticket lookup.")
    grounded: bool = Field(default=True, description="Flag indicating if the response is grounded.")
    escalation_recommended: bool = Field(default=False, description="Flag indicating whether supervisor escalation is recommended.")


class SupportResponse(BaseModel):
    """Structured response model for all customer support interactions."""

    answer: str = Field(..., description="Grounded response text to the user query.")
    sources: list[str] = Field(default_factory=list, description="List of source policy files or data references.")
    ticket_id: str | None = Field(default=None, description="Ticket ID if query concerned a ticket lookup.")
    escalation_score: float | None = Field(default=None, description="Escalation risk score in [0.0, 1.0] if ticket query.")
    grounded: bool = Field(default=True, description="Flag indicating if the response is grounded in policy docs or verified data.")
    confidence: float = Field(default=1.0, description="Confidence score in [0.0, 1.0].")
    route: str | None = Field(default=None, description="Inquiry route: policy | ticket_lookup | analytics.")
    sql: str | None = Field(default=None, description="Sanitized SQL query if executed.")
    chart_type: str | None = Field(default=None, description="Recommended visualization: bar | line | None.")
    x_col: str | None = Field(default=None, description="Chart X-axis column name.")
    y_col: str | None = Field(default=None, description="Chart Y-axis column name.")
    retrieved_sources: list[str] = Field(default_factory=list, description="Source documents or databases.")
    retrieved_snippet: str | None = Field(default=None, description="Retrieved policy text snippet.")
    review_status: dict[str, Any] = Field(default_factory=dict, description="Autogen review audit notes and approval.")
    dataframe_records: list[dict[str, Any]] | None = Field(default=None, description="Tabular data records for rendering in UI.")


__all__ = ["CrewResponse", "SupportResponse"]
