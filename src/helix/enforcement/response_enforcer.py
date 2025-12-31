"""
Response Enforcer - Wrapper for ClaudeRunner with validation and retry logic.

Validates LLM responses against configurable validators and automatically
retries with feedback when validation fails.

ADR-038: Deterministic LLM Response Enforcement
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any, TYPE_CHECKING

from .validators.base import ResponseValidator, ValidationIssue

if TYPE_CHECKING:
    from helix.consultant.claude_runner import ClaudeRunner

logger = logging.getLogger(__name__)


@dataclass
class EnforcementResult:
    """
    Result of enforcement validation.

    Attributes:
        success: True if response passed validation (or fallback worked)
        response: The final response text (possibly corrected)
        attempts: Number of attempts made (1 = first try succeeded)
        issues: Any remaining validation issues (warnings if success)
        fallback_applied: True if a fallback heuristic was used
    """

    success: bool
    response: str
    attempts: int
    issues: list[ValidationIssue] = field(default_factory=list)
    fallback_applied: bool = False

    def __bool__(self) -> bool:
        """EnforcementResult is truthy if successful."""
        return self.success


class ResponseEnforcer:
    """
    Wrapper around ClaudeRunner that enforces LLM output requirements.

    Validates responses against configurable validators and performs
    automatic retry with feedback when validation fails.

    Flow:
        1. Run Claude and get response
        2. Validate response against all validators
        3. If errors: retry with feedback prompt (up to max_retries)
        4. If max_retries reached: try fallback heuristics
        5. If no fallback possible: return failure

    Example:
        enforcer = ResponseEnforcer(
            runner=claude_runner,
            max_retries=2,
            validators=[StepMarkerValidator()]
        )
        result = await enforcer.run_with_enforcement(
            session_id="session-123",
            prompt="Create an ADR for..."
        )
        if result.success:
            process(result.response)
        else:
            handle_error(result.issues)
    """

    def __init__(
        self,
        runner: "ClaudeRunner",
        max_retries: int = 2,
        validators: Optional[list[ResponseValidator]] = None,
    ):
        """
        Initialize the ResponseEnforcer.

        Args:
            runner: ClaudeRunner instance for executing Claude
            max_retries: Maximum retry attempts on validation failure
            validators: List of validators to apply (default: none)
        """
        self.runner = runner
        self.max_retries = max_retries
        self.validators = validators or []

    def add_validator(self, validator: ResponseValidator) -> None:
        """
        Add a validator to the enforcement pipeline.

        Args:
            validator: Validator instance to add
        """
        self.validators.append(validator)

    def remove_validator(self, name: str) -> bool:
        """
        Remove a validator by name.

        Args:
            name: Name of validator to remove

        Returns:
            True if validator was found and removed
        """
        for i, v in enumerate(self.validators):
            if v.name == name:
                del self.validators[i]
                return True
        return False

    async def run_with_enforcement(
        self,
        session_id: str,
        prompt: str,
        validator_names: Optional[list[str]] = None,
        context: Optional[dict] = None,
        **runner_kwargs: Any,
    ) -> EnforcementResult:
        """
        Run Claude with response enforcement.

        Executes Claude, validates the response, and retries with
        feedback if validation fails.

        Args:
            session_id: Session ID for session continuation
            prompt: Initial prompt to send
            validator_names: List of validator names to use (None = all)
            context: Additional context for validators
            **runner_kwargs: Additional arguments for ClaudeRunner

        Returns:
            EnforcementResult with response and metadata
        """
        context = context or {}
        active_validators = self._get_validators(validator_names)
        all_issues: list[ValidationIssue] = []

        for attempt in range(self.max_retries + 1):
            # Execute Claude
            if attempt == 0:
                result = await self.runner.run_session(
                    session_id=session_id,
                    prompt=prompt,
                    **runner_kwargs,
                )
            else:
                # Retry with feedback using --continue
                feedback_prompt = self._build_feedback_prompt(all_issues)
                result = await self.runner.continue_session(
                    session_id=session_id,
                    prompt=feedback_prompt,
                    **runner_kwargs,
                )

            response = result.stdout if hasattr(result, "stdout") else str(result)

            # Validate response
            issues: list[ValidationIssue] = []
            for validator in active_validators:
                issues.extend(validator.validate(response, context))

            # Only errors count for retry (warnings are ok)
            errors = [i for i in issues if i.severity == "error"]

            if not errors:
                # Success - return with any warnings
                return EnforcementResult(
                    success=True,
                    response=response,
                    attempts=attempt + 1,
                    issues=[i for i in issues if i.severity == "warning"],
                    fallback_applied=False,
                )

            # Store errors for next retry feedback
            all_issues = errors
            logger.warning(
                f"Response validation failed (attempt {attempt + 1}/{self.max_retries + 1}): "
                f"{[i.code for i in errors]}"
            )

        # Max retries reached - try fallbacks
        fallback_response = self._apply_fallbacks(response, all_issues, context)

        if fallback_response:
            logger.info(f"Applied fallback for issues: {[i.code for i in all_issues]}")
            return EnforcementResult(
                success=True,
                response=fallback_response,
                attempts=self.max_retries + 1,
                issues=all_issues,
                fallback_applied=True,
            )

        # No fallback possible - return failure
        return EnforcementResult(
            success=False,
            response=response,
            attempts=self.max_retries + 1,
            issues=all_issues,
            fallback_applied=False,
        )

    def _get_validators(
        self, names: Optional[list[str]] = None
    ) -> list[ResponseValidator]:
        """
        Get validators filtered by name.

        Args:
            names: List of validator names to include (None = all)

        Returns:
            List of matching validators
        """
        if names is None:
            return self.validators
        return [v for v in self.validators if v.name in names]

    def _build_feedback_prompt(self, issues: list[ValidationIssue]) -> str:
        """
        Build feedback prompt for retry.

        Creates a prompt that explains the validation errors and
        asks the LLM to correct them.

        Args:
            issues: List of validation issues to address

        Returns:
            Formatted feedback prompt
        """
        lines = [
            "WICHTIG: Deine letzte Antwort hatte Validierungsfehler. Bitte korrigiere:",
            "",
        ]

        for issue in issues:
            lines.append(f"**{issue.code}**: {issue.message}")
            lines.append(f"  → Fix: {issue.fix_hint}")
            lines.append("")

        lines.append("Bitte wiederhole deine Antwort mit den Korrekturen.")

        return "\n".join(lines)

    def _apply_fallbacks(
        self,
        response: str,
        issues: list[ValidationIssue],
        context: dict,
    ) -> Optional[str]:
        """
        Apply fallback heuristics for all unresolved issues.

        Iterates through validators and attempts to apply their
        fallback methods to fix the response.

        Args:
            response: Current response text
            issues: Unresolved validation issues
            context: Validation context

        Returns:
            Corrected response if all issues resolved, else None
        """
        current_response = response

        # Try to fix each issue
        for issue in issues:
            # Find validator that can handle this issue
            for validator in self.validators:
                validator_issues = validator.validate(current_response, context)
                if any(i.code == issue.code for i in validator_issues):
                    fallback = validator.apply_fallback(current_response, context)
                    if fallback:
                        current_response = fallback
                        break

        # Check if all issues are resolved
        remaining_issues: list[ValidationIssue] = []
        for validator in self.validators:
            remaining_issues.extend(validator.validate(current_response, context))

        remaining_errors = [i for i in remaining_issues if i.severity == "error"]

        if not remaining_errors:
            return current_response

        return None

    async def stream_enforcement_error(
        self, issues: list[ValidationIssue]
    ) -> AsyncIterator[str]:
        """
        Stream enforcement errors to Open WebUI.

        Yields SSE-compatible chunks that display the validation
        errors to the user.

        Args:
            issues: List of validation issues to display

        Yields:
            SSE data chunks
        """
        yield "data: [ENFORCEMENT ERROR]\n\n"
        yield "data: Die LLM-Response konnte nicht validiert werden:\n\n"

        for issue in issues:
            yield f"data: - {issue.code}: {issue.message}\n\n"

        yield "data: Bitte versuche es erneut oder kontaktiere den Administrator.\n\n"
        yield "data: [DONE]\n\n"
