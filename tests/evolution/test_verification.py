"""Tests for phase verification system."""

import pytest
from pathlib import Path
import tempfile
import shutil

from helix.evolution.verification import PhaseVerifier, VerificationResult


class TestVerificationResult:
    """Test VerificationResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = VerificationResult(
            success=True,
            found_files=["src/module.py"],
            message="All files found"
        )
        assert result.success is True
        assert len(result.missing_files) == 0
        assert len(result.syntax_errors) == 0
    
    def test_failure_result(self):
        """Test creating a failed result."""
        result = VerificationResult(
            success=False,
            missing_files=["src/missing.py"],
            syntax_errors={"src/bad.py": "Line 5: invalid syntax"},
            message="Verification failed"
        )
        assert result.success is False
        assert "missing.py" in result.missing_files[0]
        assert "bad.py" in list(result.syntax_errors.keys())[0]
    
    def test_to_dict(self):
        """Test JSON serialization."""
        result = VerificationResult(
            success=True,
            found_files=["a.py"],
            message="OK"
        )
        d = result.to_dict()
        assert d["success"] is True
        assert "a.py" in d["found_files"]


class TestPhaseVerifier:
    """Test PhaseVerifier class."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        project = tmp_path / "test-project"
        project.mkdir()
        
        # Create phase directory
        phase_dir = project / "phases" / "1"
        phase_dir.mkdir(parents=True)
        
        # Create output directory
        output_dir = phase_dir / "output"
        output_dir.mkdir()
        
        return project, phase_dir, output_dir
    
    def test_verify_no_expected_files(self, temp_project):
        """Test verification with no expected files."""
        project, phase_dir, _ = temp_project
        
        verifier = PhaseVerifier(project)
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=[]
        )
        
        assert result.success is True
        assert "No expected files" in result.message
    
    def test_verify_file_exists_in_output(self, temp_project):
        """Test finding file in output/ directory."""
        project, phase_dir, output_dir = temp_project
        
        # Create expected file
        (output_dir / "src").mkdir(parents=True)
        (output_dir / "src" / "module.py").write_text("# Python file")
        
        verifier = PhaseVerifier(project)
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=["src/module.py"]
        )
        
        assert result.success is True
        assert len(result.found_files) == 1
    
    def test_verify_file_missing(self, temp_project):
        """Test detecting missing file."""
        project, phase_dir, _ = temp_project
        
        verifier = PhaseVerifier(project)
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=["src/nonexistent.py"]
        )
        
        assert result.success is False
        assert "nonexistent.py" in result.missing_files[0]
    
    def test_verify_syntax_error(self, temp_project):
        """Test detecting Python syntax errors."""
        project, phase_dir, output_dir = temp_project
        
        # Create file with syntax error
        bad_file = output_dir / "bad.py"
        bad_file.write_text("def broken(\n  # missing close paren")
        
        verifier = PhaseVerifier(project)
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=["bad.py"]
        )
        
        assert result.success is False
        assert len(result.syntax_errors) == 1
    
    def test_verify_valid_python(self, temp_project):
        """Test valid Python passes syntax check."""
        project, phase_dir, output_dir = temp_project
        
        # Create valid Python file
        good_file = output_dir / "good.py"
        good_file.write_text("def hello():\n    return 'world'\n")
        
        verifier = PhaseVerifier(project)
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=["good.py"]
        )
        
        assert result.success is True
        assert len(result.syntax_errors) == 0
    
    def test_verify_strips_prefixes(self, temp_project):
        """Test that new/ and modified/ prefixes are handled."""
        project, phase_dir, output_dir = temp_project
        
        # Create file
        (output_dir / "src").mkdir(parents=True)
        (output_dir / "src" / "module.py").write_text("# OK")
        
        verifier = PhaseVerifier(project)
        
        # Should find file even with new/ prefix
        result = verifier.verify_phase_output(
            phase_id="1",
            phase_dir=phase_dir,
            expected_files=["new/src/module.py"]
        )
        
        assert result.success is True


class TestRetryPrompt:
    """Test retry prompt generation."""
    
    def test_format_retry_prompt_missing(self):
        """Test prompt for missing files."""
        verifier = PhaseVerifier(Path("/tmp"))
        result = VerificationResult(
            success=False,
            missing_files=["src/module.py"],
            message="Failed"
        )
        
        prompt = verifier.format_retry_prompt(result, retry_number=1)
        
        assert "Missing Files" in prompt
        assert "src/module.py" in prompt
        assert "Retry 1 of 2" in prompt
    
    def test_format_retry_prompt_syntax(self):
        """Test prompt for syntax errors."""
        verifier = PhaseVerifier(Path("/tmp"))
        result = VerificationResult(
            success=False,
            syntax_errors={"src/bad.py": "Line 5: invalid syntax"},
            message="Failed"
        )
        
        prompt = verifier.format_retry_prompt(result, retry_number=2)
        
        assert "Syntax Errors" in prompt
        assert "src/bad.py" in prompt
        assert "Retry 2 of 2" in prompt
        assert "last retry" in prompt.lower()
    
    def test_write_retry_file(self, tmp_path):
        """Test writing VERIFICATION_ERRORS.md."""
        verifier = PhaseVerifier(tmp_path)
        result = VerificationResult(
            success=False,
            missing_files=["module.py"],
            message="Failed"
        )
        
        file_path = verifier.write_retry_file(tmp_path, result)
        
        assert file_path.exists()
        assert file_path.name == "VERIFICATION_ERRORS.md"
        content = file_path.read_text()
        assert "module.py" in content


class TestVerificationIntegration:
    """Integration tests for verification in streaming."""
    
    def test_verification_result_serializable(self):
        """Test that VerificationResult can be serialized for events."""
        result = VerificationResult(
            success=False,
            missing_files=["src/module.py"],
            syntax_errors={"bad.py": "Line 1: error"},
            found_files=["existing.py"],
            message="Test message"
        )
        
        d = result.to_dict()
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(d)
        assert "module.py" in json_str
        assert "bad.py" in json_str
    
    def test_retry_prompt_includes_all_errors(self):
        """Test that retry prompt includes all error types."""
        verifier = PhaseVerifier(Path("/tmp"))
        result = VerificationResult(
            success=False,
            missing_files=["a.py", "b.py"],
            syntax_errors={"c.py": "error1", "d.py": "error2"},
            message="Multiple errors"
        )
        
        prompt = verifier.format_retry_prompt(result, retry_number=1, max_retries=2)
        
        # Check all files mentioned
        assert "a.py" in prompt
        assert "b.py" in prompt
        assert "c.py" in prompt
        assert "d.py" in prompt
        
        # Check sections exist
        assert "Missing Files" in prompt
        assert "Syntax Errors" in prompt
    
    def test_max_retries_in_prompt(self):
        """Test that last retry shows warning."""
        verifier = PhaseVerifier(Path("/tmp"))
        result = VerificationResult(success=False, missing_files=["x.py"], message="")
        
        # First retry - no warning
        prompt1 = verifier.format_retry_prompt(result, retry_number=1, max_retries=2)
        assert "last retry" not in prompt1.lower()
        
        # Second (last) retry - warning
        prompt2 = verifier.format_retry_prompt(result, retry_number=2, max_retries=2)
        assert "last retry" in prompt2.lower()
