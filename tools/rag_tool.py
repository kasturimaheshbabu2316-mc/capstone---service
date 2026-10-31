"""RAG Policy Lookup Tool for CrewAI and Agent Workflows.

Track: Business Operations / Customer Support (Ola)
Exposes rag_lookup(query) tool returning grounded answers or calibrated fallback.
"""

from typing import Any
import os

# Suppress telemetry prior to CrewAI imports
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from rag.generate import grounded_generate, FALLBACK_REFUSAL
from governance.least_autonomy import ToolAccessControl, CURRENT_CALLER_ROLE


def rag_lookup(query: str, caller_role: str | None = None) -> dict[str, Any]:
    """Retrieves policy information from the Ola knowledge base.

    Args:
        query: The policy question to search, e.g. 'What is the SLA for Sev-1?'.
        caller_role: Optional calling agent role name.

    Returns:
        Structured dictionary containing answer, sources, grounded flag, and confidence.
    """
    curr = CURRENT_CALLER_ROLE.get()
    effective_role = (
        caller_role
        if caller_role is not None
        else (curr if curr in ("Support Response Composer", "Composer", "Composer Agent", "Policy Retrieval Specialist", "Retrieval Agent") else "Policy Retrieval Specialist")
    )
    ToolAccessControl.verify_agent_tool_access(effective_role, "rag_lookup")

    clean_query = str(query).strip()
    result = grounded_generate(clean_query, collection_name="kb_sentence")

    return {
        "query": clean_query,
        "answer": result["answer"],
        "sources": result["sources"],
        "grounded": result["grounded"],
        "confidence": round(float(result["top_similarity"]), 4),
        "refusal": result["answer"] == FALLBACK_REFUSAL,
    }


try:
    from crewai.tools import tool

    @tool("rag_lookup")
    def rag_lookup_crew_tool(query: str, caller_role: str | None = None) -> str:
        """Looks up internal Ola support policies, SLAs, refund rules, and operational guidelines."""
        curr = CURRENT_CALLER_ROLE.get()
        effective_role = (
            caller_role
            if caller_role is not None
            else (curr if curr in ("Support Response Composer", "Composer", "Composer Agent", "Policy Retrieval Specialist", "Retrieval Agent") else "Policy Retrieval Specialist")
        )
        ToolAccessControl.verify_agent_tool_access(effective_role, "rag_lookup_crew_tool")
        res = rag_lookup(query, caller_role=effective_role)
        sources_str = ", ".join(res["sources"]) if res["sources"] else "None"
        return f"Policy Answer: {res['answer']}\nSources: {sources_str}\nGrounded: {res['grounded']}\nConfidence: {res['confidence']}"

except ImportError:
    rag_lookup_crew_tool = rag_lookup  # fallback if crewai not available
