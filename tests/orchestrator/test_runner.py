"""Tests for OrchestratorRunner."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from helix.orchestrator.runner import OrchestratorRunner, RunConfig
from helix.orchestrator.status import StatusTracker, ProjectStatus, PhaseStatus
from helix.orchestrator.phase_executor import PhaseExecutor, PhaseResult
from helix.orchestrator.data_flow import DataFlowManager


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        # Create phases.yaml
        phases_yaml = {
            "project": {"name": "test-project", "type": "simple"},
            "phases": [
                {"id": "phase1", "type": "development"},
                {"id": "phase2", "type": "development", "input_from": ["phase1"]},
            ],
        }
        with open(project_dir / "phases.yaml", "w") as f:
            yaml.dump(phases_yaml, f)

        # Create phase directories
        for phase_id in ["phase1", "phase2"]:
            phase_dir = project_dir / "phases" / phase_id
            (phase_dir / "input").mkdir(parents=True)
            (phase_dir / "output").mkdir(parents=True)
            (phase_dir / "CLAUDE.md").write_text(f"# Phase {phase_id}\n")

        yield project_dir


@pytest.fixture
def mock_executor():
    """Create a mock PhaseExecutor."""
    executor = MagicMock(spec=PhaseExecutor)

    async def mock_execute(*args, **kwargs):
        from datetime import datetime
        return PhaseResult(
            phase_id=kwargs.get("phase_config", MagicMock()).id,
            success=True,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_seconds=0.1,
        )

    executor.execute = AsyncMock(side_effect=mock_execute)
    return executor


class TestRunConfig:
    """Tests for RunConfig."""

    def test_default_values(self, temp_project_dir):
        """Test default configuration values."""
        config = RunConfig(project_dir=temp_project_dir)

        assert config.resume is False
        assert config.dry_run is False
        assert config.timeout_per_phase == 600
        assert config.max_retries == 3
        assert config.parallel is False

    def test_custom_values(self, temp_project_dir):
        """Test custom configuration values."""
        config = RunConfig(
            project_dir=temp_project_dir,
            resume=True,
            dry_run=True,
            timeout_per_phase=300,
            max_retries=5,
        )

        assert config.resume is True
        assert config.dry_run is True
        assert config.timeout_per_phase == 300
        assert config.max_retries == 5


class TestOrchestratorRunner:
    """Tests for OrchestratorRunner."""

    def test_initialization(self):
        """Test runner initialization."""
        runner = OrchestratorRunner()

        assert runner.executor is not None
        assert runner.data_flow is not None
        assert runner.status_tracker is not None

    def test_initialization_with_custom_components(self, mock_executor):
        """Test runner initialization with custom components."""
        data_flow = DataFlowManager()
        status_tracker = StatusTracker()

        runner = OrchestratorRunner(
            phase_executor=mock_executor,
            data_flow=data_flow,
            status_tracker=status_tracker,
        )

        assert runner.executor == mock_executor
        assert runner.data_flow == data_flow
        assert runner.status_tracker == status_tracker

    @pytest.mark.asyncio
    async def test_run_dry_run(self, temp_project_dir, mock_executor):
        """Test dry run mode."""
        runner = OrchestratorRunner(phase_executor=mock_executor)

        config = RunConfig(
            project_dir=temp_project_dir,
            dry_run=True,
        )

        result = await runner.run("test-project", config)

        assert result.status == "completed"
        assert result.completed_phases == 2
        assert result.total_phases == 2

    @pytest.mark.asyncio
    async def test_run_with_progress_callback(self, temp_project_dir, mock_executor):
        """Test progress callback is called."""
        runner = OrchestratorRunner(phase_executor=mock_executor)

        config = RunConfig(
            project_dir=temp_project_dir,
            dry_run=True,
        )

        events = []

        async def on_progress(event, message, details):
            events.append((event, message, details))

        result = await runner.run("test-project", config, on_progress=on_progress)

        assert result.status == "completed"
        assert len(events) > 0

        # Check for expected events
        event_types = [e[0] for e in events]
        assert "project_started" in event_types
        assert "phase_started" in event_types
        assert "phase_completed" in event_types
        assert "project_completed" in event_types

    @pytest.mark.asyncio
    async def test_run_resume(self, temp_project_dir, mock_executor):
        """Test resume functionality."""
        runner = OrchestratorRunner(phase_executor=mock_executor)

        # First run - complete phase1
        config = RunConfig(
            project_dir=temp_project_dir,
            dry_run=True,
        )

        result = await runner.run("test-project", config)
        assert result.status == "completed"

        # Mark as partially complete for resume test
        status = runner.status_tracker.load(temp_project_dir)
        status.status = "running"
        status.completed_phases = 1
        # Only phase1 is completed
        status.phases = {"phase1": PhaseStatus(phase_id="phase1", status="completed")}
        runner.status_tracker.save(status)

        # Resume run
        config_resume = RunConfig(
            project_dir=temp_project_dir,
            resume=True,
            dry_run=True,
        )

        events = []

        async def on_progress(event, message, details):
            events.append((event, message, details))

        result = await runner.run("test-project", config_resume, on_progress=on_progress)

        assert result.status == "completed"

        # Check that phase1 was skipped
        skipped = [e for e in events if e[0] == "phase_skipped"]
        assert len(skipped) == 1
        assert skipped[0][2]["phase_id"] == "phase1"

    @pytest.mark.asyncio
    async def test_run_failure(self, temp_project_dir):
        """Test handling of phase failure."""
        # Create executor that fails
        executor = MagicMock(spec=PhaseExecutor)

        async def mock_execute(*args, **kwargs):
            from datetime import datetime
            return PhaseResult(
                phase_id=kwargs.get("phase_config", MagicMock()).id,
                success=False,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error="Simulated failure",
            )

        executor.execute = AsyncMock(side_effect=mock_execute)

        runner = OrchestratorRunner(phase_executor=executor)

        config = RunConfig(
            project_dir=temp_project_dir,
            max_retries=1,  # Reduce retries for faster test
        )

        result = await runner.run("test-project", config)

        assert result.status == "failed"
        assert "phase1" in result.error

    @pytest.mark.asyncio
    async def test_get_status(self, temp_project_dir, mock_executor):
        """Test getting project status."""
        runner = OrchestratorRunner(phase_executor=mock_executor)

        # Run project first
        config = RunConfig(project_dir=temp_project_dir, dry_run=True)
        await runner.run("test-project", config)

        # Get status
        status = await runner.get_status("test-project")

        assert status is not None
        assert status.status == "completed"
        assert status.completed_phases == 2

    def test_list_projects(self, temp_project_dir):
        """Test listing projects."""
        runner = OrchestratorRunner()

        # Create projects base directory
        projects_base = temp_project_dir.parent

        projects = runner.list_projects(projects_base)

        assert len(projects) == 1
        assert projects[0].project_id == "test-project"


class TestStatusPersistence:
    """Tests for status persistence across runs."""

    @pytest.mark.asyncio
    async def test_status_persisted(self, temp_project_dir, mock_executor):
        """Test that status is persisted to file."""
        runner = OrchestratorRunner(phase_executor=mock_executor)

        config = RunConfig(project_dir=temp_project_dir, dry_run=True)
        await runner.run("test-project", config)

        # Check status file exists
        status_file = temp_project_dir / "status.yaml"
        assert status_file.exists()

        # Load and verify
        with open(status_file) as f:
            data = yaml.safe_load(f)

        assert data["status"] == "completed"
        assert data["completed_phases"] == 2

    @pytest.mark.asyncio
    async def test_status_survives_restart(self, temp_project_dir, mock_executor):
        """Test that status can be loaded after 'restart'."""
        runner1 = OrchestratorRunner(phase_executor=mock_executor)

        config = RunConfig(project_dir=temp_project_dir, dry_run=True)
        await runner1.run("test-project", config)

        # Create new runner (simulating restart)
        runner2 = OrchestratorRunner(phase_executor=mock_executor)

        status = runner2.status_tracker.load(temp_project_dir)

        assert status is not None
        assert status.status == "completed"
        assert status.completed_phases == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
