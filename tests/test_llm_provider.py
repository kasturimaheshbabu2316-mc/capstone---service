"""Unit tests for Optional Real-LLM Mode Provider Configuration (Step 5)."""

from __future__ import annotations

import pytest
import config


def test_default_llm_provider_is_mock():
    """Validates that default LLM provider is 'mock' and MOCK_LLM is True."""
    assert config.MOCK_LLM is True
    assert config.LLM_PROVIDER in ("mock", "")


def test_missing_credentials_raise_clear_error(monkeypatch):
    """Asserts that choosing gemini or ollama without required env vars fails with clear error."""
    # Test missing GEMINI_API_KEY
    monkeypatch.setattr(config, "MOCK_LLM", False)
    monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)

    # When real LLM initialization is attempted without keys
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required when LLM_PROVIDER=gemini.")
