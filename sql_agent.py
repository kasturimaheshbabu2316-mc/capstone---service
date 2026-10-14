"""Text-to-SQL Agent with MockProvider & GeminiProvider for Ola Support Operations.

Track: Business Operations / Customer Support (Ola)
Responsibilities:
1. LLMProvider interface with deterministic MockProvider (default) and GeminiProvider (optional).
2. MockProvider maps business intents to safe SQL templates (TKT lookup, SLA breaches,
   severity counts, VIP tickets, avg resolution times).
3. Dynamic system prompt injecting get_database_schema() and case-insensitive LOWER() filters.
4. Self-correction loop: regenerates SQL once if SQL guardrail rejects query.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from guardrails import strip_markdown_fences, validate_sql
from ingest import get_database_schema

logger = logging.getLogger("SQLAgent")


# ==============================================================================
# 1. LLM Provider Interface
# ==============================================================================
class LLMProvider(ABC):
    """Abstract interface for SQL generation providers."""

    @abstractmethod
    def generate_sql(self, question: str, system_prompt: str) -> str:
        """Generates raw SQL given a user question and schema system prompt."""
        pass


class MockProvider(LLMProvider):
    """Deterministic, keyless Mock SQL provider emulating LLM query translation."""

    def generate_sql(self, question: str, system_prompt: str) -> str:
        q = question.strip()
        q_lower = q.lower()

        # 1. Specific Ticket ID Lookup (e.g. TKT-0007, TKT-0042)
        tkt_match = re.search(r"\b(TKT-\d{4})\b", q, re.IGNORECASE)
        if tkt_match:
            tkt_id = tkt_match.group(1).upper()
            return f"SELECT * FROM support_tickets WHERE UPPER(ticket_id) = '{tkt_id}'"

        # 2. Count by Severity
        if "severity" in q_lower or "sev-1" in q_lower or "breakdown by severity" in q_lower:
            return (
                "SELECT severity, COUNT(*) AS ticket_count "
                "FROM support_tickets "
                "GROUP BY severity "
                "ORDER BY ticket_count DESC"
            )

        # 3. SLA Breaches / Overdue Tickets
        if any(w in q_lower for w in ["breach", "overdue", "sla", "delay", "exceeded"]):
            return (
                "SELECT ticket_id, customer_name, category, severity, status, sla_hours "
                "FROM support_tickets "
                "WHERE status = 'Escalated' OR (resolved_at IS NULL AND sla_hours <= 6.0) "
                "ORDER BY sla_hours ASC"
            )

        # 4. Average Resolution Time by Category
        if any(w in q_lower for w in ["average resolution", "resolution time", "avg time", "duration"]):
            return (
                "SELECT category, COUNT(*) AS resolved_count, "
                "ROUND(AVG((strftime('%s', resolved_at) - strftime('%s', created_at)) / 3600.0), 1) AS avg_resolution_hours "
                "FROM support_tickets "
                "WHERE resolved_at IS NOT NULL "
                "GROUP BY category "
                "ORDER BY avg_resolution_hours DESC"
            )

        # 5. VIP / Ola Select Customers
        if any(w in q_lower for w in ["vip", "ola select", "select"]):
            return (
                "SELECT ticket_id, customer_name, city, category, severity, status, refund_amount "
                "FROM support_tickets "
                "WHERE is_vip = 1 "
                "ORDER BY created_at DESC"
            )

        # 6. City / Regional Breakdown
        if any(w in q_lower for w in ["city", "region", "bangalore", "mumbai", "delhi", "pune", "hyderabad"]):
            # Filter by specific city if mentioned
            for city in ["bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai"]:
                if city in q_lower:
                    return f"SELECT * FROM support_tickets WHERE LOWER(city) = '{city}' ORDER BY created_at DESC"
            return (
                "SELECT city, COUNT(*) AS ticket_count, SUM(refund_amount) AS total_refunds "
                "FROM support_tickets "
                "GROUP BY city "
                "ORDER BY ticket_count DESC"
            )

        # 7. Refunds / Compensation
        if any(w in q_lower for w in ["refund", "compensation", "credit", "money"]):
            return (
                "SELECT ticket_id, customer_name, category, refund_amount, status "
                "FROM support_tickets "
                "WHERE refund_amount > 0 "
                "ORDER BY refund_amount DESC"
            )

        # 8. Status Inquiries (e.g. Open / Escalated)
        for st in ["open", "escalated", "in progress", "resolved", "closed"]:
            if st in q_lower:
                return f"SELECT * FROM support_tickets WHERE LOWER(status) = '{st}' ORDER BY created_at DESC"

        # Default fallback: recent tickets
        return "SELECT ticket_id, customer_name, category, severity, status, created_at FROM support_tickets ORDER BY created_at DESC LIMIT 10"


class GeminiProvider(LLMProvider):
    """Real LLM provider using Google Gemini SDK (active only when MOCK_LLM=false)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided for GeminiProvider.")

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def generate_sql(self, question: str, system_prompt: str) -> str:
        from google.genai import types

        resp = self.client.models.generate_content(
            model=self.model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
            ),
        )
        return strip_markdown_fences(resp.text)


# ==============================================================================
# 2. Text-to-SQL Agent with Self-Correction Loop
# ==============================================================================
class SQLAgent:
    """Orchestrates schema context injection, SQL generation, and guardrail self-correction."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        dialect: str = "sqlite",
    ):
        self.dialect = dialect
        mock_mode = os.environ.get("MOCK_LLM", "true").lower() == "true"
        api_key = os.environ.get("GEMINI_API_KEY")

        if provider is not None:
            self.provider = provider
        elif not mock_mode and api_key:
            try:
                self.provider = GeminiProvider(api_key=api_key)
                logger.info("SQLAgent initialized with GeminiProvider.")
            except Exception as e:
                logger.warning("GeminiProvider failed to initialize: %s. Using MockProvider.", e)
                self.provider = MockProvider()
        else:
            self.provider = MockProvider()
            logger.info("SQLAgent initialized with deterministic MockProvider (MOCK_LLM=true).")

    def build_system_prompt(self, schema_text: str) -> str:
        """Constructs the schema-aware system prompt enforcing case-insensitivity and raw SQL."""
        return f"""You are an elite SQL Data Engineer for Ola Customer Support Operations.
Your task is to translate natural language questions into precise, secure, read-only SQL queries for {self.dialect.upper()}.

=== RELATIONAL DATABASE SCHEMA ===
{schema_text}

=== MANDATORY RULES ===
1. Return ONLY the raw SQL statement. NO markdown code blocks (NO ```sql). No explanations.
2. Only SELECT queries are permitted. Never use DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, EXEC, or GRANT.
3. Case-Insensitive Filtering: Always use LOWER(column) = 'value' or UPPER(column) = 'VALUE' for text comparisons.
4. Table Name: The primary table is `support_tickets`.
5. Group By: When calculating aggregates (COUNT, SUM, AVG), include all unaggregated SELECT columns in GROUP BY.
"""

    def translate_to_sql(self, question: str) -> Tuple[bool, str, Optional[str]]:
        """Translates a natural language question into sanitized SQL.

        Applies self-correction: if guardrail rejects the SQL, gives the provider
        one feedback pass to regenerate, then fails gracefully.

        Returns:
            (is_safe, sanitized_sql, error_message)
        """
        schema_text = get_database_schema()
        system_prompt = self.build_system_prompt(schema_text)

        # Attempt 1
        generated_sql = self.provider.generate_sql(question, system_prompt)
        validation = validate_sql(generated_sql)

        if validation.is_safe:
            return True, validation.sanitized_query, None

        logger.warning(
            "SQL Guardrail rejected query on Attempt 1: %s. Initiating self-correction...",
            validation.error_message,
        )

        # Attempt 2: Self-correction feedback loop
        correction_prompt = (
            f"The previous query you generated was rejected by the SQL Security Guardrail:\n"
            f"Query: {generated_sql}\n"
            f"Rejection Reason: {validation.error_message}\n\n"
            f"Please rewrite the query to fix this error. Output ONLY raw read-only SQL."
        )

        corrected_sql = self.provider.generate_sql(correction_prompt, system_prompt)
        retry_validation = validate_sql(corrected_sql)

        if retry_validation.is_safe:
            logger.info("Self-correction successful on Attempt 2.")
            return True, retry_validation.sanitized_query, None

        logger.error("Self-correction failed on Attempt 2: %s", retry_validation.error_message)
        return False, generated_sql, f"SQL Guardrail Violation: {retry_validation.error_message}"

    def generate_sql(self, question: str) -> Dict[str, Any]:
        """Convenience method returning a dictionary with SQL and guardrail metadata."""
        is_safe, sanitized_sql, err = self.translate_to_sql(question)
        return {
            "sql": sanitized_sql,
            "guardrails": {"is_safe": is_safe, "error": err},
            "self_corrected": False,
        }


if __name__ == "__main__":
    print("Testing SQLAgent with MockProvider...")
    agent = SQLAgent()

    test_queries = [
        "What is the status of ticket TKT-0007?",
        "How many tickets do we have per severity?",
        "Show me all SLA breaches",
        "Which city has the highest number of refunds?",
        "List all Ola Select VIP tickets",
    ]

    for q in test_queries:
        safe, sql, err = agent.translate_to_sql(q)
        print(f"\nQuestion: {q}")
        print(f"Safe: {safe} | SQL: {sql}")
