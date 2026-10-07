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


def rag_lookup(query: str) -> dict[str, Any]:
    """Retrieves policy information from the Ola knowledge base.

    Args:
        query: The policy question to search, e.g. 'What is the SLA for Sev-1?'.

    Returns:
        Structured dictionary containing answer, sources, grounded flag, and confidence.
    """
    clean_query = str(query).strip()
    result = grounded_generate(clean_query, collection_name="ola_sentence")

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
    def rag_lookup_crew_tool(query: str) -> str:
        """Looks up internal Ola support policies, SLAs, refund rules, and operational guidelines."""
        res = rag_lookup(query)
        sources_str = ", ".join(res["sources"]) if res["sources"] else "None"
        return f"Policy Answer: {res['answer']}\nSources: {sources_str}\nGrounded: {res['grounded']}\nConfidence: {res['confidence']}"

except ImportError:
    rag_lookup_crew_tool = rag_lookup  # fallback if crewai not available
