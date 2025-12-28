"""Tests for retry handler module.

Tests the retry logic for transient pipeline errors as defined in ADR-030 Fix 4.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from helix.pipeline.retry_handler import (
    ErrorCategory,
    RetryConfig,
    categorize_error,
    calculate_delay,
    with_retry,
    sync_with_retry,
    TRANSIENT_PATTERNS,
    PERMANENT_PATTERNS,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_enum_values(self):
        """Verify all expected categories exist."""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Verify default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0

    def test_custom_values(self):
        """Verify custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0


class TestCategorizeError:
    """Tests for error categorization logic."""

    @pytest.mark.parametrize("error_message,expected", [
        # Transient errors should be retried
        ("Error 429: Too Many Requests", ErrorCategory.TRANSIENT),
        ("HTTP 429 rate limit exceeded", ErrorCategory.TRANSIENT),
        ("Connection timeout after 30s", ErrorCategory.TRANSIENT),
        ("Connection reset by peer", ErrorCategory.TRANSIENT),
        ("ETIMEDOUT: connection timed out", ErrorCategory.TRANSIENT),
        ("ECONNRESET: connection reset", ErrorCategory.TRANSIENT),
        ("ECONNREFUSED: connection refused", ErrorCategory.TRANSIENT),
        ("503 Service Unavailable", ErrorCategory.TRANSIENT),
        ("502 Bad Gateway", ErrorCategory.TRANSIENT),
        ("504 Gateway Timeout", ErrorCategory.TRANSIENT),
        ("temporary failure in name resolution", ErrorCategory.TRANSIENT),
    ])
    def test_transient_errors(self, error_message, expected):
        """Verify transient errors are correctly identified."""
        error = Exception(error_message)
        assert categorize_error(error) == expected

    @pytest.mark.parametrize("error_message,expected", [
        # Permanent errors should not be retried
        ("SyntaxError: invalid syntax", ErrorCategory.PERMANENT),
        ("IndentationError: unexpected indent", ErrorCategory.PERMANENT),
        ("ImportError: No module named 'foo'", ErrorCategory.PERMANENT),
        ("ModuleNotFoundError: No module named 'bar'", ErrorCategory.PERMANENT),
        ("NameError: name 'x' is not defined", ErrorCategory.PERMANENT),
        ("TypeError: unsupported operand type", ErrorCategory.PERMANENT),
        ("AttributeError: object has no attribute 'y'", ErrorCategory.PERMANENT),
    ])
    def test_permanent_errors(self, error_message, expected):
        """Verify permanent errors are correctly identified."""
        error = Exception(error_message)
        assert categorize_error(error) == expected

    def test_permanent_error_by_type(self):
        """Verify error types are used for categorization."""
        # Create actual exception types
        error = SyntaxError("invalid syntax at line 1")
        assert categorize_error(error) == ErrorCategory.PERMANENT

    def test_unknown_errors(self):
        """Verify unknown errors are categorized correctly."""
        error = Exception("Some random error message")
        assert categorize_error(error) == ErrorCategory.UNKNOWN

    def test_case_insensitive_matching(self):
        """Verify pattern matching is case-insensitive."""
        error = Exception("RATE LIMIT exceeded")
        assert categorize_error(error) == ErrorCategory.TRANSIENT

        error = Exception("CONNECTION TIMEOUT")
        assert categorize_error(error) == ErrorCategory.TRANSIENT


class TestCalculateDelay:
    """Tests for exponential backoff delay calculation."""

    def test_initial_delay(self):
        """First attempt uses initial delay."""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0)
        assert calculate_delay(0, config) == 1.0

    def test_exponential_increase(self):
        """Delay increases exponentially."""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=100.0)
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0

    def test_max_delay_cap(self):
        """Delay is capped at max_delay."""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=5.0)
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 5.0  # Capped at max_delay
        assert calculate_delay(10, config) == 5.0  # Still capped

    def test_custom_exponential_base(self):
        """Different exponential bases work correctly."""
        config = RetryConfig(initial_delay=1.0, exponential_base=3.0, max_delay=100.0)
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 3.0
        assert calculate_delay(2, config) == 9.0


class TestWithRetry:
    """Tests for async retry wrapper."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Function returns immediately on success."""
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(successful_func)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Transient errors trigger retry."""
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Error 429: Too Many Requests")
            return "success"

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        result = await with_retry(fail_then_succeed, config=config)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self):
        """Permanent errors are not retried."""
        call_count = 0

        async def permanent_fail():
            nonlocal call_count
            call_count += 1
            raise SyntaxError("invalid syntax")

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        with pytest.raises(SyntaxError):
            await with_retry(permanent_fail, config=config)
        assert call_count == 1  # Only one attempt

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Exception raised after max retries exhausted."""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Connection timeout")

        config = RetryConfig(max_retries=2, initial_delay=0.01)
        with pytest.raises(Exception, match="Connection timeout"):
            await with_retry(always_fail, config=config)
        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_default_config(self):
        """Default config is used when not provided."""
        async def successful_func():
            return "success"

        result = await with_retry(successful_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_error_context_in_logs(self):
        """Error context is included in log messages."""
        async def fail_once():
            raise Exception("temporary failure")

        config = RetryConfig(max_retries=0, initial_delay=0.01)

        with patch("helix.pipeline.retry_handler.logger") as mock_logger:
            with pytest.raises(Exception):
                await with_retry(fail_once, config=config, error_context="Phase 1")
            # Check that error was logged with context
            assert any("Phase 1" in str(call) for call in mock_logger.method_calls)

    @pytest.mark.asyncio
    async def test_unknown_error_retried(self):
        """Unknown errors are retried (conservative approach)."""
        call_count = 0

        async def unknown_error_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Some unknown error")
            return "success"

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        result = await with_retry(unknown_error_then_succeed, config=config)
        assert result == "success"
        assert call_count == 2


class TestSyncWithRetry:
    """Tests for synchronous retry wrapper."""

    def test_success_on_first_attempt(self):
        """Function returns immediately on success."""
        call_count = 0

        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = sync_with_retry(successful_func)
        assert result == "success"
        assert call_count == 1

    def test_retry_on_transient_error(self):
        """Transient errors trigger retry."""
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Error 429: Too Many Requests")
            return "success"

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        result = sync_with_retry(fail_then_succeed, config=config)
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_permanent_error(self):
        """Permanent errors are not retried."""
        call_count = 0

        def permanent_fail():
            nonlocal call_count
            call_count += 1
            raise SyntaxError("invalid syntax")

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        with pytest.raises(SyntaxError):
            sync_with_retry(permanent_fail, config=config)
        assert call_count == 1

    def test_max_retries_exhausted(self):
        """Exception raised after max retries exhausted."""
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("ECONNREFUSED")

        config = RetryConfig(max_retries=2, initial_delay=0.01)
        with pytest.raises(Exception, match="ECONNREFUSED"):
            sync_with_retry(always_fail, config=config)
        assert call_count == 3


class TestPatternLists:
    """Tests for pattern lists completeness."""

    def test_transient_patterns_not_empty(self):
        """Transient patterns list is populated."""
        assert len(TRANSIENT_PATTERNS) > 0

    def test_permanent_patterns_not_empty(self):
        """Permanent patterns list is populated."""
        assert len(PERMANENT_PATTERNS) > 0

    def test_patterns_are_strings(self):
        """All patterns are strings."""
        for pattern in TRANSIENT_PATTERNS:
            assert isinstance(pattern, str)
        for pattern in PERMANENT_PATTERNS:
            assert isinstance(pattern, str)

    def test_no_overlap_between_patterns(self):
        """Transient and permanent patterns don't overlap."""
        transient_lower = {p.lower() for p in TRANSIENT_PATTERNS}
        permanent_lower = {p.lower() for p in PERMANENT_PATTERNS}
        overlap = transient_lower & permanent_lower
        assert not overlap, f"Overlapping patterns: {overlap}"
