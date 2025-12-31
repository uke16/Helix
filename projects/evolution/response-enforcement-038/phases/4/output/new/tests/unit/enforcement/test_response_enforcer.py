"""
Tests for ResponseEnforcer.

Tests the retry logic, fallback mechanism, and validator integration.
"""

import pytest
from unittest.mock import AsyncMock

from helix.enforcement.response_enforcer import ResponseEnforcer, EnforcementResult
from helix.enforcement.validators.base import ValidationIssue
from helix.enforcement.validators.step_marker import StepMarkerValidator


class TestEnforcementResult:
    """Tests for EnforcementResult dataclass."""

    def test_successful_result_is_truthy(self):
        """Successful result should be truthy."""
        result = EnforcementResult(
            success=True,
            response="valid",
            attempts=1,
        )
        assert result
        assert bool(result) is True

    def test_failed_result_is_falsy(self):
        """Failed result should be falsy."""
        result = EnforcementResult(
            success=False,
            response="invalid",
            attempts=3,
        )
        assert not result
        assert bool(result) is False

    def test_result_with_fallback(self):
        """Result should track fallback application."""
        result = EnforcementResult(
            success=True,
            response="fixed",
            attempts=3,
            fallback_applied=True,
        )
        assert result.fallback_applied is True


class TestResponseEnforcerInit:
    """Tests for ResponseEnforcer initialization."""

    def test_init_with_defaults(self, mock_runner):
        """Should initialize with default values."""
        enforcer = ResponseEnforcer(runner=mock_runner)

        assert enforcer.runner is mock_runner
        assert enforcer.max_retries == 2
        assert enforcer.validators == []

    def test_init_with_validators(self, mock_runner, passing_validator):
        """Should accept validators in constructor."""
        enforcer = ResponseEnforcer(
            runner=mock_runner,
            validators=[passing_validator],
        )
        assert len(enforcer.validators) == 1

    def test_add_validator(self, mock_runner, passing_validator):
        """Should add validators dynamically."""
        enforcer = ResponseEnforcer(runner=mock_runner)
        enforcer.add_validator(passing_validator)

        assert len(enforcer.validators) == 1
        assert enforcer.validators[0].name == "passing"

    def test_remove_validator(self, mock_runner, passing_validator, failing_validator):
        """Should remove validators by name."""
        enforcer = ResponseEnforcer(
            runner=mock_runner,
            validators=[passing_validator, failing_validator],
        )

        removed = enforcer.remove_validator("failing")
        assert removed is True
        assert len(enforcer.validators) == 1

        not_found = enforcer.remove_validator("nonexistent")
        assert not_found is False


class TestValidationSuccess:
    """Tests for successful validation."""

    @pytest.mark.asyncio
    async def test_valid_response_succeeds_immediately(
        self, success_runner, passing_validator
    ):
        """Valid response should succeed on first attempt."""
        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[passing_validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is True
        assert result.attempts == 1
        assert result.fallback_applied is False
        success_runner.run_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_validators_always_succeeds(self, success_runner):
        """No validators means response always passes."""
        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is True
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_warnings_do_not_trigger_retry(self, success_runner, mock_runner):
        """Warnings should not trigger retry."""
        from tests.unit.enforcement.conftest import MockValidator

        warning_validator = MockValidator(
            name="warning",
            issues=[
                ValidationIssue(
                    code="WARN_001",
                    message="Just a warning",
                    fix_hint="Optional fix",
                    severity="warning",
                )
            ],
        )

        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[warning_validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is True
        assert result.attempts == 1
        assert len(result.issues) == 1
        assert result.issues[0].severity == "warning"


class TestRetryMechanism:
    """Tests for retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_validation_failure(self, failing_then_success_runner):
        """Should retry when validation fails."""
        validator = StepMarkerValidator()

        enforcer = ResponseEnforcer(
            runner=failing_then_success_runner,
            max_retries=2,
            validators=[validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is True
        assert result.attempts == 2
        failing_then_success_runner.continue_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, always_failing_runner, failing_validator):
        """Should stop after max_retries."""
        enforcer = ResponseEnforcer(
            runner=always_failing_runner,
            max_retries=2,
            validators=[failing_validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        # 1 initial + 2 retries = 3 attempts
        assert result.attempts == 3
        assert always_failing_runner.run_session.call_count == 1
        assert always_failing_runner.continue_session.call_count == 2

    @pytest.mark.asyncio
    async def test_feedback_prompt_contains_issues(self, mock_runner, failing_validator):
        """Retry should include validation issues in feedback."""
        mock_runner.run_session.return_value = AsyncMock(stdout="invalid")()
        mock_runner.continue_session.return_value = AsyncMock(stdout="still invalid")()

        enforcer = ResponseEnforcer(
            runner=mock_runner,
            max_retries=1,
            validators=[failing_validator],
        )

        await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        # Check that continue_session was called with feedback
        call_args = mock_runner.continue_session.call_args
        feedback_prompt = call_args.kwargs.get("prompt") or call_args.args[1] if len(call_args.args) > 1 else ""

        # The feedback should mention the issue
        assert "TEST_ERROR" in feedback_prompt or "Validierungsfehler" in feedback_prompt


class TestFallbackMechanism:
    """Tests for fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_applied_when_available(
        self, always_failing_runner, failing_with_fallback_validator
    ):
        """Should apply fallback when max retries reached."""
        enforcer = ResponseEnforcer(
            runner=always_failing_runner,
            max_retries=1,
            validators=[failing_with_fallback_validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is True
        assert result.fallback_applied is True
        assert "Fixed by fallback" in result.response

    @pytest.mark.asyncio
    async def test_no_fallback_returns_failure(
        self, always_failing_runner, failing_validator
    ):
        """Should fail when no fallback available."""
        enforcer = ResponseEnforcer(
            runner=always_failing_runner,
            max_retries=1,
            validators=[failing_validator],
        )

        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
        )

        assert result.success is False
        assert result.fallback_applied is False
        assert len(result.issues) > 0


class TestValidatorFiltering:
    """Tests for validator name filtering."""

    @pytest.mark.asyncio
    async def test_filter_validators_by_name(
        self, success_runner, passing_validator, failing_validator
    ):
        """Should only use specified validators."""
        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[passing_validator, failing_validator],
        )

        # Only use passing validator
        result = await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
            validator_names=["passing"],
        )

        assert result.success is True
        assert passing_validator.validate_call_count == 1
        assert failing_validator.validate_call_count == 0

    @pytest.mark.asyncio
    async def test_none_names_uses_all_validators(
        self, success_runner, passing_validator
    ):
        """None validator_names should use all validators."""
        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[passing_validator],
        )

        await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
            validator_names=None,
        )

        assert passing_validator.validate_call_count == 1


class TestFeedbackPrompt:
    """Tests for feedback prompt generation."""

    def test_build_feedback_prompt_format(self, mock_runner):
        """Feedback prompt should include all issues."""
        enforcer = ResponseEnforcer(runner=mock_runner)

        issues = [
            ValidationIssue(
                code="ERROR_1",
                message="First error",
                fix_hint="Fix hint 1",
            ),
            ValidationIssue(
                code="ERROR_2",
                message="Second error",
                fix_hint="Fix hint 2",
            ),
        ]

        prompt = enforcer._build_feedback_prompt(issues)

        assert "Validierungsfehler" in prompt
        assert "ERROR_1" in prompt
        assert "First error" in prompt
        assert "Fix hint 1" in prompt
        assert "ERROR_2" in prompt


class TestStreamEnforcementError:
    """Tests for error streaming."""

    @pytest.mark.asyncio
    async def test_stream_enforcement_error_format(self, mock_runner):
        """Should stream errors in SSE format."""
        enforcer = ResponseEnforcer(runner=mock_runner)

        issues = [
            ValidationIssue(
                code="TEST_ERROR",
                message="Test message",
                fix_hint="Test fix",
            )
        ]

        chunks = []
        async for chunk in enforcer.stream_enforcement_error(issues):
            chunks.append(chunk)

        combined = "".join(chunks)
        assert "[ENFORCEMENT ERROR]" in combined
        assert "TEST_ERROR" in combined
        assert "[DONE]" in combined


class TestContextPassing:
    """Tests for context handling."""

    @pytest.mark.asyncio
    async def test_context_passed_to_validators(self, success_runner):
        """Context should be passed to validators."""
        from tests.unit.enforcement.conftest import MockValidator

        received_context = {}

        class ContextCapturingValidator(MockValidator):
            def validate(self, response, context):
                received_context.update(context)
                return []

        validator = ContextCapturingValidator(name="context_capture")

        enforcer = ResponseEnforcer(
            runner=success_runner,
            validators=[validator],
        )

        await enforcer.run_with_enforcement(
            session_id="test-session",
            prompt="test prompt",
            context={"custom_key": "custom_value"},
        )

        assert received_context.get("custom_key") == "custom_value"
