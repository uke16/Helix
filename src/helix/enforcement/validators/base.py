"""
Base classes for response validation.

Provides the abstract base class for all validators and
data classes for validation results.

ADR-038: Deterministic LLM Response Enforcement
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationIssue:
    """
    A single validation issue found in the response.

    Attributes:
        code: Unique identifier for this issue type (e.g., "MISSING_STEP_MARKER")
        message: Human-readable description of the issue
        fix_hint: Suggestion for how to fix the issue
        severity: Issue severity - "error" blocks, "warning" is informational
    """

    code: str
    message: str
    fix_hint: str
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        """String representation for logging."""
        prefix = "ERROR" if self.severity == "error" else "WARNING"
        return f"[{prefix}] {self.code}: {self.message}"


@dataclass
class ValidationResult:
    """
    Result of validating a response against all validators.

    Attributes:
        valid: True if no errors (warnings allowed)
        issues: List of all validation issues found
    """

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]

    def __bool__(self) -> bool:
        """ValidationResult is truthy if valid."""
        return self.valid


class ResponseValidator(ABC):
    """
    Abstract base class for response validators.

    Each validator checks a specific aspect of LLM responses
    and can optionally provide fallback behavior when validation fails.

    Subclasses must implement:
        - name: Unique identifier for the validator
        - validate: Check response and return issues

    Subclasses may override:
        - apply_fallback: Attempt automatic fix when max retries reached
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name for this validator.

        Used for filtering validators and logging.

        Returns:
            Validator name (e.g., "step_marker", "adr_structure")
        """
        pass

    @abstractmethod
    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """
        Validate an LLM response.

        Args:
            response: The full LLM response text
            context: Additional context (session_state, etc.)

        Returns:
            List of ValidationIssues (empty if valid)
        """
        pass

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """
        Apply fallback heuristics when max retries reached.

        Override this method to provide automatic fixes for common issues.
        Return None if no fallback is possible.

        Args:
            response: The invalid response text
            context: Additional context

        Returns:
            Corrected response text, or None if no fallback possible
        """
        return None

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.name!r})"
