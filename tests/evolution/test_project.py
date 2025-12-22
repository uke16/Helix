"""Tests for EvolutionProject and EvolutionProjectManager."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from helix.evolution.project import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    EvolutionError,
)


@pytest.fixture
def temp_helix_root():
    """Create a temporary HELIX root directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        helix_root = Path(tmpdir)
        (helix_root / "projects" / "evolution").mkdir(parents=True)
        yield helix_root


@pytest.fixture
def manager(temp_helix_root):
    """Create a project manager with temp root."""
    return EvolutionProjectManager(helix_root=temp_helix_root)


class TestEvolutionProject:
    """Tests for EvolutionProject class."""

    def test_create_project(self, temp_helix_root):
        """Test creating a new project."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test Feature", "description": "A test"}
        
        project = EvolutionProject.create(
            base_path=base_path,
            name="test-feature",
            spec=spec,
        )
        
        assert project.name == "test-feature"
        assert project.path.exists()
        assert (project.path / "spec.yaml").exists()
        assert (project.path / "status.json").exists()
        assert (project.path / "new").exists()
        assert (project.path / "modified").exists()

    def test_create_project_with_phases(self, temp_helix_root):
        """Test creating project with phases."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        phases = {"phases": [{"id": "1", "name": "Phase 1"}]}
        
        project = EvolutionProject.create(
            base_path=base_path,
            name="with-phases",
            spec=spec,
            phases=phases,
        )
        
        assert (project.path / "phases.yaml").exists()
        loaded_phases = project.get_phases()
        assert loaded_phases["phases"][0]["id"] == "1"

    def test_create_duplicate_fails(self, temp_helix_root):
        """Test that creating duplicate project fails."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        EvolutionProject.create(base_path, "duplicate", spec)
        
        with pytest.raises(EvolutionError):
            EvolutionProject.create(base_path, "duplicate", spec)

    def test_sanitize_project_name(self, temp_helix_root):
        """Test project name sanitization."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        # Spaces and special chars should be removed
        project = EvolutionProject.create(
            base_path=base_path,
            name="Test Feature!@#$",
            spec=spec,
        )
        
        assert project.name == "testfeature"

    def test_get_status(self, temp_helix_root):
        """Test getting project status."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "status-test", spec)
        
        assert project.get_status() == EvolutionStatus.PENDING

    def test_set_status(self, temp_helix_root):
        """Test setting project status."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "set-status", spec)
        
        project.set_status(EvolutionStatus.DEVELOPING, current_phase="1.1")
        
        assert project.get_status() == EvolutionStatus.DEVELOPING
        data = project.get_status_data()
        assert data["current_phase"] == "1.1"

    def test_set_status_with_error(self, temp_helix_root):
        """Test setting failed status with error."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "error-test", spec)
        
        project.set_status(
            EvolutionStatus.FAILED,
            error="Syntax error in module.py",
        )
        
        assert project.get_status() == EvolutionStatus.FAILED
        data = project.get_status_data()
        assert "Syntax error" in data["error"]

    def test_add_new_file(self, temp_helix_root):
        """Test adding a new file."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "new-file", spec)
        
        file_path = project.add_new_file(
            Path("src/helix/evolution/new_module.py"),
            "# New module\nprint('hello')",
        )
        
        assert file_path.exists()
        assert file_path.read_text() == "# New module\nprint('hello')"

    def test_add_modified_file(self, temp_helix_root):
        """Test adding a modified file."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "mod-file", spec)
        
        file_path = project.add_modified_file(
            Path("src/helix/orchestrator.py"),
            "# Modified orchestrator",
        )
        
        assert file_path.exists()
        assert "Modified" in file_path.read_text()

    def test_list_new_files(self, temp_helix_root):
        """Test listing new files."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "list-new", spec)
        
        project.add_new_file(Path("src/a.py"), "a")
        project.add_new_file(Path("src/b.py"), "b")
        project.add_new_file(Path("tests/test_a.py"), "test")
        
        files = project.list_new_files()
        
        assert len(files) == 3
        assert Path("src/a.py") in files

    def test_list_modified_files(self, temp_helix_root):
        """Test listing modified files."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "list-mod", spec)
        
        project.add_modified_file(Path("src/x.py"), "x")
        project.add_modified_file(Path("src/y.py"), "y")
        
        files = project.list_modified_files()
        
        assert len(files) == 2

    def test_get_file_count(self, temp_helix_root):
        """Test getting file counts."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "count", spec)
        
        project.add_new_file(Path("a.py"), "a")
        project.add_new_file(Path("b.py"), "b")
        project.add_modified_file(Path("c.py"), "c")
        
        counts = project.get_file_count()
        
        assert counts["new"] == 2
        assert counts["modified"] == 1

    def test_to_dict(self, temp_helix_root):
        """Test converting project to dict."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "to-dict", spec)
        project.add_new_file(Path("a.py"), "a")
        
        data = project.to_dict()
        
        assert data["name"] == "to-dict"
        assert data["status"] == "pending"
        assert data["files"]["new"] == 1
        assert "created_at" in data

    def test_delete_project(self, temp_helix_root):
        """Test deleting a project."""
        base_path = temp_helix_root / "projects" / "evolution"
        spec = {"name": "Test"}
        
        project = EvolutionProject.create(base_path, "to-delete", spec)
        project_path = project.path
        
        project.delete()
        
        assert not project_path.exists()


class TestEvolutionProjectManager:
    """Tests for EvolutionProjectManager class."""

    def test_list_empty(self, manager):
        """Test listing with no projects."""
        projects = manager.list_projects()
        assert projects == []

    def test_create_and_list(self, manager):
        """Test creating and listing projects."""
        spec = {"name": "Feature A"}
        
        manager.create_project("feature-a", spec)
        manager.create_project("feature-b", spec)
        
        projects = manager.list_projects()
        
        assert len(projects) == 2
        names = [p.name for p in projects]
        assert "feature-a" in names
        assert "feature-b" in names

    def test_get_project(self, manager):
        """Test getting a project by name."""
        spec = {"name": "Test"}
        
        manager.create_project("get-me", spec)
        
        project = manager.get_project("get-me")
        
        assert project is not None
        assert project.name == "get-me"

    def test_get_nonexistent_project(self, manager):
        """Test getting a nonexistent project."""
        project = manager.get_project("nonexistent")
        
        assert project is None

    def test_delete_project(self, manager):
        """Test deleting a project via manager."""
        spec = {"name": "Test"}
        
        manager.create_project("delete-me", spec)
        
        result = manager.delete_project("delete-me")
        
        assert result is True
        assert manager.get_project("delete-me") is None

    def test_delete_nonexistent(self, manager):
        """Test deleting nonexistent project."""
        result = manager.delete_project("nope")
        
        assert result is False

    def test_get_projects_by_status(self, manager):
        """Test filtering projects by status."""
        spec = {"name": "Test"}
        
        p1 = manager.create_project("pending-1", spec)
        p2 = manager.create_project("ready-1", spec)
        p2.set_status(EvolutionStatus.READY)
        p3 = manager.create_project("ready-2", spec)
        p3.set_status(EvolutionStatus.READY)
        
        ready = manager.get_projects_by_status(EvolutionStatus.READY)
        
        assert len(ready) == 2
        assert all(p.get_status() == EvolutionStatus.READY for p in ready)

    def test_get_ready_projects(self, manager):
        """Test getting ready projects."""
        spec = {"name": "Test"}
        
        p1 = manager.create_project("not-ready", spec)
        p2 = manager.create_project("is-ready", spec)
        p2.set_status(EvolutionStatus.READY)
        
        ready = manager.get_ready_projects()
        
        assert len(ready) == 1
        assert ready[0].name == "is-ready"

    def test_get_deployed_project(self, manager):
        """Test getting deployed project."""
        spec = {"name": "Test"}
        
        p1 = manager.create_project("not-deployed", spec)
        p2 = manager.create_project("deployed-one", spec)
        p2.set_status(EvolutionStatus.DEPLOYED)
        
        deployed = manager.get_deployed_project()
        
        assert deployed is not None
        assert deployed.name == "deployed-one"

    def test_get_deployed_project_none(self, manager):
        """Test getting deployed project when none deployed."""
        spec = {"name": "Test"}
        
        manager.create_project("just-pending", spec)
        
        deployed = manager.get_deployed_project()
        
        assert deployed is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
