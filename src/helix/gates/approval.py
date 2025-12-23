"""Generic Approval Gate for HELIX v4.

Implements the `approval` quality gate that spawns a sub-agent for
validation. This is a general-purpose gate that can be used for any
approval type (adr, code, docs, security, etc.).

The gate delegates to the ApprovalRunner which:
1. Prepares the approval directory
2. Spawns a Claude Code sub-agent
3. Parses the result from the sub-agent output

Example:
    >>> from helix.gates.approval import check_approval
    >>> from pathlib import Path
    >>>
    >>> result = await check_approval(
    ...     phase_dir=Path("projects/sessions/feature/"),
    ...     gate_config={
    ...         "approval_type": "code",
    ...         "input": ["output/src/**.py"],
    ...         "timeout": 600,
    ...     },
    ... )
    >>> if not result.passed:
    ...     print(f"Approval failed: {result.message}")

See Also:
    - ADR-015: Approval & Validation System
    - helix.approval.runner: ApprovalRunner
    - approvals/: Approval type definitions
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import glob

from helix.quality_gates import GateResult
from helix.approval.runner import ApprovalRunner, ApprovalConfig
from helix.approval.result import ApprovalResult, Severity


@dataclass
class ApprovalGateResult:
    """Result of an approval gate check.

    Wraps the ApprovalResult with additional gate-specific information.

    Attributes:
        passed: True if approval passed (approved or needs_revision with no errors)
        approval_type: Type of approval (e.g., "adr", "code")
        approval_result: The underlying ApprovalResult
        input_files: Files that were checked
        gate_message: Summary message for the gate
    """
    passed: bool
    approval_type: str
    approval_result: Optional[ApprovalResult] = None
    input_files: list[Path] = field(default_factory=list)
    gate_message: str = ""

    def to_gate_result(self) -> GateResult:
        """Convert to standard GateResult.

        Returns:
            GateResult for QualityGateRunner
        """
        details: dict[str, Any] = {
            "approval_type": self.approval_type,
            "input_files": [str(f) for f in self.input_files],
        }

        if self.approval_result:
            details["result"] = self.approval_result.result
            details["confidence"] = self.approval_result.confidence
            details["errors"] = self.approval_result.error_count
            details["warnings"] = self.approval_result.warning_count
            details["duration_seconds"] = self.approval_result.duration_seconds

            if self.approval_result.findings:
                details["findings"] = [
                    f.to_dict() for f in self.approval_result.findings
                ]

            if self.approval_result.recommendations:
                details["recommendations"] = self.approval_result.recommendations

        return GateResult(
            passed=self.passed,
            gate_type="approval",
            message=self.gate_message,
            details=details,
        )


async def check_approval(
    phase_dir: Path,
    gate_config: dict[str, Any],
) -> GateResult:
    """Run sub-agent approval check.

    Spawns a Claude Code sub-agent to perform independent validation
    of the specified artifacts.

    Args:
        phase_dir: Path to the phase directory
        gate_config: Configuration dict with:
            - approval_type: Type of approval (required)
            - input: List of file patterns to check (optional, defaults to ["output/**"])
            - timeout: Timeout in seconds (optional, default: 300)
            - model: Model to use (optional)
            - required_confidence: Minimum confidence (optional, default: 0.8)
            - strict: If True, needs_revision is also a failure (optional, default: False)

    Returns:
        GateResult indicating pass/fail with details

    Example:
        >>> result = await check_approval(
        ...     phase_dir=Path("phases/02-development"),
        ...     gate_config={
        ...         "approval_type": "code",
        ...         "input": ["output/src/**/*.py"],
        ...         "timeout": 600,
        ...     },
        ... )
    """
    # Extract configuration
    approval_type = gate_config.get("approval_type")
    if not approval_type:
        return GateResult(
            passed=False,
            gate_type="approval",
            message="Missing required 'approval_type' in gate config",
            details={"config": gate_config},
        )

    input_patterns = gate_config.get("input", ["output/**"])
    timeout = gate_config.get("timeout", 300)
    model = gate_config.get("model", "claude-sonnet-4-20250514")
    required_confidence = gate_config.get("required_confidence", 0.8)
    strict = gate_config.get("strict", False)

    # Find input files
    input_files = _find_input_files(phase_dir, input_patterns)
    if not input_files:
        return GateResult(
            passed=False,
            gate_type="approval",
            message=f"No input files found matching patterns: {input_patterns}",
            details={
                "approval_type": approval_type,
                "patterns": input_patterns,
                "phase_dir": str(phase_dir),
            },
        )

    # Build config
    config = ApprovalConfig(
        approval_type=approval_type,
        model=model,
        timeout=timeout,
        required_confidence=required_confidence,
    )

    # Run approval
    runner = ApprovalRunner()
    approval_result = await runner.run_approval(
        approval_type=approval_type,
        input_files=input_files,
        config=config,
    )

    # Determine pass/fail
    passed = _determine_pass(approval_result, strict)

    # Build message
    if passed:
        gate_message = f"Approval passed: {approval_result.result} (confidence: {approval_result.confidence:.0%})"
    else:
        gate_message = f"Approval failed: {approval_result.result} - {approval_result.error_count} errors"

    result = ApprovalGateResult(
        passed=passed,
        approval_type=approval_type,
        approval_result=approval_result,
        input_files=input_files,
        gate_message=gate_message,
    )

    return result.to_gate_result()


def _find_input_files(phase_dir: Path, patterns: list[str]) -> list[Path]:
    """Find all files matching input patterns.

    Args:
        phase_dir: Phase directory
        patterns: List of glob patterns

    Returns:
        List of matching file paths
    """
    files: list[Path] = []

    for pattern in patterns:
        full_pattern = str(phase_dir / pattern)
        matches = glob.glob(full_pattern, recursive=True)

        for match in matches:
            path = Path(match)
            if path.is_file() and path not in files:
                files.append(path)

    # Sort for deterministic ordering
    files.sort()
    return files


def _determine_pass(result: ApprovalResult, strict: bool) -> bool:
    """Determine if the approval passes.

    Args:
        result: ApprovalResult from sub-agent
        strict: If True, needs_revision is also a failure

    Returns:
        True if approval passes
    """
    if result.approved:
        return True

    if result.rejected:
        return False

    # needs_revision
    if strict:
        return False

    # In non-strict mode, needs_revision passes if no errors
    return result.error_count == 0
