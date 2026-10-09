"""Conversational Session Memory & Entity Resolution Module.

Track: Business Operations / Customer Support (Ola)
Implements InMemoryChatMessageHistory with ticket entity tracking and pronoun resolution.
"""

import re
import warnings
from typing import Any
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

# Suppress LangChain deprecation warning for in-memory chat history
warnings.filterwarnings("ignore", message=".*InMemoryChatMessageHistory.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)



class SessionMemoryManager:
    """Manages multi-turn conversation sessions and pronoun resolution."""

    def __init__(self):
        self._sessions: dict[str, InMemoryChatMessageHistory] = {}
        self._session_state: dict[str, dict[str, Any]] = {}

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """Retrieves or creates an in-memory message history for the given session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = InMemoryChatMessageHistory()
            self._session_state[session_id] = {"last_ticket_id": None}
        return self._sessions[session_id]

    def record_interaction(self, session_id: str, user_query: str, ai_response: str) -> None:
        """Records a user query and assistant response, updating tracked entity state."""
        history = self.get_history(session_id)
        history.add_message(HumanMessage(content=user_query))
        history.add_message(AIMessage(content=ai_response))

        # Track any ticket ID mentioned in user or assistant messages
        found = re.search(r"\b(TKT-\d{4})\b", user_query + " " + ai_response, re.IGNORECASE)
        if found:
            self._session_state[session_id]["last_ticket_id"] = found.group(1).upper()

    def get_last_ticket_id(self, session_id: str) -> str | None:
        """Returns the most recent ticket ID discussed in this session."""
        if session_id in self._session_state:
            return self._session_state[session_id].get("last_ticket_id")
        return None

    def resolve_query(self, session_id: str, query: str) -> tuple[str, bool]:
        """Resolves pronouns like 'that one', 'it', 'the ticket' using session state.

        Returns:
            (resolved_query, was_resolved)
        """
        last_tid = self.get_last_ticket_id(session_id)
        lower_q = query.lower()

        # If already contains explicit ticket ID, update state and return as-is
        explicit_tid = re.search(r"\b(TKT-\d{4})\b", query, re.IGNORECASE)
        if explicit_tid:
            if session_id in self._session_state:
                self._session_state[session_id]["last_ticket_id"] = explicit_tid.group(1).upper()
            return query, False

        # Check for ambiguous pronoun references
        pronoun_triggers = ["that one", "that ticket", "the ticket", "this ticket", "it at risk", "is it escalated"]
        has_pronoun = any(trig in lower_q for trig in pronoun_triggers)

        if has_pronoun:
            if last_tid:
                # Replace pronoun with concrete ticket ID
                resolved = re.sub(r"\b(that one|that ticket|the ticket|this ticket)\b", last_tid, query, flags=re.IGNORECASE)
                if resolved == query and "it" in lower_q:
                    resolved = query.replace("it", last_tid).replace("It", last_tid)
                return resolved, True
            else:
                # No context exists in this session
                return query, False

        return query, False

    def clear(self, session_id: str | None = None) -> None:
        """Clears memory for a specific session or all sessions."""
        if session_id:
            self._sessions.pop(session_id, None)
            self._session_state.pop(session_id, None)
        else:
            self._sessions.clear()
            self._session_state.clear()


# Global singleton memory manager
session_memory = SessionMemoryManager()
