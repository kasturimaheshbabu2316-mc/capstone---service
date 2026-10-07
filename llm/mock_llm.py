"""Deterministic Mock LLM Implementation for CrewAI and Agent Workflows.

Track: Business Operations / Customer Support (Ola)
Provides MockLLM subclassing crewai.llms.base_llm.BaseLLM to guarantee 100% offline,
deterministic, zero-cost execution with zero API keys.
Resolves Pitfall 1 (Template Contamination) and Pitfall 2 (Tool Substring Collision).
"""

from typing import Any
import re
import json
from pydantic import BaseModel
from crewai.llms.base_llm import BaseLLM
from tools.ticket_tool import check_support_ticket_status
from tools.rag_tool import rag_lookup


class MockLLM(BaseLLM):
    """Deterministic, zero-network Mock LLM adhering to CrewAI's BaseLLM specification."""

    def __init__(self, model: str = "mock-ola-support-v1", **kwargs: Any):
        super().__init__(model=model, **kwargs)
        self.model = model

    def _extract_recent_text(self, messages: Any) -> tuple[str, str]:
        """Extracts the system instructions and the most recent message turn to avoid template contamination."""
        full_text = ""
        recent_turn = ""

        if isinstance(messages, str):
            full_text = messages
            # Look for recent user input or observation appended after prompt
            parts = messages.split("Observation:")
            if len(parts) > 1:
                recent_turn = "Observation:" + parts[-1]
            else:
                recent_turn = messages
        elif isinstance(messages, list):
            for m in messages:
                content = m.get("content", "") if isinstance(m, dict) else str(m)
                full_text += "\n" + content
            if messages:
                last_msg = messages[-1]
                recent_turn = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        return full_text, recent_turn

    def _extract_ticket_id(self, text: str) -> str | None:
        """Extracts ticket ID matching TKT-XXXX pattern."""
        match = re.search(r"\b(TKT-\d{4})\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    def call(
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> str:
        """Executes a deterministic ReAct step or synthesis turn."""
        full_text, recent_turn = self._extract_recent_text(messages)
        agent_role = getattr(from_agent, "role", "") if from_agent else ""

        # --- Pitfall 1 Guard: Verify if a REAL tool observation has arrived ---
        # Exclude CrewAI prompt template instructions ("Observation: the result of the action")
        has_real_observation = False
        obs_lines = re.findall(r"(?:^|\n)Observation:\s*([^\n]+)", full_text)
        for obs in obs_lines:
            obs_clean = obs.strip()
            if obs_clean and "the result of the action" not in obs_clean and not obs_clean.startswith("["):
                has_real_observation = True
                break

        # Check if tools are provided to this agent
        agent_tools = getattr(from_agent, "tools", []) if from_agent else []
        tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in agent_tools]

        # -------------------------------------------------------------
        # STEP 1: ReAct Action dispatch (Call 1 when tools exist and no real observation yet)
        # -------------------------------------------------------------
        if agent_tools and not has_real_observation:
            ticket_id = self._extract_ticket_id(full_text)

            # Pitfall 2 Solution: Explicit schema-based dispatch based on agent role & tool names
            if any("check_support_ticket_status" in name for name in tool_names) or "Ticket" in agent_role or "Lookup" in agent_role:
                tid = ticket_id or "TKT-0001"
                action_input = json.dumps({"record_id": tid})
                return (
                    f"Thought: I need to check the status and escalation risk for ticket {tid}.\n"
                    f"Action: check_support_ticket_status\n"
                    f"Action Input: {action_input}"
                )

            if "rag_lookup" in tool_names or "Retrieval" in agent_role:
                # Extract clean user query
                query_str = full_text
                # If there is a 'user' turn or 'Task:' line, extract it
                task_match = re.search(r"(?:Task:|User:)\s*([^\n]+)", full_text)
                if task_match:
                    query_str = task_match.group(1).strip()
                elif "What" in full_text or "How" in full_text or "When" in full_text:
                    q_line = [line for line in full_text.splitlines() if any(k in line for k in ["What", "How", "When", "SLA", "refund"])]
                    if q_line:
                        query_str = q_line[-1].strip()

                action_input = json.dumps({"query": query_str})
                return (
                    f"Thought: I need to search the knowledge base for policy guidelines.\n"
                    f"Action: rag_lookup\n"
                    f"Action Input: {action_input}"
                )

        # -------------------------------------------------------------
        # STEP 2: ReAct Final Answer or Direct Synthesis (Call 2 or Toolless Agent)
        # -------------------------------------------------------------
        ticket_id = self._extract_ticket_id(full_text)

        # Case A: Response Model requested (Task 9 Structured Pydantic Output)
        if response_model is not None:
            if ticket_id:
                ticket_res = check_support_ticket_status(ticket_id)
                status = ticket_res.get("status", "Unknown")
                res_time = ticket_res.get("resolution_time_hours", 0.0)
                esc_score = ticket_res.get("escalation_score", 0.0)
                risk = ticket_res.get("risk_level", "Normal")
                ans = (
                    f"Ticket {ticket_id} is currently {status} with resolution time of {res_time} hours. "
                    f"Escalation score is {esc_score:.4f} ({risk})."
                )
                payload = {
                    "answer": ans,
                    "sources": ["dataset.py"],
                    "ticket_id": ticket_id,
                    "escalation_score": esc_score,
                    "grounded": True,
                    "confidence": 0.98,
                }
            else:
                rag_res = rag_lookup(full_text)
                payload = {
                    "answer": rag_res["answer"],
                    "sources": rag_res["sources"],
                    "ticket_id": None,
                    "escalation_score": None,
                    "grounded": rag_res["grounded"],
                    "confidence": rag_res["confidence"],
                }
            return json.dumps(payload)

        # Case B: Ticket query answer synthesis
        if ticket_id or "Lookup" in agent_role:
            tid = ticket_id or "TKT-0001"
            ticket_res = check_support_ticket_status(tid)
            if "error" in ticket_res:
                ans = f"Ticket {tid} could not be found in the system."
            else:
                ans = (
                    f"Ticket {tid} ({ticket_res['category']}) is currently {ticket_res['status']}. "
                    f"Recorded resolution time is {ticket_res['resolution_time_hours']} hours. "
                    f"Escalation score: {ticket_res['escalation_score']:.4f} ({ticket_res['risk_level']})."
                )
            return f"Thought: I now know the final answer.\nFinal Answer: {ans}"

        # Case C: Policy query answer synthesis
        rag_res = rag_lookup(full_text)
        sources_str = ", ".join(rag_res["sources"]) if rag_res["sources"] else "None"
        ans = f"{rag_res['answer']} (Sources: {sources_str})"
        return f"Thought: I now know the final answer.\nFinal Answer: {ans}"
