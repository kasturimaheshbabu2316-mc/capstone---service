"""Conversational Session Memory & Entity Resolution Module (Task 8).

Track: Business Operations / Customer Support (Ola)
Uses InMemoryChatMessageHistory + RunnableWithMessageHistory with a session_id store.
NOTE: LangChainDeprecationWarning is expected and NOT silenced per system specification.
Injects conversation history into tasks for pronoun resolution (e.g., 'what about its SLA?').
"""

import re
from typing import Any
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

# Session store mapping session_id -> InMemoryChatMessageHistory
SESSION_STORE: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Retrieves or creates an InMemoryChatMessageHistory instance for the given session."""
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = InMemoryChatMessageHistory()
    return SESSION_STORE[session_id]


def extract_last_entities_from_history(history: list[BaseMessage]) -> tuple[str | None, str | None]:
    """Inspects chat history messages in reverse to find the most recent ticket ID or policy topic."""
    last_ticket_id: str | None = None
    last_policy_topic: str | None = None

    for msg in reversed(history):
        content = msg.content if hasattr(msg, "content") else str(msg)

        # Check for ticket ID
        if not last_ticket_id:
            ticket_match = re.search(r"\b(TKT-\d{4})\b", content, re.IGNORECASE)
            if ticket_match:
                last_ticket_id = ticket_match.group(1).upper()

        # Check for policy topic mentions
        if not last_policy_topic:
            lower = content.lower()
            if "sev-1" in lower or "sev 1" in lower:
                last_policy_topic = "Sev-1 safety incident"
            elif "sev-2" in lower or "sev 2" in lower:
                last_policy_topic = "Sev-2 incident"
            elif "refund" in lower or "cancellation" in lower:
                last_policy_topic = "cancellation refund policy"
            elif "vip" in lower or "ola select" in lower:
                last_policy_topic = "VIP Ola Select policy"
            elif "repeat complaint" in lower:
                last_policy_topic = "repeat complaint policy"
            elif "business hours" in lower or "holiday" in lower:
                last_policy_topic = "business hours support policy"

        if last_ticket_id and last_policy_topic:
            break

    return last_ticket_id, last_policy_topic


def resolve_pronouns_with_history(query: str, history: list[BaseMessage]) -> tuple[str, bool, str | None]:
    """Resolves pronouns like 'that one', 'it', 'what about its SLA?' using injected conversation history.

    Returns:
        (resolved_query, was_resolved, referent_id)
    """
    clean_q = query.strip()
    lower_q = clean_q.lower()

    # If query already specifies an explicit ticket ID, no pronoun resolution needed
    explicit_match = re.search(r"\b(TKT-\d{4})\b", clean_q, re.IGNORECASE)
    if explicit_match:
        return clean_q, False, explicit_match.group(1).upper()

    last_ticket_id, last_policy_topic = extract_last_entities_from_history(history)

    # Pattern A: SLA inquiry on previous ticket or policy ("what about its SLA?", "what is its SLA?")
    sla_triggers = ["its sla", "about its sla", "what is its sla", "what about its sla"]
    if any(trig in lower_q for trig in sla_triggers):
        if last_ticket_id:
            resolved = f"What is the SLA and escalation risk for ticket {last_ticket_id}?"
            return resolved, True, last_ticket_id
        if last_policy_topic:
            resolved = f"What is the resolution SLA for {last_policy_topic}?"
            return resolved, True, None
        return clean_q, False, None

    # Pattern B: Risk or escalation inquiry ("is that one at risk of escalation?", "is it at risk?")
    risk_triggers = ["that one", "that ticket", "the ticket", "this ticket", "is it at risk", "is it escalated", "at risk of escalation"]
    if any(trig in lower_q for trig in risk_triggers):
        if last_ticket_id:
            resolved = re.sub(
                r"\b(that one|that ticket|the ticket|this ticket)\b",
                last_ticket_id,
                clean_q,
                flags=re.IGNORECASE,
            )
            if resolved == clean_q and "it" in lower_q:
                resolved = re.sub(r"\bit\b", last_ticket_id, clean_q, flags=re.IGNORECASE)
            return resolved, True, last_ticket_id
        return clean_q, False, None

    return clean_q, False, None


class SessionMemoryManager:
    """Object manager encapsulating session memory state and pronoun resolution."""

    def __init__(self):
        self._store = SESSION_STORE

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        return get_session_history(session_id)

    def record_interaction(self, session_id: str, user_query: str, ai_response: str) -> None:
        hist = self.get_history(session_id)
        hist.add_message(HumanMessage(content=user_query))
        hist.add_message(AIMessage(content=ai_response))

    def get_last_ticket_id(self, session_id: str) -> str | None:
        hist = self.get_history(session_id)
        last_tid, _ = extract_last_entities_from_history(hist.messages)
        return last_tid

    def resolve_query(self, session_id: str, query: str) -> tuple[str, bool]:
        hist = self.get_history(session_id)
        resolved_q, was_resolved, _ = resolve_pronouns_with_history(query, hist.messages)
        return resolved_q, was_resolved

    def clear(self, session_id: str | None = None) -> None:
        if session_id:
            self._store.pop(session_id, None)
        else:
            self._store.clear()


# Global singleton manager
session_memory = SessionMemoryManager()


def _raw_runnable_worker(inputs: dict[str, Any]) -> str:
    """Worker called inside RunnableWithMessageHistory."""
    query = inputs.get("input", "")
    history = inputs.get("history", [])
    resolved_query, was_resolved, _ = resolve_pronouns_with_history(query, history)
    return resolved_query


# Core RunnableWithMessageHistory wrapper
crew_runnable_with_history = RunnableWithMessageHistory(
    RunnableLambda(_raw_runnable_worker),
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

__all__ = [
    "InMemoryChatMessageHistory",
    "RunnableWithMessageHistory",
    "SESSION_STORE",
    "get_session_history",
    "resolve_pronouns_with_history",
    "session_memory",
    "crew_runnable_with_history",
]
