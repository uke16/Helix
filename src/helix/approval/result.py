"""Result classes for approval checks.

This module defines the data structures for approval results returned
by the ApprovalRunner after a sub-agent has completed its checks.

The main classes are:
- Finding: A single issue found during approval
- ApprovalResult: The complete result of an approval check

Example:
    >>> from helix.approval.result import ApprovalResult, Finding, Severity
    >>>
    >>> result = ApprovalResult(
    ...     approval_id="abc123",
    ...     approval_type="adr",
    ...     result="approved",
    ...     confidence=0.95,
    ...     findings=[
    ...         Finding(
    ...             severity=Severity.INFO,
    ...             check="completeness",
    ...             message="All sections present",
    ...         )
    ...     ],
    ... )
    >>> print(result.approved)  # True

See Also:
    - ADR-015: Approval & Validation System
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Severity(Enum):
    """Severity levels for findings.

    Determines how a finding affects the approval decision.

    Attributes:
        ERROR: Critical issue, causes rejection
        WARNING: Non-critical issue, may cause needs_revision
        INFO: Informational, doesn't affect decision
    """
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ApprovalDecision(Enum):
    """Possible approval decisions.

    The final decision made by the sub-agent after running all checks.

    Attributes:
        APPROVED: All checks passed, artifact is approved
        REJECTED: Critical issues found, artifact is rejected
        NEEDS_REVISION: Minor issues found, revision recommended
    """
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Finding:
    """A single finding from an approval check.

    Represents one issue or observation found by the sub-agent
    during the approval process.

    Attributes:
        severity: How serious the finding is (error/warning/info)
        check: Name of the check that found this (e.g., "completeness")
        message: Human-readable description of the finding
        location: Optional location in the artifact (section, line, etc.)

    Example:
        >>> finding = Finding(
        ...     severity=Severity.ERROR,
        ...     check="migration",
        ...     message="Migration section missing for major change",
        ...     location="YAML header: change_scope",
        ... )
    """
    severity: Severity
    check: str
    message: str
    location: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation of the finding
        """
        return {
            "severity": self.severity.value,
            "check": self.check,
            "message": self.message,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        """Create Finding from dictionary.

        Args:
            data: Dict with finding data

        Returns:
            Finding instance
        """
        return cls(
            severity=Severity(data["severity"]),
            check=data["check"],
            message=data["message"],
            location=data.get("location"),
        )

    def __str__(self) -> str:
        """Format finding for display."""
        severity_icon = {
            Severity.ERROR: "❌",
            Severity.WARNING: "⚠️",
            Severity.INFO: "ℹ️",
        }.get(self.severity, "•")

        if self.location:
            return f"{severity_icon} [{self.check}] {self.message} (in {self.location})"
        return f"{severity_icon} [{self.check}] {self.message}"


@dataclass
class ApprovalResult:
    """Result of an approval check.

    Contains the complete result of a sub-agent approval run,
    including the decision, confidence, all findings, and metadata.

    Attributes:
        approval_id: Unique identifier for this approval run
        approval_type: Type of approval (e.g., "adr", "code")
        result: Decision string ("approved", "rejected", "needs_revision")
        confidence: Confidence in the decision (0.0 to 1.0)
        findings: List of all findings from all checks
        recommendations: List of improvement suggestions
        timestamp: When the approval was completed
        duration_seconds: How long the approval took
        tokens_used: Number of tokens used (for cost tracking)

    Example:
        >>> result = ApprovalResult(
        ...     approval_id="abc123",
        ...     approval_type="adr",
        ...     result="approved",
        ...     confidence=0.95,
        ... )
        >>> if result.approved:
        ...     print("Approved!")
    """
    approval_id: str
    approval_type: str
    result: str  # "approved", "rejected", "needs_revision"
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    tokens_used: int = 0

    @property
    def approved(self) -> bool:
        """Check if the result is approved.

        Returns:
            True if result is "approved"
        """
        return self.result == "approved"

    @property
    def rejected(self) -> bool:
        """Check if the result is rejected.

        Returns:
            True if result is "rejected"
        """
        return self.result == "rejected"

    @property
    def needs_revision(self) -> bool:
        """Check if revision is needed.

        Returns:
            True if result is "needs_revision"
        """
        return self.result == "needs_revision"

    @property
    def errors(self) -> list[Finding]:
        """Get all error-level findings.

        Returns:
            List of findings with ERROR severity
        """
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        """Get all warning-level findings.

        Returns:
            List of findings with WARNING severity
        """
        return [f for f in self.findings if f.severity == Severity.WARNING]

    @property
    def infos(self) -> list[Finding]:
        """Get all info-level findings.

        Returns:
            List of findings with INFO severity
        """
        return [f for f in self.findings if f.severity == Severity.INFO]

    @property
    def error_count(self) -> int:
        """Number of errors found."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings found."""
        return len(self.warnings)

    @property
    def summary(self) -> str:
        """Generate a summary message.

        Returns:
            Human-readable summary of the approval result
        """
        result_text = {
            "approved": "✅ Approved",
            "rejected": "❌ Rejected",
            "needs_revision": "⚠️ Needs Revision",
        }.get(self.result, self.result)

        return (
            f"{result_text} (confidence: {self.confidence:.0%}) - "
            f"{self.error_count} errors, {self.warning_count} warnings"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation of the approval result
        """
        return {
            "approval_id": self.approval_id,
            "approval_type": self.approval_type,
            "result": self.result,
            "confidence": self.confidence,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "agent_context": {
                "duration_seconds": self.duration_seconds,
                "tokens_used": self.tokens_used,
            },
        }

    @classmethod
    def from_dict(
        cls,
        approval_id: str,
        approval_type: str,
        data: dict[str, Any],
    ) -> "ApprovalResult":
        """Create from dictionary (parsed from agent output).

        This is used to parse the JSON output from a sub-agent
        back into an ApprovalResult object.

        Args:
            approval_id: Unique ID for this approval run
            approval_type: Type of approval
            data: Dict parsed from sub-agent's JSON output

        Returns:
            ApprovalResult instance
        """
        findings = [
            Finding.from_dict(f)
            for f in data.get("findings", [])
        ]

        agent_context = data.get("agent_context", {})

        return cls(
            approval_id=approval_id,
            approval_type=approval_type,
            result=data.get("result", "rejected"),
            confidence=data.get("confidence", 0.0),
            findings=findings,
            recommendations=data.get("recommendations", []),
            duration_seconds=agent_context.get("duration_seconds", 0.0),
            tokens_used=agent_context.get("tokens_used", 0),
        )

    def __str__(self) -> str:
        """Format result for display."""
        lines = [self.summary, ""]

        if self.errors:
            lines.append("Errors:")
            for finding in self.errors:
                lines.append(f"  {finding}")
            lines.append("")

        if self.warnings:
            lines.append("Warnings:")
            for finding in self.warnings:
                lines.append(f"  {finding}")
            lines.append("")

        if self.recommendations:
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  • {rec}")

        return "\n".join(lines)


# JSON Schema for approval-result.json (for validation)
APPROVAL_RESULT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["result", "confidence", "findings"],
    "properties": {
        "result": {
            "type": "string",
            "enum": ["approved", "rejected", "needs_revision"],
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "check", "message"],
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["error", "warning", "info"],
                    },
                    "check": {"type": "string"},
                    "message": {"type": "string"},
                    "location": {"type": "string"},
                },
            },
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "agent_context": {
            "type": "object",
            "properties": {
                "duration_seconds": {"type": "number"},
                "tokens_used": {"type": "integer"},
            },
        },
    },
}
