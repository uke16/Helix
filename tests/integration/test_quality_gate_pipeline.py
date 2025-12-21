import pytest
from pathlib import Path
import subprocess

from helix.quality_gates import QualityGateRunner, GateResult
from helix.escalation import EscalationManager, EscalationLevel


class TestQualityGatePipeline:
    """Integration tests for quality gate system."""

    @pytest.fixture
    def python_project(self, temp_dir):
        """Create a Python project structure."""
        src = temp_dir / "src"
        src.mkdir()

        # Valid Python file
        (src / "valid_module.py").write_text('''
"""A valid Python module."""

def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator."""

    def add(self, a: int, b: int) -> int:
        return a + b
''')

        # Invalid Python file
        (src / "invalid_module.py").write_text('''
def broken_function(
    # Missing closing parenthesis
''')

        return temp_dir

    def test_syntax_check_valid_file(self, python_project):
        """Should pass for valid Python."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "valid_module.py")

        assert result.passed
        assert result.gate_type == "syntax_check"

    def test_syntax_check_invalid_file(self, python_project):
        """Should fail for invalid Python."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "invalid_module.py")

        assert not result.passed
        assert "error" in str(result.details).lower() or "syntax" in str(result.details).lower()

    def test_files_exist_all_present(self, python_project):
        """Should pass when all files exist."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            python_project / "src",
            files=["valid_module.py"]
        )

        assert result.passed

    def test_files_exist_missing(self, python_project):
        """Should fail when files missing."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            python_project / "src",
            files=["valid_module.py", "missing.py"]
        )

        assert not result.passed
        assert "missing.py" in str(result.details)

    def test_escalation_on_syntax_error(self, python_project):
        """Syntax errors should trigger Level 1 escalation."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "invalid_module.py")

        escalation = EscalationManager()
        level = escalation.determine_level(str(result.details))

        assert level == EscalationLevel.STUFE_1

    def test_gate_result_structure(self, python_project):
        """GateResult should have all required fields."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "valid_module.py")

        assert hasattr(result, 'passed')
        assert hasattr(result, 'gate_type')
        assert hasattr(result, 'details')
