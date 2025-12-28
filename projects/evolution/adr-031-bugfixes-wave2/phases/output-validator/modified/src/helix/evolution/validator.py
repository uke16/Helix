"""Evolution Validator.

Validates evolution projects after deployment to the test system.

Validation steps:
1. syntax_check() - Python syntax validation on all .py files
2. run_unit_tests() - Run pytest on tests/
3. run_e2e_tests() - Run API endpoint tests
4. full_validation() - All checks combined

ADR-031: Added OutputValidator for flexible output directory support.
Supports three output conventions:
- output/     : Simple flat output
- new/        : New files (ADR-030 style)
- modified/   : Modified files (ADR-030 style)
"""

import asyncio
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ValidationLevel(str, Enum):
    """Level of validation."""
    SYNTAX = "syntax"
    UNIT = "unit"
    E2E = "e2e"
    FULL = "full"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    success: bool
    level: ValidationLevel
    message: str
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[str] = None


@dataclass
class OutputValidationResult:
    """Result of an output validation operation (ADR-031)."""
    success: bool
    found_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    message: str = ""


class OutputValidator:
    """Validates phase outputs with flexible directory support.

    Supports three output conventions:
    1. output/         - Simple flat output
    2. new/            - New files (ADR-030 style)
    3. modified/       - Modified files (ADR-030 style)

    Usage:
        validator = OutputValidator()
        files = validator.find_output_files(phase_path)
        result = validator.validate_expected_outputs(phase_path, expected_patterns)

    ADR-031: Fix 4 - Output Directory Standardization
    """

    OUTPUT_DIRS = ["output", "new", "modified"]

    def find_output_files(self, phase_path: Path) -> list[Path]:
        """Find all output files in any of the supported directories.

        Searches through output/, new/, and modified/ directories
        within the given phase path.

        Args:
            phase_path: Path to the phase directory

        Returns:
            List of output file paths found
        """
        files = []

        for dir_name in self.OUTPUT_DIRS:
            dir_path = phase_path / dir_name
            if dir_path.exists():
                files.extend(f for f in dir_path.rglob("*") if f.is_file())

        return files

    def validate_expected_outputs(
        self,
        phase_path: Path,
        expected: list[str]
    ) -> OutputValidationResult:
        """Validate that expected output files exist.

        Handles patterns with or without directory prefixes:
        - "modified/src/helix/foo.py" - looks in phase_path/modified/src/helix/foo.py
        - "src/helix/foo.py" - looks in phase_path/{output,new,modified}/src/helix/foo.py

        Args:
            phase_path: Path to phase directory
            expected: List of expected file patterns from phases.yaml

        Returns:
            OutputValidationResult with found/missing files
        """
        found = []
        missing = []

        for pattern in expected:
            file_found = False

            # First, try pattern as-is (if it includes directory prefix)
            full_path = phase_path / pattern
            if full_path.exists():
                found.append(str(full_path))
                file_found = True
            else:
                # Try pattern with each output directory prefix
                # e.g., "src/helix/foo.py" -> "output/src/helix/foo.py"
                if not pattern.startswith(tuple(self.OUTPUT_DIRS)):
                    for dir_name in self.OUTPUT_DIRS:
                        prefixed_path = phase_path / dir_name / pattern
                        if prefixed_path.exists():
                            found.append(str(prefixed_path))
                            file_found = True
                            break

            if not file_found:
                missing.append(pattern)

        return OutputValidationResult(
            success=len(missing) == 0,
            found_files=found,
            missing_files=missing,
            message=f"Found {len(found)}/{len(expected)} expected files"
        )

    def get_output_summary(self, phase_path: Path) -> dict:
        """Get a summary of output files in each directory.

        Args:
            phase_path: Path to the phase directory

        Returns:
            Dict with directory names as keys and file counts/lists as values
        """
        summary = {}

        for dir_name in self.OUTPUT_DIRS:
            dir_path = phase_path / dir_name
            if dir_path.exists():
                files = [f for f in dir_path.rglob("*") if f.is_file()]
                summary[dir_name] = {
                    "count": len(files),
                    "files": [str(f.relative_to(dir_path)) for f in files]
                }
            else:
                summary[dir_name] = {"count": 0, "files": []}

        return summary


class Validator:
    """Validates evolution projects in the test system."""

    TEST_ROOT = Path("/home/aiuser01/helix-v4-test")
    TEST_API_URL = "http://localhost:9001"

    def __init__(
        self,
        test_root: Optional[Path] = None,
        test_api_url: Optional[str] = None,
    ):
        """Initialize the validator.

        Args:
            test_root: Path to test HELIX
            test_api_url: URL of test API
        """
        self.test_root = Path(test_root or self.TEST_ROOT)
        self.test_api_url = test_api_url or self.TEST_API_URL
        # ADR-031: Add output validator instance
        self.output_validator = OutputValidator()

    async def syntax_check(
        self,
        files: Optional[list[Path]] = None,
    ) -> ValidationResult:
        """Check Python syntax of files.

        Args:
            files: List of files to check. If None, checks all .py in src/

        Returns:
            ValidationResult with syntax check results
        """
        started_at = datetime.now()
        errors = []
        passed = 0

        try:
            # Get files to check
            if files is None:
                src_dir = self.test_root / "src"
                files = list(src_dir.rglob("*.py"))

            for file_path in files:
                try:
                    # Use py_compile to check syntax
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "py_compile", str(file_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        error_msg = stderr.decode().strip() if stderr else f"Syntax error in {file_path}"
                        errors.append(error_msg)
                    else:
                        passed += 1

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            success = len(errors) == 0

            return ValidationResult(
                success=success,
                level=ValidationLevel.SYNTAX,
                message=f"Syntax check: {passed} passed, {len(errors)} failed",
                passed=passed,
                failed=len(errors),
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                level=ValidationLevel.SYNTAX,
                message="Syntax check failed",
                errors=[str(e)],
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def run_unit_tests(
        self,
        test_path: Optional[Path] = None,
        verbose: bool = True,
    ) -> ValidationResult:
        """Run unit tests with pytest.

        Args:
            test_path: Specific test path. If None, runs all tests/
            verbose: Whether to use verbose output

        Returns:
            ValidationResult with test results
        """
        started_at = datetime.now()

        try:
            # Build pytest command
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path or self.test_root / "tests"),
            ]
            if verbose:
                cmd.append("-v")

            # Set PYTHONPATH
            env = {
                "PYTHONPATH": str(self.test_root / "src"),
                "PATH": subprocess.os.environ.get("PATH", ""),
            }

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.test_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode() if stdout else ""
            output += stderr.decode() if stderr else ""

            # Parse pytest output for pass/fail counts
            passed = 0
            failed = 0
            for line in output.split("\n"):
                if "passed" in line.lower():
                    # Try to extract "X passed"
                    import re
                    match = re.search(r"(\d+) passed", line)
                    if match:
                        passed = int(match.group(1))
                if "failed" in line.lower():
                    match = re.search(r"(\d+) failed", line)
                    if match:
                        failed = int(match.group(1))

            success = process.returncode == 0

            return ValidationResult(
                success=success,
                level=ValidationLevel.UNIT,
                message=f"Unit tests: {passed} passed, {failed} failed",
                passed=passed,
                failed=failed,
                errors=[output] if not success else [],
                started_at=started_at,
                completed_at=datetime.now(),
                output=output,
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                level=ValidationLevel.UNIT,
                message="Unit tests failed to run",
                errors=[str(e)],
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def run_e2e_tests(self) -> ValidationResult:
        """Run end-to-end API tests.

        Checks that the test API is responding correctly.

        Returns:
            ValidationResult with E2E test results
        """
        import aiohttp

        started_at = datetime.now()
        passed = 0
        failed = 0
        errors = []

        try:
            async with aiohttp.ClientSession() as session:
                # Test 1: Health endpoint
                try:
                    async with session.get(
                        f"{self.test_api_url}/health",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            passed += 1
                        else:
                            failed += 1
                            errors.append(f"Health check returned {response.status}")
                except Exception as e:
                    failed += 1
                    errors.append(f"Health check failed: {e}")

                # Test 2: Docs endpoint
                try:
                    async with session.get(
                        f"{self.test_api_url}/docs",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            passed += 1
                        else:
                            failed += 1
                            errors.append(f"Docs endpoint returned {response.status}")
                except Exception as e:
                    failed += 1
                    errors.append(f"Docs check failed: {e}")

                # Test 3: OpenAPI schema
                try:
                    async with session.get(
                        f"{self.test_api_url}/openapi.json",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            passed += 1
                        else:
                            failed += 1
                            errors.append(f"OpenAPI endpoint returned {response.status}")
                except Exception as e:
                    failed += 1
                    errors.append(f"OpenAPI check failed: {e}")

            success = failed == 0

            return ValidationResult(
                success=success,
                level=ValidationLevel.E2E,
                message=f"E2E tests: {passed} passed, {failed} failed",
                passed=passed,
                failed=failed,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                level=ValidationLevel.E2E,
                message="E2E tests failed",
                errors=[str(e)],
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def full_validation(
        self,
        files: Optional[list[Path]] = None,
    ) -> ValidationResult:
        """Run full validation suite.

        Runs:
        1. Syntax check
        2. Unit tests
        3. E2E tests

        Args:
            files: Optional list of files for syntax check

        Returns:
            Combined ValidationResult
        """
        started_at = datetime.now()
        all_errors = []
        total_passed = 0
        total_failed = 0

        # Step 1: Syntax check
        syntax_result = await self.syntax_check(files)
        if not syntax_result.success:
            all_errors.extend(syntax_result.errors)
            total_failed += syntax_result.failed
        else:
            total_passed += syntax_result.passed

        # Step 2: Unit tests (only if syntax passes)
        if syntax_result.success:
            unit_result = await self.run_unit_tests()
            total_passed += unit_result.passed
            total_failed += unit_result.failed
            if not unit_result.success:
                all_errors.extend(unit_result.errors)

            # Step 3: E2E tests (only if unit tests pass)
            if unit_result.success:
                e2e_result = await self.run_e2e_tests()
                total_passed += e2e_result.passed
                total_failed += e2e_result.failed
                if not e2e_result.success:
                    all_errors.extend(e2e_result.errors)

        success = len(all_errors) == 0

        return ValidationResult(
            success=success,
            level=ValidationLevel.FULL,
            message=f"Full validation: {total_passed} passed, {total_failed} failed" + (f", {len(all_errors)} errors" if all_errors else ""),
            passed=total_passed,
            failed=total_failed,
            errors=all_errors,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    async def validate_phase_outputs(
        self,
        phase_path: Path,
        expected: list[str],
    ) -> OutputValidationResult:
        """Validate phase outputs using OutputValidator.

        Convenience method for validating phase outputs.

        Args:
            phase_path: Path to phase directory
            expected: List of expected file patterns

        Returns:
            OutputValidationResult with found/missing files
        """
        return self.output_validator.validate_expected_outputs(phase_path, expected)


async def quick_validate(test_root: Optional[Path] = None) -> bool:
    """Quick validation helper.

    Args:
        test_root: Path to test system

    Returns:
        True if all validations pass
    """
    validator = Validator(test_root=test_root)
    result = await validator.full_validation()
    return result.success
