"""Mock LLM compatibility module.

Re-exports MockLLM from crew.mock_llm.
"""

from crew.mock_llm import (
    MockLLM,
    get_tool_arg_names,
    check_for_real_observation,
    extract_ticket_id,
    extract_query_text,
)

__all__ = [
    "MockLLM",
    "get_tool_arg_names",
    "check_for_real_observation",
    "extract_ticket_id",
    "extract_query_text",
]
