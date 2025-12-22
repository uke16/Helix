"""Tests for the Evolution Integrator."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from helix.evolution.integrator import Integrator, IntegrationResult
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
            (prod_path / "src" / "helix").mkdir(parents=True)
            (prod_path / ".git").mkdir(parents=True)
            (prod_path / "control").mkdir(parents=True)
            (test_path / "src" / "helix").mkdir(parents=True)

            # Create mock control script
            control_script = prod_path / "control" / "helix-control.sh"
            control_script.write_text("#!/bin/bash\nexit 0")
            control_script.chmod(0o755)

            yield prod_path, test_path


@pytest.fixture
def integrator(temp_dirs):
    """Create an integrator with temp directories."""
    prod_path, test_path = temp_dirs
    return Integrator(production_root=prod_path, test_root=test_path)


@pytest.fixture
def deployed_project(temp_dirs):
    """Create a deployed evolution project."""
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

    # Set to DEPLOYED (validated in test system)
    project.set_status(EvolutionStatus.DEPLOYED)

    return project


class TestIntegratorInit:
    """Tests for Integrator initialization."""

    def test_default_paths(self):
        """Test default paths are set."""
        integrator = Integrator()
        assert integrator.production_root == Path("/home/aiuser01/helix-v4")
        assert integrator.test_root == Path("/home/aiuser01/helix-v4-test")

    def test_custom_paths(self, temp_dirs):
        """Test custom paths are used."""
        prod_path, test_path = temp_dirs
        integrator = Integrator(production_root=prod_path, test_root=test_path)
        assert integrator.production_root == prod_path
        assert integrator.test_root == test_path


class TestPreIntegrationBackup:
    """Tests for pre_integration_backup."""

    @pytest.mark.asyncio
    async def test_backup_success(self, integrator):
        """Test successful backup creation."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await integrator.pre_integration_backup()

            assert result.success
            assert result.backup_tag is not None
            assert "pre-integrate" in result.backup_tag

    @pytest.mark.asyncio
    async def test_backup_failure(self, integrator):
        """Test backup handles git failures."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"error: tag failed")
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            result = await integrator.pre_integration_backup()

            assert not result.success


class TestIntegrate:
    """Tests for integrate."""

    @pytest.mark.asyncio
    async def test_integrate_success(self, integrator, deployed_project, temp_dirs):
        """Test successful integration."""
        prod_path, _ = temp_dirs

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await integrator.integrate(deployed_project)

            assert result.success
            assert result.files_integrated == 2

            # Verify files were copied
            assert (prod_path / "src" / "helix" / "new_module.py").exists()
            assert (prod_path / "src" / "helix" / "existing.py").exists()

            # Verify project status updated
            assert deployed_project.get_status() == EvolutionStatus.INTEGRATED

    @pytest.mark.asyncio
    async def test_integrate_wrong_status(self, integrator, temp_dirs):
        """Test integrate fails for wrong status."""
        prod_path, _ = temp_dirs
        base_path = prod_path / "projects" / "evolution"

        project = EvolutionProject.create(
            base_path=base_path,
            name="pending-project",
            spec={"name": "Test"},
        )
        # Status is PENDING, not DEPLOYED

        result = await integrator.integrate(project)

        assert not result.success
        assert "not ready" in result.message.lower()


class TestPostIntegrationRestart:
    """Tests for post_integration_restart."""

    @pytest.mark.asyncio
    async def test_restart_success(self, integrator):
        """Test successful restart."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Restarted", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with patch("asyncio.sleep"):
                result = await integrator.post_integration_restart()

            assert result.success

    @pytest.mark.asyncio
    async def test_restart_script_missing(self, temp_dirs):
        """Test restart fails if control script missing."""
        prod_path, test_path = temp_dirs

        # Remove control script
        (prod_path / "control" / "helix-control.sh").unlink()

        integrator = Integrator(production_root=prod_path, test_root=test_path)
        result = await integrator.post_integration_restart()

        assert not result.success


class TestRollback:
    """Tests for rollback."""

    @pytest.mark.asyncio
    async def test_rollback_with_tag(self, integrator):
        """Test rollback with existing backup tag."""
        integrator._backup_tag = "pre-integrate-20241221-120000"

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with patch("asyncio.sleep"):
                result = await integrator.rollback()

            assert result.success
            assert "pre-integrate" in result.backup_tag

    @pytest.mark.asyncio
    async def test_rollback_finds_tag(self, integrator):
        """Test rollback finds latest tag if none stored."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            # First call returns list of tags
            mock_process.communicate.side_effect = [
                (b"pre-integrate-20241221-120000\npre-integrate-20241221-110000", b""),
                (b"", b""),  # git reset
                (b"", b""),  # control script restart
            ]
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            with patch("asyncio.sleep"):
                result = await integrator.rollback()

            assert result.success

    @pytest.mark.asyncio
    async def test_rollback_no_tag(self, integrator):
        """Test rollback fails without backup tag."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await integrator.rollback()

            assert not result.success
            assert "no backup tag" in result.message.lower()


class TestFullIntegration:
    """Tests for full_integration workflow."""

    @pytest.mark.asyncio
    async def test_full_integration_success(self, integrator, deployed_project):
        """Test full integration workflow."""
        with patch.object(integrator, "pre_integration_backup") as mock_backup:
            mock_backup.return_value = IntegrationResult(
                success=True, message="Backup", backup_tag="test-tag"
            )

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_process.returncode = 0
                mock_exec.return_value = mock_process

                with patch("asyncio.sleep"):
                    result = await integrator.full_integration(deployed_project)

                    assert result.success
                    assert result.files_integrated == 2

    @pytest.mark.asyncio
    async def test_full_integration_backup_failure(self, integrator, deployed_project):
        """Test full integration fails on backup failure."""
        with patch.object(integrator, "pre_integration_backup") as mock_backup:
            mock_backup.return_value = IntegrationResult(
                success=False, message="Backup failed", error="Git error"
            )

            result = await integrator.full_integration(deployed_project)

            assert not result.success


class TestCheckProductionHealth:
    """Tests for check_production_health."""

    def test_integration_result_structure(self):
        """Test IntegrationResult has correct structure."""
        result = IntegrationResult(
            success=True,
            message="Healthy",
            backup_tag="test-tag",
            files_integrated=5,
        )
        assert result.success is True
        assert result.backup_tag == "test-tag"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
