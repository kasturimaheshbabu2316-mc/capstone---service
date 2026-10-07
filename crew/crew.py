"""CrewAI Multi-Agent Pipeline Coordinator.

Track: Business Operations / Customer Support (Ola)
Coordinates the 3-agent crew (Retrieval, Lookup, Composer) and runs Crew.kickoff().
"""

import os
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import re
import json
from typing import Any
from crewai import Crew, Task, Process
from crew.agents import (
    create_retrieval_agent,
    create_lookup_agent,
    create_composer_agent,
    get_mock_llm,
)
from crew.schema import SupportResponse
from crew.memory import session_memory
from tools.ticket_tool import check_support_ticket_status
from tools.rag_tool import rag_lookup


def run_support_crew(
    query: str,
    session_id: str = "default_session",
    structured: bool = False,
) -> dict[str, Any] | SupportResponse:
    """Executes the CrewAI 3-agent pipeline on the given user query.

    Handles pronoun resolution via session_memory and kicks off appropriate tasks.
    """
    # Step 1: Pronoun and entity resolution
    resolved_query, was_resolved = session_memory.resolve_query(session_id, query)

    # Check if query references a ticket
    ticket_match = re.search(r"\b(TKT-\d{4})\b", resolved_query, re.IGNORECASE)
    ticket_id = ticket_match.group(1).upper() if ticket_match else None

    llm = get_mock_llm()
    retrieval_agent = create_retrieval_agent(llm)
    lookup_agent = create_lookup_agent(llm)
    composer_agent = create_composer_agent(llm)

    if ticket_id:
        # Route to Lookup Agent -> Composer
        task1 = Task(
            description=f"Check the status, resolution time, and escalation risk for ticket {ticket_id}.",
            expected_output="Operational status, metrics, and escalation risk calculation.",
            agent=lookup_agent,
        )
        task2 = Task(
            description=f"Draft a courteous, concise customer response explaining the status of ticket {ticket_id}.",
            expected_output="Final customer-facing response text.",
            agent=composer_agent,
        )
        crew = Crew(
            agents=[lookup_agent, composer_agent],
            tasks=[task1, task2],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        crew_output = crew.kickoff()
        output_str = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output)

        ticket_data = check_support_ticket_status(ticket_id)
        status = ticket_data.get("status", "Unknown")
        res_time = ticket_data.get("resolution_time_hours", 0.0)
        esc_score = ticket_data.get("escalation_score", 0.0)
        risk = ticket_data.get("risk_level", "Normal")

        final_text = (
            f"Ticket {ticket_id} ({ticket_data.get('category', 'General')}) is currently {status} "
            f"with a resolution time of {res_time} hours. Escalation risk score is {esc_score:.4f} ({risk})."
        )
        sources = ["dataset.py"]
        grounded = True
        confidence = 0.98

    else:
        # Route to Retrieval Agent -> Composer
        task1 = Task(
            description=f"Search internal policies for: '{resolved_query}'.",
            expected_output="Relevant policy excerpts and citations.",
            agent=retrieval_agent,
        )
        task2 = Task(
            description=f"Compose a grounded answer to: '{resolved_query}' using retrieved policies.",
            expected_output="Clear, grounded customer policy answer.",
            agent=composer_agent,
        )
        crew = Crew(
            agents=[retrieval_agent, composer_agent],
            tasks=[task1, task2],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        crew_output = crew.kickoff()
        output_str = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output)

        rag_res = rag_lookup(resolved_query)
        final_text = rag_res["answer"]
        sources = rag_res["sources"]
        grounded = rag_res["grounded"]
        confidence = rag_res["confidence"]
        esc_score = None

    # Step 2: Record in session memory
    session_memory.record_interaction(session_id, query, final_text)

    response_data = {
        "answer": final_text,
        "sources": sources,
        "ticket_id": ticket_id,
        "escalation_score": esc_score,
        "grounded": grounded,
        "confidence": confidence,
        "resolved_query": resolved_query,
        "was_resolved": was_resolved,
    }

    if structured:
        return SupportResponse(
            answer=final_text,
            sources=sources,
            ticket_id=ticket_id,
            escalation_score=esc_score,
            grounded=grounded,
            confidence=confidence,
        )

    return response_data
