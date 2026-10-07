"""Application Least Autonomy Tool Binding Registry.

Track: Business Operations / Customer Support (Ola)
Enforces strict role-based tool authorization boundaries.
Raises PermissionError if an agent or caller attempts unauthorized tool invocation.
"""

from typing import Any, Callable

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Policy Retrieval Specialist": {"rag_lookup", "rag_lookup_crew_tool"},
    "Ticket Operations Specialist": {"check_support_ticket_status", "check_support_ticket_status_crew_tool"},
    "Support Response Composer": set(),  # Toolless
    "Customer Support Agent": set(),
}


class ToolAccessControl:
    """Enforces least autonomy tool permissions."""

    @staticmethod
    def verify_agent_tool_access(role: str, tool_name: str) -> bool:
        """Verifies if an agent role is permitted to bind or invoke a tool.

        Raises PermissionError if unauthorized.
        """
        allowed = ROLE_PERMISSIONS.get(role, set())
        if tool_name not in allowed:
            raise PermissionError(
                f"Least Autonomy Violation: Agent '{role}' is not authorized to use tool '{tool_name}'. "
                f"Allowed tools: {list(allowed) if allowed else 'None'}."
            )
        return True

    @staticmethod
    def authorize_tool_binding(agent_role: str, tools: list[Any]) -> list[Any]:
        """Validates all tools bound to an agent role at initialization time."""
        for t in tools:
            name = getattr(t, "name", getattr(t, "__name__", str(t)))
            ToolAccessControl.verify_agent_tool_access(agent_role, name)
        return tools
