"""Pytest configuration for evolution ADR system tests.

This conftest.py documents the testing setup for the ADR evolution project.

IMPORTANT: Run tests with --import-mode=importlib to properly resolve imports:
    pytest tests/adr/ -v --import-mode=importlib

Or run from this directory:
    cd projects/evolution/adr-system/new
    python -m pytest tests/adr/ -v --rootdir=. --import-mode=importlib

The import mode is needed because:
1. The evolution project has its own helix package in new/src/ with adr and quality_gates
2. The importlib mode properly handles the package namespace during test collection
"""

import sys
from pathlib import Path

# Set up import paths
_test_dir = Path(__file__).parent
_new_src = _test_dir.parent / "src"

# Add new src so helix.adr is found
if str(_new_src) not in sys.path:
    sys.path.insert(0, str(_new_src))


# ============================================================================
# Global Test Fixtures
# ============================================================================

import pytest
import tempfile
import shutil
from unittest.mock import MagicMock


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests.
    
    This is an alias for pytest's built-in tmp_path fixture,
    provided for backward compatibility with tests using temp_dir.
    """
    return tmp_path


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample HELIX project structure for testing."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    # Create phases.yaml
    phases_yaml = project_dir / "phases.yaml"
    phases_yaml.write_text("""
name: test-project
description: Test project for unit tests
project_type: helix_internal
complexity: simple

phases:
  - id: development
    name: "Development"
    type: development
    output:
      files:
        - "output.py"
    quality_gate:
      type: files_exist
""")
    
    # Create status.json
    status_json = project_dir / "status.json"
    status_json.write_text("""{
  "project_id": "test-project",
  "status": "pending",
  "phases": {"development": "pending"}
}""")
    
    # Create phases directory
    phases_dir = project_dir / "phases" / "development" / "output"
    phases_dir.mkdir(parents=True)
    
    return project_dir


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response for testing."""
    response = MagicMock()
    response.content = "Test response from LLM"
    response.model = "test-model"
    response.usage = MagicMock(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    return response
