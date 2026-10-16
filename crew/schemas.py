"""Pydantic Schema definitions for CrewAI support agent (Task 9).

Track: Business Operations / Customer Support (Ola)
Provides CrewResponse schema validated with CrewResponse.model_validate.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ValidationError


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
    review_status: Optional[dict[str, Any]] = Field(default=None, description="Secondary AutoGen review stage verdict and compliance status.")


def validate_crew_response(data: Any) -> CrewResponse:
    """Validates arbitrary input against the CrewResponse schema.

    Raises:
        ValueError: If validation fails with a clear description of the mismatch.
    """
    try:
        if isinstance(data, CrewResponse):
            return data
        return CrewResponse.model_validate(data)
    except ValidationError as err:
        raise ValueError(f"CrewResponse schema mismatch error: {err}") from err


# Re-export legacy SupportResponse for backwards compatibility
from crew.schema import SupportResponse

__all__ = ["CrewResponse", "SupportResponse", "ValidationError", "validate_crew_response"]
