"""Structured JSON-Lines Audit Logging Utility.

Re-exports from api.logging_setup for seamless backward compatibility.
"""

from api.logging_setup import (
    audit_logger,
    AuditLogger,
    RequestAuditLogger,
    LOG_FILE,
    LOG_DIR,
)

__all__ = ["audit_logger", "AuditLogger", "RequestAuditLogger", "LOG_FILE", "LOG_DIR"]
