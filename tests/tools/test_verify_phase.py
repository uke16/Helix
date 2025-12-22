"""Tests for verify_phase tool."""

import pytest
from pathlib import Path
import tempfile
import yaml

from helix.tools.verify_phase import (
    verify_phase_output,
    _find_project_root,
    _load_expected_files,
)


class TestVerifyPhaseOutput:
    """Test verify_phase_output function."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with phases."""
        project = tmp_path / "project"
        project.mkdir()
        
        # Create phases.yaml
        phases_yaml = {
            "phases": [
                {
                    "id": "1",
                    "name": "Test Phase",
                    "output": ["src/module.py", "tests/test_module.py"]
                }
            ]
        }
        (project / "phases.yaml").write_text(yaml.dump(phases_yaml))
        
        # Create phase directory
        phase_dir = project / "phases" / "1"
        phase_dir.mkdir(parents=True)
        output_dir = phase_dir / "output"
        output_dir.mkdir()
        
        return project, phase_dir, output_dir
    
    def test_verify_with_explicit_files(self, temp_project):
        """Test verification with explicitly provided files."""
        project, phase_dir, output_dir = temp_project
        
        # Create expected file
        (output_dir / "module.py").write_text("# OK")
        
        result = verify_phase_output(
            expected_files=["module.py"],
            phase_dir=str(phase_dir),
            project_dir=str(project)
        )
        
        assert result["success"] is True
        assert len(result["found"]) == 1
    
    def test_verify_missing_file(self, temp_project):
        """Test verification with missing file."""
        project, phase_dir, _ = temp_project
        
        result = verify_phase_output(
            expected_files=["nonexistent.py"],
            phase_dir=str(phase_dir),
            project_dir=str(project)
        )
        
        assert result["success"] is False
        assert "nonexistent.py" in result["missing"][0]
    
    def test_verify_syntax_error(self, temp_project):
        """Test verification catches syntax errors."""
        project, phase_dir, output_dir = temp_project
        
        # Create file with syntax error
        (output_dir / "bad.py").write_text("def broken(\n")
        
        result = verify_phase_output(
            expected_files=["bad.py"],
            phase_dir=str(phase_dir),
            project_dir=str(project)
        )
        
        assert result["success"] is False
        assert len(result["syntax_errors"]) == 1


class TestFindProjectRoot:
    """Test _find_project_root function."""
    
    def test_finds_phases_yaml(self, tmp_path):
        """Test finding project by phases.yaml."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "phases.yaml").write_text("phases: []")
        
        phase_dir = project / "phases" / "1"
        phase_dir.mkdir(parents=True)
        
        result = _find_project_root(phase_dir)
        assert result == project
    
    def test_finds_adr_files(self, tmp_path):
        """Test finding project by ADR files."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "ADR-test.md").write_text("# ADR")
        
        phase_dir = project / "sub" / "dir"
        phase_dir.mkdir(parents=True)
        
        result = _find_project_root(phase_dir)
        assert result == project


class TestLoadExpectedFiles:
    """Test _load_expected_files function."""
    
    def test_loads_from_phases_yaml(self, tmp_path):
        """Test loading expected files from phases.yaml."""
        project = tmp_path
        
        phases_yaml = {
            "phases": [
                {"id": "1", "output": ["a.py", "b.py"]},
                {"id": "2", "output": ["c.py"]}
            ]
        }
        (project / "phases.yaml").write_text(yaml.dump(phases_yaml))
        
        phase_dir = project / "phases" / "1"
        phase_dir.mkdir(parents=True)
        
        result = _load_expected_files(project, phase_dir)
        
        assert result == ["a.py", "b.py"]
    
    def test_returns_none_without_phases_yaml(self, tmp_path):
        """Test returns None when no phases.yaml."""
        result = _load_expected_files(tmp_path, tmp_path)
        assert result is None
