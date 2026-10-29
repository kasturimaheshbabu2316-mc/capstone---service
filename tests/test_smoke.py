"""Smoke Test Suite: Verifies imports of all target modules.

Track: Business Operations / Customer Support (Ola)
"""

import pytest


def test_import_dataset():
    import dataset
    assert hasattr(dataset, "SUPPORT_TICKETS") or hasattr(dataset, "SUPPORT_TICKETS_BY_ID")


def test_import_rag():
    import rag.chunking
    import rag.index
    import rag.generate
    import rag.calibrate
    import rag.evaluate_chunking
    assert callable(rag.generate.grounded_generate)
    assert callable(rag.calibrate.calibrate_threshold)


def test_import_tools():
    import tools.ticket_tool
    assert callable(tools.ticket_tool.check_support_ticket_status)


def test_import_crew():
    import crew.mock_llm
    import crew.crew
    import crew.memory
    import crew.schemas
    assert crew.mock_llm.MockLLM is not None
    assert crew.schemas.SupportResponse is not None


def test_import_safety():
    import safety.guardrails
    assert callable(safety.guardrails.validate_sql)
    assert callable(safety.guardrails.mask_pii)
    assert callable(safety.guardrails.check_security)
    assert callable(safety.guardrails.check_payload_budget)


def test_import_review():
    import review.autogen_review
    assert callable(review.autogen_review.review_support_response)


def test_import_governance():
    import governance.budget
    assert callable(governance.budget.check_budget_limit)


def test_import_cache():
    import cache
    assert cache.response_cache is not None


def test_import_api():
    import api.main
    import api.logging_setup
    assert api.main.app is not None
    assert api.logging_setup.audit_logger is not None


def test_import_evaluation():
    import evaluation.judge
    import evaluation.queries
    import evaluation.run_eval
    assert len(evaluation.queries.EVAL_BENCHMARK_QUERIES) == 15
    assert callable(evaluation.judge.judge_response)
    assert callable(evaluation.run_eval.run_benchmark_evaluation)


def test_import_config():
    import config
    assert config.MOCK_LLM is True
    assert config.CREWAI_DISABLE_TELEMETRY is True
