"""CrewAI Support Agent Package (Tasks 7, 8, 9).

Track: Business Operations / Customer Support (Ola)
Uses PEP 562 lazy module attributes to prevent unnecessary memory bloat at package import time.
"""

from typing import Any

__all__ = [
    "SupportResponse",
    "session_memory",
    "run_support_crew",
    "create_retrieval_agent",
    "create_lookup_agent",
    "create_composer_agent",
]


def __getattr__(name: str) -> Any:
    if name == "SupportResponse":
        from crew.schema import SupportResponse
        return SupportResponse
    elif name == "session_memory":
        from crew.memory import session_memory
        return session_memory
    elif name == "run_support_crew":
        from crew.crew import run_support_crew
        return run_support_crew
    elif name in ("create_retrieval_agent", "create_lookup_agent", "create_composer_agent"):
        import crew.agents as agents_mod
        return getattr(agents_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
