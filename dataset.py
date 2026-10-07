"""Ola Domain Support Agent — Operational Dataset Generator.

Track: Business Operations / Customer Support (Ola)
Generates deterministic synthetic support ticket records for status lookups and risk evaluation.
"""

import math
import random
from typing import Any

# Frozen Design Choices
SEED = 42
TOTAL_RECORDS = 60

CATEGORIES = [
    "Billing",
    "Technical Issue",
    "Account Access",
    "Product Defect",
    "General Inquiry",
]
CATEGORY_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.15]

STATUSES = ["Open", "In Progress", "Escalated", "Resolved", "Closed"]
STATUS_WEIGHTS = [0.20, 0.20, 0.15, 0.25, 0.20]

# Resolution time parameters (log-normal distribution skewed between 0.5h and 72.0h)
LOGNORM_MU = 2.2
LOGNORM_SIGMA = 0.8
MIN_RESOLUTION_HOURS = 0.5
MAX_RESOLUTION_HOURS = 72.0


def generate_single_record(record_idx: int, rng: random.Random) -> dict[str, Any]:
    """Generates a single deterministic support ticket record."""
    record_id = f"TKT-{record_idx:04d}"
    category = rng.choices(CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
    status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

    # Skewed resolution time (log-normal, clipped between 0.5h and 72h)
    raw_res = math.exp(rng.gauss(LOGNORM_MU, LOGNORM_SIGMA))
    resolution_time_hours = round(
        max(MIN_RESOLUTION_HOURS, min(MAX_RESOLUTION_HOURS, raw_res)), 1
    )

    # Days since created (0 to 30)
    days_since_created = rng.randint(0, 30)

    # Conditional Bernoulli for escalation:
    # If status is Escalated, high probability (0.85); otherwise low probability (0.08)
    # This keeps overall escalation percentage stably around 18-22% (strictly within 10-30%)
    if status == "Escalated":
        escalated = rng.random() < 0.85
    else:
        escalated = rng.random() < 0.08

    return {
        "record_id": record_id,
        "category": category,
        "status": status,
        "resolution_time_hours": resolution_time_hours,
        "days_since_created": days_since_created,
        "escalated": escalated,
    }


def generate_dataset(
    seed: int = SEED, count: int = TOTAL_RECORDS
) -> list[dict[str, Any]]:
    """Generates the full dataset of support tickets."""
    rng = random.Random(seed)
    return [generate_single_record(i, rng) for i in range(1, count + 1)]


# Global dataset export
SUPPORT_TICKETS: list[dict[str, Any]] = generate_dataset(SEED, TOTAL_RECORDS)
SUPPORT_TICKETS_BY_ID: dict[str, dict[str, Any]] = {
    t["record_id"]: t for t in SUPPORT_TICKETS
}


def validate_dataset(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """Validates acceptance criteria and prints statistical breakdown."""
    total = len(tickets)
    cat_counts = {c: 0 for c in CATEGORIES}
    status_counts = {s: 0 for s in STATUSES}
    escalated_count = 0
    res_times = []

    for t in tickets:
        cat_counts[t["category"]] += 1
        status_counts[t["status"]] += 1
        if t["escalated"]:
            escalated_count += 1
        res_times.append(t["resolution_time_hours"])

    escalated_pct = (escalated_count / total) * 100.0

    # Invariant assertions
    assert total >= 40, f"Expected at least 40 records, got {total}"
    for cat, cnt in cat_counts.items():
        assert cnt >= 3, f"Category {cat} has only {cnt} records (< 3)"
    for st, cnt in status_counts.items():
        assert cnt >= 1, f"Status {st} has only {cnt} records (< 1)"
    assert (
        10.0 <= escalated_pct <= 30.0
    ), f"Escalated percentage {escalated_pct:.1f}% outside [10%, 30%]"

    return {
        "total": total,
        "category_counts": cat_counts,
        "status_counts": status_counts,
        "escalated_count": escalated_count,
        "escalated_percentage": escalated_pct,
        "min_res_hours": min(res_times),
        "max_res_hours": max(res_times),
        "avg_res_hours": sum(res_times) / total,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("OLA DOMAIN SUPPORT AGENT — DATASET VALIDATION (TASK 1)")
    print("=" * 70)
    print(f"Track: Business Operations / Customer Support (Ola)")
    print(f"Random Seed: {SEED}")
    print(f"Total Records Generated: {TOTAL_RECORDS}\n")

    # Run 1
    stats1 = validate_dataset(SUPPORT_TICKETS)

    print("--- 1. CATEGORY DISTRIBUTION (Requirement: each >= 3) ---")
    for cat, count in stats1["category_counts"].items():
        print(f"  • {cat:<20}: {count:>3} records (PASS)")

    print("\n--- 2. STATUS DISTRIBUTION (Requirement: each >= 1) ---")
    for st, count in stats1["status_counts"].items():
        print(f"  • {st:<20}: {count:>3} records (PASS)")

    print("\n--- 3. ESCALATION RATE (Requirement: 10% - 30%) ---")
    print(
        f"  • Escalated Count     : {stats1['escalated_count']} / {stats1['total']}"
    )
    print(
        f"  • Escalation Percentage: {stats1['escalated_percentage']:.2f}% (PASS: within 10%-30% band)"
    )

    print("\n--- 4. RESOLUTION TIME RANGE (Log-Normal Distribution) ---")
    print(f"  • Min Resolution Time : {stats1['min_res_hours']:.1f} hours")
    print(f"  • Max Resolution Time : {stats1['max_res_hours']:.1f} hours")
    print(f"  • Mean Resolution Time: {stats1['avg_res_hours']:.1f} hours")

    # Reproducibility check: Run 2
    tickets_run2 = generate_dataset(SEED, TOTAL_RECORDS)
    stats2 = validate_dataset(tickets_run2)
    assert (
        SUPPORT_TICKETS == tickets_run2
    ), "Reproducibility failure: Run 1 and Run 2 produced different records!"
    print("\n--- 5. REPRODUCIBILITY CHECK ---")
    print(
        "  • Ran generator twice with Seed 42: SUCCESS (byte-identical outputs verified)"
    )

    print("\n--- 6. SAMPLE RECORDS (First 5) ---")
    for rec in SUPPORT_TICKETS[:5]:
        print(f"  {rec}")

    print("\n" + "=" * 70)
    print("TASK 1 ACCEPTANCE CRITERIA: ALL INVARIANTS SATISFIED")
    print("=" * 70)
