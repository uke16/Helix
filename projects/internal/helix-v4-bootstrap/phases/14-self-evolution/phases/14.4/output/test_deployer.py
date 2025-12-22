"""
Unit tests for the Deployer module.

Tests the deployment functionality for evolution projects.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deployer import (
    Deployer,
    DeploymentResult,
    DeploymentStatus,
    create_deployer,
)


@pytest.fixture
def temp_dirs(tmp_path: Path):
    """Create temporary production and test directories."""
    production = tmp_path / "helix-v4"
    test_system = tmp_path / "helix-v4-test"

    # Create production structure
    production.mkdir()
    (production / "src" / "helix").mkdir(parents=True)
    (production / "control").mkdir()
    (production / "projects" / "evolution").mkdir(parents=True)

    # Create test system structure
    test_system.mkdir()
    (test_system / "src" / "helix").mkdir(parents=True)
    (test_system / "control").mkdir()
    (test_system / ".git").mkdir()

    # Create control script in test system
    control_script = test_system / "control" / "helix-control.sh"
    control_script.write_text("#!/bin/bash\necho 'mock control script'\nexit 0\n")
    control_script.chmod(0o755)

    return {
        "production": production,
        "test_system": test_system,
    }


@pytest.fixture
def deployer(temp_dirs):
    """Create a Deployer instance with temp directories."""
    return Deployer(
        production_path=temp_dirs["production"],
        test_system_path=temp_dirs["test_system"],
    )


@pytest.fixture
def mock_project(temp_dirs):
    """Create a mock evolution project."""
    project_path = temp_dirs["production"] / "projects" / "evolution" / "test-feature"
    project_path.mkdir(parents=True)

    # Create new/ directory with a file
    new_dir = project_path / "new" / "src" / "helix" / "new_module"
    new_dir.mkdir(parents=True)
    (new_dir / "feature.py").write_text("# New feature\nprint('hello')\n")

    # Create modified/ directory with a file
    modified_dir = project_path / "modified" / "src" / "helix"
    modified_dir.mkdir(parents=True)
    (modified_dir / "existing.py").write_text("# Modified\nprint('modified')\n")

    # Create status.json
    status = {
        "status": "ready",
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


class TestDeploymentResult:
    """Tests for DeploymentResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = DeploymentResult(
            success=True,
            status=DeploymentStatus.COMPLETED,
            message="Deployment completed",
            files_copied=["file1.py", "file2.py"],
        )
        result.completed_at = datetime.now()

        d = result.to_dict()

        assert d["success"] is True
        assert d["status"] == "completed"
        assert d["message"] == "Deployment completed"
        assert len(d["files_copied"]) == 2
        assert d["completed_at"] is not None


class TestDeployer:
    """Tests for the Deployer class."""

    def test_init_default_paths(self):
        """Test default path initialization."""
        deployer = Deployer()

        assert deployer.production_path == Path("/home/aiuser01/helix-v4")
        assert deployer.test_system_path == Path("/home/aiuser01/helix-v4-test")

    def test_init_custom_paths(self, temp_dirs):
        """Test custom path initialization."""
        deployer = Deployer(
            production_path=temp_dirs["production"],
            test_system_path=temp_dirs["test_system"],
        )

        assert deployer.production_path == temp_dirs["production"]
        assert deployer.test_system_path == temp_dirs["test_system"]

    def test_check_test_system_exists(self, deployer, temp_dirs):
        """Test checking if test system exists."""
        assert deployer._check_test_system_exists() is True

        # Remove test system
        shutil.rmtree(temp_dirs["test_system"])
        assert deployer._check_test_system_exists() is False

    @pytest.mark.asyncio
    async def test_run_command_success(self, deployer):
        """Test running a successful command."""
        returncode, stdout, stderr = await deployer._run_command(
            ["echo", "hello"],
            timeout=5.0,
        )

        assert returncode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_run_command_failure(self, deployer):
        """Test running a failing command."""
        returncode, stdout, stderr = await deployer._run_command(
            ["false"],  # Always returns 1
            timeout=5.0,
        )

        assert returncode == 1

    @pytest.mark.asyncio
    async def test_run_command_timeout(self, deployer):
        """Test command timeout."""
        returncode, stdout, stderr = await deployer._run_command(
            ["sleep", "10"],
            timeout=0.1,
        )

        assert returncode == -1
        assert "timed out" in stderr.lower()

    @pytest.mark.asyncio
    async def test_pre_deploy_sync_no_test_system(self, temp_dirs):
        """Test pre_deploy_sync when test system doesn't exist."""
        deployer = Deployer(
            production_path=temp_dirs["production"],
            test_system_path=temp_dirs["test_system"] / "nonexistent",
        )

        result = await deployer.pre_deploy_sync()

        assert result.success is False
        assert result.status == DeploymentStatus.FAILED
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pre_deploy_sync_not_git_repo(self, temp_dirs):
        """Test pre_deploy_sync when test system is not a git repo."""
        # Remove .git directory
        shutil.rmtree(temp_dirs["test_system"] / ".git")

        deployer = Deployer(
            production_path=temp_dirs["production"],
            test_system_path=temp_dirs["test_system"],
        )

        result = await deployer.pre_deploy_sync()

        assert result.success is False
        assert result.status == DeploymentStatus.FAILED
        assert "git" in result.message.lower()

    @pytest.mark.asyncio
    async def test_deploy_success(self, deployer, mock_project, temp_dirs):
        """Test successful deployment."""
        result = await deployer.deploy(mock_project)

        assert result.success is True
        assert result.status == DeploymentStatus.COMPLETED
        assert len(result.files_copied) == 2

        # Check files were copied
        new_file = temp_dirs["test_system"] / "src" / "helix" / "new_module" / "feature.py"
        modified_file = temp_dirs["test_system"] / "src" / "helix" / "existing.py"

        assert new_file.exists()
        assert modified_file.exists()

    @pytest.mark.asyncio
    async def test_deploy_no_files(self, deployer):
        """Test deployment with no files."""
        mock_project = MagicMock()
        mock_project.path = Path("/tmp/test")
        mock_project.get_new_files.return_value = []
        mock_project.get_modified_files.return_value = []

        result = await deployer.deploy(mock_project)

        assert result.success is False
        assert result.status == DeploymentStatus.FAILED
        assert "no files" in result.message.lower()

    @pytest.mark.asyncio
    async def test_deploy_no_test_system(self, temp_dirs, mock_project):
        """Test deployment when test system doesn't exist."""
        deployer = Deployer(
            production_path=temp_dirs["production"],
            test_system_path=Path("/nonexistent"),
        )

        result = await deployer.deploy(mock_project)

        assert result.success is False
        assert result.status == DeploymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_restart_test_system_no_script(self, temp_dirs):
        """Test restart when control script doesn't exist."""
        # Remove control script
        (temp_dirs["test_system"] / "control" / "helix-control.sh").unlink()

        deployer = Deployer(
            production_path=temp_dirs["production"],
            test_system_path=temp_dirs["test_system"],
        )

        result = await deployer.restart_test_system()

        assert result.success is False
        assert result.status == DeploymentStatus.FAILED
        assert "control script" in result.message.lower()

    @pytest.mark.asyncio
    async def test_rollback_success(self, deployer):
        """Test rollback with mocked git commands."""
        with patch.object(deployer, "_run_command") as mock_cmd:
            # Mock successful git reset and clean
            mock_cmd.return_value = (0, "", "")

            # Mock restart
            with patch.object(deployer, "restart_test_system") as mock_restart:
                mock_restart.return_value = DeploymentResult(
                    success=True,
                    status=DeploymentStatus.COMPLETED,
                    message="Restarted",
                )

                result = await deployer.rollback()

        assert result.success is True
        assert result.status == DeploymentStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_get_test_system_status(self, deployer, temp_dirs):
        """Test getting test system status."""
        with patch.object(deployer, "_run_command") as mock_cmd:
            # Mock git status
            mock_cmd.return_value = (0, "", "")

            status = await deployer.get_test_system_status()

        assert status["exists"] is True
        assert status["path"] == str(temp_dirs["test_system"])
        assert status["control_script_exists"] is True

    @pytest.mark.asyncio
    async def test_full_deploy(self, deployer, mock_project):
        """Test full deployment workflow."""
        with patch.object(deployer, "pre_deploy_sync") as mock_sync:
            mock_sync.return_value = DeploymentResult(
                success=True,
                status=DeploymentStatus.COMPLETED,
                message="Synced",
            )

            with patch.object(deployer, "deploy") as mock_deploy:
                mock_deploy.return_value = DeploymentResult(
                    success=True,
                    status=DeploymentStatus.COMPLETED,
                    message="Deployed",
                    files_copied=["file1.py"],
                )

                with patch.object(deployer, "restart_test_system") as mock_restart:
                    mock_restart.return_value = DeploymentResult(
                        success=True,
                        status=DeploymentStatus.COMPLETED,
                        message="Restarted",
                    )

                    result = await deployer.full_deploy(mock_project)

        assert result.success is True
        assert result.status == DeploymentStatus.COMPLETED
        assert len(result.files_copied) == 1


class TestCreateDeployer:
    """Tests for the factory function."""

    def test_create_deployer_defaults(self):
        """Test creating deployer with defaults."""
        deployer = create_deployer()

        assert deployer.production_path == Path("/home/aiuser01/helix-v4")
        assert deployer.test_system_path == Path("/home/aiuser01/helix-v4-test")

    def test_create_deployer_custom(self, temp_dirs):
        """Test creating deployer with custom paths."""
        deployer = create_deployer(
            production_path=temp_dirs["production"],
            test_system_path=temp_dirs["test_system"],
        )

        assert deployer.production_path == temp_dirs["production"]
        assert deployer.test_system_path == temp_dirs["test_system"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
