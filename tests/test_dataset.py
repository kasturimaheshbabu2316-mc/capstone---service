"""Unit tests for dataset generation (Task 1)."""

import pytest
from dataset import (
    generate_dataset,
    SUPPORT_TICKETS,
    SUPPORT_TICKETS_BY_ID,
    CATEGORIES,
    STATUSES,
)


def test_dataset_reproducibility():
    d1 = generate_dataset(seed=42)
    d2 = generate_dataset(seed=42)
    assert d1 == d2, "Dataset generation with seed 42 must be 100% deterministic"


def test_dataset_size_and_fields():
    assert len(SUPPORT_TICKETS) == 60
    assert len(SUPPORT_TICKETS_BY_ID) == 60

    required_fields = {
        "record_id",
        "category",
        "status",
        "resolution_time_hours",
        "days_since_created",
        "escalated",
    }
    for item in SUPPORT_TICKETS:
        assert required_fields.issubset(item.keys())
        assert 0 <= item["days_since_created"] <= 30
        assert 0.5 <= item["resolution_time_hours"] <= 72.0


def test_category_and_status_coverage():
    for cat in CATEGORIES:
        count = sum(1 for t in SUPPORT_TICKETS if t["category"] == cat)
        assert count >= 3, f"Category {cat} must have at least 3 records"

    for stat in STATUSES:
        count = sum(1 for t in SUPPORT_TICKETS if t["status"] == stat)
        assert count >= 1, f"Status {stat} must have at least 1 record"


def test_escalation_rate_band():
    escalated_count = sum(1 for t in SUPPORT_TICKETS if t["escalated"])
    rate = escalated_count / len(SUPPORT_TICKETS)
    assert 0.10 <= rate <= 0.30, f"Escalation rate {rate:.2%} must be in [10%, 30%]"
