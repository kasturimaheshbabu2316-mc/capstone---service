"""Knowledge Base loader and validation utility for Ola Support policies.

Loads all markdown policy documents from the kb/ directory, parses metadata,
extracts title headers, and provides sentence-counting utilities.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Any

# Standard 12 required Ola domain support policy topics
REQUIRED_TOPIC_IDS: list[str] = [
    "ticket_priority_rules",
    "sla_by_severity",
    "escalation_matrix",
    "refund_compensation_policy",
    "communication_channels",
    "business_hours_support",
    "repeat_complaint_handling",
    "service_credit_policy",
    "feedback_collection",
    "vip_customer_policy",
    "outage_communication",
    "data_retention_policy",
]


def count_sentences(text: str) -> int:
    """Counts sentences in a text block, ignoring markdown headings.

    Sentences are recognized by terminal punctuation (. ? !) followed by
    whitespace or end of string.

    Args:
        text: Raw text string (may include markdown headings).

    Returns:
        Integer count of sentences.
    """
    if not text or not text.strip():
        return 0

    # Filter out markdown heading lines
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    body = " ".join(lines).strip()
    if not body:
        return 0

    # Split on sentence terminals followed by space or boundary
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    return len(sentences)


def extract_title_and_text(content: str, default_title: str = "") -> tuple[str, str]:
    """Extracts document title (from leading # heading) and body text.

    Args:
        content: Raw markdown document content.
        default_title: Fallback title if no H1 heading is found.

    Returns:
        Tuple of (title, body_text).
    """
    lines = content.splitlines()
    title = default_title
    body_lines: list[str] = []

    title_found = False
    for line in lines:
        stripped = line.strip()
        if not title_found and stripped.startswith("# "):
            title = stripped[2:].strip()
            title_found = True
        else:
            body_lines.append(line)

    body_text = "\n".join(body_lines).strip()
    return title, body_text


def load_kb(kb_dir: str | Path = "kb") -> list[dict[str, str]]:
    """Loads all markdown policy documents from the knowledge base directory.

    Args:
        kb_dir: Directory path containing the .md policy documents.

    Returns:
        List of dicts formatted as:
        [
            {
                "doc_id": "sla_by_severity",
                "title": "Service Level Agreement (SLA) Policy",
                "text": "Ola enforces strict resolution Service Level Agreements..."
            },
            ...
        ]
    """
    base_path = Path(kb_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"Knowledge base directory not found: {base_path}")

    pattern = str(base_path / "*.md")
    files = sorted(glob.glob(pattern))

    documents: list[dict[str, str]] = []
    for file_path in files:
        doc_path = Path(file_path)
        doc_id = doc_path.stem
        with open(doc_path, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()

        default_title = doc_id.replace("_", " ").title()
        title, text = extract_title_and_text(raw_content, default_title)

        documents.append({
            "doc_id": doc_id,
            "title": title,
            "text": text,
        })

    return documents


def get_doc_by_id(doc_id: str, kb_dir: str | Path = "kb") -> dict[str, str] | None:
    """Finds a single policy document by its doc_id stem.

    Args:
        doc_id: Document stem identifier (e.g., 'sla_by_severity').
        kb_dir: Directory containing policy files.

    Returns:
        Document dict if found, else None.
    """
    docs = load_kb(kb_dir)
    for doc in docs:
        if doc["doc_id"] == doc_id:
            return doc
    return None


def validate_kb(kb_dir: str | Path = "kb") -> dict[str, Any]:
    """Validates that all required topics exist and meet sentence constraints.

    Returns:
        Dict containing validation summary and boolean passed status.
    """
    docs = load_kb(kb_dir)
    doc_map = {d["doc_id"]: d for d in docs}

    missing_topics = [t for t in REQUIRED_TOPIC_IDS if t not in doc_map]
    invalid_sentences: list[dict[str, Any]] = []

    for doc in docs:
        s_count = count_sentences(doc["text"])
        if not (2 <= s_count <= 5):
            invalid_sentences.append({
                "doc_id": doc["doc_id"],
                "sentence_count": s_count,
            })

    passed = len(missing_topics) == 0 and len(invalid_sentences) == 0

    return {
        "total_documents": len(docs),
        "required_topics_present": len(REQUIRED_TOPIC_IDS) - len(missing_topics),
        "missing_topics": missing_topics,
        "invalid_sentence_docs": invalid_sentences,
        "passed": passed,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("OLA SUPPORT KNOWLEDGE BASE — SUMMARY & VALIDATION")
    print("=" * 70)

    docs = load_kb("kb")
    print(f"Total documents loaded: {len(docs)}")
    print("-" * 70)
    print(f"{'Doc ID':<30} | {'Sentences':<9} | {'Title'}")
    print("-" * 70)
    for d in docs:
        sc = count_sentences(d["text"])
        print(f"{d['doc_id']:<30} | {sc:<9} | {d['title']}")
    print("-" * 70)

    summary = validate_kb("kb")
    print(f"Validation Result: {'PASSED' if summary['passed'] else 'FAILED'}")
    if not summary["passed"]:
        if summary["missing_topics"]:
            print(f"Missing required topics: {summary['missing_topics']}")
        if summary["invalid_sentence_docs"]:
            print(f"Invalid sentence counts: {summary['invalid_sentence_docs']}")
    print("=" * 70)
