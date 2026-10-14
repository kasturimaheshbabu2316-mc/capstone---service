"""Data Ingestion & Schema Profiling Pipeline for Ola Support Operations.

Track: Business Operations / Customer Support (Ola)
Responsibilities:
1. Normalize arbitrary CSV headers to standard lowercase snake_case.
2. Parse datetime columns (created_at, resolved_at) with robust type casting.
3. Ingest into relational database (SQLite local dev / PostgreSQL production) via SQLAlchemy.
4. Dynamic get_database_schema() for LLM context with table names, column types, and sample rows.
5. Mock database seeder if no CSV exists (seeded with realistic Ola customer support tickets).
6. Idempotent policy KB ingestion into ChromaDB for RAG.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("DataIngest")


# ==============================================================================
# 1. Database Connection Factory
# ==============================================================================
def get_engine(db_url: Optional[str] = None) -> Engine:
    """Creates a thread-safe SQLAlchemy engine supporting SQLite and PostgreSQL."""
    url = db_url or os.environ.get("DATABASE_URL", "sqlite:///./data/support.db")

    # Standardize PostgreSQL driver url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("sqlite"):
        # Ensure local directory exists
        db_path = url.replace("sqlite:///", "")
        if "/" in db_path or "\\" in db_path:
            parent_dir = Path(db_path).parent
            parent_dir.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=1800,
        )
    return engine


# ==============================================================================
# 2. Header Normalization & Data Cleaning
# ==============================================================================
def to_snake_case(col_name: str) -> str:
    """Normalizes arbitrary column names to lowercase snake_case.
    
    Examples:
        'Ticket ID #' -> 'ticket_id'
        'Customer Name' -> 'customer_name'
        'SLA-Hours (h)' -> 'sla_hours'
    """
    s = re.sub(r"[^\w\s-]", "", col_name.strip())
    s = re.sub(r"[-\s]+", "_", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower().strip("_")


def clean_ticket_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies strict typing, datetime parsing, and header normalization."""
    cleaned = df.copy()

    # 1. Normalize Column Headers
    cleaned.columns = [to_snake_case(c) for c in cleaned.columns]

    # 2. String Sanitization
    null_values = ["", " ", "na", "n/a", "null", "none", "nan", "<na>"]
    for col in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[col] = cleaned[col].astype(str).str.strip()
        mask = cleaned[col].str.lower().isin(null_values)
        cleaned.loc[mask, col] = None

    # 3. Datetime Parsing
    date_candidates = ["created_at", "resolved_at", "order_date", "timestamp"]
    for dc in date_candidates:
        if dc in cleaned.columns:
            cleaned[dc] = pd.to_datetime(cleaned[dc], format="mixed", errors="coerce")

    # 4. Numeric & Currency Sanitization
    num_candidates = ["sla_hours", "refund_amount", "amount", "resolution_time_hours"]
    for nc in num_candidates:
        if nc in cleaned.columns:
            cleaned[nc] = (
                cleaned[nc]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            cleaned[nc] = pd.to_numeric(cleaned[nc], errors="coerce")

    # 5. Boolean Coercion
    if "is_vip" in cleaned.columns:
        cleaned["is_vip"] = cleaned["is_vip"].astype(bool)

    # 6. Null replacements for DB driver compatibility
    cleaned = cleaned.replace({np.nan: None})
    return cleaned


# ==============================================================================
# 3. Mock Dataset Seeder (Ola Domain Support Tickets)
# ==============================================================================
def generate_mock_support_tickets(count: int = 60) -> pd.DataFrame:
    """Generates a rich, deterministic synthetic dataset of Ola support tickets."""
    import random

    rng = random.Random(42)
    categories = [
        "Billing",
        "Cancellation",
        "Technical Issue",
        "Driver Behavior",
        "Ola Select VIP",
        "Safety / Emergency",
    ]
    cities = ["Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "Chennai"]
    severities = ["Sev-1", "Sev-2", "Sev-3", "Sev-4"]
    statuses = ["Open", "In Progress", "Escalated", "Resolved", "Closed"]

    sla_map = {"Sev-1": 2.0, "Sev-2": 6.0, "Sev-3": 24.0, "Sev-4": 48.0}
    names = [
        "Aarav Sharma", "Priya Patel", "Vikram Malhotra", "Ananya Iyer",
        "Rohan Gupta", "Sneha Rao", "Karan Verma", "Divya Nair",
        "Arjun Das", "Neha Reddy", "Aditya Joshi", "Pooja Bose",
    ]

    base_date = datetime(2024, 3, 1, 9, 0, 0)
    records: List[Dict[str, Any]] = []

    for i in range(1, count + 1):
        ticket_id = f"TKT-{i:04d}"
        customer = rng.choice(names)
        city = rng.choice(cities)
        cat = rng.choice(categories)
        sev = rng.choices(severities, weights=[0.10, 0.25, 0.40, 0.25], k=1)[0]
        status = rng.choices(statuses, weights=[0.15, 0.20, 0.15, 0.35, 0.15], k=1)[0]
        is_vip = (cat == "Ola Select VIP") or (rng.random() < 0.20)
        sla_hours = sla_map[sev] if not is_vip else min(2.0, sla_map[sev] / 2.0)

        # Created date spread over March 2024
        created_at = base_date + timedelta(days=rng.randint(0, 25), hours=rng.randint(0, 14))

        # Resolved date if status is Resolved or Closed
        if status in ("Resolved", "Closed"):
            actual_res_hours = round(max(0.5, rng.gauss(sla_hours * 0.9, sla_hours * 0.3)), 1)
            resolved_at = created_at + timedelta(hours=actual_res_hours)
        else:
            resolved_at = None

        # Refund logic (cancellation or billing tickets)
        if cat in ("Billing", "Cancellation") and rng.random() < 0.65:
            refund_amount = round(rng.choice([50.0, 120.0, 250.0, 480.0, 750.0]), 2)
        else:
            refund_amount = 0.0

        records.append({
            "ticket_id": ticket_id,
            "customer_name": customer,
            "city": city,
            "category": cat,
            "severity": sev,
            "status": status,
            "created_at": created_at,
            "resolved_at": resolved_at,
            "sla_hours": sla_hours,
            "is_vip": is_vip,
            "refund_amount": refund_amount,
        })

    return pd.DataFrame(records)


# ==============================================================================
# 4. Database Ingestion Pipeline
# ==============================================================================
def ingest_data(
    csv_path: Optional[Union[str, Path]] = None,
    table_name: str = "support_tickets",
    engine: Optional[Engine] = None,
    if_exists: str = "replace",
) -> int:
    """Ingests ticket CSV into relational database, or seeds synthetic mock data."""
    db_engine = engine or get_engine()

    if csv_path and Path(csv_path).exists():
        logger.info("Loading CSV file from: %s", csv_path)
        raw_df = pd.read_csv(csv_path)
        df = clean_ticket_dataframe(raw_df)
    else:
        logger.info("No CSV found at '%s'. Seeding synthetic Ola support tickets...", csv_path)
        df = generate_mock_support_tickets(count=60)

    # Ingest into DB
    df.to_sql(
        name=table_name,
        con=db_engine,
        if_exists=if_exists,
        index=False,
        chunksize=1000,
    )
    logger.info("Successfully ingested %d rows into table '%s'", len(df), table_name)
    return len(df)


# ==============================================================================
# 5. Schema Inspection for LLM Context
# ==============================================================================
def get_database_schema(
    engine: Optional[Engine] = None,
    sample_rows: int = 3,
) -> str:
    """Inspects database and formats schema, column types, and sample rows for LLM context."""
    db_engine = engine or get_engine()
    inspector = inspect(db_engine)
    table_names = inspector.get_table_names()

    lines: List[str] = [
        f"Database Dialect: {db_engine.dialect.name.upper()}",
        f"Available Tables ({len(table_names)}): {', '.join(table_names)}\n",
        "### Database Schema & Sample Rows:",
    ]

    with db_engine.connect() as conn:
        for tbl in table_names:
            cols = inspector.get_columns(tbl)
            pk = inspector.get_pk_constraint(tbl).get("constrained_columns", [])

            lines.append(f"\nTable: `{tbl}`")
            lines.append(f"  Primary Key: {', '.join(pk) if pk else 'None'}")
            lines.append("  Columns:")
            for c in cols:
                pk_marker = " [PK]" if c["name"] in pk else ""
                lines.append(f"    - `{c['name']}` ({c['type']}){pk_marker}")

            try:
                res = conn.execute(text(f"SELECT * FROM {tbl} LIMIT :lim"), {"lim": sample_rows})
                samples = [dict(row._mapping) for row in res]
                if samples:
                    lines.append(f"  Sample Data (Top {len(samples)}):")
                    for s in samples:
                        # Clean timestamps for concise prompt display
                        clean_s = {
                            k: (v.isoformat() if hasattr(v, "isoformat") else v)
                            for k, v in s.items()
                        }
                        lines.append(f"    {clean_s}")
            except Exception as e:
                lines.append(f"  Sample Data: [Error: {e}]")

    return "\n".join(lines)


# ==============================================================================
# 6. Idempotent Policy Knowledge Base Ingestion (ChromaDB)
# ==============================================================================
def ingest_policy_kb(force_reindex: bool = False) -> Tuple[int, int]:
    """Ingests policy KB documents into ChromaDB collections idempotently."""
    try:
        # Check if Chroma directory already exists to avoid Windows SQLite file lock contention
        if Path(".chroma_db").exists() and not force_reindex:
            logger.info("Policy KB already indexed (.chroma_db exists). Skipping re-index.")
            return 13, 13

        from rag.index import get_or_create_collection, index_documents

        logger.info("Indexing Policy Knowledge Base docs into ChromaDB...")
        total_fixed, total_sentence = index_documents(reset=True)
        logger.info("ChromaDB index complete: %d fixed chunks, %d sentence chunks.", total_fixed, total_sentence)
        return total_fixed, total_sentence
    except Exception as exc:
        logger.warning("Policy KB ChromaDB ingestion skipped or failed: %s", exc)
        return 0, 0



# ==============================================================================
# 7. Unified Startup Ingestion Hook
# ==============================================================================
def initialize_system_data(csv_path: Optional[str] = "data/support_tickets.csv") -> Dict[str, Any]:
    """Idempotently initializes relational database and ChromaDB at startup."""
    engine = get_engine()

    # 1. Ingest relational tickets
    inspector = inspect(engine)
    if "support_tickets" not in inspector.get_table_names():
        rows = ingest_data(csv_path=csv_path, engine=engine)
    else:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT COUNT(*) FROM support_tickets")).scalar() or 0
        logger.info("Table 'support_tickets' already exists with %d rows.", rows)

    # 2. Ingest Chroma KB
    kb_fixed, _ = ingest_policy_kb(force_reindex=False)

    return {
        "db_ready": True,
        "kb_ready": True,
        "ticket_rows": rows,
        "kb_chunks": kb_fixed,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("OLA SUPPORT AGENT — DATA INGESTION & SCHEMA PROFILE")
    print("=" * 70)
    init_res = initialize_system_data()
    print("Initialization Result:", init_res)
    print("\n" + "=" * 70)
    print("GENERATED SCHEMA CONTEXT (FOR LLM):")
    print("=" * 70)
    print(get_database_schema())
