"""Rate Limiting Middleware for HELIX API.

ADR-035 Fix 3: Rate limiting to prevent resource exhaustion.

This module provides:
- IP-based rate limiting using slowapi
- Configurable limits per endpoint
- Default limit: 10 requests per minute per IP

Usage:
    # In main.py:
    from helix.api.middleware.rate_limiter import limiter, RateLimitExceededHandler

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, RateLimitExceededHandler)

    # In route file:
    from helix.api.middleware.rate_limiter import limiter

    @router.post("/endpoint")
    @limiter.limit("10/minute")
    async def my_endpoint(request: Request):
        ...

Dependencies:
    slowapi>=0.1.9
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse


# === Configuration Constants ===

DEFAULT_RATE_LIMIT = "10/minute"
"""Default rate limit for API endpoints."""

CHAT_COMPLETIONS_LIMIT = "10/minute"
"""Rate limit for the /v1/chat/completions endpoint.

This is critical as each request spawns a Claude Code process.
10 requests per minute per IP prevents resource exhaustion.
"""

BURST_LIMIT = "30/minute"
"""Higher limit for less resource-intensive endpoints like /v1/models."""


# === Rate Limiter Setup ===

def get_client_ip(request: Request) -> str:
    """Extract client IP from request.

    Handles X-Forwarded-For header for proxied requests.
    Falls back to direct client IP if header is not present.

    Args:
        request: The incoming Starlette/FastAPI request.

    Returns:
        Client IP address as string.
    """
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2
        # The first one is the original client IP
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    return get_remote_address(request)


# Create the limiter instance with IP-based key function
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[DEFAULT_RATE_LIMIT],
    headers_enabled=True,  # Add rate limit headers to responses
)


# === Exception Handler ===

async def RateLimitExceededHandler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Handle rate limit exceeded errors.

    Returns a JSON response with:
    - 429 Too Many Requests status code
    - Error message with retry information
    - Rate limit headers

    Args:
        request: The incoming request that exceeded the limit.
        exc: The RateLimitExceeded exception.

    Returns:
        JSONResponse with 429 status and error details.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "type": "rate_limit_error",
            "retry_after": _get_retry_after(exc),
        },
        headers={
            "Retry-After": str(_get_retry_after(exc)),
            "X-RateLimit-Limit": exc.detail,
        },
    )


def _get_retry_after(exc: RateLimitExceeded) -> int:
    """Extract retry-after seconds from rate limit exception.

    Args:
        exc: The RateLimitExceeded exception.

    Returns:
        Seconds until the rate limit resets (default: 60).
    """
    # slowapi includes retry-after info in headers if available
    # Default to 60 seconds if not available
    return 60


# === Decorator Helpers ===

def rate_limit(limit: str = DEFAULT_RATE_LIMIT):
    """Decorator factory for rate limiting endpoints.

    Usage:
        @router.post("/endpoint")
        @rate_limit("5/minute")
        async def my_endpoint(request: Request):
            ...

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour").

    Returns:
        The limiter decorator with the specified limit.
    """
    return limiter.limit(limit)


# === Exports ===

__all__ = [
    "limiter",
    "RateLimitExceededHandler",
    "RateLimitExceeded",
    "rate_limit",
    "get_client_ip",
    "DEFAULT_RATE_LIMIT",
    "CHAT_COMPLETIONS_LIMIT",
    "BURST_LIMIT",
]
