"""
Documentation References Valid Quality Gate.

ADR-019: Quality gate that validates all documentation references in
docs/sources/*.yaml files point to existing code symbols, files, and scripts.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from helix.docs.diagram_validator import DiagramValidator
from helix.docs.reference_resolver import ReferenceResolver
from helix.docs.schema import GateResult, ValidationIssue


class DocsRefsValidGate:
    """Quality gate that validates all documentation references.

    This gate scans all YAML files in docs/sources/ and validates that:
    - $ref references point to existing modules, classes, or methods
    - $uses references point to existing methods or functions
    - $file references point to existing files
    - $calls references point to existing scripts
    - Diagram $refs declarations are valid
    """

    name = "docs_refs_valid"
    description = "Validates that all $ref in docs/sources/*.yaml point to existing symbols"

    def __init__(self, project_root: Path):
        """Initialize the quality gate.

        Args:
            project_root: Root directory of the project.
        """
        self.root = project_root
        self.resolver = ReferenceResolver(project_root)
        self.diagram_validator = DiagramValidator(self.resolver)

    async def check(self, strict: bool = False) -> GateResult:
        """Run the validation.

        Args:
            strict: If True, treat warnings as errors.

        Returns:
            GateResult indicating pass/fail with details.
        """
        sources_dir = self.root / "docs" / "sources"
        all_issues: list[ValidationIssue] = []

        if not sources_dir.exists():
            return GateResult(
                passed=True,
                message="No docs/sources directory found - nothing to validate",
                details={},
            )

        yaml_files = list(sources_dir.glob("*.yaml"))
        if not yaml_files:
            return GateResult(
                passed=True,
                message="No YAML files in docs/sources - nothing to validate",
                details={},
            )

        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                if data is None:
                    continue

                # Validate references
                issues = self.resolver.validate_all(data)
                for issue in issues:
                    issue.file = yaml_file
                all_issues.extend(issues)

                # Validate diagrams
                diagrams = data.get("diagrams", [])
                if diagrams:
                    diagram_issues = self.diagram_validator.validate_all(
                        diagrams, yaml_file
                    )
                    all_issues.extend(diagram_issues)

            except yaml.YAMLError as e:
                all_issues.append(
                    ValidationIssue(
                        severity="error",
                        file=yaml_file,
                        path="",
                        ref="",
                        message=f"Invalid YAML: {e}",
                    )
                )
            except Exception as e:
                all_issues.append(
                    ValidationIssue(
                        severity="error",
                        file=yaml_file,
                        path="",
                        ref="",
                        message=f"Error processing file: {e}",
                    )
                )

        errors = [i for i in all_issues if i.severity == "error"]
        warnings = [i for i in all_issues if i.severity == "warning"]

        if errors:
            return GateResult(
                passed=False,
                message=f"Found {len(errors)} broken references",
                details={
                    "errors": [asdict(e) for e in errors],
                    "warnings": [asdict(w) for w in warnings],
                },
            )

        if warnings and strict:
            return GateResult(
                passed=False,
                message=f"Found {len(warnings)} warnings (strict mode)",
                details={"warnings": [asdict(w) for w in warnings]},
            )

        if warnings:
            return GateResult(
                passed=True,
                message=f"All references valid ({len(warnings)} warnings)",
                details={"warnings": [asdict(w) for w in warnings]},
            )

        return GateResult(
            passed=True,
            message="All references valid",
            details={},
        )

    def check_sync(self, strict: bool = False) -> GateResult:
        """Synchronous version of check.

        Args:
            strict: If True, treat warnings as errors.

        Returns:
            GateResult indicating pass/fail with details.
        """
        import asyncio

        return asyncio.run(self.check(strict=strict))

    def format_report(self, result: GateResult) -> str:
        """Format a human-readable report from the gate result.

        Args:
            result: GateResult from check().

        Returns:
            Formatted report string.
        """
        lines = []

        if result.passed:
            lines.append(f"✅ {result.message}")
        else:
            lines.append(f"❌ {result.message}")

        errors = result.details.get("errors", [])
        if errors:
            lines.append("")
            lines.append("ERRORS:")
            for error in errors:
                file_path = error.get("file", "unknown")
                yaml_path = error.get("path", "")
                message = error.get("message", "")
                lines.append(f"  {file_path}:{yaml_path}")
                lines.append(f"    → {message}")

        warnings = result.details.get("warnings", [])
        if warnings:
            lines.append("")
            lines.append(f"WARNINGS ({len(warnings)}):")
            for warning in warnings[:10]:  # Show first 10
                file_path = warning.get("file", "unknown")
                yaml_path = warning.get("path", "")
                message = warning.get("message", "")
                lines.append(f"  {file_path}:{yaml_path}")
                lines.append(f"    → {message}")
            if len(warnings) > 10:
                lines.append(f"  ... and {len(warnings) - 10} more")

        return "\n".join(lines)


def run_gate(project_root: Path | str, strict: bool = False) -> bool:
    """Run the docs_refs_valid gate from the command line.

    Args:
        project_root: Project root directory.
        strict: If True, treat warnings as errors.

    Returns:
        True if gate passed, False otherwise.
    """
    root = Path(project_root) if isinstance(project_root, str) else project_root
    gate = DocsRefsValidGate(root)
    result = gate.check_sync(strict=strict)
    print(gate.format_report(result))
    return result.passed


if __name__ == "__main__":
    import sys

    root = Path(".") if len(sys.argv) < 2 else Path(sys.argv[1])
    strict = "--strict" in sys.argv

    success = run_gate(root, strict=strict)
    sys.exit(0 if success else 1)
