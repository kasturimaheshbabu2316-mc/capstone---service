"""CrewAI Multi-Agent Pipeline Coordinator.

Track: Business Operations / Customer Support (Ola)
Coordinates the 3-agent crew (Retrieval Agent, Lookup Agent, Response Composer),
executes sequential workflows via Crew.kickoff(), chains task contexts,
and validates output using CrewResponse.
"""

from __future__ import annotations

import os
# Suppress telemetry prior to CrewAI imports
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import json
import logging
import re
import threading
from typing import Any

from crewai import Crew, Task, Process
from crew.agents import (
    create_retrieval_agent,
    create_lookup_agent,
    create_composer_agent,
    get_mock_llm,
)
from crew.mock_llm import parse_ticket_from_text, extract_ticket_id
from crew.schemas import CrewResponse, validate_crew_response
from crew.memory import session_memory, crew_runnable_with_history

logger = logging.getLogger("ola_domain_agent.crew")

_crew_lock = threading.Lock()


def parse_ticket_from_output(task_output: Any) -> dict[str, Any]:
    """Extracts operational ticket metadata directly from the Lookup task's tool output."""
    text = ""
    if hasattr(task_output, "messages") and task_output.messages:
        for msg in task_output.messages:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if "Observation:" in content and "Ticket ID:" in content:
                text = content.split("Observation:", 1)[1]
                break
    if not text and hasattr(task_output, "raw"):
        text = str(task_output.raw)

    return parse_ticket_from_text(text)


def parse_rag_from_output(task_output: Any) -> dict[str, Any]:
    """Extracts policy sources, grounding status, and confidence directly from Retrieval task output."""
    text = ""
    if hasattr(task_output, "messages") and task_output.messages:
        for msg in task_output.messages:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if "Observation:" in content and "Policy Answer:" in content:
                text = content.split("Observation:", 1)[1]
                break
    if not text and hasattr(task_output, "raw"):
        text = str(task_output.raw)

    sources: list[str] = []
    grounded = True
    confidence = 0.85

    m_src = re.search(r"Sources:\s*([^\n]+)", text)
    if m_src:
        src_str = m_src.group(1).split("Grounded:")[0].strip()
        sources = [s.strip() for s in src_str.split(",") if s.strip() and s.strip() != "None"]
    else:
        m_paren = re.search(r"\(Sources:\s*([^\)]+)\)", text)
        if m_paren:
            sources = [s.strip() for s in m_paren.group(1).split(",") if s.strip() and s.strip() != "None"]

    m_grounded = re.search(r"Grounded:\s*(True|False)", text, re.IGNORECASE)
    if m_grounded:
        grounded = m_grounded.group(1).lower() == "true"

    m_conf = re.search(r"Confidence:\s*([0-9.]+)", text)
    if m_conf:
        try:
            confidence = float(m_conf.group(1))
        except ValueError:
            pass

    return {
        "sources": sources,
        "grounded": grounded,
        "confidence": confidence,
    }


def create_policy_crew(
    retrieval_agent=None, composer_agent=None
) -> tuple[Crew, Task, Task]:
    """Creates a fresh Policy Crew with sequential task context chaining."""
    rag_agent = retrieval_agent or create_retrieval_agent()
    comp_agent = composer_agent or create_composer_agent()
    task1 = Task(
        description="Search internal policies for: '{query}'.",
        expected_output="Relevant policy excerpts and citations.",
        agent=rag_agent,
    )
    task2 = Task(
        description="Compose a grounded customer answer to: '{query}' using retrieved policies.",
        expected_output="Clear, grounded customer policy answer.",
        agent=comp_agent,
        context=[task1],
    )
    crew = Crew(
        agents=[rag_agent, comp_agent],
        tasks=[task1, task2],
        process=Process.sequential,
        verbose=False,
    )
    return crew, task1, task2


def create_ticket_crew(
    lookup_agent=None, composer_agent=None
) -> tuple[Crew, Task, Task]:
    """Creates a fresh Ticket Crew with sequential task context chaining."""
    look_agent = lookup_agent or create_lookup_agent()
    comp_agent = composer_agent or create_composer_agent()
    task1 = Task(
        description="Check the status, resolution time, and escalation risk for ticket {ticket_id}.",
        expected_output="Operational status, metrics, and escalation risk calculation.",
        agent=look_agent,
    )
    task2 = Task(
        description="Draft a courteous, concise customer response explaining the status of ticket {ticket_id}.",
        expected_output="Final customer-facing response text.",
        agent=comp_agent,
        context=[task1],
    )
    crew = Crew(
        agents=[look_agent, comp_agent],
        tasks=[task1, task2],
        process=Process.sequential,
        verbose=False,
    )
    return crew, task1, task2


def create_both_crew(
    retrieval_agent=None, lookup_agent=None, composer_agent=None
) -> tuple[Crew, Task, Task, Task]:
    """Creates a fresh Crew for hybrid ticket + policy queries, chaining both contexts to Composer."""
    rag_agent = retrieval_agent or create_retrieval_agent()
    look_agent = lookup_agent or create_lookup_agent()
    comp_agent = composer_agent or create_composer_agent()
    task_retrieval = Task(
        description="Search internal policies for: '{query}'.",
        expected_output="Relevant policy excerpts and citations.",
        agent=rag_agent,
    )
    task_lookup = Task(
        description="Check the status, resolution time, and escalation risk for ticket {ticket_id}.",
        expected_output="Operational status, metrics, and escalation risk calculation.",
        agent=look_agent,
    )
    task_composer = Task(
        description="Synthesize both ticket status for {ticket_id} and policy guidelines for '{query}' into a comprehensive customer response.",
        expected_output="Final customer-facing response covering ticket details and policy.",
        agent=comp_agent,
        context=[task_retrieval, task_lookup],
    )
    crew = Crew(
        agents=[rag_agent, look_agent, comp_agent],
        tasks=[task_retrieval, task_lookup, task_composer],
        process=Process.sequential,
        verbose=False,
    )
    return crew, task_retrieval, task_lookup, task_composer


def get_policy_crew() -> Crew:
    """Legacy helper returning a fresh policy crew."""
    crew, _, _ = create_policy_crew()
    return crew


def get_ticket_crew() -> Crew:
    """Legacy helper returning a fresh ticket crew."""
    crew, _, _ = create_ticket_crew()
    return crew


def run_support_crew(
    query: str,
    session_id: str = "default_session",
    structured: bool = False,
) -> dict[str, Any] | CrewResponse:
    """Executes the CrewAI 3-agent pipeline on the given user query.

    Chains tasks with context=[...] so the Composer receives retrieval or lookup output.
    Uses the crew's result as the answer, extracts ticket data directly from Lookup task output,
    handles route 'both', and enforces least autonomy boundaries.
    """
    # Step 1: Pronoun and entity resolution via RunnableWithMessageHistory
    resolved_query = crew_runnable_with_history.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}},
    )
    was_resolved = resolved_query.strip().lower() != query.strip().lower()

    # Check if query references an operational ticket (with paraphrase normalization)
    ticket_id = extract_ticket_id(resolved_query)

    # Check if query references policy guidelines
    has_policy_interest = any(
        kw in resolved_query.lower()
        for kw in (
            "sla", "policy", "refund", "hour", "time", "rule", "sev-",
            "guideline", "credit", "vip", "clause", "safe-harbor", "harbor", "fastag", "toll"
        )
    )

    if ticket_id and has_policy_interest:
        route = "both"
    elif ticket_id:
        route = "lookup"
    else:
        route = "rag"

    # Step 2: Thread-safe execution of fresh Crew per request
    with _crew_lock:
        if route == "both":
            crew, task_retrieval, task_lookup, task_composer = create_both_crew()
            crew_output = crew.kickoff(inputs={"query": resolved_query, "ticket_id": ticket_id})
            final_text = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output).strip()

            ticket_payload = parse_ticket_from_output(task_lookup.output)
            rag_meta = parse_rag_from_output(task_retrieval.output)
            sources = rag_meta.get("sources", [])
            grounded = rag_meta.get("grounded", True)
            confidence = rag_meta.get("confidence", 0.95)
            esc_score = ticket_payload.get("escalation_score")
            escalation_recommended = ticket_payload.get("recommend_escalation", False)
            tool_invoked = "check_support_ticket_status, rag_lookup"

        elif route == "lookup":
            crew, task_lookup, task_composer = create_ticket_crew()
            crew_output = crew.kickoff(inputs={"ticket_id": ticket_id})
            final_text = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output).strip()

            ticket_payload = parse_ticket_from_output(task_lookup.output)
            sources = ["dataset.py"]
            grounded = True
            confidence = 0.98
            esc_score = ticket_payload.get("escalation_score")
            escalation_recommended = ticket_payload.get("recommend_escalation", False)
            tool_invoked = "check_support_ticket_status"

        else:
            crew, task_retrieval, task_composer = create_policy_crew()
            crew_output = crew.kickoff(inputs={"query": resolved_query})
            final_text = str(crew_output.raw if hasattr(crew_output, "raw") else crew_output).strip()

            rag_meta = parse_rag_from_output(task_retrieval.output)
            sources = rag_meta.get("sources", [])
            grounded = rag_meta.get("grounded", True)
            confidence = rag_meta.get("confidence", 0.85)
            esc_score = None
            escalation_recommended = False
            ticket_payload = None
            tool_invoked = "rag_lookup"

    # Step 3: AutoGen Secondary Review Stage (Task 14) with Coordinator Feedback Loop
    from review.autogen_review import review_support_response

    context_summary = ""
    if route == "both":
        ticket_ctx = (
            f"Ticket {ticket_id}: Status={ticket_payload.get('status')}, "
            f"ResolutionTime={ticket_payload.get('resolution_time_hours')}h, "
            f"Risk={ticket_payload.get('risk_level')}, "
            f"EscalationScore={ticket_payload.get('escalation_score')}"
        ) if ticket_payload else ""
        sources_ctx = " ".join(sources) if isinstance(sources, list) else str(sources)
        context_summary = f"{ticket_ctx} {sources_ctx}".strip()
    elif route in ("rag", "both") and sources:
        context_summary = " ".join(sources) if isinstance(sources, list) else str(sources)
    elif ticket_payload:
        context_summary = (
            f"Ticket {ticket_id}: Status={ticket_payload.get('status')}, "
            f"ResolutionTime={ticket_payload.get('resolution_time_hours')}h, "
            f"Risk={ticket_payload.get('risk_level')}, "
            f"EscalationScore={ticket_payload.get('escalation_score')}"
        )

    review_verdict = review_support_response(
        query=resolved_query,
        draft_answer=final_text,
        sources=sources,
        grounded=grounded,
        confidence=confidence,
        context_text=context_summary,
    )

    if not review_verdict.approved:
        logger.warning(
            "Compliance review flagged issue in draft: '%s'. Adopting compliant revised text.",
            review_verdict.reason,
        )
        final_text = review_verdict.final_answer
    else:
        final_text = review_verdict.final_answer

    review_status_dict = review_verdict.model_dump()

    # Step 4: Record in session memory
    session_memory.record_interaction(session_id, query, final_text)

    # Step 5: Construct structured response dictionary
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

    # Step 6: Strict validation using CrewResponse.model_validate
    validated_model = validate_crew_response(response_data)

    if structured:
        return validated_model

    return response_data
