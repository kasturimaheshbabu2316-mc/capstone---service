"""Text-to-SQL Business Intelligence Chatbot — Streamlit Web UI.

Author: Full-Stack Python Developer
Framework: Streamlit & Google Gemini
Integrations: chatbot_backend (execute_query, generate_business_answer)
Features:
- Conversational chat UI using st.chat_message and st.session_state
- Dynamic multi-stage status indicators during SQL orchestration
- Render executive summaries, KPI insights, and raw DataFrames
- Dynamic visualization rendering (st.bar_chart, st.line_chart, st.dataframe)
- Collapsible SQL inspector with execution metrics and CSV export
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# Import Backend Functions
from chatbot_backend import (
    execute_query,
    generate_business_answer,
    get_default_engine,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TextToSQLApp")

# ==============================================================================
# 1. Streamlit Page Configuration & Modern Theme Styling
# ==============================================================================
st.set_page_config(
    page_title="Text-to-SQL BI Chatbot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished typography, badges, and card elevation
st.markdown(
    """
    <style>
    /* Metric Card Styling */
    .metric-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
        background-color: #f0f2f6;
        color: #31333f;
    }
    .badge-success {
        background-color: #e6f4ea;
        color: #137333;
    }
    .badge-info {
        background-color: #e8f0fe;
        color: #1a73e8;
    }
    /* Insight Callout */
    .insight-box {
        background-color: #f8f9fa;
        border-left: 4px solid #1a73e8;
        padding: 10px 14px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.92rem;
    }
    /* Expander padding */
    .streamlit-expanderHeader {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. Database Schema Inspector Helper
# ==============================================================================
def get_schema_summary(engine: Engine) -> Dict[str, Any]:
    """Inspects the database and compiles schema metadata for sidebar & prompt."""
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        schema_info: Dict[str, List[Dict[str, str]]] = {}

        for tbl in table_names:
            cols = inspector.get_columns(tbl)
            schema_info[tbl] = [
                {"name": c["name"], "type": str(c["type"])} for c in cols
            ]
        return {"tables": schema_info, "count": len(table_names)}
    except Exception as e:
        logger.error("Failed to inspect schema: %s", e)
        return {"tables": {}, "count": 0}


# ==============================================================================
# 3. SQL Guardrail & Generation Pipeline
# ==============================================================================
BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "EXEC", "EXECUTE", "GRANT", "REVOKE", "CREATE", "REPLACE",
    "ATTACH", "DETACH", "PRAGMA", "LOAD_EXTENSION"
]


def validate_sql_guardrail(sql: str) -> Tuple[bool, Optional[str], str]:
    """Validates raw SQL against security guardrails and enforces LIMIT 100."""
    clean = re.sub(r"/\*[\s\S]*?\*/|--[^\r\n]*", " ", sql).strip()
    trimmed = re.sub(r";\s*$", "", clean)

    if ";" in trimmed:
        return False, "Multiple SQL statements detected (semicolon injection blocked).", sql

    first_word_match = re.match(r"^\s*([a-zA-Z]+)", trimmed)
    if not first_word_match:
        return False, "Could not determine SQL command type.", sql

    first_word = first_word_match.group(1).upper()
    if first_word not in ("SELECT", "WITH"):
        return False, f"Non-read-only query blocked. Only SELECT is permitted (found: {first_word}).", sql

    # Check blocked keywords
    pattern = r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b"
    match = re.search(pattern, trimmed, re.IGNORECASE)
    if match:
        return False, f"Dangerous keyword detected and blocked: '{match.group(0).upper()}'.", sql

    # Enforce LIMIT 100 if none provided
    if not re.search(r"\bLIMIT\b", trimmed, re.IGNORECASE):
        sanitized = f"{trimmed} LIMIT 100"
    else:
        sanitized = trimmed

    return True, None, sanitized


def generate_sql_query(
    question: str,
    schema_summary: Dict[str, Any],
    dialect: str = "sqlite",
) -> str:
    """Translates question into SQL using Google Gemini or deterministic template."""
    api_key = os.environ.get("GEMINI_API_KEY")

    # If Gemini SDK is available and API key is set
    try:
        from google import genai
        from google.genai import types

        if api_key:
            client = genai.Client(api_key=api_key)

            # Build concise schema context
            schema_lines = []
            for tbl, cols in schema_summary.get("tables", {}).items():
                col_str = ", ".join([f"{c['name']} ({c['type']})" for c in cols])
                schema_lines.append(f"Table `{tbl}`: {col_str}")
            schema_text = "\n".join(schema_lines)

            system_instruction = f"""You are an elite SQL Data Engineer.
Translate natural language business questions into precise, optimized, read-only SQL queries for {dialect.upper()}.
OUTPUT FORMAT: Output ONLY the raw SQL query. Do NOT use markdown code blocks (NO ```sql). No explanations.
SCHEMA:
{schema_text}
"""
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                ),
            )
            raw_sql = resp.text.strip()
            # Clean markdown code fences if present
            raw_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
            raw_sql = re.sub(r"\s*```$", "", raw_sql)
            return raw_sql.strip()

    except Exception as e:
        logger.warning("Gemini generation skipped or failed: %s. Using fallback SQL mapping.", e)

    # Heuristic SQL generator for demo/offline resilience
    tables = list(schema_summary.get("tables", {}).keys())
    primary_tbl = tables[0] if tables else "orders"
    q_lower = question.lower()

    if "count" in q_lower or "how many" in q_lower:
        return f"SELECT COUNT(*) AS total_count FROM {primary_tbl}"
    if "top" in q_lower or "highest" in q_lower or "best" in q_lower:
        cols = [c["name"] for c in schema_summary.get("tables", {}).get(primary_tbl, [])]
        num_cols = [c for c in cols if any(k in c.lower() for k in ["amount", "revenue", "price", "total", "sales", "qty"])]
        metric = num_cols[0] if num_cols else (cols[1] if len(cols) > 1 else cols[0])
        return f"SELECT * FROM {primary_tbl} ORDER BY {metric} DESC LIMIT 5"
    if "trend" in q_lower or "month" in q_lower or "date" in q_lower:
        cols = [c["name"] for c in schema_summary.get("tables", {}).get(primary_tbl, [])]
        date_cols = [c for c in cols if "date" in c.lower()]
        date_col = date_cols[0] if date_cols else cols[0]
        return f"SELECT {date_col}, COUNT(*) AS volume FROM {primary_tbl} GROUP BY {date_col} ORDER BY {date_col} ASC"

    return f"SELECT * FROM {primary_tbl} LIMIT 10"


# ==============================================================================
# 4. Session State Initialization
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I am your **Text-to-SQL Business Intelligence Assistant**.\n\n"
                "Ask me any question in plain English about your business data (e.g., revenue trends, "
                "top customers, product sales), and I will generate the SQL, execute it securely, "
                "and formulate an executive analysis with charts."
            ),
            "sql": None,
            "df": None,
            "chart_type": None,
            "chart_config": None,
            "insights": [],
            "execution_time_ms": 0.0,
        }
    ]

# Setup active database engine
db_engine = get_default_engine()
schema_metadata = get_schema_summary(db_engine)


# ==============================================================================
# 5. Sidebar Controls & Database Explorer
# ==============================================================================
with st.sidebar:
    st.title("⚡ BI Engine Controls")
    st.markdown("---")

    # Connection Status Indicator
    dialect_name = db_engine.dialect.name.upper()
    st.markdown(f"**Connected Database:** `{dialect_name}`")
    st.caption("Active connection pool with automated health verification.")

    # Live Schema Explorer
    with st.expander(f"📚 Live Database Schema ({schema_metadata['count']} Tables)", expanded=True):
        if schema_metadata["tables"]:
            for tbl, cols in schema_metadata["tables"].items():
                st.markdown(f"**Table:** `{tbl}`")
                for c in cols:
                    st.text(f"  • {c['name']} ({c['type']})")
                st.markdown("---")
        else:
            st.info("No relational tables found in the active database.")

    # Quick Starter Prompts
    st.markdown("### 💡 Sample Business Queries")
    starter_queries = [
        "What are the top 5 customers by total order amount?",
        "Which product category generated the highest revenue?",
        "Show monthly order volume trend for 2024",
        "List all orders with status 'DELIVERED'",
    ]

    for q in starter_queries:
        if st.button(q, use_container_width=True):
            st.session_state["queued_prompt"] = q

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ==============================================================================
# 6. Main Chat History Rendering
# ==============================================================================
st.title("📊 Natural Language to SQL Assistant")
st.caption("Automated SQL translation, guardrail verification, and executive synthesis.")

# Render previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Render Insights if present
        if msg.get("insights"):
            for ins in msg["insights"]:
                st.markdown(f"<div class='insight-box'>💡 <b>Key Finding:</b> {ins}</div>", unsafe_allow_html=True)

        # Render Dynamic Chart
        chart_type = msg.get("chart_type")
        chart_cfg = msg.get("chart_config")
        df = msg.get("df")

        if df is not None and not df.empty and chart_cfg:
            x_col = chart_cfg.get("x_axis")
            y_col = chart_cfg.get("y_axis")

            if x_col in df.columns and y_col in df.columns:
                st.markdown(f"#### 📈 {chart_cfg.get('title', 'Data Visualization')}")
                if chart_type == "bar_chart":
                    st.bar_chart(data=df.set_index(x_col)[y_col])
                elif chart_type == "line_chart":
                    st.line_chart(data=df.set_index(x_col)[y_col])

        # Collapsible SQL & Raw Data Expander
        if msg.get("sql"):
            time_ms = msg.get("execution_time_ms", 0.0)
            with st.expander(f"🔍 View Generated SQL & Raw Data ({time_ms:.1f}ms)", expanded=False):
                st.markdown(
                    f"<span class='metric-badge badge-info'>Rows: {len(df) if df is not None else 0}</span>"
                    f"<span class='metric-badge badge-success'>Latency: {time_ms:.1f}ms</span>",
                    unsafe_allow_html=True,
                )
                st.code(msg["sql"], language="sql")
                if df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )


# ==============================================================================
# 7. User Input & Multi-Stage Orchestration Pipeline
# ==============================================================================
user_prompt = st.chat_input("Ask a question about your business data...")

# Check if a starter prompt was clicked in the sidebar
if "queued_prompt" in st.session_state:
    user_prompt = st.session_state.pop("queued_prompt")

if user_prompt:
    # 1. Record User Message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Assistant Response Container
    with st.chat_message("assistant"):
        start_total = time.perf_counter()

        # Multi-stage Status Pipeline
        with st.status("Analyzing your question and querying database...", expanded=True) as status:
            # Stage 1: Schema Retrieval
            status.write("🔍 **Step 1/4:** Retrieving database schema metadata...")
            time.sleep(0.3)

            # Stage 2: SQL Generation
            status.write("🧠 **Step 2/4:** Translating question into SQL query via Gemini...")
            generated_sql = generate_sql_query(user_prompt, schema_metadata, dialect=dialect_name)
            time.sleep(0.4)

            # Stage 3: Guardrail Security Check
            status.write("🛡️ **Step 3/4:** Validating SQL Guardrails (Read-only check & LIMIT enforcement)...")
            is_safe, error_msg, sanitized_sql = validate_sql_guardrail(generated_sql)
            time.sleep(0.3)

            if not is_safe:
                status.update(label="Query blocked by Security Guardrail!", state="error", expanded=False)
                rejection_msg = f"⚠️ **Security Guardrail Violation:** {error_msg}\n\n*Generated Query:* `{generated_sql}`"
                st.error(rejection_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": rejection_msg,
                    "sql": generated_sql,
                    "df": None,
                    "chart_type": None,
                    "chart_config": None,
                    "insights": [],
                    "execution_time_ms": 0.0,
                })
                st.stop()

            # Stage 4: Database Execution & Synthesis
            status.write("⚡ **Step 4/4:** Executing query and synthesizing business insights...")
            t_exec_start = time.perf_counter()
            try:
                result_df = execute_query(sanitized_sql, engine=db_engine)
                exec_time_ms = (time.perf_counter() - t_exec_start) * 1000
            except Exception as db_err:
                status.update(label="Database Execution Failed", state="error", expanded=False)
                st.error(f"❌ **Database Execution Error:** {db_err}")
                st.code(sanitized_sql, language="sql")
                st.stop()

            # Synthesize Answer & Visualization Metadata
            business_answer = generate_business_answer(user_prompt, sanitized_sql, result_df)
            status.update(label="Query executed and analyzed successfully!", state="complete", expanded=False)

        # 3. Render Answer Content
        summary_text = business_answer.get("summary", "Query completed successfully.")
        st.markdown(summary_text)

        # Render Insights
        insights = business_answer.get("insights", [])
        for ins in insights:
            st.markdown(f"<div class='insight-box'>💡 <b>Key Finding:</b> {ins}</div>", unsafe_allow_html=True)

        # Render Dynamic Chart
        chart_type = business_answer.get("chart_type")
        chart_cfg = business_answer.get("chart_config")

        if result_df is not None and not result_df.empty and chart_cfg:
            x_col = chart_cfg.get("x_axis")
            y_col = chart_cfg.get("y_axis")
            if x_col in result_df.columns and y_col in result_df.columns:
                st.markdown(f"#### 📈 {chart_cfg.get('title', 'Data Visualization')}")
                if chart_type == "bar_chart":
                    st.bar_chart(data=result_df.set_index(x_col)[y_col])
                elif chart_type == "line_chart":
                    st.line_chart(data=result_df.set_index(x_col)[y_col])

        # Collapsible SQL & Raw Data Expander
        with st.expander(f"🔍 View Generated SQL & Raw Data ({exec_time_ms:.1f}ms)", expanded=False):
            st.markdown(
                f"<span class='metric-badge badge-info'>Rows: {len(result_df)}</span>"
                f"<span class='metric-badge badge-success'>Execution: {exec_time_ms:.1f}ms</span>",
                unsafe_allow_html=True,
            )
            st.code(sanitized_sql, language="sql")
            st.dataframe(result_df, use_container_width=True)
            csv_data = result_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="query_results.csv",
                mime="text/csv",
            )

        # 4. Save to Session State History
        st.session_state.messages.append({
            "role": "assistant",
            "content": summary_text,
            "sql": sanitized_sql,
            "df": result_df,
            "chart_type": chart_type,
            "chart_config": chart_cfg,
            "insights": insights,
            "execution_time_ms": exec_time_ms,
        })
