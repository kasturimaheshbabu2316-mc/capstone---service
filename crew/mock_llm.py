"""CrewAI Deterministic MockLLM Implementation (Task 7).

Track: Business Operations / Customer Support (Ola)
Provides MockLLM subclassing crewai.llms.base_llm.BaseLLM (the documented extension point).
Adheres strictly to the ReAct framework and resolves both known silent pitfalls:
1. Pitfall A: Template contamination - ignores template placeholder 'Observation: the result of the action'.
2. Pitfall B: Tool dispatch by declared argument schema (e.g. 'record_id' vs 'query'),
   never by tool name substring matching.
"""

from __future__ import annotations

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
from governance.least_autonomy import CURRENT_CALLER_ROLE


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
    """Extracts and standardizes ticket IDs from natural and paraphrased text to TKT-XXXX.

    Supports:
    - Standard: TKT-0007, tkt-0007, TKT0007, TKT 0007
    - Unpadded/paraphrased: tkt 7, ticket 7, ticket no. 0007, ticket #7, ticket id: 7
    - Natural language: "what's happening with TKT-0007", "status of tkt 7"
    """
    if not text:
        return None
    pattern = re.compile(
        r"\b(?:ticket|tkt)[\s\-_]*(?:no\.?|id|#|number|num)?[:\s\-_]*(\d{1,4})\b",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    if m:
        num = int(m.group(1))
        return f"TKT-{num:04d}"

    m2 = re.search(r"\bTKT[\-_]?(\d{1,4})\b", text, re.IGNORECASE)
    if m2:
        num = int(m2.group(1))
        return f"TKT-{num:04d}"

    return None


def extract_query_text(text: str) -> str:
    """Extracts the underlying user question or task description from message text."""
    m_search = re.search(r"Search internal policies for:\s*['\"]([^'\"]+)['\"]", text)
    if m_search:
        return m_search.group(1).strip()
    task_match = re.search(r"(?:Task:|User:)\s*([^\n]+)", text)
    if task_match:
        return task_match.group(1).strip()
    for line in text.splitlines():
        line_clean = line.strip()
        if any(line_clean.startswith(prefix) for prefix in ("What", "How", "When", "Why", "Where", "Can", "Is")):
            return line_clean
    return text.strip()


def parse_ticket_from_text(text: str) -> dict[str, Any]:
    """Reconstructs ticket metadata fields from tool output text or synthesized string."""
    data: dict[str, Any] = {}
    patterns = {
        "record_id": r"(?:Ticket ID|ticket_id|record_id|Ticket)\s*:?\s*(TKT-\d{4})",
        "status": r"(?:Status:\s*([A-Za-z ]+?)(?:\.|\n|$)|is currently\s+([A-Za-z ]+?)(?:\.|\n|,|$))",
        "category": r"(?:Category:\s*([A-Za-z0-9_ -]+)|\((Billing|Technical Issue|Account Access|Product Defect|General Inquiry)\))",
        "resolution_time_hours": r"(?:Resolution Time:\s*([0-9.]+)|resolution time (?:is|of)\s*([0-9.]+))",
        "days_since_created": r"Days Since Created:\s*([0-9]+)",
        "escalated": r"Escalated:\s*(True|False)",
        "escalation_score": r"Escalation [Ss]core(?:\s*is)?:\s*([0-9.]+)",
        "risk_level": r"(?:Risk Level:\s*([^\n]+)|\((High Risk|Normal|Unknown)\))",
        "recommend_escalation": r"Recommend Escalation:\s*(True|False)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = next((g for g in m.groups() if g is not None), "").strip()
            if key in ("resolution_time_hours", "escalation_score"):
                try:
                    data[key] = float(val)
                except ValueError:
                    pass
            elif key == "days_since_created":
                try:
                    data[key] = int(val)
                except ValueError:
                    pass
            elif key in ("escalated", "recommend_escalation"):
                data[key] = val.lower() == "true"
            else:
                data[key] = val
    if "record_id" in data:
        data["ticket_id"] = data["record_id"]
    return data


class MockLLM(BaseLLM):
    """Deterministic, offline Mock LLM subclassing CrewAI BaseLLM.

    Emits ReAct sequences:
      Turn 1 (Tool turn) : Thought / Action / Action Input
      Turn 2 (Answer turn): Thought: I now know the final answer / Final Answer: ...
    For Composer agents:
      Composes answers exclusively from input context, never invoking tools.
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

        # Propagate calling agent role to thread/contextvar for least-autonomy checks
        agent_role = getattr(from_agent, "role", None) if from_agent else None
        if agent_role:
            CURRENT_CALLER_ROLE.set(agent_role)

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

        # Determine if current execution is under the Composer agent
        is_composer = (
            (from_agent and any(term in getattr(from_agent, "role", "") for term in ("Composer", "Support Response")))
            or (from_task and any(term in getattr(from_task, "description", "").lower() for term in ("compose", "draft", "synthesize")))
            or (not candidate_tools and ("this is the context you're working with:" in full_text.lower() or "expected criteria" in full_text.lower()))
        )

        # -------------------------------------------------------------
        # STEP 1: ReAct Action dispatch (Turn 1 when tool is present and no observation yet)
        # -------------------------------------------------------------
        if (ticket_tool or rag_tool) and not has_real_obs and not is_composer:
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
        # STEP 2: Response Composer Agent (Context-only, ZERO tool calls)
        # -------------------------------------------------------------
        if is_composer:
            context_text = ""
            if "This is the context you're working with:" in full_text:
                context_text = full_text.split("This is the context you're working with:", 1)[1]
                if "Provide your complete response:" in context_text:
                    context_text = context_text.split("Provide your complete response:")[0]
                context_text = context_text.strip()
            elif has_real_obs:
                context_text = obs_content.strip()
            else:
                context_text = full_text.strip()

            t_data = parse_ticket_from_text(context_text)
            has_ticket = bool(t_data.get("record_id"))

            policy_text = ""
            sources_list: list[str] = []
            if "Policy Answer:" in context_text or "Sources:" in context_text:
                clean_p = context_text
                if "Policy Answer:" in clean_p:
                    clean_p = clean_p.split("Policy Answer:", 1)[1]
                if "Sources:" in clean_p:
                    p_body, p_src = clean_p.split("Sources:", 1)
                    policy_text = p_body.rstrip(" (").strip()
                    src_raw = p_src.split("Grounded:")[0].split("\n")[0].strip()
                    sources_list = [s.strip() for s in src_raw.split(",") if s.strip() and s.strip() != "None"]
                else:
                    policy_text = clean_p.strip()
            elif "(Sources:" in context_text:
                m_src = re.search(r"\(Sources:\s*([^\)]+)\)", context_text)
                if m_src:
                    sources_list = [s.strip() for s in m_src.group(1).split(",") if s.strip() and s.strip() != "None"]
                policy_text = context_text
            elif not has_ticket:
                policy_text = context_text

            if has_ticket and policy_text and "ticket" not in policy_text.lower():
                tid = t_data.get("record_id", "TKT-0001")
                cat = t_data.get("category", "General")
                st = t_data.get("status", "Open")
                rt = t_data.get("resolution_time_hours", 0.0)
                esc = t_data.get("escalation_score", 0.0)
                rk = t_data.get("risk_level", "Normal")
                prio_str = "High priority" if esc >= 0.44 else "Standard priority"
                risk_lbl = "High Risk" if esc >= 0.44 else "Normal"
                ans = (
                    f"Ticket {tid} ({cat}) is currently {st} with a resolution time of {rt} hours ({prio_str}). Escalation risk score is {esc:.4f} ({risk_lbl}).\n\nPolicy Guidelines: {policy_text}"
                )
            elif has_ticket:
                tid = t_data.get("record_id", "TKT-0001")
                cat = t_data.get("category", "General")
                st = t_data.get("status", "Open")
                rt = t_data.get("resolution_time_hours", 0.0)
                esc = t_data.get("escalation_score", 0.0)
                rk = t_data.get("risk_level", "Normal")
                prio_str = "High priority" if esc >= 0.44 else "Standard priority"
                risk_lbl = "High Risk" if esc >= 0.44 else "Normal"
                ans = (
                    f"Ticket {tid} ({cat}) is currently {st} with a resolution time of {rt} hours ({prio_str}). Escalation risk score is {esc:.4f} ({risk_lbl})."
                )
            else:
                ans = policy_text or context_text

            wants_json = (response_model is not None) or (
                "json" in full_text.lower() and ("crewresponse" in full_text.lower() or "route" in full_text.lower())
            )
            if wants_json:
                route_name = "both" if (has_ticket and policy_text) else ("lookup" if has_ticket else "rag")
                payload = {
                    "answer": ans,
                    "route": route_name,
                    "sources": sources_list if sources_list else (["dataset.py"] if has_ticket else []),
                    "ticket": t_data if has_ticket else None,
                    "ticket_id": t_data.get("record_id") if has_ticket else None,
                    "escalation_score": t_data.get("escalation_score") if has_ticket else None,
                    "escalation_recommended": t_data.get("recommend_escalation", False) if has_ticket else False,
                    "grounded": True,
                    "confidence": 0.98 if has_ticket else 0.85,
                    "review_status": {
                        "approved": True,
                        "final_answer": ans,
                        "reason": "Composed from verified agent context.",
                        "redactions_made": False,
                    },
                }
                json_str = json.dumps(payload)
                if response_model is not None:
                    return json_str
                return f"Thought: I now know the final answer.\nFinal Answer: {json_str}"

            return f"Thought: I now know the final answer.\nFinal Answer: {ans}"

        # -------------------------------------------------------------
        # STEP 3: ReAct Turn 2 Answer synthesis for Tool-Calling Agents
        # -------------------------------------------------------------
        if has_real_obs:
            if ticket_tool or "Ticket ID:" in obs_content or "check_support_ticket_status" in full_text:
                t_data = parse_ticket_from_text(obs_content)
                tid = t_data.get("record_id", ticket_id or "TKT-0001")
                cat = t_data.get("category", "General")
                st = t_data.get("status", "Open")
                rt = t_data.get("resolution_time_hours", 0.0)
                esc = t_data.get("escalation_score", 0.0)
                rk = t_data.get("risk_level", "Normal")
                ans = f"Ticket {tid} ({cat}) is currently {st}. Recorded resolution time is {rt} hours. Escalation score: {esc:.4f} ({rk})."
                return f"Thought: I now know the final answer.\nFinal Answer: {ans}"

            if rag_tool or "Policy Answer:" in obs_content or "rag_lookup" in full_text:
                clean_ans = obs_content
                if "Policy Answer:" in obs_content:
                    clean_ans = obs_content.split("Policy Answer:", 1)[1]
                    if "Sources:" in clean_ans:
                        p_ans, p_src = clean_ans.split("Sources:", 1)
                        clean_ans = p_ans.rstrip(" (").strip()
                        src_str = p_src.split("Grounded:")[0].strip()
                        clean_ans = f"{clean_ans} (Sources: {src_str})"
                    else:
                        clean_ans = clean_ans.strip()
                return f"Thought: I now know the final answer.\nFinal Answer: {clean_ans}"

        # -------------------------------------------------------------
        # STEP 4: Fallback Standalone Synthesis (Direct MockLLM calls without Crew)
        # -------------------------------------------------------------
        from tools.ticket_tool import check_support_ticket_status
        from tools.rag_tool import rag_lookup

        wants_json = (response_model is not None) or (
            "json" in full_text.lower() and ("crewresponse" in full_text.lower() or "route" in full_text.lower())
        )

        if wants_json:
            if ticket_id:
                ticket_res = check_support_ticket_status(ticket_id, caller_role="Lookup Agent")
                status = ticket_res.get("status", "Unknown")
                res_time = ticket_res.get("resolution_time_hours", 0.0)
                esc_score = ticket_res.get("escalation_score", 0.0)
                risk = ticket_res.get("risk_level", "Normal")
                esc_rec = ticket_res.get("recommend_escalation", False)
                prio_str = "High priority" if esc_score >= 0.44 else "Standard priority"
                ans = (
                    f"Ticket {ticket_id} is currently {status} with resolution time of {res_time} hours ({prio_str})."
                )
                payload = {
                    "answer": ans,
                    "route": "lookup",
                    "sources": ["dataset.py"],
                    "ticket": ticket_res,
                    "ticket_id": ticket_id,
                    "escalation_score": esc_score,
                    "escalation_recommended": esc_rec,
                    "grounded": True,
                    "confidence": 0.98,
                    "review_status": {
                        "approved": True,
                        "final_answer": ans,
                        "reason": "Verified operational ticket data against dataset.",
                        "redactions_made": False,
                    },
                }
            else:
                clean_q = extract_query_text(full_text)
                rag_res = rag_lookup(clean_q, caller_role="Policy Retrieval Specialist")
                ans = rag_res["answer"]
                payload = {
                    "answer": ans,
                    "route": "rag",
                    "sources": rag_res["sources"],
                    "ticket": None,
                    "ticket_id": None,
                    "escalation_score": None,
                    "escalation_recommended": False,
                    "grounded": rag_res["grounded"],
                    "confidence": rag_res["confidence"],
                    "review_status": {
                        "approved": True,
                        "final_answer": ans,
                        "reason": "Verified policy guidelines against knowledge base.",
                        "redactions_made": False,
                    },
                }

            json_str = json.dumps(payload)
            if response_model is not None:
                return json_str
            return f"Thought: I now know the final answer.\nFinal Answer: {json_str}"

        if ticket_id:
            ticket_res = check_support_ticket_status(ticket_id, caller_role="Lookup Agent")
            if "error" in ticket_res:
                ans = f"Ticket {ticket_id} could not be found in the operational database."
            else:
                ans = (
                    f"Ticket {ticket_id} ({ticket_res['category']}) is currently {ticket_res['status']}. "
                    f"Recorded resolution time is {ticket_res['resolution_time_hours']} hours. "
                    f"Escalation score: {ticket_res['escalation_score']:.4f} ({ticket_res['risk_level']})."
                )
            return f"Thought: I now know the final answer.\nFinal Answer: {ans}"

        clean_q = extract_query_text(full_text)
        rag_res = rag_lookup(clean_q, caller_role="Policy Retrieval Specialist")
        sources_str = ", ".join(rag_res["sources"]) if rag_res["sources"] else "None"
        ans = f"{rag_res['answer']} (Sources: {sources_str})"
        return f"Thought: I now know the final answer.\nFinal Answer: {ans}"
