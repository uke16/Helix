"""HELIX API Middleware Package.

ADR-035: Security & Reliability Fixes.
Contains middleware components for input validation and rate limiting.
"""

from .input_validator import InputValidator, MAX_MESSAGE_LENGTH, MAX_MESSAGES_PER_REQUEST, VALID_ROLES
from .rate_limiter import (
    limiter,
    RateLimitExceededHandler,
    RateLimitExceeded,
    rate_limit,
    get_client_ip,
    DEFAULT_RATE_LIMIT,
    CHAT_COMPLETIONS_LIMIT,
    BURST_LIMIT,
)

__all__ = [
    # Input Validation
    "InputValidator",
    "MAX_MESSAGE_LENGTH",
    "MAX_MESSAGES_PER_REQUEST",
    "VALID_ROLES",
    # Rate Limiting
    "limiter",
    "RateLimitExceededHandler",
    "RateLimitExceeded",
    "rate_limit",
    "get_client_ip",
    "DEFAULT_RATE_LIMIT",
    "CHAT_COMPLETIONS_LIMIT",
    "BURST_LIMIT",
]
