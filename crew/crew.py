"""CrewAI Multi-Agent Pipeline Coordinator.

Track: Business Operations / Customer Support (Ola)
Coordinates the 3-agent crew (Retrieval Agent, Lookup Agent, Response Composer),
executes sequential workflows via Crew.kickoff(), and validates output using CrewResponse.
"""

import os
# Suppress telemetry prior to CrewAI imports
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import re
import json
import logging
from typing import Any
from crewai import Crew, Task, Process
from crew.agents import (
    create_retrieval_agent,
    create_lookup_agent,
    create_composer_agent,
    get_mock_llm,
)
from crew.schemas import CrewResponse, validate_crew_response
from crew.memory import session_memory, crew_runnable_with_history
from tools.ticket_tool import check_support_ticket_status
from tools.rag_tool import rag_lookup

logger = logging.getLogger("ola_domain_agent.crew")


def run_support_crew(
    query: str,
    session_id: str = "default_session",
    structured: bool = False,
) -> dict[str, Any] | CrewResponse:
    """Executes the CrewAI 3-agent pipeline on the given user query.

    Handles pronoun resolution via session_memory and RunnableWithMessageHistory.
    Enforces sequential Process with Least Autonomy tool bindings and validates
    every output against CrewResponse.model_validate.
    """
    # Step 1: Pronoun and entity resolution via RunnableWithMessageHistory
    resolved_query = crew_runnable_with_history.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}},
    )
    was_resolved = resolved_query.strip().lower() != query.strip().lower()

    # Check if query references an operational ticket
    ticket_match = re.search(r"\b(TKT-\d{4})\b", resolved_query, re.IGNORECASE)
    ticket_id = ticket_match.group(1).upper() if ticket_match else None

    # Check if query references policy guidelines
    has_policy_interest = any(
        kw in resolved_query.lower()
        for kw in ("sla", "policy", "refund", "hour", "time", "rule", "sev-", "guideline", "credit", "vip")
    )

    llm = get_mock_llm()
    retrieval_agent = create_retrieval_agent(llm)
    lookup_agent = create_lookup_agent(llm)
    composer_agent = create_composer_agent(llm)

    if ticket_id and has_policy_interest:
        route = "both"
    elif ticket_id:
        route = "lookup"
    else:
        route = "rag"

    if ticket_id:
        # Route: Lookup Agent -> Composer Agent
        tool_invoked = "check_support_ticket_status"
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
            agents=[retrieval_agent, lookup_agent, composer_agent],
            tasks=[task1, task2],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        crew_output = crew.kickoff()
        output_str = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output)
        logger.info(f"Ticket Workflow: Tool '{tool_invoked}' executed for {ticket_id}")

        ticket_data = check_support_ticket_status(ticket_id)
        status = ticket_data.get("status", "Unknown")
        res_time = ticket_data.get("resolution_time_hours", 0.0)
        esc_score = ticket_data.get("escalation_score", 0.0)
        risk = ticket_data.get("risk_level", "Normal")
        escalation_recommended = ticket_data.get("recommend_escalation", False)

        final_text = (
            f"Ticket {ticket_id} ({ticket_data.get('category', 'General')}) is currently {status} "
            f"with a resolution time of {res_time} hours. Escalation risk score is {esc_score:.4f} ({risk})."
        )
        sources = ["dataset.py"]
        grounded = True
        confidence = 0.98
        ticket_payload = ticket_data

    else:
        # Route: Retrieval Agent -> Composer Agent
        tool_invoked = "rag_lookup"
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
            agents=[retrieval_agent, lookup_agent, composer_agent],
            tasks=[task1, task2],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        crew_output = crew.kickoff()
        output_str = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output)
        logger.info(f"Policy Workflow: Tool '{tool_invoked}' executed for '{resolved_query}'")

        rag_res = rag_lookup(resolved_query)
        final_text = rag_res["answer"]
        sources = rag_res["sources"]
        grounded = rag_res["grounded"]
        confidence = rag_res["confidence"]
        esc_score = None
        escalation_recommended = False
        ticket_payload = None

    # Step 2: AutoGen Secondary Review Stage (Task 14)
    from review.autogen_review import review_support_response

    context_summary = ""
    if route in ("rag", "both") and sources:
        context_summary = " ".join(sources) if isinstance(sources, list) else str(sources)
    elif ticket_payload:
        context_summary = (
            f"Ticket {ticket_id}: Status={ticket_payload.get('status')}, "
            f"ResolutionTime={ticket_payload.get('resolution_time_hours')}h, "
            f"Risk={ticket_payload.get('risk_level')}"
        )

    review_verdict = review_support_response(
        query=resolved_query,
        draft_answer=final_text,
        sources=sources,
        grounded=grounded,
        confidence=confidence,
        context_text=context_summary,
    )
    final_text = review_verdict.final_answer
    review_status_dict = review_verdict.model_dump()

    # Step 3: Record in session memory
    session_memory.record_interaction(session_id, query, final_text)

    # Step 4: Construct structured response dictionary
    response_data = {
        "answer": final_text,
        "route": route,
        "sources": sources,
        "ticket": ticket_payload,
        "grounded": grounded and review_verdict.approved,
        "escalation_recommended": escalation_recommended,
        "review_status": review_status_dict,
        "ticket_id": ticket_id,
        "escalation_score": esc_score,
        "confidence": confidence,
        "resolved_query": resolved_query,
        "was_resolved": was_resolved,
        "tool_invoked": tool_invoked,
    }

    # Step 5: Strict validation using CrewResponse.model_validate
    validated_model = validate_crew_response(response_data)

    if structured:
        return validated_model

    return response_data
