"""Tests for the Evolution Deployer."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from helix.evolution.deployer import Deployer, DeployResult
from helix.evolution.project import EvolutionProject, EvolutionStatus


@pytest.fixture
def temp_dirs():
    """Create temporary production and test directories."""
    with tempfile.TemporaryDirectory() as prod_dir:
        with tempfile.TemporaryDirectory() as test_dir:
            prod_path = Path(prod_dir)
            test_path = Path(test_dir)

            # Create basic structure
            (prod_path / "projects" / "evolution").mkdir(parents=True)
            (test_path / "src" / "helix").mkdir(parents=True)
            (test_path / ".git").mkdir(parents=True)
            (test_path / "control").mkdir(parents=True)

            # Create mock control script
            control_script = test_path / "control" / "helix-control.sh"
            control_script.write_text("#!/bin/bash\nexit 0")
            control_script.chmod(0o755)

            yield prod_path, test_path


@pytest.fixture
def deployer(temp_dirs):
    """Create a deployer with temp directories."""
    prod_path, test_path = temp_dirs
    return Deployer(production_root=prod_path, test_root=test_path)


@pytest.fixture
def sample_project(temp_dirs):
    """Create a sample evolution project."""
    prod_path, _ = temp_dirs
    base_path = prod_path / "projects" / "evolution"

    project = EvolutionProject.create(
        base_path=base_path,
        name="test-feature",
        spec={"name": "Test Feature"},
    )

    # Add some files
    project.add_new_file(Path("src/helix/new_module.py"), "# New module\n")
    project.add_modified_file(Path("src/helix/existing.py"), "# Modified\n")

    # Set to READY
    project.set_status(EvolutionStatus.READY)

    return project


class TestDeployerInit:
    """Tests for Deployer initialization."""

    def test_default_paths(self):
        """Test default paths are set."""
        deployer = Deployer()
        assert deployer.production_root == Path("/home/aiuser01/helix-v4")
        assert deployer.test_root == Path("/home/aiuser01/helix-v4-test")

    def test_custom_paths(self, temp_dirs):
        """Test custom paths are used."""
        prod_path, test_path = temp_dirs
        deployer = Deployer(production_root=prod_path, test_root=test_path)
        assert deployer.production_root == prod_path
        assert deployer.test_root == test_path


class TestPreDeploySync:
    """Tests for pre_deploy_sync."""

    @pytest.mark.asyncio
    async def test_sync_success(self, deployer, temp_dirs):
        """Test successful pre-deploy sync."""
        _, test_path = temp_dirs

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await deployer.pre_deploy_sync()

            assert result.success
            assert "synced" in result.message.lower()

    @pytest.mark.asyncio
    async def test_sync_test_dir_missing(self, temp_dirs):
        """Test sync fails if test dir missing."""
        prod_path, _ = temp_dirs
        deployer = Deployer(
            production_root=prod_path,
            test_root=Path("/nonexistent"),
        )

        result = await deployer.pre_deploy_sync()

        assert not result.success
        assert "not exist" in result.message.lower()

    @pytest.mark.asyncio
    async def test_sync_git_failure(self, deployer):
        """Test sync handles git failures."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"fatal: error")
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            result = await deployer.pre_deploy_sync()

            assert not result.success


class TestDeploy:
    """Tests for deploy."""

    @pytest.mark.asyncio
    async def test_deploy_success(self, deployer, sample_project, temp_dirs):
        """Test successful deployment."""
        _, test_path = temp_dirs

        result = await deployer.deploy(sample_project)

        assert result.success
        assert result.files_copied == 2

        # Verify files were copied
        assert (test_path / "src" / "helix" / "new_module.py").exists()
        assert (test_path / "src" / "helix" / "existing.py").exists()

        # Verify project status updated
        assert sample_project.get_status() == EvolutionStatus.DEPLOYED

    @pytest.mark.asyncio
    async def test_deploy_wrong_status(self, deployer, temp_dirs):
        """Test deploy fails for wrong status."""
        prod_path, _ = temp_dirs
        base_path = prod_path / "projects" / "evolution"

        project = EvolutionProject.create(
            base_path=base_path,
            name="pending-project",
            spec={"name": "Test"},
        )
        # Status is PENDING, not READY

        result = await deployer.deploy(project)

        assert not result.success
        assert "not ready" in result.message.lower()


class TestRestartTestSystem:
    """Tests for restart_test_system."""

    @pytest.mark.asyncio
    async def test_restart_success(self, deployer):
        """Test successful restart."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Started", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with patch("asyncio.sleep"):
                result = await deployer.restart_test_system()

            assert result.success

    @pytest.mark.asyncio
    async def test_restart_script_missing(self, temp_dirs):
        """Test restart fails if control script missing."""
        prod_path, test_path = temp_dirs

        # Remove control script
        (test_path / "control" / "helix-control.sh").unlink()

        deployer = Deployer(production_root=prod_path, test_root=test_path)
        result = await deployer.restart_test_system()

        assert not result.success
        assert "not found" in result.message.lower()


class TestRollback:
    """Tests for rollback."""

    @pytest.mark.asyncio
    async def test_rollback_success(self, deployer):
        """Test successful rollback."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with patch("asyncio.sleep"):
                result = await deployer.rollback()

            assert result.success
            assert "rolled back" in result.message.lower()


class TestCheckHealth:
    """Tests for check_test_system_health.
    
    Note: These are integration tests. For unit testing we verify structure.
    """

    def test_deploy_result_structure(self):
        """Test DeployResult has correct structure."""
        result = DeployResult(
            success=True,
            message="Healthy",
            files_copied=0,
        )
        assert result.success is True
        assert result.message == "Healthy"


class TestFullDeploy:
    """Tests for full_deploy workflow."""

    @pytest.mark.asyncio
    async def test_full_deploy_success(self, deployer, sample_project):
        """Test full deploy workflow."""
        with patch.object(deployer, "pre_deploy_sync") as mock_sync:
            mock_sync.return_value = DeployResult(success=True, message="Synced")

            with patch.object(deployer, "restart_test_system") as mock_restart:
                mock_restart.return_value = DeployResult(success=True, message="Restarted")

                with patch.object(deployer, "check_test_system_health") as mock_health:
                    mock_health.return_value = DeployResult(success=True, message="Healthy")

                    result = await deployer.full_deploy(sample_project)

                    assert result.success
                    assert result.files_copied == 2

    @pytest.mark.asyncio
    async def test_full_deploy_sync_failure(self, deployer, sample_project):
        """Test full deploy fails on sync failure."""
        with patch.object(deployer, "pre_deploy_sync") as mock_sync:
            mock_sync.return_value = DeployResult(
                success=False,
                message="Sync failed",
                error="Git error",
            )

            result = await deployer.full_deploy(sample_project)

            assert not result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
