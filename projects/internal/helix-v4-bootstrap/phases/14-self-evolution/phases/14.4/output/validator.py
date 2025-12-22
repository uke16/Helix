"""
Validator module for HELIX v4 Self-Evolution System.

This module handles validation of evolution projects after deployment to the
test system. It runs syntax checks, unit tests, and end-to-end tests.

The validation workflow:
1. syntax_check() - Compile Python files to check for syntax errors
2. run_unit_tests() - Run pytest on the test suite
3. run_e2e_tests() - Run API tests against the test system
4. full_validation() - Run all validation steps
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helix.evolution.project import EvolutionProject


class ValidationLevel(str, Enum):
    """Level of validation to perform."""

    SYNTAX = "syntax"       # Syntax check only
    UNIT = "unit"           # Syntax + unit tests
    E2E = "e2e"             # E2E tests only
    FULL = "full"           # All validation steps


class ValidationStatus(str, Enum):
    """Status of a validation operation."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    check_name: str
    status: ValidationStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class FullValidationResult:
    """Result of a full validation run."""

    success: bool
    results: list[ValidationResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def passed_count(self) -> int:
        """Number of passed checks."""
        return sum(1 for r in self.results if r.status == ValidationStatus.PASSED)

    @property
    def failed_count(self) -> int:
        """Number of failed checks."""
        return sum(1 for r in self.results if r.status == ValidationStatus.FAILED)

    @property
    def total_duration(self) -> float:
        """Total duration of all checks."""
        return sum(r.duration_seconds for r in self.results)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "total_duration": self.total_duration,
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Validator:
    """
    Validates evolution projects after deployment.

    The validator runs various checks to ensure the deployed code is correct
    and doesn't break existing functionality.

    Attributes:
        test_system_path: Path to the test HELIX installation.
        test_api_url: URL of the test API for E2E tests.
    """

    def __init__(
        self,
        test_system_path: Path | None = None,
        test_api_url: str | None = None,
    ) -> None:
        """
        Initialize the validator.

        Args:
            test_system_path: Path to test HELIX. Defaults to /home/aiuser01/helix-v4-test.
            test_api_url: URL of test API. Defaults to http://localhost:9001.
        """
        self.test_system_path = test_system_path or Path("/home/aiuser01/helix-v4-test")
        self.test_api_url = test_api_url or "http://localhost:9001"

    async def _run_command(
        self,
        command: list[str],
        cwd: Path | None = None,
        timeout: float = 300.0,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """
        Run a shell command asynchronously.

        Args:
            command: Command and arguments as list.
            cwd: Working directory for the command.
            timeout: Timeout in seconds.
            env: Additional environment variables.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        import os

        # Build environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )

        except asyncio.TimeoutError:
            if process:
                process.kill()
                await process.wait()
            return (-1, "", f"Command timed out after {timeout} seconds")

        except Exception as e:
            return (-1, "", str(e))

    async def syntax_check(self, files: list[Path]) -> ValidationResult:
        """
        Check Python files for syntax errors.

        Uses py_compile to verify each file can be compiled.

        Args:
            files: List of Python file paths to check.

        Returns:
            ValidationResult with syntax check status.
        """
        start_time = datetime.now()
        result = ValidationResult(
            check_name="syntax_check",
            status=ValidationStatus.RUNNING,
            message="Checking Python syntax",
        )

        if not files:
            result.status = ValidationStatus.SKIPPED
            result.message = "No files to check"
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        # Filter for Python files
        py_files = [f for f in files if str(f).endswith(".py")]

        if not py_files:
            result.status = ValidationStatus.SKIPPED
            result.message = "No Python files to check"
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        checked_count = 0
        error_count = 0

        for py_file in py_files:
            # Construct absolute path in test system
            if not py_file.is_absolute():
                full_path = self.test_system_path / py_file
            else:
                full_path = py_file

            if not full_path.exists():
                result.warnings.append(f"File not found: {py_file}")
                continue

            # Run py_compile
            returncode, stdout, stderr = await self._run_command(
                ["python3", "-m", "py_compile", str(full_path)],
                timeout=10.0,
            )

            checked_count += 1

            if returncode != 0:
                error_count += 1
                error_msg = stderr.strip() or f"Syntax error in {py_file}"
                result.errors.append(error_msg)

        result.details = {
            "files_checked": checked_count,
            "errors_found": error_count,
        }

        if error_count > 0:
            result.status = ValidationStatus.FAILED
            result.message = f"Syntax errors found in {error_count} file(s)"
        else:
            result.status = ValidationStatus.PASSED
            result.message = f"All {checked_count} files passed syntax check"

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    async def run_unit_tests(
        self,
        test_path: Path | None = None,
        markers: list[str] | None = None,
    ) -> ValidationResult:
        """
        Run unit tests using pytest.

        Args:
            test_path: Path to test directory or file. Defaults to tests/.
            markers: Optional pytest markers to filter tests.

        Returns:
            ValidationResult with test results.
        """
        start_time = datetime.now()
        result = ValidationResult(
            check_name="unit_tests",
            status=ValidationStatus.RUNNING,
            message="Running unit tests",
        )

        test_dir = test_path or (self.test_system_path / "tests")

        if not test_dir.exists():
            result.status = ValidationStatus.SKIPPED
            result.message = f"Test directory not found: {test_dir}"
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        # Build pytest command
        pytest_args = [
            "python3", "-m", "pytest",
            str(test_dir),
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=/dev/stdout",
        ]

        # Add markers if specified
        if markers:
            for marker in markers:
                pytest_args.extend(["-m", marker])

        # Set PYTHONPATH to include src directory
        env = {
            "PYTHONPATH": str(self.test_system_path / "src"),
        }

        returncode, stdout, stderr = await self._run_command(
            pytest_args,
            cwd=self.test_system_path,
            timeout=300.0,
            env=env,
        )

        # Try to parse JSON report
        try:
            # Find JSON in stdout (pytest-json-report output)
            json_start = stdout.find('{"')
            if json_start >= 0:
                json_str = stdout[json_start:]
                # Find the end of JSON
                brace_count = 0
                json_end = 0
                for i, char in enumerate(json_str):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    report = json.loads(json_str[:json_end])
                    summary = report.get("summary", {})
                    result.details = {
                        "passed": summary.get("passed", 0),
                        "failed": summary.get("failed", 0),
                        "skipped": summary.get("skipped", 0),
                        "total": summary.get("total", 0),
                        "duration": summary.get("duration", 0),
                    }
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback: parse output manually
            result.details = {
                "raw_output": stdout[-2000:] if len(stdout) > 2000 else stdout,
            }

        if returncode == 0:
            result.status = ValidationStatus.PASSED
            passed = result.details.get("passed", "?")
            result.message = f"All tests passed ({passed} tests)"
        elif returncode == 5:
            # No tests collected
            result.status = ValidationStatus.SKIPPED
            result.message = "No tests collected"
        else:
            result.status = ValidationStatus.FAILED
            failed = result.details.get("failed", "?")
            result.message = f"Tests failed ({failed} failures)"
            if stderr:
                result.errors.append(stderr[:1000])

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    async def run_e2e_tests(
        self,
        api_url: str | None = None,
        test_endpoints: list[str] | None = None,
    ) -> ValidationResult:
        """
        Run end-to-end tests against the test API.

        Args:
            api_url: URL of the API to test. Defaults to test_api_url.
            test_endpoints: List of endpoints to test. Defaults to health check.

        Returns:
            ValidationResult with E2E test results.
        """
        start_time = datetime.now()
        result = ValidationResult(
            check_name="e2e_tests",
            status=ValidationStatus.RUNNING,
            message="Running E2E tests",
        )

        url = api_url or self.test_api_url

        # Default endpoints to test
        endpoints = test_endpoints or [
            "/health",
            "/helix/status",
        ]

        passed_endpoints = []
        failed_endpoints = []

        for endpoint in endpoints:
            full_url = f"{url}{endpoint}"

            returncode, stdout, stderr = await self._run_command(
                ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null", "--max-time", "10", full_url],
                timeout=15.0,
            )

            if returncode == 0:
                status_code = stdout.strip()
                if status_code.startswith("2"):  # 2xx status codes
                    passed_endpoints.append(endpoint)
                else:
                    failed_endpoints.append(f"{endpoint} (HTTP {status_code})")
            else:
                failed_endpoints.append(f"{endpoint} (connection failed)")

        result.details = {
            "api_url": url,
            "endpoints_tested": len(endpoints),
            "passed": len(passed_endpoints),
            "failed": len(failed_endpoints),
            "passed_endpoints": passed_endpoints,
            "failed_endpoints": failed_endpoints,
        }

        if failed_endpoints:
            result.status = ValidationStatus.FAILED
            result.message = f"E2E tests failed: {len(failed_endpoints)} endpoint(s) failed"
            result.errors.extend(failed_endpoints)
        else:
            result.status = ValidationStatus.PASSED
            result.message = f"All {len(passed_endpoints)} endpoint(s) passed"

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    async def full_validation(
        self,
        project: "EvolutionProject",
        skip_e2e: bool = False,
    ) -> FullValidationResult:
        """
        Run full validation on an evolution project.

        Runs syntax check, unit tests, and E2E tests in sequence.

        Args:
            project: The EvolutionProject to validate.
            skip_e2e: If True, skip E2E tests.

        Returns:
            FullValidationResult with all validation results.
        """
        full_result = FullValidationResult(
            success=False,
            started_at=datetime.now(),
        )

        # Get all files from project
        all_files = project.get_new_files() + project.get_modified_files()

        # Step 1: Syntax check
        syntax_result = await self.syntax_check(all_files)
        full_result.results.append(syntax_result)

        # If syntax fails, don't continue
        if syntax_result.status == ValidationStatus.FAILED:
            full_result.completed_at = datetime.now()
            return full_result

        # Step 2: Unit tests
        unit_result = await self.run_unit_tests()
        full_result.results.append(unit_result)

        # If unit tests fail, don't continue with E2E
        if unit_result.status == ValidationStatus.FAILED:
            full_result.completed_at = datetime.now()
            return full_result

        # Step 3: E2E tests (optional)
        if not skip_e2e:
            e2e_result = await self.run_e2e_tests()
            full_result.results.append(e2e_result)

        # Determine overall success
        failed_checks = [r for r in full_result.results if r.status == ValidationStatus.FAILED]
        full_result.success = len(failed_checks) == 0
        full_result.completed_at = datetime.now()

        return full_result

    async def quick_validation(self, files: list[Path]) -> ValidationResult:
        """
        Run a quick syntax-only validation on specific files.

        Args:
            files: List of files to validate.

        Returns:
            ValidationResult with syntax check status.
        """
        return await self.syntax_check(files)

    async def check_api_health(self, api_url: str | None = None) -> bool:
        """
        Check if the API is healthy.

        Args:
            api_url: URL to check. Defaults to test_api_url.

        Returns:
            True if API responds with 2xx status, False otherwise.
        """
        url = api_url or self.test_api_url

        returncode, stdout, stderr = await self._run_command(
            ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null", "--max-time", "5", f"{url}/health"],
            timeout=10.0,
        )

        if returncode == 0:
            status_code = stdout.strip()
            return status_code.startswith("2")

        return False


def create_validator(
    test_system_path: Path | None = None,
    test_api_url: str | None = None,
) -> Validator:
    """
    Factory function to create a Validator.

    Args:
        test_system_path: Optional test HELIX path.
        test_api_url: Optional test API URL.

    Returns:
        Configured Validator instance.
    """
    return Validator(
        test_system_path=test_system_path,
        test_api_url=test_api_url,
    )
