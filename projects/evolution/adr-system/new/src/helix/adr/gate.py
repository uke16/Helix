"""ADR Quality Gate for HELIX v4.

This module provides quality gate integration for ADR validation.
It integrates the ADRValidator with the QualityGateRunner system,
allowing ADR validation to be used as a quality gate in phases.yaml.

IMPORTANT: This module is placed in helix.adr.gate rather than
helix.quality_gates.adr_gate because src/helix/quality_gates.py
exists as a module file. Python cannot have both quality_gates.py
and quality_gates/ directory in the same package.

Example phases.yaml:
    quality_gate:
      type: adr_valid
      file: adr/086-new-feature.md

Example usage:
    >>> from helix.adr.gate import ADRQualityGate
    >>> gate = ADRQualityGate()
    >>> result = gate.check(Path("/project/phases/01"), "adr/086-feature.md")
    >>> if not result.passed:
    ...     print(f"Gate failed: {result.message}")

See Also:
    - helix.quality_gates: Main quality gate system
    - helix.adr.validator: ADR validation logic
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from helix.adr.parser import ADRParser
from helix.adr.validator import (
    ADRValidator,
    ValidationResult,
    IssueLevel,
)
from helix.quality_gates import GateResult, QualityGateRunner

if TYPE_CHECKING:
    pass


class ADRQualityGate:
    """Quality gate for ADR validation.

    Integrates ADR validation with the HELIX quality gate system.
    Can be used as a gate type in phases.yaml.

    The gate validates ADR files against the ADR-086 template requirements:
    - Required YAML header fields (adr_id, title, status)
    - Required markdown sections (Kontext, Entscheidung, Implementation, etc.)
    - Acceptance criteria checkboxes
    - Consistency between header and body

    Attributes:
        parser: ADRParser instance for parsing ADR files
        validator: ADRValidator instance for validation

    Example phases.yaml:
        # Validate single ADR file
        quality_gate:
          type: adr_valid
          file: adr/086-new-feature.md

        # Validate multiple ADR files
        quality_gate:
          type: adr_valid
          files:
            - adr/086-new-feature.md
            - adr/087-other-feature.md

    Example usage:
        >>> gate = ADRQualityGate()
        >>> result = gate.check(
        ...     phase_dir=Path("/project/phases/01"),
        ...     adr_file="adr/086-feature.md"
        ... )
        >>> if result.passed:
        ...     print("ADR is valid!")
        >>> else:
        ...     print(f"Validation failed: {result.message}")
        ...     for error in result.details.get("errors", []):
        ...         print(f"  - {error}")
    """

    def __init__(
        self,
        parser: Optional[ADRParser] = None,
        validator: Optional[ADRValidator] = None
    ):
        """Initialize ADR quality gate.

        Args:
            parser: Custom ADRParser instance (creates new one if not provided)
            validator: Custom ADRValidator instance (creates new one if not provided)
        """
        self.parser = parser or ADRParser()
        self.validator = validator or ADRValidator(self.parser)

    def check(self, phase_dir: Path, adr_file: str) -> GateResult:
        """Check if an ADR file is valid.

        Validates a single ADR file against the template requirements.

        Args:
            phase_dir: Base directory for resolving relative paths.
            adr_file: Path to ADR file (relative to phase_dir or absolute).

        Returns:
            GateResult with pass/fail status and validation details.

        Example:
            >>> result = gate.check(Path("/project"), "adr/001.md")
            >>> print(f"Passed: {result.passed}")
            >>> print(f"Message: {result.message}")
        """
        # Resolve file path
        adr_path = Path(adr_file)
        if not adr_path.is_absolute():
            adr_path = phase_dir / adr_file

        # Validate the ADR
        validation_result = self.validator.validate_file(adr_path)

        return self._create_gate_result(validation_result, [str(adr_path)])

    def check_multiple(self, phase_dir: Path, adr_files: list[str]) -> GateResult:
        """Validate multiple ADR files.

        Validates all specified ADR files. The gate passes only if ALL
        ADRs are valid (no errors). Warnings do not cause failure.

        Args:
            phase_dir: Base directory for resolving relative paths.
            adr_files: List of ADR file paths (relative or absolute).

        Returns:
            GateResult that passes only if ALL ADRs are valid.

        Example:
            >>> result = gate.check_multiple(
            ...     Path("/project"),
            ...     ["adr/001.md", "adr/002.md"]
            ... )
            >>> if not result.passed:
            ...     for file_result in result.details.get("file_results", []):
            ...         print(f"{file_result['file']}: {file_result['status']}")
        """
        if not adr_files:
            return GateResult(
                passed=True,
                gate_type="adr_valid",
                message="No ADR files to validate",
                details={"files_checked": 0},
            )

        all_errors: list[str] = []
        all_warnings: list[str] = []
        file_results: list[dict] = []
        all_valid = True

        for adr_file in adr_files:
            # Resolve file path
            adr_path = Path(adr_file)
            if not adr_path.is_absolute():
                adr_path = phase_dir / adr_file

            # Validate the ADR
            validation_result = self.validator.validate_file(adr_path)

            # Collect results
            file_status = "valid" if validation_result.valid else "invalid"
            file_errors = [
                f"{adr_file}: {issue.message}"
                for issue in validation_result.issues
                if issue.level == IssueLevel.ERROR
            ]
            file_warnings = [
                f"{adr_file}: {issue.message}"
                for issue in validation_result.issues
                if issue.level == IssueLevel.WARNING
            ]

            all_errors.extend(file_errors)
            all_warnings.extend(file_warnings)

            file_results.append({
                "file": str(adr_path),
                "status": file_status,
                "error_count": validation_result.error_count,
                "warning_count": validation_result.warning_count,
            })

            if not validation_result.valid:
                all_valid = False

        # Build result
        if all_valid:
            message = f"All {len(adr_files)} ADR file(s) are valid"
            if all_warnings:
                message += f" ({len(all_warnings)} warning(s))"
        else:
            invalid_count = sum(1 for fr in file_results if fr["status"] == "invalid")
            message = f"Validation failed for {invalid_count} of {len(adr_files)} ADR file(s)"

        return GateResult(
            passed=all_valid,
            gate_type="adr_valid",
            message=message,
            details={
                "files_checked": len(adr_files),
                "valid_count": sum(1 for fr in file_results if fr["status"] == "valid"),
                "invalid_count": sum(1 for fr in file_results if fr["status"] == "invalid"),
                "total_errors": len(all_errors),
                "total_warnings": len(all_warnings),
                "errors": all_errors,
                "warnings": all_warnings,
                "file_results": file_results,
            },
        )

    def _create_gate_result(
        self,
        validation_result: ValidationResult,
        files_checked: list[str]
    ) -> GateResult:
        """Create GateResult from ValidationResult.

        Args:
            validation_result: Result from ADRValidator
            files_checked: List of file paths that were validated

        Returns:
            GateResult for the quality gate system
        """
        errors = [
            issue.message
            for issue in validation_result.issues
            if issue.level == IssueLevel.ERROR
        ]
        warnings = [
            issue.message
            for issue in validation_result.issues
            if issue.level == IssueLevel.WARNING
        ]

        if validation_result.valid:
            message = "ADR validation passed"
            if warnings:
                message += f" ({len(warnings)} warning(s))"
        else:
            message = f"ADR validation failed with {len(errors)} error(s)"

        # Include ADR metadata in details if available
        adr_info = {}
        if validation_result.adr:
            adr_info = {
                "adr_id": validation_result.adr.metadata.adr_id,
                "title": validation_result.adr.metadata.title,
                "status": validation_result.adr.metadata.status.value,
            }

        return GateResult(
            passed=validation_result.valid,
            gate_type="adr_valid",
            message=message,
            details={
                "files_checked": files_checked,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "errors": errors,
                "warnings": warnings,
                "adr_info": adr_info,
            },
        )


def register_adr_gate(runner: QualityGateRunner) -> None:
    """Register the ADR quality gate with a QualityGateRunner.

    This function is provided for explicit registration of the ADR gate.
    It patches the runner's run_gate method to support the 'adr_valid' gate type.

    Note: The preferred way to add gate support is to modify the
    QualityGateRunner.run_gate() method directly. This function provides
    an alternative for cases where modifying quality_gates.py is not desired.

    Args:
        runner: QualityGateRunner instance to register the gate with

    Example:
        >>> from helix.quality_gates import QualityGateRunner
        >>> from helix.adr.gate import register_adr_gate
        >>> runner = QualityGateRunner()
        >>> register_adr_gate(runner)
        >>> # Now runner supports 'adr_valid' gate type
    """
    original_run_gate = runner.run_gate

    async def extended_run_gate(phase_dir: Path, gate_config: dict) -> GateResult:
        """Extended run_gate that supports adr_valid gate type."""
        gate_type = gate_config.get("type")

        if gate_type == "adr_valid":
            adr_gate = ADRQualityGate()
            adr_file = gate_config.get("file")

            if adr_file:
                return adr_gate.check(phase_dir, adr_file)
            else:
                adr_files = gate_config.get("files", [])
                return adr_gate.check_multiple(phase_dir, adr_files)

        # Delegate to original implementation for other gate types
        return await original_run_gate(phase_dir, gate_config)

    runner.run_gate = extended_run_gate
