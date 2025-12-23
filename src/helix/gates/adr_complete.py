"""Complete ADR Validation Gate for HELIX v4.

Implements the `adr_complete` quality gate that runs all validation layers:

- Layer 1: Structural Validation (YAML header, sections)
- Layer 2: Contextual Rules (CompletenessValidator)
- Layer 3: Concept Diff (ConceptDiffer)
- Layer 4: Sub-Agent Approval (ApprovalRunner) - optional, for major+proposed

This gate provides a comprehensive ADR validation that goes beyond simple
template checks to ensure ADRs are complete, consistent, and ready for
implementation.

Example:
    >>> from helix.gates.adr_complete import check_adr_complete
    >>> from pathlib import Path
    >>>
    >>> result = await check_adr_complete(
    ...     phase_dir=Path("projects/sessions/feature/"),
    ...     gate_config={
    ...         "file": "output/ADR-*.md",
    ...         "concept": "output/concept.md",
    ...         "semantic": "auto",  # Run sub-agent only for major+proposed
    ...     },
    ... )
    >>> if not result.passed:
    ...     for issue in result.issues:
    ...         print(issue)

See Also:
    - ADR-015: Approval & Validation System
    - helix.adr.completeness: CompletenessValidator
    - helix.adr.concept_diff: ConceptDiffer
    - helix.approval.runner: ApprovalRunner
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import glob

from helix.quality_gates import GateResult
from helix.adr.parser import ADRParser, ADRDocument
from helix.adr.completeness import CompletenessValidator, CompletenessResult
from helix.adr.concept_diff import ConceptDiffer, ConceptDiffResult
from helix.approval.runner import ApprovalRunner, ApprovalConfig
from helix.approval.result import ApprovalResult


@dataclass
class ADRCompleteResult:
    """Result of complete ADR validation.

    Aggregates results from all validation layers.

    Attributes:
        passed: True if no blocking issues found
        adr_path: Path to the validated ADR file
        structural_valid: Layer 1 result
        completeness_result: Layer 2 result (CompletenessResult)
        concept_diff_result: Layer 3 result (ConceptDiffResult or None)
        approval_result: Layer 4 result (ApprovalResult or None)
        issues: Aggregated list of all issues
        warnings: Aggregated list of all warnings
    """
    passed: bool
    adr_path: Path
    structural_valid: bool = True
    completeness_result: Optional[CompletenessResult] = None
    concept_diff_result: Optional[ConceptDiffResult] = None
    approval_result: Optional[ApprovalResult] = None
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_gate_result(self, gate_type: str = "adr_complete") -> GateResult:
        """Convert to standard GateResult.

        Args:
            gate_type: Gate type identifier

        Returns:
            GateResult for QualityGateRunner
        """
        return GateResult(
            passed=self.passed,
            gate_type=gate_type,
            message=self._build_message(),
            details=self._build_details(),
        )

    def _build_message(self) -> str:
        """Build summary message."""
        if self.passed:
            layers_run = self._count_layers_run()
            return f"ADR validation passed ({layers_run} layers checked)"
        else:
            return f"ADR validation failed: {len(self.issues)} issue(s)"

    def _count_layers_run(self) -> int:
        """Count how many layers were executed."""
        count = 1  # Layer 1 always runs
        if self.completeness_result:
            count += 1
        if self.concept_diff_result:
            count += 1
        if self.approval_result:
            count += 1
        return count

    def _build_details(self) -> dict[str, Any]:
        """Build details dictionary."""
        details: dict[str, Any] = {
            "adr_path": str(self.adr_path),
            "structural_valid": self.structural_valid,
            "issues": self.issues,
            "warnings": self.warnings,
        }

        if self.completeness_result:
            details["completeness"] = {
                "passed": self.completeness_result.passed,
                "rules_triggered": self.completeness_result.rules_triggered,
                "rules_passed": self.completeness_result.rules_passed,
            }

        if self.concept_diff_result:
            details["concept_diff"] = {
                "coverage_percent": self.concept_diff_result.coverage_percent,
                "missing_sections": self.concept_diff_result.missing_in_adr,
            }

        if self.approval_result:
            details["approval"] = {
                "result": self.approval_result.result,
                "confidence": self.approval_result.confidence,
                "error_count": self.approval_result.error_count,
                "warning_count": self.approval_result.warning_count,
            }

        return details


async def check_adr_complete(
    phase_dir: Path,
    gate_config: dict[str, Any],
) -> GateResult:
    """Complete ADR validation with optional sub-agent.

    Runs all ADR validation layers in sequence:

    1. Find and parse ADR file
    2. Run CompletenessValidator (Layer 2)
    3. Run ConceptDiffer if concept provided (Layer 3)
    4. If major+proposed and no errors: run ApprovalRunner (Layer 4)
    5. Combine and return results

    Args:
        phase_dir: Path to the phase directory
        gate_config: Configuration dict with:
            - file: Glob pattern for ADR file (required)
            - concept: Path to concept file (optional)
            - semantic: "auto" | "true" | "false" (default: "auto")
            - rules_path: Path to completeness rules (optional)

    Returns:
        GateResult indicating pass/fail with details

    Example:
        >>> result = await check_adr_complete(
        ...     phase_dir=Path("phases/01-consultant"),
        ...     gate_config={
        ...         "file": "output/ADR-*.md",
        ...         "concept": "output/concept.md",
        ...         "semantic": "auto",
        ...     },
        ... )
    """
    # Extract configuration
    file_pattern = gate_config.get("file", "output/ADR-*.md")
    concept_path_str = gate_config.get("concept")
    semantic_mode = gate_config.get("semantic", "auto")
    rules_path_str = gate_config.get("rules_path")

    issues: list[str] = []
    warnings: list[str] = []

    # Step 1: Find and parse ADR file
    adr_path = _find_adr_file(phase_dir, file_pattern)
    if not adr_path:
        return GateResult(
            passed=False,
            gate_type="adr_complete",
            message=f"No ADR file found matching pattern: {file_pattern}",
            details={"pattern": file_pattern, "phase_dir": str(phase_dir)},
        )

    # Parse ADR
    parser = ADRParser()
    try:
        adr = parser.parse_file(adr_path)
    except Exception as e:
        return GateResult(
            passed=False,
            gate_type="adr_complete",
            message=f"Failed to parse ADR: {e}",
            details={"adr_path": str(adr_path), "error": str(e)},
        )

    # Layer 1: Basic structural validation (done by parser)
    structural_valid = True
    if not adr.metadata.adr_id:
        issues.append("Layer 1: Missing ADR ID in YAML header")
        structural_valid = False
    if not adr.metadata.title:
        issues.append("Layer 1: Missing title in YAML header")
        structural_valid = False
    if not adr.metadata.status:
        issues.append("Layer 1: Missing status in YAML header")
        structural_valid = False

    # Step 2: Run CompletenessValidator (Layer 2)
    rules_path = Path(rules_path_str) if rules_path_str else None
    completeness_validator = CompletenessValidator(rules_path=rules_path)
    completeness_result = completeness_validator.check(adr)

    if not completeness_result.passed:
        for issue in completeness_result.issues:
            level = getattr(issue, 'level', 'error')
            if hasattr(level, 'value'):
                level = level.value
            if level == "error":
                issues.append(f"Layer 2: {issue.message}")
            else:
                warnings.append(f"Layer 2: {issue.message}")

    # Step 3: Run ConceptDiffer if concept provided (Layer 3)
    concept_diff_result = None
    if concept_path_str:
        concept_path = phase_dir / concept_path_str
        differ = ConceptDiffer()
        concept_diff_result = differ.compare(concept_path, adr)

        if concept_diff_result.has_missing_sections:
            for missing in concept_diff_result.missing_in_adr:
                issues.append(f"Layer 3: Section from concept missing in ADR: {missing}")

        for warning in concept_diff_result.warnings:
            warnings.append(f"Layer 3: {warning}")

    # Step 4: Decide if Layer 4 (Sub-Agent) should run
    approval_result = None
    should_run_approval = _should_run_approval(
        adr=adr,
        semantic_mode=semantic_mode,
        has_errors=len(issues) > 0,
    )

    if should_run_approval:
        approval_result = await _run_approval(adr_path)

        if approval_result.rejected:
            for finding in approval_result.errors:
                issues.append(f"Layer 4: {finding.message}")
            for finding in approval_result.warnings:
                warnings.append(f"Layer 4: {finding.message}")
        elif approval_result.needs_revision:
            for finding in approval_result.warnings:
                warnings.append(f"Layer 4: {finding.message}")

    # Build result
    passed = len(issues) == 0

    result = ADRCompleteResult(
        passed=passed,
        adr_path=adr_path,
        structural_valid=structural_valid,
        completeness_result=completeness_result,
        concept_diff_result=concept_diff_result,
        approval_result=approval_result,
        issues=issues,
        warnings=warnings,
    )

    return result.to_gate_result()


def _find_adr_file(phase_dir: Path, pattern: str) -> Optional[Path]:
    """Find ADR file matching pattern.

    Args:
        phase_dir: Phase directory to search in
        pattern: Glob pattern (e.g., "output/ADR-*.md")

    Returns:
        Path to first matching file, or None
    """
    full_pattern = str(phase_dir / pattern)
    matches = glob.glob(full_pattern)

    if not matches:
        return None

    # Return first match (sorted for determinism)
    matches.sort()
    return Path(matches[0])


def _should_run_approval(
    adr: ADRDocument,
    semantic_mode: str,
    has_errors: bool,
) -> bool:
    """Determine if Layer 4 approval should run.

    Args:
        adr: Parsed ADR document
        semantic_mode: "auto" | "true" | "false"
        has_errors: Whether earlier layers found errors

    Returns:
        True if approval should run
    """
    # Never run if explicitly disabled
    if semantic_mode == "false":
        return False

    # Always run if explicitly enabled
    if semantic_mode == "true":
        return True

    # Auto mode: run only for major+proposed without errors
    if semantic_mode == "auto":
        if has_errors:
            return False  # Don't waste tokens if already failing

        # Check change_scope
        change_scope = getattr(adr.metadata, 'change_scope', None)
        if hasattr(change_scope, 'value'):
            change_scope = change_scope.value

        # Check status
        status = getattr(adr.metadata, 'status', None)
        if hasattr(status, 'value'):
            status = status.value

        is_major = change_scope == "major"
        is_proposed = status and status.lower() == "proposed"

        return is_major and is_proposed

    return False


async def _run_approval(adr_path: Path) -> ApprovalResult:
    """Run the approval sub-agent.

    Args:
        adr_path: Path to ADR file

    Returns:
        ApprovalResult from sub-agent
    """
    runner = ApprovalRunner()
    config = ApprovalConfig(
        approval_type="adr",
        timeout=300,
        required_confidence=0.8,
    )

    return await runner.run_approval(
        approval_type="adr",
        input_files=[adr_path],
        config=config,
    )
