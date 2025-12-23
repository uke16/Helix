"""Rejection Handler for HELIX v4 Quality Gates.

Handles gate rejections by determining what action to take based on
the rejection configuration. Supports retry, skip, fail, and escalate.

When a quality gate fails, the orchestrator calls the rejection handler
to determine the next action. The handler considers:
- The rejection action configured (retry_phase, skip, fail, escalate)
- Retry limits and current retry count
- Feedback to provide to the retrying phase

Example:
    >>> from helix.rejection.handler import handle_rejection, RejectionConfig
    >>> from helix.quality_gates import GateResult
    >>>
    >>> gate_result = GateResult(
    ...     passed=False,
    ...     gate_type="approval",
    ...     message="ADR rejected: missing migration plan",
    ...     details={"errors": ["Migration section required for major changes"]},
    ... )
    >>>
    >>> config = RejectionConfig(
    ...     action="retry_phase",
    ...     target_phase="consultant",
    ...     max_retries=2,
    ...     feedback_template="Please address: {issues}",
    ... )
    >>>
    >>> result = await handle_rejection(
    ...     phase_id="approval",
    ...     gate_result=gate_result,
    ...     rejection_config=config,
    ...     current_retry=0,
    ... )
    >>> if result.action == RejectionAction.RETRY:
    ...     # Re-run target phase with feedback
    ...     run_phase(result.target_phase, feedback=result.feedback)

See Also:
    - ADR-015: Approval & Validation System
    - helix.quality_gates: Quality gate system
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from helix.quality_gates import GateResult


class RejectionAction(Enum):
    """Actions that can be taken on rejection.

    Attributes:
        RETRY: Retry the target phase with feedback
        SKIP: Skip the rejection and continue workflow
        FAIL: Stop the workflow with failure
        ESCALATE: Escalate to human review
    """
    RETRY = "retry"
    SKIP = "skip"
    FAIL = "fail"
    ESCALATE = "escalate"


@dataclass
class RejectionConfig:
    """Configuration for rejection handling.

    Specifies how to handle a gate rejection, including what action
    to take and any retry limits.

    Attributes:
        action: Action to take ("retry_phase", "skip", "fail", "escalate")
        target_phase: Phase to retry (required for retry_phase)
        max_retries: Maximum number of retries (default: 2)
        feedback_template: Template for generating feedback
        escalation_channel: Where to escalate (for escalate action)

    Example:
        >>> config = RejectionConfig(
        ...     action="retry_phase",
        ...     target_phase="consultant",
        ...     max_retries=2,
        ...     feedback_template="## Issues\\n{issues}\\n\\n## Recommendations\\n{recommendations}",
        ... )
    """
    action: str  # "retry_phase" | "skip" | "fail" | "escalate"
    target_phase: Optional[str] = None
    max_retries: int = 2
    feedback_template: Optional[str] = None
    escalation_channel: Optional[str] = None

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "RejectionConfig":
        """Create from dictionary (e.g., from phases.yaml).

        Args:
            config: Dict with configuration

        Returns:
            RejectionConfig instance
        """
        return cls(
            action=config.get("action", "fail"),
            target_phase=config.get("target_phase"),
            max_retries=config.get("max_retries", 2),
            feedback_template=config.get("feedback_template"),
            escalation_channel=config.get("escalation_channel"),
        )


@dataclass
class RejectionResult:
    """Result of rejection handling.

    Contains the determined action and any associated data.

    Attributes:
        action: The action to take
        target_phase: Phase to retry (for RETRY action)
        feedback: Feedback to provide (for RETRY action)
        message: Human-readable explanation
        escalation_info: Info for escalation (for ESCALATE action)
        should_continue: Whether workflow should continue
    """
    action: RejectionAction
    target_phase: Optional[str] = None
    feedback: Optional[str] = None
    message: str = ""
    escalation_info: Optional[dict[str, Any]] = None
    should_continue: bool = False

    @property
    def is_retry(self) -> bool:
        """Check if action is retry."""
        return self.action == RejectionAction.RETRY

    @property
    def is_failure(self) -> bool:
        """Check if action stops the workflow."""
        return self.action == RejectionAction.FAIL


async def handle_rejection(
    phase_id: str,
    gate_result: GateResult,
    rejection_config: RejectionConfig | dict[str, Any],
    current_retry: int = 0,
) -> RejectionResult:
    """Handle a gate rejection.

    Determines what action to take based on the rejection configuration
    and current retry count.

    Args:
        phase_id: ID of the phase that had the rejection
        gate_result: The failed gate result
        rejection_config: Configuration for handling (or dict)
        current_retry: Current retry attempt number (0-indexed)

    Returns:
        RejectionResult with determined action

    Example:
        >>> result = await handle_rejection(
        ...     phase_id="approval",
        ...     gate_result=failed_gate_result,
        ...     rejection_config={"action": "retry_phase", "target_phase": "consultant"},
        ...     current_retry=0,
        ... )
    """
    # Convert dict to config if needed
    if isinstance(rejection_config, dict):
        rejection_config = RejectionConfig.from_dict(rejection_config)

    action_str = rejection_config.action.lower()

    # Handle retry_phase action
    if action_str == "retry_phase":
        return _handle_retry(
            phase_id=phase_id,
            gate_result=gate_result,
            config=rejection_config,
            current_retry=current_retry,
        )

    # Handle skip action
    if action_str == "skip":
        return RejectionResult(
            action=RejectionAction.SKIP,
            message=f"Skipping rejection for phase '{phase_id}': {gate_result.message}",
            should_continue=True,
        )

    # Handle escalate action
    if action_str == "escalate":
        return _handle_escalate(
            phase_id=phase_id,
            gate_result=gate_result,
            config=rejection_config,
        )

    # Default: fail
    return RejectionResult(
        action=RejectionAction.FAIL,
        message=f"Gate failed for phase '{phase_id}': {gate_result.message}",
        should_continue=False,
    )


def _handle_retry(
    phase_id: str,
    gate_result: GateResult,
    config: RejectionConfig,
    current_retry: int,
) -> RejectionResult:
    """Handle retry_phase action.

    Args:
        phase_id: Current phase ID
        gate_result: Failed gate result
        config: Rejection configuration
        current_retry: Current retry number

    Returns:
        RejectionResult
    """
    # Check retry limit
    if current_retry >= config.max_retries:
        return RejectionResult(
            action=RejectionAction.FAIL,
            message=f"Max retries ({config.max_retries}) exceeded for phase '{phase_id}'",
            should_continue=False,
        )

    # Validate target phase
    target_phase = config.target_phase
    if not target_phase:
        return RejectionResult(
            action=RejectionAction.FAIL,
            message="retry_phase action requires 'target_phase' configuration",
            should_continue=False,
        )

    # Generate feedback
    feedback = _generate_feedback(gate_result, config.feedback_template)

    return RejectionResult(
        action=RejectionAction.RETRY,
        target_phase=target_phase,
        feedback=feedback,
        message=f"Retrying phase '{target_phase}' (attempt {current_retry + 2}/{config.max_retries + 1})",
        should_continue=True,
    )


def _handle_escalate(
    phase_id: str,
    gate_result: GateResult,
    config: RejectionConfig,
) -> RejectionResult:
    """Handle escalate action.

    Args:
        phase_id: Current phase ID
        gate_result: Failed gate result
        config: Rejection configuration

    Returns:
        RejectionResult with escalation info
    """
    escalation_info = {
        "phase_id": phase_id,
        "gate_type": gate_result.gate_type,
        "message": gate_result.message,
        "details": gate_result.details,
        "channel": config.escalation_channel or "default",
    }

    return RejectionResult(
        action=RejectionAction.ESCALATE,
        message=f"Escalating rejection for phase '{phase_id}' to human review",
        escalation_info=escalation_info,
        should_continue=False,  # Wait for human decision
    )


def _generate_feedback(
    gate_result: GateResult,
    template: Optional[str],
) -> str:
    """Generate feedback for retry.

    Uses the template if provided, otherwise generates default feedback.

    Args:
        gate_result: Failed gate result
        template: Optional template string

    Returns:
        Feedback string
    """
    # Extract issues from details
    details = gate_result.details
    issues = details.get("issues", [])
    warnings = details.get("warnings", [])
    recommendations = details.get("recommendations", [])
    findings = details.get("findings", [])

    # Also check for errors in findings
    if findings:
        for finding in findings:
            if finding.get("severity") == "error":
                issues.append(finding.get("message", ""))
            elif finding.get("severity") == "warning":
                warnings.append(finding.get("message", ""))

    # Use template if provided
    if template:
        return template.format(
            message=gate_result.message,
            issues=_format_list(issues),
            warnings=_format_list(warnings),
            recommendations=_format_list(recommendations),
            gate_type=gate_result.gate_type,
        )

    # Generate default feedback
    lines = [
        "## Freigabe nicht erteilt",
        "",
        f"**Gate:** {gate_result.gate_type}",
        f"**Nachricht:** {gate_result.message}",
    ]

    if issues:
        lines.extend([
            "",
            "### Blocking Issues:",
            _format_list(issues),
        ])

    if warnings:
        lines.extend([
            "",
            "### Warnungen:",
            _format_list(warnings),
        ])

    if recommendations:
        lines.extend([
            "",
            "### Empfehlungen:",
            _format_list(recommendations),
        ])

    lines.extend([
        "",
        "---",
        "Bitte überarbeite das Artefakt und behebe die oben genannten Issues.",
    ])

    return "\n".join(lines)


def _format_list(items: list[str]) -> str:
    """Format a list as markdown bullets.

    Args:
        items: List of items

    Returns:
        Formatted string
    """
    if not items:
        return "(keine)"

    return "\n".join(f"- {item}" for item in items if item)
