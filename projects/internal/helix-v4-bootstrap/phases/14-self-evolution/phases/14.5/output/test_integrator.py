"""
Unit tests for the Integrator module.

Tests the integration functionality for evolution projects into production.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrator import (
    Integrator,
    IntegrationResult,
    IntegrationStatus,
    create_integrator,
)


@pytest.fixture
def temp_production(tmp_path: Path):
    """Create a temporary production directory."""
    production = tmp_path / "helix-v4"

    # Create production structure
    production.mkdir()
    (production / "src" / "helix").mkdir(parents=True)
    (production / "control").mkdir()
    (production / "projects" / "evolution").mkdir(parents=True)

    # Create .git directory (simulate git repo)
    (production / ".git").mkdir()

    # Create control script
    control_script = production / "control" / "helix-control.sh"
    control_script.write_text("#!/bin/bash\necho 'mock control script'\nexit 0\n")
    control_script.chmod(0o755)

    return production


@pytest.fixture
def integrator(temp_production: Path):
    """Create an Integrator instance with temp production directory."""
    return Integrator(production_path=temp_production)


@pytest.fixture
def mock_project(temp_production: Path):
    """Create a mock evolution project."""
    project_path = temp_production / "projects" / "evolution" / "test-feature"
    project_path.mkdir(parents=True)

    # Create new/ directory with a file
    new_dir = project_path / "new" / "src" / "helix" / "new_module"
    new_dir.mkdir(parents=True)
    (new_dir / "feature.py").write_text("# New feature\ndef hello():\n    print('hello')\n")

    # Create modified/ directory with a file
    modified_dir = project_path / "modified" / "src" / "helix"
    modified_dir.mkdir(parents=True)
    (modified_dir / "existing.py").write_text("# Modified\ndef modified():\n    return 'modified'\n")

    # Create status.json
    status = {
        "status": "deployed",
        "session_id": "test-session",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    (project_path / "status.json").write_text(json.dumps(status))

    # Create a mock project object
    mock = MagicMock()
    mock.name = "test-feature"
    mock.path = project_path
    mock.get_new_files.return_value = [Path("src/helix/new_module/feature.py")]
    mock.get_modified_files.return_value = [Path("src/helix/existing.py")]

    return mock


class TestIntegrationResult:
    """Tests for IntegrationResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = IntegrationResult(
            success=True,
            status=IntegrationStatus.COMPLETED,
            message="Integration completed",
            backup_tag="pre-evolution-test-20240101-120000",
            files_integrated=["file1.py", "file2.py"],
        )
        result.completed_at = datetime.now()

        d = result.to_dict()

        assert d["success"] is True
        assert d["status"] == "completed"
        assert d["message"] == "Integration completed"
        assert d["backup_tag"] == "pre-evolution-test-20240101-120000"
        assert len(d["files_integrated"]) == 2
        assert d["completed_at"] is not None


class TestIntegrator:
    """Tests for the Integrator class."""

    def test_init_default_path(self):
        """Test default path initialization."""
        integrator = Integrator()

        assert integrator.production_path == Path("/home/aiuser01/helix-v4")

    def test_init_custom_path(self, temp_production: Path):
        """Test custom path initialization."""
        integrator = Integrator(production_path=temp_production)

        assert integrator.production_path == temp_production

    def test_check_production_exists(self, integrator: Integrator, temp_production: Path):
        """Test checking if production exists."""
        assert integrator._check_production_exists() is True

        # Remove production
        shutil.rmtree(temp_production)
        assert integrator._check_production_exists() is False

    def test_check_is_git_repo(self, integrator: Integrator, temp_production: Path):
        """Test checking if production is a git repo."""
        assert integrator._check_is_git_repo() is True

        # Remove .git
        shutil.rmtree(temp_production / ".git")
        assert integrator._check_is_git_repo() is False

    @pytest.mark.asyncio
    async def test_run_command_success(self, integrator: Integrator):
        """Test running a successful command."""
        returncode, stdout, stderr = await integrator._run_command(
            ["echo", "hello"],
            timeout=5.0,
        )

        assert returncode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_run_command_failure(self, integrator: Integrator):
        """Test running a failing command."""
        returncode, stdout, stderr = await integrator._run_command(
            ["false"],  # Always returns 1
            timeout=5.0,
        )

        assert returncode == 1

    @pytest.mark.asyncio
    async def test_run_command_timeout(self, integrator: Integrator):
        """Test command timeout."""
        returncode, stdout, stderr = await integrator._run_command(
            ["sleep", "10"],
            timeout=0.1,
        )

        assert returncode == -1
        assert "timed out" in stderr.lower()

    @pytest.mark.asyncio
    async def test_pre_integration_backup_no_production(self, temp_production: Path):
        """Test pre_integration_backup when production doesn't exist."""
        integrator = Integrator(production_path=temp_production / "nonexistent")

        result = await integrator.pre_integration_backup("test-feature")

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pre_integration_backup_not_git_repo(self, temp_production: Path):
        """Test pre_integration_backup when not a git repo."""
        # Remove .git directory
        shutil.rmtree(temp_production / ".git")

        integrator = Integrator(production_path=temp_production)
        result = await integrator.pre_integration_backup("test-feature")

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED
        assert "git" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pre_integration_backup_success(self, integrator: Integrator):
        """Test successful pre_integration_backup with mocked git."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            # Mock all git commands succeeding
            mock_cmd.return_value = (0, "", "")

            with patch.object(integrator, "_has_uncommitted_changes") as mock_changes:
                mock_changes.return_value = False

                with patch.object(integrator, "_get_current_commit") as mock_commit:
                    mock_commit.return_value = "abc1234"

                    result = await integrator.pre_integration_backup("test-feature")

        assert result.success is True
        assert result.status == IntegrationStatus.COMPLETED
        assert result.backup_tag is not None
        assert "pre-evolution" in result.backup_tag
        assert "test-feature" in result.backup_tag

    @pytest.mark.asyncio
    async def test_integrate_success(
        self, integrator: Integrator, mock_project: MagicMock, temp_production: Path
    ):
        """Test successful integration."""
        result = await integrator.integrate(mock_project)

        assert result.success is True
        assert result.status == IntegrationStatus.COMPLETED
        assert len(result.files_integrated) == 2

        # Check files were copied
        new_file = temp_production / "src" / "helix" / "new_module" / "feature.py"
        modified_file = temp_production / "src" / "helix" / "existing.py"

        assert new_file.exists()
        assert modified_file.exists()
        assert "hello" in new_file.read_text()
        assert "modified" in modified_file.read_text()

    @pytest.mark.asyncio
    async def test_integrate_no_files(self, integrator: Integrator):
        """Test integration with no files."""
        mock_project = MagicMock()
        mock_project.path = Path("/tmp/test")
        mock_project.get_new_files.return_value = []
        mock_project.get_modified_files.return_value = []

        result = await integrator.integrate(mock_project)

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED
        assert "no files" in result.message.lower()

    @pytest.mark.asyncio
    async def test_integrate_no_production(self, temp_production: Path, mock_project: MagicMock):
        """Test integration when production doesn't exist."""
        integrator = Integrator(production_path=Path("/nonexistent"))

        result = await integrator.integrate(mock_project)

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED

    @pytest.mark.asyncio
    async def test_commit_integration_success(self, integrator: Integrator):
        """Test successful commit with mocked git."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            # Mock git add and commit succeeding
            mock_cmd.return_value = (0, "commit message", "")

            result = await integrator.commit_integration("test-feature")

        assert result.success is True
        assert result.status == IntegrationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_commit_integration_nothing_to_commit(self, integrator: Integrator):
        """Test commit when nothing to commit."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            # Mock git add succeeding, commit returning "nothing to commit"
            def side_effect(*args, **kwargs):
                if "commit" in args[0]:
                    return (1, "nothing to commit", "")
                return (0, "", "")

            mock_cmd.side_effect = side_effect

            result = await integrator.commit_integration("test-feature")

        assert result.success is True
        assert "no changes" in result.message.lower()

    @pytest.mark.asyncio
    async def test_post_integration_restart_no_script(self, temp_production: Path):
        """Test restart when control script doesn't exist."""
        # Remove control script
        (temp_production / "control" / "helix-control.sh").unlink()

        integrator = Integrator(production_path=temp_production)
        result = await integrator.post_integration_restart()

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED
        assert "control script" in result.message.lower()

    @pytest.mark.asyncio
    async def test_post_integration_restart_success(self, integrator: Integrator):
        """Test successful restart with mocked commands."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (0, "restarted", "")

            result = await integrator.post_integration_restart()

        assert result.success is True
        assert result.status == IntegrationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_rollback_no_tag(self, integrator: Integrator):
        """Test rollback with no tag specified."""
        integrator._last_backup_tag = None

        result = await integrator.rollback()

        assert result.success is False
        assert result.status == IntegrationStatus.FAILED
        assert "no rollback tag" in result.message.lower()

    @pytest.mark.asyncio
    async def test_rollback_success(self, integrator: Integrator):
        """Test successful rollback with mocked commands."""
        integrator._last_backup_tag = "pre-evolution-test-20240101-120000"

        with patch.object(integrator, "_run_command") as mock_cmd:
            # Mock all git commands succeeding
            mock_cmd.return_value = (0, "pre-evolution-test-20240101-120000", "")

            with patch.object(integrator, "post_integration_restart") as mock_restart:
                mock_restart.return_value = IntegrationResult(
                    success=True,
                    status=IntegrationStatus.COMPLETED,
                    message="Restarted",
                )

                result = await integrator.rollback()

        assert result.success is True
        assert result.status == IntegrationStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_tag_not_found(self, integrator: Integrator):
        """Test rollback when tag doesn't exist."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            # Mock git tag -l returning empty (tag not found)
            mock_cmd.return_value = (0, "", "")

            result = await integrator.rollback("nonexistent-tag")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_full_integration(self, integrator: Integrator, mock_project: MagicMock):
        """Test full integration workflow."""
        with patch.object(integrator, "pre_integration_backup") as mock_backup:
            mock_backup.return_value = IntegrationResult(
                success=True,
                status=IntegrationStatus.COMPLETED,
                message="Backup created",
                backup_tag="pre-evolution-test",
            )

            with patch.object(integrator, "integrate") as mock_integrate:
                mock_integrate.return_value = IntegrationResult(
                    success=True,
                    status=IntegrationStatus.COMPLETED,
                    message="Integrated",
                    files_integrated=["file1.py"],
                )

                with patch.object(integrator, "commit_integration") as mock_commit:
                    mock_commit.return_value = IntegrationResult(
                        success=True,
                        status=IntegrationStatus.COMPLETED,
                        message="Committed",
                    )

                    with patch.object(integrator, "post_integration_restart") as mock_restart:
                        mock_restart.return_value = IntegrationResult(
                            success=True,
                            status=IntegrationStatus.COMPLETED,
                            message="Restarted",
                        )

                        result = await integrator.full_integration(mock_project)

        assert result.success is True
        assert result.status == IntegrationStatus.COMPLETED
        assert result.backup_tag == "pre-evolution-test"
        assert len(result.files_integrated) == 1

    @pytest.mark.asyncio
    async def test_full_integration_rollback_on_failure(
        self, integrator: Integrator, mock_project: MagicMock
    ):
        """Test full integration rollback when integrate fails."""
        with patch.object(integrator, "pre_integration_backup") as mock_backup:
            mock_backup.return_value = IntegrationResult(
                success=True,
                status=IntegrationStatus.COMPLETED,
                message="Backup created",
                backup_tag="pre-evolution-test",
            )

            with patch.object(integrator, "integrate") as mock_integrate:
                mock_integrate.return_value = IntegrationResult(
                    success=False,
                    status=IntegrationStatus.FAILED,
                    message="Integration failed",
                )

                with patch.object(integrator, "rollback") as mock_rollback:
                    mock_rollback.return_value = IntegrationResult(
                        success=True,
                        status=IntegrationStatus.ROLLED_BACK,
                        message="Rolled back",
                    )

                    result = await integrator.full_integration(mock_project)

        assert result.success is False
        mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_integration_status(self, integrator: Integrator):
        """Test getting integration status."""
        with patch.object(integrator, "_get_current_commit") as mock_commit:
            mock_commit.return_value = "abc1234"

            with patch.object(integrator, "_has_uncommitted_changes") as mock_changes:
                mock_changes.return_value = False

                with patch.object(integrator, "_run_command") as mock_cmd:
                    mock_cmd.return_value = (0, "", "")

                    status = await integrator.get_integration_status()

        assert status["exists"] is True
        assert status["is_git_repo"] is True
        assert status["control_script_exists"] is True
        assert status["current_commit"] == "abc1234"
        assert status["has_uncommitted_changes"] is False

    @pytest.mark.asyncio
    async def test_list_backup_tags(self, integrator: Integrator):
        """Test listing backup tags."""
        with patch.object(integrator, "_run_command") as mock_cmd:
            mock_cmd.return_value = (
                0,
                "pre-evolution-test-20240102\npre-evolution-test-20240101\n",
                "",
            )

            tags = await integrator.list_backup_tags()

        assert len(tags) == 2
        assert "pre-evolution-test-20240102" in tags
        assert "pre-evolution-test-20240101" in tags


class TestCreateIntegrator:
    """Tests for the factory function."""

    def test_create_integrator_defaults(self):
        """Test creating integrator with defaults."""
        integrator = create_integrator()

        assert integrator.production_path == Path("/home/aiuser01/helix-v4")

    def test_create_integrator_custom(self, temp_production: Path):
        """Test creating integrator with custom path."""
        integrator = create_integrator(production_path=temp_production)

        assert integrator.production_path == temp_production


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
