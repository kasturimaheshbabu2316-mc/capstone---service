"""Pydantic Structured Output Schema for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Enforces strongly-typed contract for all agent responses.
"""

from pydantic import BaseModel, Field


from typing import Any
from pydantic import BaseModel, Field


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
