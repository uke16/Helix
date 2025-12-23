"""Rejection Handling for HELIX v4 Quality Gates.

This package provides handlers for when quality gates or approvals fail.
The rejection handler determines what action to take based on configuration.

Available Actions:
    - retry_phase: Re-run a phase with feedback
    - skip: Skip the rejection and continue
    - fail: Stop the workflow
    - escalate: Escalate to human review

Example:
    >>> from helix.rejection import handle_rejection, RejectionConfig
    >>> from helix.quality_gates import GateResult
    >>>
    >>> gate_result = GateResult(passed=False, gate_type="approval", ...)
    >>> config = RejectionConfig(
    ...     action="retry_phase",
    ...     target_phase="consultant",
    ...     max_retries=2,
    ... )
    >>>
    >>> action = await handle_rejection(
    ...     phase_id="review",
    ...     gate_result=gate_result,
    ...     rejection_config=config,
    ... )

See Also:
    - ADR-015: Approval & Validation System
    - helix.quality_gates: Quality gate system
"""

from .handler import (
    handle_rejection,
    RejectionConfig,
    RejectionAction,
    RejectionResult,
)

__all__ = [
    "handle_rejection",
    "RejectionConfig",
    "RejectionAction",
    "RejectionResult",
]
