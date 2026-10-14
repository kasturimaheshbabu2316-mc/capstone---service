"""Chatbot Backend: Query Execution & Natural Language Response Synthesis.

Author: Backend Python Developer
SDK: SQLAlchemy, Pandas & Google Gemini (google-genai)
Features:
- Safe, pooled SQL query execution returning Pandas DataFrames
- Structured executive business answer synthesis using Google Gemini
- Autonomous visualization classifier (Bar Chart, Line Chart, Data Table)
- Deterministic heuristic fallback when Gemini API key is absent or offline
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# RAG, Review, and SQL Agent Integrations
from rag.generate import grounded_generate, FALLBACK_REFUSAL
from review.autogen_review import review_support_response
from sql_agent import SQLAgent
from guardrails import validate_sql

# Google GenAI modern SDK import (with graceful fallback)
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ChatbotBackend")


# ==============================================================================
# 1. Pydantic Models for Structured LLM Output
# ==============================================================================
class ChartConfig(BaseModel):
    """Configuration metadata for rendering charts in the frontend."""
    x_axis: Optional[str] = Field(None, description="Column name for the X-axis (dimension/time)")
    y_axis: Optional[str] = Field(None, description="Column name for the Y-axis (metric/value)")
    title: Optional[str] = Field(None, description="Descriptive chart title for the UI")


class BusinessResponse(BaseModel):
    """Structured response schema returned by Google Gemini."""
    summary: str = Field(
        ...,
        description="Clear, professional executive summary answering the user's question with key figures and context.",
    )
    chart_type: str = Field(
        ...,
        description="Recommended visualization: 'bar_chart', 'line_chart', or 'data_table'.",
    )
    chart_config: Optional[ChartConfig] = Field(
        None,
        description="Axis and title specifications if a chart is recommended.",
    )
    insights: List[str] = Field(
        default_factory=list,
        description="2 to 3 bullet-point analytical takeaways derived from the data.",
    )


# ==============================================================================
# 2. Database Execution Engine
# ==============================================================================
_DEFAULT_ENGINE: Optional[Engine] = None


def get_default_engine() -> Engine:
    """Provides a singleton database engine configured from environment."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./data/support.db")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        is_sqlite = db_url.startswith("sqlite")
        if is_sqlite:
            _DEFAULT_ENGINE = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            _DEFAULT_ENGINE = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                pool_recycle=1800,
            )
    return _DEFAULT_ENGINE


def execute_query(
    sql: str,
    engine: Optional[Engine] = None,
) -> pd.DataFrame:
    """Executes the sanitized SQL query safely using SQLAlchemy and returns a Pandas DataFrame.

    Args:
        sql: The validated, sanitized SQL query.
        engine: Optional SQLAlchemy engine. Falls back to default engine if None.

    Returns:
        pd.DataFrame: Query results formatted as a Pandas DataFrame.

    Raises:
        SQLAlchemyError: Propagated if database syntax/connection error occurs.
    """
    db_engine = engine or get_default_engine()
    clean_sql = sql.strip()

    logger.info("Executing SQL Query against database:\n%s", clean_sql)
    start_time = time.perf_counter()

    with db_engine.connect() as conn:
        df = pd.read_sql_query(text(clean_sql), con=conn)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info("Executed successfully in %.2fms. Rows returned: %d", elapsed_ms, len(df))

    # Standardize column names to string type
    df.columns = [str(c) for c in df.columns]
    return df


# ==============================================================================
# 3. Deterministic Heuristic Fallback
# ==============================================================================
def infer_chart_type_heuristics(df: pd.DataFrame) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Fallback classifier: determines visual representation from dtypes & cardinality."""
    if df.empty or len(df.columns) < 2:
        return "data_table", None

    # Detect numeric columns
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return "data_table", None

    metric_col = numeric_cols[0]

    # Detect temporal columns (dates, years, months)
    datetime_cols = [
        c for c in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[c])
        or any(tok in c.lower() for tok in ["date", "month", "year", "day", "week", "quarter"])
    ]

    # Rule 1: Continuous time-series -> Line Chart
    if datetime_cols:
        return "line_chart", {
            "x_axis": datetime_cols[0],
            "y_axis": metric_col,
            "title": f"{metric_col.replace('_', ' ').title()} Trend over Time",
        }

    # Rule 2: Discrete categories (<= 30 distinct values) -> Bar Chart
    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]
    if categorical_cols and len(df) <= 30:
        cat_col = categorical_cols[0]
        return "bar_chart", {
            "x_axis": cat_col,
            "y_axis": metric_col,
            "title": f"{metric_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
        }

    # Rule 3: Complex / wide tables -> Data Table
    return "data_table", None


def generate_rule_based_summary(
    user_question: str,
    df: pd.DataFrame,
) -> Dict[str, Any]:
    """Generates an executive analytical summary when Gemini is offline or unkeyed."""
    chart_type, chart_cfg = infer_chart_type_heuristics(df)

    if df.empty:
        return {
            "summary": "No matching records were found in the database for your inquiry.",
            "chart_type": "data_table",
            "chart_config": None,
            "insights": ["The query returned 0 rows."],
        }

    row_count = len(df)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if numeric_cols:
        num_col = numeric_cols[0]
        total_val = df[num_col].sum()
        avg_val = df[num_col].mean()
        max_val = df[num_col].max()

        summary = (
            f"The query retrieved {row_count} records. The total aggregated {num_col.replace('_', ' ')} "
            f"stands at {total_val:,.2f}, with an average of {avg_val:,.2f} per record."
        )
        insights = [
            f"Maximum recorded {num_col.replace('_', ' ')} is {max_val:,.2f}.",
            f"Total combined {num_col.replace('_', ' ')} across {row_count} items is {total_val:,.2f}.",
        ]
    else:
        summary = f"The query successfully returned {row_count} records matching your question."
        insights = [f"Result set contains {len(df.columns)} dimensions across {row_count} rows."]

    return {
        "summary": summary,
        "chart_type": chart_type,
        "chart_config": chart_cfg,
        "insights": insights,
    }


# ==============================================================================
# 4. Natural Language Response Synthesis via Google Gemini
# ==============================================================================
def generate_business_answer(
    user_question: str,
    query: str,
    df: pd.DataFrame,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """Calls Google Gemini with the original question and SQL result to formulate a business answer.

    Args:
        user_question: The original natural language question from the user.
        query: The SQL query that produced the result.
        df: The query result as a Pandas DataFrame.
        api_key: Optional Google Gemini API key (defaults to GEMINI_API_KEY env var).
        model_name: Gemini model name (default: gemini-2.5-flash).

    Returns:
        dict: Containing 'summary', 'chart_type', 'chart_config', and 'insights'.
    """
    # 1. Handle Empty DataFrame Edge Case
    if df.empty:
        return {
            "summary": "No data found matching your query criteria. Please verify your filters or date range.",
            "chart_type": "data_table",
            "chart_config": None,
            "insights": ["Result set is empty (0 rows returned)."],
            "row_count": 0,
        }

    # 2. Check for Gemini SDK & Credentials
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not HAS_GENAI or not key:
        logger.info(
            "Gemini API key or `google-genai` SDK unavailable. Using deterministic BI synthesizer."
        )
        fallback = generate_rule_based_summary(user_question, df)
        fallback["row_count"] = len(df)
        return fallback

    # 3. Format Data Context (limiting to top 50 rows to protect prompt budget)
    sample_df = df.head(50)
    data_markdown = sample_df.to_markdown(index=False)
    summary_stats = ""
    if len(df.select_dtypes(include=[np.number]).columns) > 0:
        summary_stats = f"\nStatistical Summary:\n{df.describe().to_markdown()}"

    system_instruction = """You are a Senior Business Intelligence Lead and Executive Data Storyteller.
Your role is to translate raw tabular database outputs into clear, impactful, executive-ready business answers.

CRITICAL INSTRUCTIONS:
1. SUMMARY:
   - Provide a concise, highly professional 2-3 sentence executive answer directly addressing the user's question.
   - Include actual figures (formatted as currency $, percentages %, or integers).
   - Compare figures where meaningful (e.g., "up 12%", "accounting for 45% of total sales").

2. CHART SELECTION:
   - "bar_chart": Use when comparing discrete categories, rankings, departments, or products (cardinality <= 30).
   - "line_chart": Use when analyzing continuous time-series, historical trends, dates, or monthly progressions.
   - "data_table": Use for multi-column record lookups, high-cardinality data, or non-numeric/text listings.

3. CHART CONFIGURATION:
   - If recommending bar_chart or line_chart, designate exact x_axis and y_axis column names from the data.
   - Provide a clean, descriptive chart title.

4. INSIGHTS:
   - Extract 2 to 3 bullet-point analytical takeaways (e.g. top performer, lowest performer, distribution skew).
"""

    user_prompt = f"""User Question:
{user_question}

Executed SQL Query:
{query}

Query Results ({len(df)} total rows):
{data_markdown}
{summary_stats}
"""

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,  # Low temperature for factual synthesis
                response_mime_type="application/json",
                response_schema=BusinessResponse,
            ),
        )

        parsed_json = json.loads(response.text)
        parsed_json["row_count"] = len(df)
        return parsed_json

    except Exception as exc:
        logger.error("Gemini answer synthesis failed: %s. Falling back to rule-based summary.", exc)
        fallback = generate_rule_based_summary(user_question, df)
        fallback["row_count"] = len(df)
        return fallback


# ==============================================================================
# 5. End-to-End Orchestrator Helper
# ==============================================================================
def handle_user_query(
    user_question: str,
    sanitized_sql: str,
    engine: Optional[Engine] = None,
) -> Dict[str, Any]:
    """Orchestrates query execution and response synthesis in one cohesive call."""
    df = execute_query(sanitized_sql, engine=engine)
    business_answer = generate_business_answer(user_question, sanitized_sql, df)

    return {
        "question": user_question,
        "sql": sanitized_sql,
        "dataframe": df,
        "summary": business_answer["summary"],
        "chart_type": business_answer["chart_type"],
        "chart_config": business_answer.get("chart_config"),
        "insights": business_answer.get("insights", []),
        "row_count": len(df),
    }


# ==============================================================================
# 6. Step 5 & Step 6 Functions: Synthesis, Routing & Multi-Agent Execution
# ==============================================================================
def synthesize_business_response(
    question: str,
    df: pd.DataFrame,
) -> Dict[str, Any]:
    """Synthesizes business response JSON with summary, chart_type (bar|line|null), x_col, y_col.

    Mock mode builds this by deterministic inspection rules over column datatypes and cardinality.
    """
    mock_mode = os.environ.get("MOCK_LLM", "true").lower() == "true" or not os.environ.get("GEMINI_API_KEY")

    if not mock_mode and HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
        res = generate_business_answer(question, "SELECT ...", df)
        raw_ct = res.get("chart_type", "data_table")
        c_type = None
        if raw_ct in ("bar", "bar_chart"):
            c_type = "bar"
        elif raw_ct in ("line", "line_chart"):
            c_type = "line"

        cfg = res.get("chart_config") or {}
        return {
            "summary": res.get("summary", ""),
            "chart_type": c_type,
            "x_col": cfg.get("x_axis"),
            "y_col": cfg.get("y_axis"),
            "insights": res.get("insights", []),
        }

    # Deterministic Mock Mode
    if df.empty:
        return {
            "summary": "No matching operational records were found in the database for your inquiry.",
            "chart_type": None,
            "x_col": None,
            "y_col": None,
            "insights": ["Result set contains 0 records."],
        }

    cols = list(df.columns)
    row_count = len(df)
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and c != "is_vip"]
    datetime_cols = [
        c for c in cols
        if pd.api.types.is_datetime64_any_dtype(df[c])
        or any(tok in c.lower() for tok in ["date", "month", "created_at", "resolved_at"])
    ]
    categorical_cols = [
        c for c in cols
        if c not in numeric_cols and c not in datetime_cols and c not in ["ticket_id", "customer_name"]
    ]

    chart_type: Optional[str] = None
    x_col: Optional[str] = None
    y_col: Optional[str] = None

    # Visualization determination
    if datetime_cols and numeric_cols:
        chart_type = "line"
        x_col = datetime_cols[0]
        y_col = numeric_cols[0]
    elif categorical_cols and numeric_cols and len(df) <= 30:
        chart_type = "bar"
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
    elif len(cols) == 2 and numeric_cols:
        other_col = [c for c in cols if c != numeric_cols[0]][0]
        chart_type = "bar"
        x_col = other_col
        y_col = numeric_cols[0]

    # Domain summary generation
    insights: List[str] = []

    # Case A: Specific Ticket Lookup
    if "ticket_id" in cols and row_count == 1:
        row = df.iloc[0]
        tid = row.get("ticket_id", "TKT")
        cust = row.get("customer_name", "Customer")
        city = row.get("city", "N/A")
        cat = row.get("category", "General")
        sev = row.get("severity", "N/A")
        status = row.get("status", "N/A")
        sla = row.get("sla_hours", "N/A")
        refund = row.get("refund_amount", 0.0)
        is_vip = bool(row.get("is_vip", False))

        vip_str = " (VIP Ola Select Customer)" if is_vip else ""
        summary = (
            f"Ticket {tid}{vip_str} for {cust} ({city}) is currently '{status}'. "
            f"Category: {cat}, Severity: {sev}, Target SLA: {sla} hours. Refund Amount: ₹{refund:,.2f}."
        )
        insights = [
            f"Operational Status: {status} with severity level {sev}.",
            f"Target SLA window is {sla} hours.",
            f"Customer VIP Select status: {'Yes (Priority Routing)' if is_vip else 'Standard'}.",
        ]

    # Case B: Aggregation across categorical dimensions (severity, category, city, status)
    elif categorical_cols and numeric_cols:
        dim = categorical_cols[0]
        metric = numeric_cols[0]
        total_val = df[metric].sum()
        max_idx = df[metric].idxmax()
        top_dim = df.loc[max_idx, dim]
        top_val = df.loc[max_idx, metric]
        pct = (top_val / total_val * 100) if total_val > 0 else 0.0

        summary = (
            f"Operational breakdown across {row_count} {dim.replace('_', ' ')} segments indicates a total "
            f"{metric.replace('_', ' ')} of {total_val:,.2f}. The primary segment is '{top_dim}' "
            f"accounting for {top_val:,.2f} ({pct:.1f}%)."
        )
        insights = [
            f"Highest volume segment: '{top_dim}' with {top_val:,.2f} {metric}.",
            f"Average {metric} across segments is {(total_val / row_count):,.2f}.",
            f"Total segments monitored: {row_count}.",
        ]

    # Case C: Scalar aggregation
    elif row_count == 1 and numeric_cols:
        parts = [f"{c.replace('_', ' ').title()}: {df.iloc[0][c]:,.2f}" for c in numeric_cols]
        summary = f"Aggregated customer operations metric: {', '.join(parts)}."
        insights = parts

    # Case D: General record listing
    else:
        summary = f"Retrieved {row_count} operational support records matching your query criteria."
        insights = [
            f"Total records: {row_count} across {len(cols)} operational fields.",
            f"Columns: {', '.join(cols[:5])}."
        ]

    return {
        "summary": summary,
        "chart_type": chart_type,
        "x_col": x_col,
        "y_col": y_col,
        "insights": insights,
    }


def classify_question_route(question: str) -> str:
    """Classifies user inquiry into 'policy', 'ticket_lookup', or 'analytics'.

    Args:
        question: Natural language inquiry string.

    Returns:
        One of 'policy', 'ticket_lookup', or 'analytics'.
    """
    clean_q = str(question).strip().lower()

    # Rule 1: Ticket lookup by ticket ID or explicit ticket lookup
    if re.search(r"\b(tkt-\d{4,})\b", clean_q) or "check ticket" in clean_q or "ticket details" in clean_q:
        return "ticket_lookup"

    # Rule 2: Explicit policy questions (SLA rules, cancellation refunds, VIP Select guidelines)
    policy_keywords = [
        "sla rule", "sev-1 sla", "sev-1 rule", "cancellation refund", "cancellation policy",
        "refund policy", "vip ola select", "select customer", "select sla", "compensation",
        "delay policy", "service credit", "complaint policy", "chronic complaint", "operating hour",
        "driver partner center", "safety policy", "safety incident", "baggage", "lost item",
        "guideline", "procedure", "terms", "what is the sla for", "under what condition",
        "when does ola provide", "what happens when a customer", "how does ola handle"
    ]
    if any(pk in clean_q for pk in policy_keywords):
        return "policy"

    # Rule 3: Analytics / Aggregations / Metrics / Trends
    analytics_keywords = [
        "how many", "count", "average", "avg", "total", "sum", "distribution", "breakdown",
        "percentage", "by category", "by city", "by severity", "by status", "sla breach",
        "breaches", "trend", "highest", "lowest", "top", "rate", "metrics", "stats",
        "list all tickets", "show tickets", "all tickets"
    ]
    if any(ak in clean_q for ak in analytics_keywords):
        return "analytics"

    # Fallback heuristic
    if any(q_word in clean_q for q_word in ["policy", "rule", "guideline", "how do", "what is", "can i"]):
        return "policy"

    return "analytics"


def route_and_process_query(
    question: str,
    engine: Optional[Engine] = None,
    session_id: str = "default_session",
) -> Dict[str, Any]:
    """Routes inquiry to RAG or Text-to-SQL, reviews with AutoGen, and synthesizes final answer.

    Flow:
    question -> Router -> [RAG over policy KB] or [Schema -> Text-to-SQL -> SQL Guardrails -> SQLite]
                        -> Autogen Reviewer -> Business Answer

    Returns:
        Dict containing:
        - answer: str (final reviewed customer-facing answer)
        - route: str ('policy' | 'ticket_lookup' | 'analytics')
        - sql: Optional[str]
        - dataframe: Optional[pd.DataFrame]
        - chart_type: Optional[str] ('bar' | 'line' | None)
        - x_col: Optional[str]
        - y_col: Optional[str]
        - retrieved_sources: List[str]
        - retrieved_snippet: Optional[str]
        - review_status: Dict[str, Any]
        - guardrail_flags: Dict[str, Any]
    """
    route = classify_question_route(question)
    guardrail_flags: Dict[str, Any] = {"route": route}

    if route == "policy":
        # 1. RAG over Policy KB
        rag_res = grounded_generate(question, collection_name="ola_sentence")
        draft_answer = rag_res["answer"]
        sources = rag_res.get("sources", [])
        grounded = rag_res.get("grounded", True)
        confidence = float(rag_res.get("top_similarity", 1.0))
        chunks = rag_res.get("retrieved_chunks", [])
        snippet = chunks[0]["text"] if chunks else draft_answer

        # 2. Autogen Reviewer Stage
        verdict = review_support_response(
            query=question,
            draft_answer=draft_answer,
            sources=sources,
            grounded=grounded,
            confidence=confidence,
        )

        guardrail_flags.update({
            "policy_grounded": grounded,
            "confidence": confidence,
            "redactions_made": verdict.redactions_made,
        })

        return {
            "answer": verdict.final_answer,
            "route": "policy",
            "sql": None,
            "dataframe": pd.DataFrame(),
            "chart_type": None,
            "x_col": None,
            "y_col": None,
            "retrieved_sources": sources,
            "retrieved_snippet": snippet,
            "review_status": {"approved": verdict.approved, "notes": verdict.review_notes},
            "guardrail_flags": guardrail_flags,
        }

    else:
        # Route is ticket_lookup or analytics -> Text-to-SQL
        sql_agent = SQLAgent()
        sql_result = sql_agent.generate_sql(question)
        sql = sql_result["sql"]
        guardrail_flags["sql_safe"] = sql_result["guardrails"].get("is_safe", True)
        guardrail_flags["self_corrected"] = sql_result.get("self_corrected", False)

        try:
            df = execute_query(sql, engine=engine)
        except Exception as e:
            logger.error("Database execution error for SQL '%s': %s", sql, e)
            return {
                "answer": f"Unable to execute SQL query: {str(e)}",
                "route": route,
                "sql": sql,
                "dataframe": pd.DataFrame(),
                "chart_type": None,
                "x_col": None,
                "y_col": None,
                "retrieved_sources": ["support_tickets (SQL Database)"],
                "retrieved_snippet": None,
                "review_status": {"approved": False, "notes": f"SQL Execution Failed: {str(e)}"},
                "guardrail_flags": guardrail_flags,
            }

        # 2. Synthesize Business Response
        biz_resp = synthesize_business_response(question, df)
        draft_summary = biz_resp["summary"]

        # 3. Autogen Reviewer Stage
        verdict = review_support_response(
            query=question,
            draft_answer=draft_summary,
            sources=["support_tickets (SQL Database)"],
            grounded=True,
            confidence=1.0,
        )

        guardrail_flags["redactions_made"] = verdict.redactions_made
        guardrail_flags["row_count"] = len(df)

        return {
            "answer": verdict.final_answer,
            "route": route,
            "sql": sql,
            "dataframe": df,
            "chart_type": biz_resp["chart_type"],
            "x_col": biz_resp["x_col"],
            "y_col": biz_resp["y_col"],
            "retrieved_sources": ["support_tickets (SQL Database)"],
            "retrieved_snippet": None,
            "review_status": {"approved": verdict.approved, "notes": verdict.review_notes},
            "guardrail_flags": guardrail_flags,
        }

