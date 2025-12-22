"""Tests for ADR functionality in EvolutionProject.

Tests the get_adr() method and get_spec() fallback behavior that enables
ADRs to serve as the Single Source of Truth for evolution projects.

See ADR-012: ADR als Single Source of Truth für Evolution Workflows
"""

import tempfile
from pathlib import Path

import pytest

from helix.evolution.project import (
    EvolutionProject,
    EvolutionStatus,
)


# Sample ADR content for testing
SAMPLE_ADR_CONTENT = """\
---
adr_id: "999"
title: "Test Feature ADR"
status: Proposed

component_type: TOOL
classification: NEW
change_scope: minor

domain: helix
language: python
skills:
  - helix
  - testing

files:
  create:
    - src/helix/test_feature.py
    - tests/test_test_feature.py
  modify:
    - src/helix/__init__.py
  docs:
    - docs/TEST_FEATURE.md

depends_on: []
---

# ADR-999: Test Feature ADR

## Kontext

This is a test ADR for testing the get_adr() functionality.

## Entscheidung

We will implement the test feature as described.

## Implementation

```python
def test_feature():
    return "Hello World"
```

## Dokumentation

- docs/TEST_FEATURE.md

## Akzeptanzkriterien

- [ ] Feature implemented
- [ ] Tests pass
- [ ] Documentation updated

## Konsequenzen

### Positiv

- Better testing

### Negativ

- None
"""

SAMPLE_ADR_MINIMAL = """\
---
adr_id: "001"
title: "Minimal ADR"
status: Accepted

files:
  create:
    - src/minimal.py
---

# ADR-001: Minimal ADR

## Kontext

Minimal test.

## Entscheidung

Implement minimal feature.

## Implementation

Minimal implementation.

## Dokumentation

None.

## Akzeptanzkriterien

- [ ] Done

## Konsequenzen

None.
"""


@pytest.fixture
def temp_helix_root():
    """Create a temporary HELIX root directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        helix_root = Path(tmpdir)
        (helix_root / "projects" / "evolution").mkdir(parents=True)
        yield helix_root


@pytest.fixture
def project_with_adr(temp_helix_root):
    """Create a project with an ADR file."""
    base_path = temp_helix_root / "projects" / "evolution"
    spec = {"name": "Legacy Spec"}

    project = EvolutionProject.create(
        base_path=base_path,
        name="with-adr",
        spec=spec,
    )

    # Add ADR file
    adr_path = project.path / "ADR-test-feature.md"
    adr_path.write_text(SAMPLE_ADR_CONTENT)

    return project


@pytest.fixture
def project_with_numbered_adr(temp_helix_root):
    """Create a project with a numbered ADR file (NNN-name.md format)."""
    base_path = temp_helix_root / "projects" / "evolution"
    spec = {"name": "Legacy Spec"}

    project = EvolutionProject.create(
        base_path=base_path,
        name="with-numbered-adr",
        spec=spec,
    )

    # Add numbered ADR file (like in adr/ directory)
    adr_path = project.path / "999-test-feature.md"
    adr_path.write_text(SAMPLE_ADR_CONTENT)

    return project


@pytest.fixture
def project_without_adr(temp_helix_root):
    """Create a project without an ADR file (legacy spec.yaml only)."""
    base_path = temp_helix_root / "projects" / "evolution"
    spec = {
        "name": "Legacy Feature",
        "description": "A feature using old spec.yaml format",
        "output": ["src/legacy.py"],
    }

    project = EvolutionProject.create(
        base_path=base_path,
        name="without-adr",
        spec=spec,
    )

    return project


class TestGetADR:
    """Tests for the get_adr() method."""

    def test_get_adr_returns_parsed_document(self, project_with_adr):
        """Test that get_adr() returns a parsed ADRDocument."""
        adr = project_with_adr.get_adr()

        assert adr is not None
        assert adr.metadata.adr_id == "999"
        assert adr.metadata.title == "Test Feature ADR"

    def test_get_adr_with_numbered_format(self, project_with_numbered_adr):
        """Test that get_adr() finds NNN-name.md format files."""
        adr = project_with_numbered_adr.get_adr()

        assert adr is not None
        assert adr.metadata.adr_id == "999"

    def test_get_adr_returns_none_when_no_adr(self, project_without_adr):
        """Test that get_adr() returns None when no ADR exists."""
        adr = project_without_adr.get_adr()

        assert adr is None

    def test_get_adr_metadata_fields(self, project_with_adr):
        """Test that ADR metadata fields are correctly parsed."""
        adr = project_with_adr.get_adr()

        assert adr.metadata.domain == "helix"
        assert adr.metadata.language == "python"
        assert "helix" in adr.metadata.skills
        assert "testing" in adr.metadata.skills

    def test_get_adr_files_create(self, project_with_adr):
        """Test that files.create is correctly parsed from ADR."""
        adr = project_with_adr.get_adr()

        assert len(adr.metadata.files.create) == 2
        assert "src/helix/test_feature.py" in adr.metadata.files.create
        assert "tests/test_test_feature.py" in adr.metadata.files.create

    def test_get_adr_files_modify(self, project_with_adr):
        """Test that files.modify is correctly parsed from ADR."""
        adr = project_with_adr.get_adr()

        assert len(adr.metadata.files.modify) == 1
        assert "src/helix/__init__.py" in adr.metadata.files.modify

    def test_get_adr_acceptance_criteria(self, project_with_adr):
        """Test that acceptance criteria are extracted from ADR."""
        adr = project_with_adr.get_adr()

        assert len(adr.acceptance_criteria) == 3
        assert any("Feature implemented" in c.text for c in adr.acceptance_criteria)
        assert all(not c.checked for c in adr.acceptance_criteria)


class TestGetSpecWithADRFallback:
    """Tests for get_spec() with ADR as primary source."""

    def test_get_spec_prefers_adr(self, project_with_adr):
        """Test that get_spec() prefers ADR over spec.yaml."""
        spec = project_with_adr.get_spec()

        assert spec is not None
        # ADR values should be used
        assert spec["meta"]["id"] == "999"
        assert spec["meta"]["name"] == "Test Feature ADR"

    def test_get_spec_falls_back_to_spec_yaml(self, project_without_adr):
        """Test that get_spec() falls back to spec.yaml when no ADR."""
        spec = project_without_adr.get_spec()

        assert spec is not None
        # Legacy spec.yaml values should be used
        assert spec["name"] == "Legacy Feature"
        assert "output" in spec

    def test_get_spec_includes_domain_from_adr(self, project_with_adr):
        """Test that domain is extracted from ADR for skill loading."""
        spec = project_with_adr.get_spec()

        assert spec["meta"]["domain"] == "helix"

    def test_get_spec_includes_language_from_adr(self, project_with_adr):
        """Test that language is extracted from ADR."""
        spec = project_with_adr.get_spec()

        assert spec["meta"]["language"] == "python"

    def test_get_spec_includes_skills_from_adr(self, project_with_adr):
        """Test that skills list is extracted from ADR."""
        spec = project_with_adr.get_spec()

        assert "helix" in spec["context"]["skills"]
        assert "testing" in spec["context"]["skills"]

    def test_get_spec_includes_files_from_adr(self, project_with_adr):
        """Test that output files are extracted from ADR files.create."""
        spec = project_with_adr.get_spec()

        assert "src/helix/test_feature.py" in spec["output"]["files"]
        assert "tests/test_test_feature.py" in spec["output"]["files"]


class TestADREdgeCases:
    """Tests for edge cases in ADR handling."""

    def test_multiple_adr_files_uses_first(self, temp_helix_root):
        """Test behavior when multiple ADR files exist."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}

        project = EvolutionProject.create(base_path, "multi-adr", spec)

        # Create multiple ADR files
        (project.path / "ADR-feature-a.md").write_text(SAMPLE_ADR_CONTENT)
        (project.path / "ADR-feature-b.md").write_text(SAMPLE_ADR_MINIMAL)

        # Should find at least one ADR
        adr = project.get_adr()
        assert adr is not None
        assert adr.metadata.adr_id in ["999", "001"]

    def test_invalid_adr_returns_none(self, temp_helix_root):
        """Test that invalid ADR file returns None gracefully."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}

        project = EvolutionProject.create(base_path, "invalid-adr", spec)

        # Create invalid ADR file (no YAML header)
        (project.path / "ADR-invalid.md").write_text("# Just a markdown file\n\nNo YAML header here.")

        # Should return None, not raise exception
        adr = project.get_adr()
        assert adr is None

    def test_adr_with_minimal_metadata(self, temp_helix_root):
        """Test ADR with only required fields."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}

        project = EvolutionProject.create(base_path, "minimal-adr", spec)

        (project.path / "ADR-minimal.md").write_text(SAMPLE_ADR_MINIMAL)

        adr = project.get_adr()
        assert adr is not None
        assert adr.metadata.adr_id == "001"
        assert adr.metadata.title == "Minimal ADR"

    def test_get_spec_returns_none_when_no_adr_or_spec(self, temp_helix_root):
        """Test get_spec() returns None when neither ADR nor spec.yaml exists."""
        base_path = temp_helix_root / "projects" / "evolution"

        # Manually create project structure without spec.yaml
        project_path = base_path / "empty-project"
        project_path.mkdir(parents=True)
        (project_path / "new").mkdir()
        (project_path / "modified").mkdir()

        # Create minimal status.json
        import json
        with open(project_path / "status.json", "w") as f:
            json.dump({"status": "pending"}, f)

        project = EvolutionProject(project_path)

        spec = project.get_spec()
        assert spec is None


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with spec.yaml projects."""

    def test_legacy_project_still_works(self, project_without_adr):
        """Test that projects using spec.yaml still work correctly."""
        # Should be able to get spec
        spec = project_without_adr.get_spec()
        assert spec is not None
        assert spec["name"] == "Legacy Feature"

        # Should be able to get status
        status = project_without_adr.get_status()
        assert status == EvolutionStatus.PENDING

        # Should be able to add files
        project_without_adr.add_new_file(Path("src/test.py"), "# test")
        files = project_without_adr.list_new_files()
        assert len(files) == 1

    def test_spec_yaml_not_required_when_adr_exists(self, temp_helix_root):
        """Test that spec.yaml is optional when ADR exists."""
        base_path = temp_helix_root / "projects" / "evolution"

        # Create project structure manually without spec.yaml
        project_path = base_path / "adr-only-project"
        project_path.mkdir(parents=True)
        (project_path / "new").mkdir()
        (project_path / "modified").mkdir()

        import json
        with open(project_path / "status.json", "w") as f:
            json.dump({"status": "pending"}, f)

        # Add only ADR
        (project_path / "ADR-feature.md").write_text(SAMPLE_ADR_CONTENT)

        project = EvolutionProject(project_path)

        # Should get spec from ADR
        spec = project.get_spec()
        assert spec is not None
        assert spec["meta"]["id"] == "999"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
