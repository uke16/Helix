"""
HELIX Response Enforcement Package.

Provides deterministic LLM response validation and enforcement.
Implements ADR-038: Deterministic LLM Response Enforcement.

Components:
    - ResponseEnforcer: Wrapper for ClaudeRunner with validation and retry logic
    - Validators: Pluggable validators for response checking
        - StepMarkerValidator: Ensures STEP markers are present
        - ADRStructureValidator: Validates ADR structure completeness
        - FileExistenceValidator: Checks file references exist

Usage:
    from helix.enforcement import ResponseEnforcer
    from helix.enforcement.validators import StepMarkerValidator

    enforcer = ResponseEnforcer(
        runner=claude_runner,
        validators=[StepMarkerValidator()]
    )
    result = await enforcer.run_with_enforcement(session_id, prompt)
"""

from .response_enforcer import ResponseEnforcer, EnforcementResult
from .validators.base import (
    ResponseValidator,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    "ResponseEnforcer",
    "EnforcementResult",
    "ResponseValidator",
    "ValidationIssue",
    "ValidationResult",
]
