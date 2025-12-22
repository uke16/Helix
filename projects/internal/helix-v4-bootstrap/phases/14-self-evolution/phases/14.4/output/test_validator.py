"""
Unit tests for the Validator module.

Tests the validation functionality for evolution projects.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from validator import (
    FullValidationResult,
    ValidationLevel,
    ValidationResult,
    ValidationStatus,
    Validator,
    create_validator,
)


@pytest.fixture
def temp_test_system(tmp_path: Path):
    """Create a temporary test system directory."""
    test_system = tmp_path / "helix-v4-test"
    test_system.mkdir()

    # Create src directory
    (test_system / "src" / "helix").mkdir(parents=True)

    # Create tests directory
    tests_dir = test_system / "tests"
    tests_dir.mkdir()

    # Create a simple test file
    test_file = tests_dir / "test_example.py"
    test_file.write_text("""
import pytest

def test_example():
    assert 1 + 1 == 2

def test_another():
    assert True
""")

    return test_system


@pytest.fixture
def validator(temp_test_system):
    """Create a Validator instance with temp directory."""
    return Validator(
        test_system_path=temp_test_system,
        test_api_url="http://localhost:9001",
    )


@pytest.fixture
def mock_project(tmp_path: Path):
    """Create a mock evolution project."""
    project_path = tmp_path / "test-feature"
    project_path.mkdir()

    # Create new/ directory with Python files
    new_dir = project_path / "new" / "src" / "helix"
    new_dir.mkdir(parents=True)
    (new_dir / "feature.py").write_text("# Valid Python\nprint('hello')\n")

    # Create modified/ directory
    modified_dir = project_path / "modified" / "src" / "helix"
    modified_dir.mkdir(parents=True)
    (modified_dir / "existing.py").write_text("# Modified\nx = 1 + 2\n")

    # Create status.json
    status = {
        "status": "deployed",
        "session_id": "test-session",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    (project_path / "status.json").write_text(json.dumps(status))

    # Create mock project object
    mock = MagicMock()
    mock.name = "test-feature"
    mock.path = project_path
    mock.get_new_files.return_value = [Path("src/helix/feature.py")]
    mock.get_modified_files.return_value = [Path("src/helix/existing.py")]

    return mock


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ValidationResult(
            check_name="syntax_check",
            status=ValidationStatus.PASSED,
            message="All files passed",
            details={"files_checked": 5},
            errors=[],
            duration_seconds=1.5,
        )

        d = result.to_dict()

        assert d["check_name"] == "syntax_check"
        assert d["status"] == "passed"
        assert d["message"] == "All files passed"
        assert d["details"]["files_checked"] == 5
        assert d["duration_seconds"] == 1.5


class TestFullValidationResult:
    """Tests for FullValidationResult dataclass."""

    def test_passed_count(self):
        """Test counting passed checks."""
        result = FullValidationResult(
            success=True,
            results=[
                ValidationResult(
                    check_name="check1",
                    status=ValidationStatus.PASSED,
                    message="OK",
                ),
                ValidationResult(
                    check_name="check2",
                    status=ValidationStatus.PASSED,
                    message="OK",
                ),
                ValidationResult(
                    check_name="check3",
                    status=ValidationStatus.FAILED,
                    message="Failed",
                ),
            ],
        )

        assert result.passed_count == 2
        assert result.failed_count == 1

    def test_total_duration(self):
        """Test calculating total duration."""
        result = FullValidationResult(
            success=True,
            results=[
                ValidationResult(
                    check_name="check1",
                    status=ValidationStatus.PASSED,
                    message="OK",
                    duration_seconds=1.0,
                ),
                ValidationResult(
                    check_name="check2",
                    status=ValidationStatus.PASSED,
                    message="OK",
                    duration_seconds=2.5,
                ),
            ],
        )

        assert result.total_duration == 3.5

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = FullValidationResult(
            success=True,
            results=[
                ValidationResult(
                    check_name="check1",
                    status=ValidationStatus.PASSED,
                    message="OK",
                ),
            ],
        )
        result.completed_at = datetime.now()

        d = result.to_dict()

        assert d["success"] is True
        assert d["passed_count"] == 1
        assert d["failed_count"] == 0
        assert len(d["results"]) == 1


class TestValidator:
    """Tests for the Validator class."""

    def test_init_default_paths(self):
        """Test default initialization."""
        validator = Validator()

        assert validator.test_system_path == Path("/home/aiuser01/helix-v4-test")
        assert validator.test_api_url == "http://localhost:9001"

    def test_init_custom_paths(self, temp_test_system):
        """Test custom initialization."""
        validator = Validator(
            test_system_path=temp_test_system,
            test_api_url="http://localhost:8080",
        )

        assert validator.test_system_path == temp_test_system
        assert validator.test_api_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_run_command_success(self, validator):
        """Test running a successful command."""
        returncode, stdout, stderr = await validator._run_command(
            ["echo", "test"],
            timeout=5.0,
        )

        assert returncode == 0
        assert "test" in stdout

    @pytest.mark.asyncio
    async def test_run_command_with_env(self, validator):
        """Test running command with environment variables."""
        returncode, stdout, stderr = await validator._run_command(
            ["printenv", "TEST_VAR"],
            env={"TEST_VAR": "hello"},
            timeout=5.0,
        )

        assert returncode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_syntax_check_valid_files(self, validator, temp_test_system):
        """Test syntax check with valid Python files."""
        # Create valid Python file
        py_file = temp_test_system / "src" / "helix" / "valid.py"
        py_file.write_text("x = 1 + 2\nprint(x)\n")

        files = [Path("src/helix/valid.py")]
        result = await validator.syntax_check(files)

        assert result.status == ValidationStatus.PASSED
        assert result.details["files_checked"] == 1
        assert result.details["errors_found"] == 0

    @pytest.mark.asyncio
    async def test_syntax_check_invalid_files(self, validator, temp_test_system):
        """Test syntax check with invalid Python files."""
        # Create invalid Python file
        py_file = temp_test_system / "src" / "helix" / "invalid.py"
        py_file.write_text("def broken(\n    pass\n")  # Syntax error

        files = [Path("src/helix/invalid.py")]
        result = await validator.syntax_check(files)

        assert result.status == ValidationStatus.FAILED
        assert result.details["errors_found"] > 0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_syntax_check_empty_list(self, validator):
        """Test syntax check with empty file list."""
        result = await validator.syntax_check([])

        assert result.status == ValidationStatus.SKIPPED
        assert "no files" in result.message.lower()

    @pytest.mark.asyncio
    async def test_syntax_check_no_python_files(self, validator):
        """Test syntax check with no Python files."""
        files = [Path("file.txt"), Path("data.json")]
        result = await validator.syntax_check(files)

        assert result.status == ValidationStatus.SKIPPED
        assert "no python files" in result.message.lower()

    @pytest.mark.asyncio
    async def test_run_unit_tests_no_tests_dir(self, validator, temp_test_system):
        """Test unit tests when tests directory doesn't exist."""
        # Remove tests directory
        import shutil
        shutil.rmtree(temp_test_system / "tests")

        result = await validator.run_unit_tests()

        assert result.status == ValidationStatus.SKIPPED
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_run_unit_tests_with_mock(self, validator):
        """Test unit tests with mocked pytest output."""
        with patch.object(validator, "_run_command") as mock_cmd:
            # Mock successful pytest output
            mock_cmd.return_value = (
                0,
                '{"summary": {"passed": 5, "failed": 0, "total": 5}}',
                "",
            )

            result = await validator.run_unit_tests()

        assert result.status == ValidationStatus.PASSED
        assert "passed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_run_unit_tests_failed(self, validator):
        """Test unit tests when some tests fail."""
        with patch.object(validator, "_run_command") as mock_cmd:
            # Mock failed pytest output
            mock_cmd.return_value = (
                1,
                '{"summary": {"passed": 3, "failed": 2, "total": 5}}',
                "2 tests failed",
            )

            result = await validator.run_unit_tests()

        assert result.status == ValidationStatus.FAILED

    @pytest.mark.asyncio
    async def test_run_e2e_tests_success(self, validator):
        """Test E2E tests with mocked curl."""
        with patch.object(validator, "_run_command") as mock_cmd:
            # Mock successful curl responses
            mock_cmd.return_value = (0, "200", "")

            result = await validator.run_e2e_tests()

        assert result.status == ValidationStatus.PASSED
        assert len(result.details["passed_endpoints"]) == 2

    @pytest.mark.asyncio
    async def test_run_e2e_tests_failure(self, validator):
        """Test E2E tests when endpoint fails."""
        with patch.object(validator, "_run_command") as mock_cmd:
            # Mock mixed responses
            mock_cmd.side_effect = [
                (0, "200", ""),  # /health passes
                (0, "500", ""),  # /helix/status fails
            ]

            result = await validator.run_e2e_tests()

        assert result.status == ValidationStatus.FAILED
        assert len(result.details["failed_endpoints"]) == 1

    @pytest.mark.asyncio
    async def test_run_e2e_tests_custom_endpoints(self, validator):
        """Test E2E tests with custom endpoints."""
        with patch.object(validator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (0, "200", "")

            result = await validator.run_e2e_tests(
                test_endpoints=["/custom1", "/custom2", "/custom3"]
            )

        assert result.status == ValidationStatus.PASSED
        assert len(result.details["passed_endpoints"]) == 3

    @pytest.mark.asyncio
    async def test_full_validation_success(self, validator, mock_project):
        """Test full validation success."""
        with patch.object(validator, "syntax_check") as mock_syntax:
            mock_syntax.return_value = ValidationResult(
                check_name="syntax_check",
                status=ValidationStatus.PASSED,
                message="OK",
            )

            with patch.object(validator, "run_unit_tests") as mock_unit:
                mock_unit.return_value = ValidationResult(
                    check_name="unit_tests",
                    status=ValidationStatus.PASSED,
                    message="OK",
                )

                with patch.object(validator, "run_e2e_tests") as mock_e2e:
                    mock_e2e.return_value = ValidationResult(
                        check_name="e2e_tests",
                        status=ValidationStatus.PASSED,
                        message="OK",
                    )

                    result = await validator.full_validation(mock_project)

        assert result.success is True
        assert result.passed_count == 3
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_full_validation_syntax_fails(self, validator, mock_project):
        """Test full validation stops on syntax failure."""
        with patch.object(validator, "syntax_check") as mock_syntax:
            mock_syntax.return_value = ValidationResult(
                check_name="syntax_check",
                status=ValidationStatus.FAILED,
                message="Syntax error",
            )

            result = await validator.full_validation(mock_project)

        assert result.success is False
        assert len(result.results) == 1  # Only syntax check ran

    @pytest.mark.asyncio
    async def test_full_validation_skip_e2e(self, validator, mock_project):
        """Test full validation with E2E skipped."""
        with patch.object(validator, "syntax_check") as mock_syntax:
            mock_syntax.return_value = ValidationResult(
                check_name="syntax_check",
                status=ValidationStatus.PASSED,
                message="OK",
            )

            with patch.object(validator, "run_unit_tests") as mock_unit:
                mock_unit.return_value = ValidationResult(
                    check_name="unit_tests",
                    status=ValidationStatus.PASSED,
                    message="OK",
                )

                result = await validator.full_validation(mock_project, skip_e2e=True)

        assert result.success is True
        assert len(result.results) == 2  # No E2E

    @pytest.mark.asyncio
    async def test_quick_validation(self, validator, temp_test_system):
        """Test quick validation (syntax only)."""
        # Create valid file
        py_file = temp_test_system / "src" / "helix" / "quick.py"
        py_file.write_text("x = 42\n")

        files = [Path("src/helix/quick.py")]
        result = await validator.quick_validation(files)

        assert result.check_name == "syntax_check"

    @pytest.mark.asyncio
    async def test_check_api_health_success(self, validator):
        """Test API health check success."""
        with patch.object(validator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (0, "200", "")

            is_healthy = await validator.check_api_health()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_check_api_health_failure(self, validator):
        """Test API health check failure."""
        with patch.object(validator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (0, "503", "")

            is_healthy = await validator.check_api_health()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_check_api_health_connection_error(self, validator):
        """Test API health check with connection error."""
        with patch.object(validator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (7, "", "Connection refused")  # curl error 7

            is_healthy = await validator.check_api_health()

        assert is_healthy is False


class TestCreateValidator:
    """Tests for the factory function."""

    def test_create_validator_defaults(self):
        """Test creating validator with defaults."""
        validator = create_validator()

        assert validator.test_system_path == Path("/home/aiuser01/helix-v4-test")
        assert validator.test_api_url == "http://localhost:9001"

    def test_create_validator_custom(self, temp_test_system):
        """Test creating validator with custom paths."""
        validator = create_validator(
            test_system_path=temp_test_system,
            test_api_url="http://localhost:8080",
        )

        assert validator.test_system_path == temp_test_system
        assert validator.test_api_url == "http://localhost:8080"


class TestValidationEnums:
    """Tests for validation enums."""

    def test_validation_level_values(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.SYNTAX.value == "syntax"
        assert ValidationLevel.UNIT.value == "unit"
        assert ValidationLevel.E2E.value == "e2e"
        assert ValidationLevel.FULL.value == "full"

    def test_validation_status_values(self):
        """Test ValidationStatus enum values."""
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.RUNNING.value == "running"
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.SKIPPED.value == "skipped"
        assert ValidationStatus.ERROR.value == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
