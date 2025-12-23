"""Approval System for HELIX v4.

This package provides the Sub-Agent approval system for independent
validation of artifacts like ADRs, code, and documentation.

The approval system spawns independent Claude Code instances (sub-agents)
with fresh context to perform unbiased validation checks.

Modules:
    result: ApprovalResult and Finding data classes
    runner: ApprovalRunner for spawning sub-agents

Example:
    >>> from helix.approval import ApprovalRunner, ApprovalResult
    >>> from pathlib import Path
    >>>
    >>> runner = ApprovalRunner()
    >>> result = await runner.run_approval(
    ...     approval_type="adr",
    ...     input_files=[Path("output/ADR-feature.md")],
    ... )
    >>> if result.approved:
    ...     print("ADR approved!")
    ... else:
    ...     for finding in result.errors:
    ...         print(f"Error: {finding.message}")

See Also:
    - ADR-015: Approval & Validation System
    - approvals/adr/CLAUDE.md: Sub-Agent instructions for ADR approval
"""

from helix.approval.result import (
    ApprovalResult,
    Finding,
    Severity,
    ApprovalDecision,
)

from helix.approval.runner import (
    ApprovalRunner,
    ApprovalConfig,
)

__all__ = [
    # Main classes
    "ApprovalRunner",
    "ApprovalConfig",
    "ApprovalResult",
    # Supporting classes
    "Finding",
    "Severity",
    "ApprovalDecision",
]
