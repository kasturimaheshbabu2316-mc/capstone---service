"""Guardrails package initialization.

Re-exports core SQL and Governance guardrails from guardrails.py along with input/output guards.
"""

import sys
import importlib.util
from pathlib import Path

# Re-export from root guardrails.py
_root_guardrails = Path(__file__).resolve().parent.parent / "guardrails.py"
if _root_guardrails.exists():
    _spec = importlib.util.spec_from_file_location("guardrails_root", str(_root_guardrails))
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["guardrails_root"] = _mod
        _spec.loader.exec_module(_mod)
        for _name in dir(_mod):
            if not _name.startswith("__"):
                globals()[_name] = getattr(_mod, _name)

from guardrails.input_guard import (
    mask_phone_numbers,
    detect_prompt_injection,
    sanitize_and_validate_input,
)
from guardrails.output_guard import verify_groundedness

__all__ = [
    "SQLValidationResult",
    "strip_markdown_fences",
    "validate_sql",
    "mask_pii",
    "check_security",
    "check_payload_budget",
    "mask_phone_numbers",
    "detect_prompt_injection",
    "sanitize_and_validate_input",
    "verify_groundedness",
]


