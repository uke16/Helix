"""
Unit tests for the Evolution Project Manager module.

Tests cover:
- EvolutionProject creation and status management
- EvolutionProjectManager CRUD operations
- File detection (new/modified)
- Conflict detection
- Edge cases and error handling
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from project import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    create_project_manager,
)


@pytest.fixture
def temp_helix_root(tmp_path: Path) -> Path:
    """Create a temporary HELIX root directory."""
    helix_root = tmp_path / "helix-v4"
    helix_root.mkdir()
    (helix_root / "projects" / "evolution").mkdir(parents=True)
    return helix_root


@pytest.fixture
def manager(temp_helix_root: Path) -> EvolutionProjectManager:
    """Create an EvolutionProjectManager with temporary root."""
    return EvolutionProjectManager(helix_root=temp_helix_root)


@pytest.fixture
def sample_spec() -> dict:
    """Sample project specification."""
    return {
        "version": "1.0",
        "name": "test-feature",
        "type": "evolution",
        "description": "A test evolution feature",
        "goals": ["Add new functionality"],
        "requirements": ["Must be backwards compatible"],
    }


@pytest.fixture
def sample_phases() -> dict:
    """Sample project phases."""
    return {
        "version": "1.0",
        "phases": [
            {
                "id": "01-analysis",
                "name": "Analysis",
                "type": "development",
                "outputs": ["analysis.md"],
            },
            {
                "id": "02-implementation",
                "name": "Implementation",
                "type": "development",
                "outputs": ["new/src/helix/feature.py"],
            },
        ],
    }


class TestEvolutionStatus:
    """Tests for EvolutionStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert EvolutionStatus.PENDING.value == "pending"
        assert EvolutionStatus.DEVELOPING.value == "developing"
        assert EvolutionStatus.READY.value == "ready"
        assert EvolutionStatus.DEPLOYED.value == "deployed"
        assert EvolutionStatus.INTEGRATED.value == "integrated"
        assert EvolutionStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Test creating status from string value."""
        assert EvolutionStatus("pending") == EvolutionStatus.PENDING
        assert EvolutionStatus("ready") == EvolutionStatus.READY


class TestEvolutionProject:
    """Tests for EvolutionProject class."""

    def test_create_project(self, temp_helix_root: Path):
        """Test basic project creation."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        assert project.name == "test-project"
        assert project.session_id == "session-123"
        assert project.status == EvolutionStatus.PENDING
        assert project.path == project_path
        assert project.error is None

    def test_get_new_files_empty(self, temp_helix_root: Path):
        """Test getting new files when directory is empty."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)
        (project_path / "new").mkdir()

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        assert project.get_new_files() == []

    def test_get_new_files_with_content(self, temp_helix_root: Path):
        """Test getting new files when files exist."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        new_dir = project_path / "new" / "src" / "helix"
        new_dir.mkdir(parents=True)

        # Create test files
        (new_dir / "feature.py").write_text("# New feature")
        (new_dir / "utils.py").write_text("# Utils")

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        new_files = project.get_new_files()
        assert len(new_files) == 2
        assert Path("src/helix/feature.py") in new_files
        assert Path("src/helix/utils.py") in new_files

    def test_get_modified_files(self, temp_helix_root: Path):
        """Test getting modified files."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        modified_dir = project_path / "modified" / "src" / "helix"
        modified_dir.mkdir(parents=True)

        # Create modified file
        (modified_dir / "orchestrator.py").write_text("# Modified orchestrator")

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        modified_files = project.get_modified_files()
        assert len(modified_files) == 1
        assert Path("src/helix/orchestrator.py") in modified_files

    def test_get_all_files(self, temp_helix_root: Path):
        """Test getting all files."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        (project_path / "new" / "src").mkdir(parents=True)
        (project_path / "modified" / "src").mkdir(parents=True)

        (project_path / "new" / "src" / "new_file.py").write_text("# New")
        (project_path / "modified" / "src" / "modified_file.py").write_text("# Modified")

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        all_files = project.get_all_files()
        assert "new" in all_files
        assert "modified" in all_files
        assert len(all_files["new"]) == 1
        assert len(all_files["modified"]) == 1

    def test_update_status(self, temp_helix_root: Path):
        """Test updating project status."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        project.update_status(EvolutionStatus.DEVELOPING)

        assert project.status == EvolutionStatus.DEVELOPING

        # Check that status.json was written
        status_file = project_path / "status.json"
        assert status_file.exists()

        with open(status_file) as f:
            status_data = json.load(f)

        assert status_data["status"] == "developing"

    def test_update_status_with_error(self, temp_helix_root: Path):
        """Test updating status to FAILED with error message."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.DEVELOPING,
            path=project_path,
        )

        project.update_status(EvolutionStatus.FAILED, error="Tests failed")

        assert project.status == EvolutionStatus.FAILED
        assert project.error == "Tests failed"

        status_file = project_path / "status.json"
        with open(status_file) as f:
            status_data = json.load(f)

        assert status_data["error"] == "Tests failed"

    def test_get_spec(self, temp_helix_root: Path, sample_spec: dict):
        """Test loading spec.yaml."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        spec_file = project_path / "spec.yaml"
        spec_file.write_text(yaml.dump(sample_spec))

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        spec = project.get_spec()
        assert spec["name"] == "test-feature"
        assert spec["type"] == "evolution"

    def test_get_spec_not_found(self, temp_helix_root: Path):
        """Test error when spec.yaml doesn't exist."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        with pytest.raises(FileNotFoundError):
            project.get_spec()

    def test_get_phases(self, temp_helix_root: Path, sample_phases: dict):
        """Test loading phases.yaml."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        phases_file = project_path / "phases.yaml"
        phases_file.write_text(yaml.dump(sample_phases))

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.PENDING,
            path=project_path,
        )

        phases = project.get_phases()
        assert len(phases["phases"]) == 2
        assert phases["phases"][0]["id"] == "01-analysis"

    def test_to_dict(self, temp_helix_root: Path):
        """Test converting project to dictionary."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        (project_path / "new").mkdir(parents=True)
        (project_path / "modified").mkdir(parents=True)

        project = EvolutionProject(
            name="test-project",
            session_id="session-123",
            status=EvolutionStatus.READY,
            path=project_path,
        )

        result = project.to_dict()

        assert result["name"] == "test-project"
        assert result["session_id"] == "session-123"
        assert result["status"] == "ready"
        assert "created_at" in result
        assert "files" in result

    def test_from_path(self, temp_helix_root: Path):
        """Test loading project from path."""
        project_path = temp_helix_root / "projects" / "evolution" / "test-project"
        project_path.mkdir(parents=True)

        # Create status.json
        status_data = {
            "status": "ready",
            "session_id": "session-456",
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-02T15:30:00",
            "error": None,
        }
        (project_path / "status.json").write_text(json.dumps(status_data))

        project = EvolutionProject.from_path(project_path)

        assert project.name == "test-project"
        assert project.session_id == "session-456"
        assert project.status == EvolutionStatus.READY

    def test_from_path_not_found(self, temp_helix_root: Path):
        """Test error when loading from non-existent path."""
        project_path = temp_helix_root / "projects" / "evolution" / "nonexistent"
        project_path.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            EvolutionProject.from_path(project_path)


class TestEvolutionProjectManager:
    """Tests for EvolutionProjectManager class."""

    def test_init_creates_base_path(self, temp_helix_root: Path):
        """Test that init creates the base directory."""
        # Remove existing evolution dir
        evolution_path = temp_helix_root / "projects" / "evolution"
        evolution_path.rmdir()

        manager = EvolutionProjectManager(helix_root=temp_helix_root)

        assert manager.base_path.exists()
        assert manager.base_path == evolution_path

    def test_list_projects_empty(self, manager: EvolutionProjectManager):
        """Test listing projects when none exist."""
        projects = manager.list_projects()
        assert projects == []

    def test_create_project(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test creating a new project."""
        project = manager.create_project(
            name="my-feature",
            spec=sample_spec,
            phases=sample_phases,
            session_id="session-789",
        )

        assert project.name == "my-feature"
        assert project.session_id == "session-789"
        assert project.status == EvolutionStatus.PENDING
        assert project.path.exists()

        # Check directories were created
        assert (project.path / "new").exists()
        assert (project.path / "modified").exists()
        assert (project.path / "phases").exists()

        # Check files were created
        assert (project.path / "spec.yaml").exists()
        assert (project.path / "phases.yaml").exists()
        assert (project.path / "status.json").exists()

    def test_create_project_duplicate(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test error when creating duplicate project."""
        manager.create_project("my-feature", sample_spec, sample_phases)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_project("my-feature", sample_spec, sample_phases)

    def test_get_project(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test getting a project by name."""
        manager.create_project("my-feature", sample_spec, sample_phases)

        project = manager.get_project("my-feature")

        assert project is not None
        assert project.name == "my-feature"

    def test_get_project_not_found(self, manager: EvolutionProjectManager):
        """Test getting non-existent project."""
        project = manager.get_project("nonexistent")
        assert project is None

    def test_list_projects(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test listing multiple projects."""
        manager.create_project("feature-a", sample_spec, sample_phases)
        manager.create_project("feature-b", sample_spec, sample_phases)
        manager.create_project("feature-c", sample_spec, sample_phases)

        projects = manager.list_projects()

        assert len(projects) == 3
        names = [p.name for p in projects]
        assert "feature-a" in names
        assert "feature-b" in names
        assert "feature-c" in names

    def test_delete_project(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test deleting a project."""
        project = manager.create_project("to-delete", sample_spec, sample_phases)
        project_path = project.path

        result = manager.delete_project("to-delete")

        assert result is True
        assert not project_path.exists()

    def test_delete_project_not_found(self, manager: EvolutionProjectManager):
        """Test deleting non-existent project."""
        result = manager.delete_project("nonexistent")
        assert result is False

    def test_delete_active_project_fails(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test that deleting an active project fails."""
        project = manager.create_project("active", sample_spec, sample_phases)
        project.update_status(EvolutionStatus.DEVELOPING)

        with pytest.raises(ValueError, match="Cannot delete"):
            manager.delete_project("active")

    def test_delete_active_project_force(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test force deleting an active project."""
        project = manager.create_project("active", sample_spec, sample_phases)
        project.update_status(EvolutionStatus.DEVELOPING)

        result = manager.delete_project("active", force=True)

        assert result is True
        assert not project.path.exists()

    def test_get_projects_by_status(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test filtering projects by status."""
        p1 = manager.create_project("pending-1", sample_spec, sample_phases)
        p2 = manager.create_project("ready-1", sample_spec, sample_phases)
        p3 = manager.create_project("ready-2", sample_spec, sample_phases)

        p2.update_status(EvolutionStatus.READY)
        p3.update_status(EvolutionStatus.READY)

        pending = manager.get_projects_by_status(EvolutionStatus.PENDING)
        ready = manager.get_projects_by_status(EvolutionStatus.READY)

        assert len(pending) == 1
        assert len(ready) == 2

    def test_get_ready_projects(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test getting ready projects."""
        p1 = manager.create_project("pending", sample_spec, sample_phases)
        p2 = manager.create_project("ready", sample_spec, sample_phases)
        p2.update_status(EvolutionStatus.READY)

        ready = manager.get_ready_projects()

        assert len(ready) == 1
        assert ready[0].name == "ready"

    def test_get_active_deployment_none(self, manager: EvolutionProjectManager):
        """Test when no project is deployed."""
        deployment = manager.get_active_deployment()
        assert deployment is None

    def test_get_active_deployment(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test getting the currently deployed project."""
        p1 = manager.create_project("deployed", sample_spec, sample_phases)
        p1.update_status(EvolutionStatus.DEPLOYED)

        deployment = manager.get_active_deployment()

        assert deployment is not None
        assert deployment.name == "deployed"

    def test_check_conflicts_none(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test conflict check when no conflicts exist."""
        project = manager.create_project("project-a", sample_spec, sample_phases)

        conflicts = manager.check_conflicts(project)

        assert conflicts == {}

    def test_check_conflicts_detected(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test that file conflicts are detected."""
        p1 = manager.create_project("project-a", sample_spec, sample_phases)
        p2 = manager.create_project("project-b", sample_spec, sample_phases)

        # Create conflicting files
        (p1.path / "new" / "src").mkdir(parents=True)
        (p1.path / "new" / "src" / "shared.py").write_text("# Version A")

        (p2.path / "new" / "src").mkdir(parents=True)
        (p2.path / "new" / "src" / "shared.py").write_text("# Version B")

        conflicts = manager.check_conflicts(p1)

        assert "project-b" in conflicts
        assert "src/shared.py" in conflicts["project-b"]

    def test_check_conflicts_ignores_completed(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test that integrated/failed projects are ignored in conflict check."""
        p1 = manager.create_project("project-a", sample_spec, sample_phases)
        p2 = manager.create_project("project-b", sample_spec, sample_phases)
        p2.update_status(EvolutionStatus.INTEGRATED)

        # Create same file in both
        (p1.path / "new" / "src").mkdir(parents=True)
        (p1.path / "new" / "src" / "shared.py").write_text("# Version A")

        (p2.path / "new" / "src").mkdir(parents=True)
        (p2.path / "new" / "src" / "shared.py").write_text("# Version B")

        conflicts = manager.check_conflicts(p1)

        # project-b should be ignored because it's integrated
        assert "project-b" not in conflicts


class TestFactoryFunction:
    """Tests for the create_project_manager factory function."""

    def test_create_with_path(self, temp_helix_root: Path):
        """Test creating manager with custom path."""
        manager = create_project_manager(helix_root=temp_helix_root)

        assert manager.helix_root == temp_helix_root
        assert manager.base_path == temp_helix_root / "projects" / "evolution"

    def test_create_default_path(self):
        """Test creating manager with default path."""
        manager = create_project_manager()

        assert manager.helix_root == Path("/home/aiuser01/helix-v4")


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_project_lifecycle(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test the complete project lifecycle."""
        # 1. Create project
        project = manager.create_project(
            name="lifecycle-test",
            spec=sample_spec,
            phases=sample_phases,
            session_id="integration-test",
        )
        assert project.status == EvolutionStatus.PENDING

        # 2. Start development
        project.update_status(EvolutionStatus.DEVELOPING)
        assert project.status == EvolutionStatus.DEVELOPING

        # 3. Add new files
        new_file = project.path / "new" / "src" / "helix" / "new_feature.py"
        new_file.parent.mkdir(parents=True, exist_ok=True)
        new_file.write_text("# New feature implementation")

        # 4. Add modified files
        mod_file = project.path / "modified" / "src" / "helix" / "orchestrator.py"
        mod_file.parent.mkdir(parents=True, exist_ok=True)
        mod_file.write_text("# Modified orchestrator")

        # 5. Mark as ready
        project.update_status(EvolutionStatus.READY)
        assert len(project.get_new_files()) == 1
        assert len(project.get_modified_files()) == 1

        # 6. Deploy
        project.update_status(EvolutionStatus.DEPLOYED)
        assert manager.get_active_deployment() is not None

        # 7. Integrate
        project.update_status(EvolutionStatus.INTEGRATED)
        assert project.status == EvolutionStatus.INTEGRATED

        # 8. Verify final state
        reloaded = manager.get_project("lifecycle-test")
        assert reloaded is not None
        assert reloaded.status == EvolutionStatus.INTEGRATED

    def test_failed_project_workflow(
        self,
        manager: EvolutionProjectManager,
        sample_spec: dict,
        sample_phases: dict,
    ):
        """Test workflow when project fails."""
        project = manager.create_project("failing-test", sample_spec, sample_phases)

        project.update_status(EvolutionStatus.DEVELOPING)
        project.update_status(EvolutionStatus.DEPLOYED)

        # Simulate failure
        project.update_status(
            EvolutionStatus.FAILED,
            error="Unit tests failed: 3 errors in test_feature.py"
        )

        assert project.status == EvolutionStatus.FAILED
        assert "Unit tests failed" in project.error

        # Verify persistence
        reloaded = manager.get_project("failing-test")
        assert reloaded.error == project.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
