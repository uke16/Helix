import pytest
from pathlib import Path

from helix.quality_gates import QualityGateRunner, GateResult


class TestQualityGateRunner:
    """Tests for QualityGateRunner."""

    def test_files_exist_pass(self, temp_dir):
        """Should pass if all files exist."""
        (temp_dir / "test.py").write_text("# test")

        runner = QualityGateRunner()
        result = runner.check_files_exist(
            temp_dir,
            files=["test.py"],
        )

        assert result.passed
        assert result.gate_type == "files_exist"

    def test_files_exist_fail(self, temp_dir):
        """Should fail if files missing."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            temp_dir,
            files=["missing.py"],
        )

        assert not result.passed
        assert "missing.py" in str(result.details)

    def test_syntax_check_python_valid(self, temp_dir):
        """Should pass for valid Python."""
        (temp_dir / "valid.py").write_text("def foo(): pass")

        runner = QualityGateRunner()
        result = runner.check_syntax(temp_dir / "valid.py")

        assert result.passed

    def test_syntax_check_python_invalid(self, temp_dir):
        """Should fail for invalid Python."""
        (temp_dir / "invalid.py").write_text("def foo(")

        runner = QualityGateRunner()
        result = runner.check_syntax(temp_dir / "invalid.py")

        assert not result.passed
