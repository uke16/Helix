"""Retry handler for transient pipeline errors.

This module provides automatic retry functionality for the Evolution Pipeline,
implementing exponential backoff for transient errors while immediately failing
on permanent errors.

Part of ADR-030: Evolution Pipeline Reliability - Fix 4.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(Enum):
    """Categorization of errors for retry decisions."""

    TRANSIENT = "transient"      # Network, throttling - retry
    PERMANENT = "permanent"       # Syntax, logic - no retry
    UNKNOWN = "unknown"          # Default - retry once


# Patterns that indicate transient errors
TRANSIENT_PATTERNS = [
    "429",
    "Too Many Requests",
    "rate limit",
    "timeout",
    "connection reset",
    "temporary failure",
    "ETIMEDOUT",
    "ECONNRESET",
    "ECONNREFUSED",
    "ENETUNREACH",
    "service unavailable",
    "503",
    "502",
    "504",
    "gateway timeout",
]

# Patterns that indicate permanent errors (no retry)
PERMANENT_PATTERNS = [
    "syntax",
    "syntaxerror",
    "import",
    "importerror",
    "name error",
    "nameerror",
    "type error",
    "typeerror",
    "attribute error",
    "attributeerror",
    "indentation",
    "indentationerror",
    "invalid syntax",
    "module not found",
    "modulenotfounderror",
]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an error to determine retry strategy.

    Args:
        error: The exception to categorize

    Returns:
        ErrorCategory indicating whether to retry
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()

    # Check for permanent errors first
    for pattern in PERMANENT_PATTERNS:
        if pattern in error_msg or pattern in error_type:
            return ErrorCategory.PERMANENT

    # Check for transient errors
    for pattern in TRANSIENT_PATTERNS:
        if pattern.lower() in error_msg:
            return ErrorCategory.TRANSIENT

    return ErrorCategory.UNKNOWN


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate delay for next retry attempt using exponential backoff.

    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration

    Returns:
        Delay in seconds before next retry
    """
    delay = config.initial_delay * (config.exponential_base ** attempt)
    return min(delay, config.max_delay)


async def with_retry(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
    error_context: str = "operation"
) -> T:
    """Execute an async function with retry on transient errors.

    Args:
        func: Async function to execute
        config: Retry configuration (uses defaults if None)
        error_context: Context string for error messages

    Returns:
        Result of the function

    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e
            category = categorize_error(e)

            if category == ErrorCategory.PERMANENT:
                logger.warning(
                    f"{error_context}: Permanent error, no retry. {e}"
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    f"{error_context}: Max retries ({config.max_retries}) "
                    f"exhausted. Last error: {e}"
                )
                raise

            delay = calculate_delay(attempt, config)

            logger.info(
                f"{error_context}: Attempt {attempt + 1} failed ({category.value}), "
                f"retrying in {delay:.1f}s. Error: {e}"
            )

            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    assert last_error is not None
    raise last_error


def sync_with_retry(
    func: Callable[[], T],
    config: RetryConfig | None = None,
    error_context: str = "operation"
) -> T:
    """Execute a synchronous function with retry on transient errors.

    Args:
        func: Synchronous function to execute
        config: Retry configuration (uses defaults if None)
        error_context: Context string for error messages

    Returns:
        Result of the function

    Raises:
        Last exception if all retries exhausted
    """
    import time

    config = config or RetryConfig()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            category = categorize_error(e)

            if category == ErrorCategory.PERMANENT:
                logger.warning(
                    f"{error_context}: Permanent error, no retry. {e}"
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    f"{error_context}: Max retries ({config.max_retries}) "
                    f"exhausted. Last error: {e}"
                )
                raise

            delay = calculate_delay(attempt, config)

            logger.info(
                f"{error_context}: Attempt {attempt + 1} failed ({category.value}), "
                f"retrying in {delay:.1f}s. Error: {e}"
            )

            time.sleep(delay)

    # Should not reach here, but satisfy type checker
    assert last_error is not None
    raise last_error
