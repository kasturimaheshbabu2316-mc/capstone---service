"""CrewAI Agent Definitions for Ola Domain Support System.

Track: Business Operations / Customer Support (Ola)
Defines 3 specialized agents adhering to Least Autonomy tool binding:
1. Retrieval Agent (Tool: rag_lookup)
2. Lookup Agent (Tool: check_support_ticket_status)
3. Response Composer (Tool: None)
"""

import os
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent
from llm.mock_llm import MockLLM
from tools.rag_tool import rag_lookup_crew_tool
from tools.ticket_tool import check_support_ticket_status_crew_tool


def get_mock_llm() -> MockLLM:
    """Returns a deterministic MockLLM instance."""
    return MockLLM()


def create_retrieval_agent(llm: MockLLM | None = None) -> Agent:
    """Creates the Retrieval Agent with exclusive access to the RAG policy tool."""
    return Agent(
        role="Policy Retrieval Specialist",
        goal="Retrieve accurate Ola policies, SLAs, refund conditions, and guidelines from the knowledge base.",
        backstory="Expert on Ola operational documentation, priority matrices, and business hour procedures.",
        tools=[rag_lookup_crew_tool],
        llm=llm or get_mock_llm(),
        verbose=False,
    )


def create_lookup_agent(llm: MockLLM | None = None) -> Agent:
    """Creates the Lookup Agent with exclusive access to ticket status and escalation tools."""
    return Agent(
        role="Ticket Operations Specialist",
        goal="Lookup customer support tickets, calculate empirical escalation risk, and report operational status.",
        backstory="Senior operations lead analyzing ticket resolution times, active aging, and escalation thresholds.",
        tools=[check_support_ticket_status_crew_tool],
        llm=llm or get_mock_llm(),
        verbose=False,
    )


def create_composer_agent(llm: MockLLM | None = None) -> Agent:
    """Creates the Response Composer Agent with zero tool permissions (least autonomy)."""
    return Agent(
        role="Support Response Composer",
        goal="Synthesize retrieved policy data or ticket status into clear, grounded, professional customer responses.",
        backstory="Experienced customer experience editor ensuring all output is grounded, courteous, and accurate.",
        tools=[],  # Strictly toolless under Least Autonomy
        llm=llm or get_mock_llm(),
        verbose=False,
    )
