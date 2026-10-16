"""CrewAI Deterministic MockLLM Implementation (Task 7).

Track: Business Operations / Customer Support (Ola)
Provides MockLLM subclassing crewai.llms.base_llm.BaseLLM (the documented extension point).
Adheres strictly to the ReAct framework and resolves both known silent pitfalls:
1. Pitfall A: Template contamination - ignores template placeholder 'Observation: the result of the action'.
2. Pitfall B: Tool dispatch by declared argument schema (e.g. 'record_id' vs 'query'),
   never by tool name substring matching.
"""

import os
# Suppress telemetry prior to any CrewAI imports
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import inspect
import json
import re
from typing import Any
from pydantic import BaseModel
from crewai.llms.base_llm import BaseLLM
from tools.ticket_tool import check_support_ticket_status
from tools.rag_tool import rag_lookup


def get_tool_arg_names(tool: Any) -> list[str]:
    """Extracts declared parameter names from a tool's schema or signature.

    Resolves Pitfall B: Dispatches by declared argument schema rather than tool name.
    """
    # 1. Pydantic schema via args_schema (standard CrewAI / LangChain tool)
    schema = getattr(tool, "args_schema", None)
    if schema:
        if hasattr(schema, "model_fields"):
            return list(schema.model_fields.keys())
        if hasattr(schema, "__fields__"):
            return list(schema.__fields__.keys())

    # 2. args dictionary (LangChain BaseTool attribute)
    args_dict = getattr(tool, "args", None)
    if isinstance(args_dict, dict):
        return list(args_dict.keys())

    # 3. underlying function signature
    fn = getattr(tool, "fn", getattr(tool, "func", tool))
    if callable(fn):
        try:
            return list(inspect.signature(fn).parameters.keys())
        except Exception:
            pass

    return []


def check_for_real_observation(messages: Any) -> tuple[bool, str]:
    """Checks whether a real tool result has arrived, ignoring system prompt template text.

    Resolves Pitfall A: Excludes CrewAI prompt template instructions
    ('Observation: the result of the action') and only recognizes observations
    appearing in non-system turns or after the model's Action Input.
    """
    if isinstance(messages, list):
        # Exclude system messages where CrewAI's ReAct template instructions live
        non_system_turns = [
            m for m in messages
            if (isinstance(m, dict) and m.get("role") != "system")
            or (hasattr(m, "role") and getattr(m, "role") != "system")
        ]
        for turn in reversed(non_system_turns):
            content = turn.get("content", "") if isinstance(turn, dict) else getattr(turn, "content", str(turn))
            role = turn.get("role", "") if isinstance(turn, dict) else getattr(turn, "role", "")
            if role in ("tool", "function"):
                return True, str(content).strip()
            if "Observation:" in content:
                obs_part = content.split("Observation:", 1)[1].strip()
                if obs_part and "the result of the action" not in obs_part:
                    return True, obs_part
        return False, ""

    elif isinstance(messages, str):
        # In a plain string, CrewAI appends turns sequentially.
        # A real observation must appear strictly AFTER the model's 'Action Input:'.
        if "Action Input:" in messages:
            after_action_input = messages.rsplit("Action Input:", 1)[1]
            if "Observation:" in after_action_input:
                obs_part = after_action_input.split("Observation:", 1)[1].strip()
                first_line = obs_part.splitlines()[0] if obs_part else ""
                if first_line and "the result of the action" not in first_line:
                    return True, obs_part
        return False, ""

    return False, ""


def extract_ticket_id(text: str) -> str | None:
    """Extracts ticket ID matching TKT-XXXX pattern."""
    match = re.search(r"\b(TKT-\d{4})\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def extract_query_text(text: str) -> str:
    """Extracts the underlying user question or task description from message text."""
    task_match = re.search(r"(?:Task:|User:)\s*([^\n]+)", text)
    if task_match:
        return task_match.group(1).strip()
    for line in text.splitlines():
        line_clean = line.strip()
        if any(line_clean.startswith(prefix) for prefix in ("What", "How", "When", "Why", "Where", "Can", "Is")):
            return line_clean
    return text.strip()


class MockLLM(BaseLLM):
    """Deterministic, offline Mock LLM subclassing CrewAI BaseLLM.

    Emits ReAct sequences:
      Turn 1 (Tool turn) : Thought / Action / Action Input
      Turn 2 (Answer turn): Thought: I now know the final answer / Final Answer: ...
    """

    def __init__(self, model: str = "mock-ola-support-v1", **kwargs: Any):
        super().__init__(model=model, **kwargs)
        self.model = model

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
        # Convert messages to string representation for content analysis
        if isinstance(messages, str):
            full_text = messages
        elif isinstance(messages, list):
            full_text = "\n".join(
                (m.get("content", "") if isinstance(m, dict) else getattr(m, "content", str(m)))
                for m in messages
            )
        else:
            full_text = str(messages)

        # 1. Collect candidate tools available for this step
        candidate_tools: list[Any] = []
        if tools:
            candidate_tools.extend(tools if isinstance(tools, list) else [tools])
        if from_agent and hasattr(from_agent, "tools") and from_agent.tools:
            candidate_tools.extend(from_agent.tools)
        if available_functions:
            candidate_tools.extend(available_functions if isinstance(available_functions, list) else [available_functions])

        # 2. Inspect tools by declared args schema (Pitfall B)
        ticket_tool = None
        rag_tool = None

        for t in candidate_tools:
            arg_names = get_tool_arg_names(t)
            if "record_id" in arg_names:
                ticket_tool = t
            elif "query" in arg_names:
                rag_tool = t

        # 3. Check for real observation (Pitfall A)
        has_real_obs, obs_content = check_for_real_observation(messages)

        ticket_id = extract_ticket_id(full_text)

        # -------------------------------------------------------------
        # STEP 1: ReAct Action dispatch (Turn 1 when tool is present and no observation yet)
        # -------------------------------------------------------------
        if (ticket_tool or rag_tool) and not has_real_obs:
            if ticket_tool:
                tid = ticket_id or "TKT-0001"
                tool_name = getattr(ticket_tool, "name", "check_support_ticket_status")
                action_input = json.dumps({"record_id": tid})
                return (
                    f"Thought: I need to check the status and escalation risk for ticket {tid}.\n"
                    f"Action: {tool_name}\n"
                    f"Action Input: {action_input}"
                )

            if rag_tool:
                clean_q = extract_query_text(full_text)
                tool_name = getattr(rag_tool, "name", "rag_lookup")
                action_input = json.dumps({"query": clean_q})
                return (
                    f"Thought: I need to search the knowledge base for policy guidelines.\n"
                    f"Action: {tool_name}\n"
                    f"Action Input: {action_input}"
                )

        # -------------------------------------------------------------
        # STEP 2: ReAct Final Answer or Direct Synthesis (Turn 2 or Toolless Agent)
        # -------------------------------------------------------------

        # Case A: Structured Pydantic Output requested (Task 9)
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

        # Case B: Ticket query synthesis
        if ticket_id:
            ticket_res = check_support_ticket_status(ticket_id)
            if "error" in ticket_res:
                ans = f"Ticket {ticket_id} could not be found in the operational database."
            else:
                ans = (
                    f"Ticket {ticket_id} ({ticket_res['category']}) is currently {ticket_res['status']}. "
                    f"Recorded resolution time is {ticket_res['resolution_time_hours']} hours. "
                    f"Escalation score: {ticket_res['escalation_score']:.4f} ({ticket_res['risk_level']})."
                )
            return f"Thought: I now know the final answer.\nFinal Answer: {ans}"

        # Case C: Policy query synthesis
        clean_q = extract_query_text(full_text)
        rag_res = rag_lookup(clean_q)
        sources_str = ", ".join(rag_res["sources"]) if rag_res["sources"] else "None"
        ans = f"{rag_res['answer']} (Sources: {sources_str})"
        return f"Thought: I now know the final answer.\nFinal Answer: {ans}"
