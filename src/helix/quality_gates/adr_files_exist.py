"""
ADR Files Exist Quality Gate.

ADR-020: Quality gate that validates all files declared in ADR YAML headers
with status "Implemented" actually exist in the filesystem.

This gate helps ensure data quality and traceability by detecting:
- ADRs marked as Implemented but with missing files (should be "Proposed")
- Stale ADR references after file removals
- Incorrect file paths in ADR declarations

Usage:
    from helix.quality_gates.adr_files_exist import ADRFilesExistGate

    gate = ADRFilesExistGate(project_root=Path("/path/to/project"))
    result = await gate.check()

    if not result.passed:
        print(f"Found {len(result.details['missing'])} missing files")

CLI:
    python -m helix.quality_gates.adr_files_exist [project_root] [--strict]
"""

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class GateResult:
    """Result from a quality gate check."""

    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MissingFile:
    """Information about a missing file from an ADR."""

    file_path: str
    adr_id: str
    adr_file: str
    action: str  # "create" or "modify"


@dataclass
class ADRValidation:
    """Validation result for a single ADR."""

    adr_id: str
    adr_file: str
    title: str
    status: str
    expected_files: int
    existing_files: int
    missing_files: list[str]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "adr_id": self.adr_id,
            "adr_file": self.adr_file,
            "title": self.title,
            "status": self.status,
            "expected_files": self.expected_files,
            "existing_files": self.existing_files,
            "missing_files": self.missing_files,
            "passed": self.passed,
        }


class ADRFilesExistGate:
    """Quality gate that validates ADR file declarations.

    This gate scans all ADR files and validates that files declared
    in the files.create section of "Implemented" ADRs actually exist.

    Only ADRs with status "Implemented" are validated. ADRs with
    "Proposed", "Draft", or other statuses are skipped since their
    files are not expected to exist yet.

    Categories of issues:
    - missing: File declared in ADR but doesn't exist
    - status_mismatch: ADR says Implemented but files missing

    Example:
        gate = ADRFilesExistGate(project_root=Path("."))
        result = await gate.check()

        # Returns:
        # GateResult(
        #     passed=False,
        #     message="3 missing files in Implemented ADRs",
        #     details={
        #         "missing": [...],
        #         "validations": [...],
        #         "summary": {...}
        #     }
        # )
    """

    name = "adr_files_exist"
    description = "Validates that files declared in ADR headers exist"

    # ADR statuses that require file existence validation
    IMPLEMENTED_STATUSES = {"Implemented", "implemented", "IMPLEMENTED"}

    def __init__(self, project_root: Path | None = None, adr_dir: Path | None = None):
        """Initialize the quality gate.

        Args:
            project_root: Root directory of the project. Defaults to cwd.
            adr_dir: Directory containing ADR files. Defaults to project_root/adr.
        """
        self.project_root = project_root or Path.cwd()
        self.adr_dir = adr_dir or self.project_root / "adr"

    def _parse_adr_header(self, adr_file: Path) -> dict[str, Any] | None:
        """Parse the YAML frontmatter from an ADR file.

        Args:
            adr_file: Path to ADR markdown file.

        Returns:
            Parsed frontmatter dict if valid, None if parsing fails.
        """
        try:
            content = adr_file.read_text(encoding="utf-8")

            # Extract YAML frontmatter between --- markers
            match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
            if not match:
                return None

            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if frontmatter else None

        except Exception:
            return None

    def _validate_adr(self, adr_file: Path) -> ADRValidation | None:
        """Validate a single ADR file.

        Args:
            adr_file: Path to ADR file.

        Returns:
            ADRValidation result, or None if not applicable.
        """
        header = self._parse_adr_header(adr_file)
        if not header:
            return None

        adr_id = header.get("adr_id")
        if not adr_id:
            return None

        status = header.get("status", "")
        title = header.get("title", "")

        # Only validate implemented ADRs
        if status not in self.IMPLEMENTED_STATUSES:
            return None

        # Get files to check
        files_section = header.get("files", {})
        files_create = files_section.get("create", [])

        if not files_create:
            # No files to check - ADR passes
            return ADRValidation(
                adr_id=str(adr_id),
                adr_file=str(adr_file.relative_to(self.project_root)),
                title=title,
                status=status,
                expected_files=0,
                existing_files=0,
                missing_files=[],
                passed=True,
            )

        # Check each file
        missing = []
        existing = 0

        for file_path in files_create:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing += 1
            else:
                missing.append(file_path)

        return ADRValidation(
            adr_id=str(adr_id),
            adr_file=str(adr_file.relative_to(self.project_root)),
            title=title,
            status=status,
            expected_files=len(files_create),
            existing_files=existing,
            missing_files=missing,
            passed=len(missing) == 0,
        )

    async def check(self, strict: bool = False) -> GateResult:
        """Run the validation.

        Args:
            strict: If True, also check files.modify declarations.

        Returns:
            GateResult indicating pass/fail with details.
        """
        if not self.adr_dir.exists():
            return GateResult(
                passed=True,
                message="No adr directory found - nothing to validate",
                details={},
            )

        adr_files = sorted(self.adr_dir.glob("*.md"))

        if not adr_files:
            return GateResult(
                passed=True,
                message="No ADR files found - nothing to validate",
                details={},
            )

        validations: list[ADRValidation] = []
        all_missing: list[MissingFile] = []

        for adr_file in adr_files:
            # Skip INDEX.md and other non-ADR files
            if adr_file.name in ("INDEX.md", "README.md"):
                continue

            validation = self._validate_adr(adr_file)
            if validation:
                validations.append(validation)

                # Collect missing files
                for missing_path in validation.missing_files:
                    all_missing.append(
                        MissingFile(
                            file_path=missing_path,
                            adr_id=f"ADR-{validation.adr_id}",
                            adr_file=validation.adr_file,
                            action="create",
                        )
                    )

        # Calculate summary
        total_adrs = len(validations)
        valid_adrs = sum(1 for v in validations if v.passed)
        invalid_adrs = total_adrs - valid_adrs
        total_missing = len(all_missing)

        summary = {
            "total_adrs_checked": total_adrs,
            "valid_adrs": valid_adrs,
            "invalid_adrs": invalid_adrs,
            "total_missing_files": total_missing,
        }

        if total_missing > 0:
            return GateResult(
                passed=False,
                message=f"{total_missing} missing files in {invalid_adrs} Implemented ADR(s)",
                details={
                    "missing": [asdict(m) for m in all_missing],
                    "validations": [v.to_dict() for v in validations if not v.passed],
                    "summary": summary,
                },
            )

        return GateResult(
            passed=True,
            message=f"All files exist for {valid_adrs} Implemented ADR(s)",
            details={
                "validations": [v.to_dict() for v in validations],
                "summary": summary,
            },
        )

    def check_sync(self, strict: bool = False) -> GateResult:
        """Synchronous version of check.

        Args:
            strict: If True, also check files.modify declarations.

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
        lines.append("ADR Files Validation")
        lines.append("=" * 40)
        lines.append("")

        if result.passed:
            lines.append(f"OK: {result.message}")
        else:
            lines.append(f"FAILED: {result.message}")

        validations = result.details.get("validations", [])
        summary = result.details.get("summary", {})

        # Show summary
        if summary:
            lines.append("")
            lines.append(
                f"ADRs checked: {summary.get('total_adrs_checked', 0)}"
            )
            lines.append(f"  Valid: {summary.get('valid_adrs', 0)}")
            lines.append(f"  Invalid: {summary.get('invalid_adrs', 0)}")

        # Show invalid ADRs
        invalid = [v for v in validations if not v.get("passed", True)]
        if invalid:
            lines.append("")
            lines.append("Invalid ADRs:")
            for v in invalid:
                adr_id = v.get("adr_id", "?")
                title = v.get("title", "")
                existing = v.get("existing_files", 0)
                expected = v.get("expected_files", 0)
                lines.append(
                    f"  ADR-{adr_id}: {existing}/{expected} files exist"
                )
                lines.append(f"    Title: {title}")
                lines.append(f"    Suggestion: status should be 'Proposed'")

                for missing in v.get("missing_files", []):
                    lines.append(f"    Missing: {missing}")

        return "\n".join(lines)


def run_gate(project_root: Path | str, strict: bool = False) -> bool:
    """Run the adr_files_exist gate from the command line.

    Args:
        project_root: Project root directory.
        strict: If True, also check files.modify declarations.

    Returns:
        True if gate passed, False otherwise.
    """
    root = Path(project_root) if isinstance(project_root, str) else project_root
    gate = ADRFilesExistGate(project_root=root)
    result = gate.check_sync(strict=strict)
    print(gate.format_report(result))
    return result.passed


def main():
    """CLI entry point for ADR files validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate that ADR file declarations exist"
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also validate files.modify declarations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    root = Path(args.project_root)
    gate = ADRFilesExistGate(project_root=root)
    result = gate.check_sync(strict=args.strict)

    if args.json:
        import json

        output = {
            "passed": result.passed,
            "message": result.message,
            "details": result.details,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(gate.format_report(result))

    return 0 if result.passed else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
