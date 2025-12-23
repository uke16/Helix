"""
Quality Gate: docs_compiled

Validates that generated documentation is up-to-date by comparing
modification timestamps of source files vs. generated output files.

This gate is part of the ADR-014 Documentation Architecture and ensures
that the single-source-of-truth principle is maintained.

Usage in phases.yaml:
    quality_gate:
      type: docs_compiled

Example:
    >>> gate = DocsCompiledGate()
    >>> result = gate.check()
    >>> if not result.passed:
    ...     print(f"Stale docs: {result.stale_files}")
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocsCompiledResult:
    """Result of the docs_compiled quality gate check.

    Attributes:
        passed: Whether all generated docs are up-to-date.
        stale_files: List of files that need regeneration.
        missing_files: List of expected files that don't exist.
        source_hash: Hash of all source files for cache comparison.
        warnings: Non-fatal issues detected.
        errors: Fatal issues that cause gate failure.
    """

    passed: bool
    stale_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    source_hash: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format.

        Returns:
            Dictionary representation of the result.
        """
        return {
            "passed": self.passed,
            "stale_files": self.stale_files,
            "missing_files": self.missing_files,
            "source_hash": self.source_hash,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class DocsCompiledGate:
    """Quality gate that validates generated documentation is up-to-date.

    This gate compares modification timestamps of source files (YAML definitions,
    templates) against generated output files (CLAUDE.md, SKILL.md) to ensure
    the documentation system is in sync.

    Args:
        root: Root directory of the HELIX project. Defaults to current directory.

    Example:
        >>> gate = DocsCompiledGate()
        >>> result = gate.check()
        >>> if result.passed:
        ...     print("Documentation is up to date")
        >>> else:
        ...     print(f"Stale: {result.stale_files}")
        ...     print(f"Missing: {result.missing_files}")
    """

    # Default source and output paths
    DEFAULT_SOURCES = [
        "docs/sources/*.yaml",
        "docs/templates/*.j2",
        "docs/templates/partials/*.j2",
    ]

    DEFAULT_OUTPUTS = [
        "CLAUDE.md",
        "skills/helix/SKILL.md",
    ]

    # Header markers indicating generated files
    GENERATION_MARKERS = [
        "<!-- AUTO-GENERATED",
        "<!-- Template:",
        "<!-- Regenerate:",
    ]

    def __init__(
        self,
        root: Path | None = None,
        sources: list[str] | None = None,
        outputs: list[str] | None = None,
    ):
        """Initialize the DocsCompiledGate.

        Args:
            root: Root directory of the HELIX project.
            sources: Glob patterns for source files.
            outputs: List of expected output file paths.
        """
        self.root = root or Path(".")
        self.source_patterns = sources or self.DEFAULT_SOURCES
        self.output_files = outputs or self.DEFAULT_OUTPUTS

    def check(self) -> DocsCompiledResult:
        """Check if generated documentation is up-to-date.

        Compares modification times and content hashes to determine
        if documentation needs regeneration.

        Returns:
            DocsCompiledResult with validation outcome.
        """
        errors: list[str] = []
        warnings: list[str] = []
        stale_files: list[str] = []
        missing_files: list[str] = []

        # Check source directory exists
        sources_dir = self.root / "docs" / "sources"
        templates_dir = self.root / "docs" / "templates"

        if not sources_dir.exists():
            errors.append(f"Sources directory not found: {sources_dir}")
            return DocsCompiledResult(
                passed=False,
                errors=errors,
            )

        if not templates_dir.exists():
            errors.append(f"Templates directory not found: {templates_dir}")
            return DocsCompiledResult(
                passed=False,
                errors=errors,
            )

        # Get latest modification time of sources
        latest_source_time = self._get_latest_source_time()
        source_hash = self._compute_source_hash()

        if latest_source_time == 0:
            warnings.append("No source files found")

        # Check each output file
        for output_file in self.output_files:
            output_path = self.root / output_file

            if not output_path.exists():
                missing_files.append(output_file)
                continue

            # Check if file is marked as generated
            if not self._is_generated_file(output_path):
                warnings.append(
                    f"{output_file} is not marked as generated (missing header)"
                )

            # Compare modification times
            output_mtime = output_path.stat().st_mtime

            if latest_source_time > output_mtime:
                stale_files.append(output_file)

        # Determine pass/fail
        passed = len(missing_files) == 0 and len(stale_files) == 0

        # Add informative messages
        if stale_files:
            warnings.append(
                f"Stale files detected. Run: python -m helix.tools.docs_compiler compile"
            )

        if missing_files:
            errors.append(
                f"Missing generated files. Run: python -m helix.tools.docs_compiler compile"
            )

        return DocsCompiledResult(
            passed=passed,
            stale_files=stale_files,
            missing_files=missing_files,
            source_hash=source_hash,
            warnings=warnings,
            errors=errors,
        )

    def _get_latest_source_time(self) -> float:
        """Get the latest modification time of all source files.

        Returns:
            Latest modification time as Unix timestamp.
        """
        latest_time = 0.0

        for pattern in self.source_patterns:
            for source_file in self.root.glob(pattern):
                if source_file.is_file():
                    mtime = source_file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime

        return latest_time

    def _compute_source_hash(self) -> str:
        """Compute a hash of all source file contents.

        This hash can be used for cache invalidation and comparison.

        Returns:
            SHA256 hash of concatenated source contents.
        """
        hasher = hashlib.sha256()

        for pattern in self.source_patterns:
            for source_file in sorted(self.root.glob(pattern)):
                if source_file.is_file():
                    try:
                        content = source_file.read_bytes()
                        hasher.update(content)
                    except OSError:
                        pass  # Skip unreadable files

        return hasher.hexdigest()[:16]  # Truncate for readability

    def _is_generated_file(self, file_path: Path) -> bool:
        """Check if a file is marked as auto-generated.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file has generation markers, False otherwise.
        """
        try:
            # Read first few lines
            content = file_path.read_text(encoding="utf-8")
            first_lines = content[:500]

            return any(
                marker in first_lines for marker in self.GENERATION_MARKERS
            )
        except OSError:
            return False

    def validate_content(self, file_path: Path) -> list[str]:
        """Validate the content of a generated file.

        Checks for common issues like broken links, empty sections, etc.

        Args:
            file_path: Path to the file to validate.

        Returns:
            List of validation warnings.
        """
        warnings: list[str] = []

        if not file_path.exists():
            return [f"File does not exist: {file_path}"]

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            return [f"Cannot read file: {e}"]

        # Check for unrendered Jinja2 syntax
        if "{{" in content or "{%" in content or "{#" in content:
            warnings.append(f"{file_path.name}: Contains unrendered Jinja2 syntax")

        # Check for empty sections
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("## ") and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line == "" or next_line.startswith("#"):
                    warnings.append(
                        f"{file_path.name}: Empty section at line {i + 1}: {line}"
                    )

        # Check for broken internal links
        import re
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(link_pattern, content):
            link_text, link_url = match.groups()
            # Check relative links
            if not link_url.startswith(("http://", "https://", "#")):
                link_path = file_path.parent / link_url
                if not link_path.exists():
                    warnings.append(
                        f"{file_path.name}: Broken link to {link_url}"
                    )

        return warnings


def check_docs_compiled(
    root: Path | None = None,
    sources: list[str] | None = None,
    outputs: list[str] | None = None,
) -> DocsCompiledResult:
    """Convenience function to run the docs_compiled gate.

    Args:
        root: Root directory of the HELIX project.
        sources: Glob patterns for source files.
        outputs: List of expected output file paths.

    Returns:
        DocsCompiledResult with validation outcome.

    Example:
        >>> result = check_docs_compiled()
        >>> if not result.passed:
        ...     print("Run: python -m helix.tools.docs_compiler compile")
    """
    gate = DocsCompiledGate(root=root, sources=sources, outputs=outputs)
    return gate.check()


def main():
    """CLI entry point for the docs_compiled gate."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check if generated documentation is up-to-date"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root directory of the HELIX project",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    gate = DocsCompiledGate(root=args.root)
    result = gate.check()

    if args.verbose:
        print("Docs Compiled Gate Result:")
        print(f"  Passed: {result.passed}")
        print(f"  Source Hash: {result.source_hash}")

        if result.stale_files:
            print(f"  Stale Files: {', '.join(result.stale_files)}")

        if result.missing_files:
            print(f"  Missing Files: {', '.join(result.missing_files)}")

        for warning in result.warnings:
            print(f"  WARNING: {warning}")

        for error in result.errors:
            print(f"  ERROR: {error}")
    else:
        if result.passed:
            print("docs_compiled: PASSED")
        else:
            print("docs_compiled: FAILED")
            if result.stale_files:
                print(f"  Stale: {', '.join(result.stale_files)}")
            if result.missing_files:
                print(f"  Missing: {', '.join(result.missing_files)}")
            for error in result.errors:
                print(f"  ERROR: {error}")

    import sys
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
