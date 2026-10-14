"""Audit Logging and Structured JSON-Lines Logger Setup.

Track: Business Operations / Customer Support (Ola)
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.logging_utils import audit_logger, AuditLogger

RequestAuditLogger = AuditLogger

__all__ = ["audit_logger", "AuditLogger", "RequestAuditLogger"]
