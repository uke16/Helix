"""
Response Enforcer - Wrapper for ClaudeRunner with validation and retry logic.

Validates LLM responses against configurable validators and automatically
retries with feedback when validation fails.

ADR-038: Deterministic LLM Response Enforcement

Integration modes:
1. run_with_enforcement() - For non-streaming with built-in retry
2. validate_response() + run_retry_phase() - For post-streaming validation
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, AsyncIterator, Any, TYPE_CHECKING

from .validators.base import ResponseValidator, ValidationIssue

if TYPE_CHECKING:
    from helix.claude_runner import ClaudeRunner

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

    # =========================================================================
    # Post-Streaming Validation API (ADR-038 Integration)
    # =========================================================================

    def validate_response(
        self,
        response: str,
        context: Optional[dict] = None,
        validator_names: Optional[list[str]] = None,
    ) -> EnforcementResult:
        """
        Validate a response that was already obtained (e.g., from streaming).

        This is the first step in post-streaming enforcement:
        1. Call validate_response() after streaming completes
        2. If validation fails, call run_retry_phase() for retry
        3. If still failing after retries, apply_all_fallbacks()

        Args:
            response: The LLM response text to validate
            context: Additional context for validators (e.g., helix_root)
            validator_names: List of validator names to use (None = all)

        Returns:
            EnforcementResult with success=True if valid, else issues list
        """
        context = context or {}
        active_validators = self._get_validators(validator_names)
        issues: list[ValidationIssue] = []

        for validator in active_validators:
            issues.extend(validator.validate(response, context))

        # Separate errors from warnings
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        if not errors:
            return EnforcementResult(
                success=True,
                response=response,
                attempts=1,
                issues=warnings,
                fallback_applied=False,
            )

        return EnforcementResult(
            success=False,
            response=response,
            attempts=1,
            issues=errors,
            fallback_applied=False,
        )

    async def run_retry_phase(
        self,
        phase_dir: Path,
        issues: list[ValidationIssue],
        runner: "ClaudeRunner",
        context: Optional[dict] = None,
        timeout: int = 300,
    ) -> EnforcementResult:
        """
        Run a retry phase with feedback about validation issues.

        Sends a feedback prompt to Claude Code asking it to correct
        the validation issues. The retry uses the same phase directory
        so Claude has full context.

        Args:
            phase_dir: Path to the session/phase directory
            issues: Validation issues to address
            runner: ClaudeRunner instance for execution
            context: Validation context
            timeout: Timeout in seconds for the retry

        Returns:
            EnforcementResult with the retry response
        """
        context = context or {}
        feedback_prompt = self._build_feedback_prompt(issues)

        # Run retry with feedback prompt
        result = await runner.run_phase(
            phase_dir=phase_dir,
            prompt=feedback_prompt,
            timeout=timeout,
        )

        response = result.stdout if result.success else ""

        # Try to extract actual response from stream-json format
        if response:
            import json
            for line in response.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "result" and data.get("result"):
                        response = data["result"]
                        break
                except json.JSONDecodeError:
                    continue

        # Validate the retry response
        return self.validate_response(response, context)

    def apply_all_fallbacks(
        self,
        response: str,
        issues: list[ValidationIssue],
        context: Optional[dict] = None,
    ) -> EnforcementResult:
        """
        Apply all available fallback heuristics to fix issues.

        Called after retries have been exhausted. Iterates through
        validators and applies their fallback methods.

        Args:
            response: The response with validation issues
            issues: Unresolved validation issues
            context: Validation context

        Returns:
            EnforcementResult with potentially corrected response
        """
        context = context or {}
        corrected = self._apply_fallbacks(response, issues, context)

        if corrected:
            logger.info(
                f"ADR-038: Applied fallbacks for issues: {[i.code for i in issues]}"
            )
            return EnforcementResult(
                success=True,
                response=corrected,
                attempts=0,  # 0 indicates fallback path
                issues=issues,
                fallback_applied=True,
            )

        return EnforcementResult(
            success=False,
            response=response,
            attempts=0,
            issues=issues,
            fallback_applied=False,
        )

    async def enforce_streaming_response(
        self,
        response: str,
        phase_dir: Path,
        runner: "ClaudeRunner",
        context: Optional[dict] = None,
        max_retries: int = 2,
    ) -> EnforcementResult:
        """
        Full enforcement pipeline for post-streaming validation.

        Convenience method that combines validate_response(),
        run_retry_phase(), and apply_all_fallbacks() into a
        single workflow.

        Flow:
        1. Validate response
        2. If errors: retry up to max_retries times
        3. If still errors: apply fallbacks
        4. Return final result

        Args:
            response: The streamed response to enforce
            phase_dir: Path to session directory for retries
            runner: ClaudeRunner for retry execution
            context: Validation context
            max_retries: Maximum retry attempts

        Returns:
            EnforcementResult with final enforced response
        """
        context = context or {}
        current_response = response
        all_issues: list[ValidationIssue] = []
        total_attempts = 1

        # Initial validation
        result = self.validate_response(current_response, context)

        if result.success:
            logger.debug("ADR-038: Response passed initial validation")
            return result

        all_issues = result.issues
        logger.info(
            f"ADR-038: Initial validation failed: {[i.code for i in all_issues]}"
        )

        # Check if all issues can be fixed by fallback (no retry needed)
        # MISSING_STEP_MARKER can always be fixed by fallback - don't waste time retrying
        fallback_fixable = all(
            i.code in ("MISSING_STEP_MARKER", "INVALID_STEP") 
            for i in all_issues 
            if i.severity == "error"
        )
        
        if fallback_fixable:
            logger.info("ADR-038: Issues are fallback-fixable, skipping retries")
            fallback_result = self.apply_all_fallbacks(
                current_response, all_issues, context
            )
            return EnforcementResult(
                success=fallback_result.success,
                response=fallback_result.response,
                attempts=1,
                issues=fallback_result.issues,
                fallback_applied=fallback_result.fallback_applied,
            )

        # Retry loop
        for attempt in range(max_retries):
            total_attempts += 1
            logger.info(
                f"ADR-038: Retry attempt {attempt + 1}/{max_retries}"
            )

            result = await self.run_retry_phase(
                phase_dir=phase_dir,
                issues=all_issues,
                runner=runner,
                context=context,
            )

            if result.success:
                logger.info(
                    f"ADR-038: Retry {attempt + 1} succeeded"
                )
                return EnforcementResult(
                    success=True,
                    response=result.response,
                    attempts=total_attempts,
                    issues=result.issues,
                    fallback_applied=False,
                )

            current_response = result.response
            all_issues = result.issues

        # Max retries exhausted - try fallbacks
        logger.info(
            f"ADR-038: Max retries exhausted, applying fallbacks"
        )

        fallback_result = self.apply_all_fallbacks(
            current_response, all_issues, context
        )

        return EnforcementResult(
            success=fallback_result.success,
            response=fallback_result.response,
            attempts=total_attempts,
            issues=fallback_result.issues,
            fallback_applied=fallback_result.fallback_applied,
        )
