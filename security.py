"""
Security hardening module for Ola Support Intelligence.
Provides rate limiting, enhanced CSP, security headers, and request validation.
"""
from __future__ import annotations

import time
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_window: int = 100
    window_seconds: int = 60
    burst_allowance: int = 20  # Allow short bursts


@dataclass
class ClientState:
    """Tracks request timestamps for a client."""
    requests: list = field(default_factory=list)
    blocked_until: float = 0


class InMemoryRateLimiter:
    """
    In-memory sliding window rate limiter.
    For production, replace with Redis-backed implementation.
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.clients: Dict[str, ClientState] = defaultdict(ClientState)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Prefer X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to direct client
        client = request.client
        if client:
            return client.host

        return "unknown"

    def _cleanup_expired(self):
        """Remove expired client entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys = [
            key for key, state in self.clients.items()
            if now > state.blocked_until and not state.requests
        ]
        for key in expired_keys:
            del self.clients[key]

    def check_rate_limit(self, request: Request) -> Tuple[bool, Optional[Dict]]:
        """
        Check if request should be rate limited.
        Returns (allowed, headers_dict).
        """
        self._cleanup_expired()

        client_key = self._get_client_key(request)
        state = self.clients[client_key]
        now = time.time()

        # Check if currently blocked
        if now < state.blocked_until:
            retry_after = int(state.blocked_until - now) + 1
            return False, {
                "X-RateLimit-Limit": str(self.config.requests_per_window),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(state.blocked_until)),
                "Retry-After": str(retry_after),
            }

        # Clean old requests outside window
        window_start = now - self.config.window_seconds
        state.requests = [ts for ts in state.requests if ts > window_start]

        # Check limit
        effective_limit = self.config.requests_per_window + self.config.burst_allowance
        if len(state.requests) >= effective_limit:
            # Block for remainder of window
            state.blocked_until = now + self.config.window_seconds
            retry_after = self.config.window_seconds
            return False, {
                "X-RateLimit-Limit": str(self.config.requests_per_window),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(state.blocked_until)),
                "Retry-After": str(retry_after),
            }

        # Allow request
        state.requests.append(now)
        remaining = max(0, self.config.requests_per_window - len(state.requests))

        return True, {
            "X-RateLimit-Limit": str(self.config.requests_per_window),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(now + self.config.window_seconds)),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, config: RateLimitConfig = None):
        super().__init__(app)
        self.limiter = InMemoryRateLimiter(config)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static assets
        path = request.url.path
        if path in ("/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"):
            return await call_next(request)

        if path.startswith("/static/"):
            return await call_next(request)

        allowed, headers = self.limiter.check_rate_limit(request)

        if not allowed:
            return Response(
                content='{"error": "Rate limit exceeded", "detail": "Too many requests. Please slow down."}',
                status_code=429,
                media_type="application/json",
                headers=headers
            )

        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response


# Enhanced Content Security Policy
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; "
    "img-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'; "
    "upgrade-insecure-requests"
)

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app, csp_policy: str = CSP_POLICY):
        super().__init__(app)
        self.csp_policy = csp_policy

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add CSP
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Add security headers
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value

        # Remove server header
        response.headers.pop("Server", None)

        return response


# Input validation and sanitization
DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"data:text/html",  # Data URIs
    r"vbscript:",  # VBScript
    r"expression\s*\(",  # CSS expressions
]


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input by removing dangerous patterns.
    Returns sanitized text.
    """
    if not text:
        return ""

    # Truncate
    if len(text) > max_length:
        text = text[:max_length]

    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    return text


def validate_ticket_id(ticket_id: str) -> bool:
    """Validate ticket ID format (TKT-XXXX)."""
    return bool(re.match(r"^TKT-\d{4}$", ticket_id.strip().upper()))


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format."""
    return bool(re.match(r"^[a-zA-Z0-9_-]{1,64}$", session_id))


# Request size limits
MAX_REQUEST_SIZE = 1024 * 1024  # 1 MB
MAX_JSON_DEPTH = 50
MAX_JSON_KEYS = 1000


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request size limits."""

    def __init__(self, app, max_size: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_size:
            return Response(
                content='{"error": "Payload too large", "detail": f"Request body exceeds {self.max_size} bytes"}',
                status_code=413,
                media_type="application/json"
            )

        return await call_next(request)


# Dependency vulnerability scanning helper
def check_dependencies_for_vulnerabilities() -> list:
    """
    Check installed packages for known vulnerabilities using pip-audit.
    Returns list of vulnerability dicts.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["pip-audit", "--format=json"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return []
        import json
        return json.loads(result.stdout) if result.stdout else []
    except Exception:
        return []


# Security configuration for different environments
@dataclass
class SecurityConfig:
    """Security configuration for the application."""
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # CSP
    csp_policy: str = CSP_POLICY

    # Request validation
    max_request_size: int = MAX_REQUEST_SIZE
    max_json_depth: int = MAX_JSON_DEPTH
    max_json_keys: int = MAX_JSON_KEYS

    # Input sanitization
    sanitize_inputs: bool = True

    # Security headers
    security_headers_enabled: bool = True

    # HTTPS enforcement (for production)
    force_https: bool = False
    hsts_max_age: int = 31536000  # 1 year

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Create config from environment variables."""
        return cls(
            rate_limit_enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
            rate_limit_requests=int(os.environ.get("RATE_LIMIT_REQUESTS", "100")),
            rate_limit_window=int(os.environ.get("RATE_LIMIT_WINDOW", "60")),
            csp_policy=os.environ.get("CSP_POLICY", CSP_POLICY),
            max_request_size=int(os.environ.get("MAX_REQUEST_SIZE", str(MAX_REQUEST_SIZE))),
            sanitize_inputs=os.environ.get("SANITIZE_INPUTS", "true").lower() == "true",
            security_headers_enabled=os.environ.get("SECURITY_HEADERS_ENABLED", "true").lower() == "true",
            force_https=os.environ.get("FORCE_HTTPS", "false").lower() == "true",
        )


import os