"""Tests for DataFlowManager."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from helix.orchestrator.data_flow import DataFlowManager
from helix.orchestrator.status import ProjectStatus


@pytest.fixture
def temp_project():
    """Create a temporary project with phases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        # Create phase1 with outputs
        phase1_dir = project_dir / "phases" / "phase1"
        (phase1_dir / "input").mkdir(parents=True)
        (phase1_dir / "output").mkdir(parents=True)
        (phase1_dir / "output" / "result.yaml").write_text("key: value\n")
        (phase1_dir / "output" / "data.json").write_text('{"test": true}')

        # Create nested output structure
        (phase1_dir / "output" / "src").mkdir()
        (phase1_dir / "output" / "src" / "main.py").write_text("print('hello')")
        (phase1_dir / "output" / "src" / "utils.py").write_text("pass")

        # Create phase2 (empty)
        phase2_dir = project_dir / "phases" / "phase2"
        (phase2_dir / "input").mkdir(parents=True)
        (phase2_dir / "output").mkdir(parents=True)

        # Create project-level files
        (project_dir / "spec.yaml").write_text("name: test\n")
        (project_dir / "ADR-001.md").write_text("# ADR\n")
        (project_dir / "phases.yaml").write_text("phases: []\n")

        yield project_dir


@pytest.fixture
def mock_phase_config():
    """Create a mock phase config with input_from."""
    config = MagicMock()
    config.id = "phase2"
    config.type = "development"
    config.config = {"input_from": ["phase1"]}
    return config


@pytest.fixture
def project_status():
    """Create a project status."""
    return ProjectStatus(
        project_id="test-project",
        status="running",
    )


class TestDataFlowManager:
    """Tests for DataFlowManager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = DataFlowManager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_prepare_phase_inputs_basic(
        self, temp_project, mock_phase_config, project_status
    ):
        """Test basic input preparation."""
        manager = DataFlowManager()

        copied = await manager.prepare_phase_inputs(
            temp_project, mock_phase_config, project_status
        )

        # Check files were copied
        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "result.yaml").exists()
        assert (phase2_input / "data.json").exists()
        assert (phase2_input / "src" / "main.py").exists()

    @pytest.mark.asyncio
    async def test_prepare_phase_inputs_with_patterns(
        self, temp_project, project_status
    ):
        """Test input preparation with glob patterns."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {"input_from": [{"phase1": ["*.yaml"]}]}

        manager = DataFlowManager()

        await manager.prepare_phase_inputs(temp_project, config, project_status)

        # Only yaml files should be copied
        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "result.yaml").exists()
        # json and src should not be there (from phase1)
        # But spec.yaml from project root might be there

    @pytest.mark.asyncio
    async def test_prepare_phase_inputs_copies_project_files(
        self, temp_project, project_status
    ):
        """Test that project-level files are copied."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {}  # No input_from

        manager = DataFlowManager()

        await manager.prepare_phase_inputs(temp_project, config, project_status)

        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "spec.yaml").exists()
        assert (phase2_input / "ADR-001.md").exists()
        assert (phase2_input / "phases.yaml").exists()

    @pytest.mark.asyncio
    async def test_prepare_phase_inputs_string_input_from(
        self, temp_project, project_status
    ):
        """Test input_from as single string."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {"input_from": "phase1"}  # String instead of list

        manager = DataFlowManager()

        copied = await manager.prepare_phase_inputs(
            temp_project, config, project_status
        )

        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "result.yaml").exists()

    @pytest.mark.asyncio
    async def test_prepare_phase_inputs_missing_source(
        self, temp_project, project_status
    ):
        """Test handling of missing source phase."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {"input_from": ["nonexistent"]}

        manager = DataFlowManager()

        # Should not raise, just skip missing
        copied = await manager.prepare_phase_inputs(
            temp_project, config, project_status
        )

        # Only project files should be copied
        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "spec.yaml").exists()


class TestCollectOutputs:
    """Tests for output collection."""

    def test_collect_outputs_all_phases(self, temp_project):
        """Test collecting outputs from all phases."""
        manager = DataFlowManager()

        with tempfile.TemporaryDirectory() as dest_tmpdir:
            dest_dir = Path(dest_tmpdir) / "collected"
            dest_dir.mkdir()

            collected = manager.collect_outputs(temp_project, dest_dir)

            assert (dest_dir / "result.yaml").exists()
            assert (dest_dir / "data.json").exists()
            assert (dest_dir / "src" / "main.py").exists()

    def test_collect_outputs_specific_phases(self, temp_project):
        """Test collecting outputs from specific phases."""
        manager = DataFlowManager()

        with tempfile.TemporaryDirectory() as dest_tmpdir:
            dest_dir = Path(dest_tmpdir) / "collected"
            dest_dir.mkdir()

            collected = manager.collect_outputs(
                temp_project, dest_dir, phases=["phase1"]
            )

            assert (dest_dir / "result.yaml").exists()


class TestDirectoryCopying:
    """Tests for directory copying utilities."""

    def test_copy_directory_contents(self, temp_project):
        """Test copying directory contents."""
        manager = DataFlowManager()

        source = temp_project / "phases" / "phase1" / "output"

        with tempfile.TemporaryDirectory() as dest_tmpdir:
            dest = Path(dest_tmpdir)

            copied = manager._copy_directory_contents(source, dest)

            assert len(copied) > 0
            assert (dest / "result.yaml").exists()
            assert (dest / "src").is_dir()

    def test_copy_matching_files(self, temp_project):
        """Test copying files matching pattern."""
        manager = DataFlowManager()

        source = temp_project / "phases" / "phase1" / "output"

        with tempfile.TemporaryDirectory() as dest_tmpdir:
            dest = Path(dest_tmpdir)

            # Copy only Python files
            copied = manager._copy_matching_files(source, dest, "**/*.py")

            assert len(copied) == 2  # main.py and utils.py
            assert (dest / "src" / "main.py").exists()
            assert (dest / "src" / "utils.py").exists()
            assert not (dest / "result.yaml").exists()

    def test_copy_matching_files_yaml(self, temp_project):
        """Test copying YAML files only."""
        manager = DataFlowManager()

        source = temp_project / "phases" / "phase1" / "output"

        with tempfile.TemporaryDirectory() as dest_tmpdir:
            dest = Path(dest_tmpdir)

            copied = manager._copy_matching_files(source, dest, "*.yaml")

            assert len(copied) == 1
            assert (dest / "result.yaml").exists()


class TestMergeDirectories:
    """Tests for directory merging."""

    def test_merge_directories(self, temp_project):
        """Test merging directories."""
        manager = DataFlowManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)

            # Create existing structure
            (dest / "existing.txt").write_text("existing")
            (dest / "subdir").mkdir()
            (dest / "subdir" / "old.txt").write_text("old")

            source = temp_project / "phases" / "phase1" / "output"

            manager._merge_directories(source, dest)

            # Check existing files preserved
            assert (dest / "existing.txt").exists()
            # Check new files added
            assert (dest / "result.yaml").exists()
            assert (dest / "src" / "main.py").exists()


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_inputs(self, temp_project):
        """Test cleaning up input directory."""
        manager = DataFlowManager()

        phase_dir = temp_project / "phases" / "phase2"
        input_dir = phase_dir / "input"

        # Add some files
        (input_dir / "test.txt").write_text("test")
        (input_dir / "subdir").mkdir()
        (input_dir / "subdir" / "nested.txt").write_text("nested")

        manager.cleanup_inputs(phase_dir)

        # Directory should exist but be empty
        assert input_dir.exists()
        assert not (input_dir / "test.txt").exists()
        assert not (input_dir / "subdir").exists()


class TestInputFromVariants:
    """Tests for different input_from configurations."""

    @pytest.mark.asyncio
    async def test_input_from_in_input_dict(self, temp_project, project_status):
        """Test input_from in input dictionary."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {}
        config.input = {"from": ["phase1"]}  # Alternative style

        manager = DataFlowManager()

        await manager.prepare_phase_inputs(temp_project, config, project_status)

        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "result.yaml").exists()

    @pytest.mark.asyncio
    async def test_input_from_as_attribute(self, temp_project, project_status):
        """Test input_from as direct attribute."""
        config = MagicMock()
        config.id = "phase2"
        config.type = "development"
        config.config = {}
        config.input = {}
        config.input_from = ["phase1"]  # Direct attribute

        manager = DataFlowManager()

        await manager.prepare_phase_inputs(temp_project, config, project_status)

        phase2_input = temp_project / "phases" / "phase2" / "input"
        assert (phase2_input / "result.yaml").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
