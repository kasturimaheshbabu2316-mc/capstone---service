"""Test Suite for Threshold Consistency and Documentation Integrity.

Verifies:
1. RAG_SIMILARITY_THRESHOLD is exactly 0.3652 across config, code, and documentation.
2. ESCALATION_RISK_THRESHOLD is exactly 0.4400 across config, code, and documentation.
3. Neither constant drifts nor is confused with the other.
4. Static assets referenced by static/index.html resolve to existing files on disk.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import config
from rag.calibrate import CALIBRATED_THRESHOLD, RAG_SIMILARITY_THRESHOLD
from tools.ticket_tool import ESCALATION_RISK_THRESHOLD, ESCALATION_THRESHOLD

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_code_threshold_constants():
    """Asserts that code constants match canonical values."""
    assert config.RAG_SIMILARITY_THRESHOLD == 0.3652
    assert config.ESCALATION_RISK_THRESHOLD == 0.4400
    assert RAG_SIMILARITY_THRESHOLD == 0.3652
    assert CALIBRATED_THRESHOLD == 0.3652
    assert ESCALATION_RISK_THRESHOLD == 0.4400
    assert ESCALATION_THRESHOLD == 0.4400


def test_rag_threshold_json_values():
    """Validates that rag/threshold.json records the calibrated similarity threshold 0.3652."""
    threshold_file = PROJECT_ROOT / "rag" / "threshold.json"
    assert threshold_file.exists(), "rag/threshold.json missing"
    data = json.loads(threshold_file.read_text(encoding="utf-8"))
    assert data["threshold"] == 0.3652
    assert data.get("rag_similarity_threshold", 0.3652) == 0.3652


def test_documentation_threshold_mentions():
    """Verifies that architecture and governance docs distinguish 0.3652 from 0.4400."""
    arch_doc = (PROJECT_ROOT / "doc" / "architecture.md").read_text(encoding="utf-8")
    assert "0.3652" in arch_doc
    assert "0.4400" in arch_doc
    assert "RAG_SIMILARITY_THRESHOLD" in arch_doc
    assert "ESCALATION_RISK_THRESHOLD" in arch_doc

    risk_doc = (PROJECT_ROOT / "governance" / "RISK.md").read_text(encoding="utf-8")
    assert "0.3652" in risk_doc
    assert "0.4400" in risk_doc

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "0.3652" in readme
    assert "0.4400" in readme


def test_static_index_html_assets_exist():
    """Validates that every <link href="..."> and <script src="..."> in static/index.html exists on disk."""
    index_html = PROJECT_ROOT / "static" / "index.html"
    assert index_html.exists(), "static/index.html missing"
    content = index_html.read_text(encoding="utf-8")

    # Find all stylesheet links
    links = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE)
    for link in links:
        if link.startswith("data:") or link.startswith("http:") or link.startswith("https:"):
            continue
        clean_path = link.split("?")[0].lstrip("/")
        file_path = PROJECT_ROOT / clean_path
        assert file_path.exists(), f"Referenced link '{link}' does not exist on disk at {file_path}"

    # Find all script tags
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    for script in scripts:
        if script.startswith("data:") or script.startswith("http:") or script.startswith("https:"):
            continue
        clean_path = script.split("?")[0].lstrip("/")
        file_path = PROJECT_ROOT / clean_path
        assert file_path.exists(), f"Referenced script '{script}' does not exist on disk at {file_path}"
