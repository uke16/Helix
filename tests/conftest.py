import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)

@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure."""
    project = temp_dir / "test-project"
    project.mkdir()
    (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Project
  domain: helix
implementation:
  language: python
  summary: A test project
""")
    (project / "phases.yaml").write_text("""
phases:
  - id: 01-test
    name: Test Phase
    type: development
""")
    return project

@pytest.fixture
def sample_spec():
    """Return sample spec dictionary."""
    return {
        "meta": {
            "id": "test-project",
            "name": "Test Project",
            "domain": "helix",
        },
        "implementation": {
            "language": "python",
            "summary": "A test project",
        },
    }

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": [{"type": "text", "text": "Test response"}],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
