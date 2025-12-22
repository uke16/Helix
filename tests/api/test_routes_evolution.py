"""Tests for Evolution API Routes."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from helix.api.main import app
from helix.evolution import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    Deployer,
    DeployResult,
    Validator,
    ValidationResult,
    ValidationLevel,
    Integrator,
    IntegrationResult,
    RAGSync,
    SyncResult,
    SyncStatus,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_manager():
    """Mock the EvolutionProjectManager."""
    with patch("helix.api.routes.evolution.EvolutionProjectManager") as mock:
        yield mock


@pytest.fixture
def sample_project_dict():
    """Sample project data."""
    return {
        "name": "test-feature",
        "path": "/tmp/test",
        "status": "ready",
        "created_at": "2024-12-22T00:00:00",
        "updated_at": "2024-12-22T00:00:00",
        "current_phase": None,
        "error": None,
        "files": {"new": 1, "modified": 1},
    }


class TestListProjects:
    """Tests for GET /helix/evolution/projects."""

    def test_list_empty(self, client, mock_manager):
        """Test listing with no projects."""
        mock_manager.return_value.list_projects.return_value = []

        response = client.get("/helix/evolution/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["projects"] == []

    def test_list_with_projects(self, client, mock_manager, sample_project_dict):
        """Test listing with projects."""
        mock_project = MagicMock()
        mock_project.to_dict.return_value = sample_project_dict
        mock_manager.return_value.list_projects.return_value = [mock_project]

        response = client.get("/helix/evolution/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["projects"][0]["name"] == "test-feature"


class TestGetProject:
    """Tests for GET /helix/evolution/projects/{name}."""

    def test_get_existing(self, client, mock_manager, sample_project_dict):
        """Test getting an existing project."""
        mock_project = MagicMock()
        mock_project.to_dict.return_value = sample_project_dict
        mock_manager.return_value.get_project.return_value = mock_project

        response = client.get("/helix/evolution/projects/test-feature")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-feature"

    def test_get_not_found(self, client, mock_manager):
        """Test getting a non-existent project."""
        mock_manager.return_value.get_project.return_value = None

        response = client.get("/helix/evolution/projects/nonexistent")

        assert response.status_code == 404


class TestDeployProject:
    """Tests for POST /helix/evolution/projects/{name}/deploy."""

    def test_deploy_success(self, client, mock_manager):
        """Test successful deploy."""
        mock_project = MagicMock()
        mock_manager.return_value.get_project.return_value = mock_project

        with patch("helix.api.routes.evolution.Deployer") as mock_deployer:
            mock_deployer.return_value.full_deploy = AsyncMock(
                return_value=DeployResult(
                    success=True,
                    message="Deployed",
                    files_copied=5,
                )
            )

            response = client.post("/helix/evolution/projects/test/deploy")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["files_copied"] == 5

    def test_deploy_not_found(self, client, mock_manager):
        """Test deploy of non-existent project."""
        mock_manager.return_value.get_project.return_value = None

        response = client.post("/helix/evolution/projects/nonexistent/deploy")

        assert response.status_code == 404


class TestValidateProject:
    """Tests for POST /helix/evolution/projects/{name}/validate."""

    def test_validate_success(self, client, mock_manager):
        """Test successful validation."""
        mock_project = MagicMock()
        mock_project.get_status.return_value = EvolutionStatus.DEPLOYED
        mock_manager.return_value.get_project.return_value = mock_project

        with patch("helix.api.routes.evolution.Validator") as mock_validator:
            mock_validator.return_value.full_validation = AsyncMock(
                return_value=ValidationResult(
                    success=True,
                    level=ValidationLevel.FULL,
                    message="All passed",
                    passed=10,
                    failed=0,
                )
            )

            response = client.post("/helix/evolution/projects/test/validate")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["passed"] == 10

    def test_validate_not_deployed(self, client, mock_manager):
        """Test validation of non-deployed project."""
        mock_project = MagicMock()
        mock_project.get_status.return_value = EvolutionStatus.PENDING
        mock_manager.return_value.get_project.return_value = mock_project

        response = client.post("/helix/evolution/projects/test/validate")

        assert response.status_code == 400


class TestIntegrateProject:
    """Tests for POST /helix/evolution/projects/{name}/integrate."""

    def test_integrate_success(self, client, mock_manager):
        """Test successful integration."""
        mock_project = MagicMock()
        mock_manager.return_value.get_project.return_value = mock_project

        with patch("helix.api.routes.evolution.Integrator") as mock_integrator:
            mock_integrator.return_value.full_integration = AsyncMock(
                return_value=IntegrationResult(
                    success=True,
                    message="Integrated",
                    files_integrated=5,
                    backup_tag="pre-integrate-123",
                )
            )

            response = client.post("/helix/evolution/projects/test/integrate")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["files_integrated"] == 5


class TestRollback:
    """Tests for POST /helix/evolution/projects/{name}/rollback."""

    def test_rollback_success(self, client):
        """Test successful rollback."""
        with patch("helix.api.routes.evolution.Integrator") as mock_integrator:
            mock_integrator.return_value.rollback = AsyncMock(
                return_value=IntegrationResult(
                    success=True,
                    message="Rolled back",
                    backup_tag="pre-integrate-123",
                )
            )

            response = client.post("/helix/evolution/projects/test/rollback")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestSyncRAG:
    """Tests for POST /helix/evolution/sync-rag."""

    def test_sync_success(self, client):
        """Test successful RAG sync."""
        with patch("helix.api.routes.evolution.RAGSync") as mock_sync:
            mock_sync.return_value.sync_all_collections = AsyncMock(
                return_value=SyncResult(
                    success=True,
                    status=SyncStatus.COMPLETED,
                    message="Synced",
                    collections_synced=3,
                    points_synced=1000,
                )
            )

            response = client.post("/helix/evolution/sync-rag")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["collections_synced"] == 3


class TestSyncRAGStatus:
    """Tests for GET /helix/evolution/sync-rag/status."""

    def test_get_status(self, client):
        """Test getting sync status."""
        with patch("helix.api.routes.evolution.RAGSync") as mock_sync:
            mock_sync.return_value.get_sync_status = AsyncMock(
                return_value=SyncResult(
                    success=True,
                    status=SyncStatus.COMPLETED,
                    message="In sync",
                    collections_synced=3,
                )
            )

            response = client.get("/helix/evolution/sync-rag/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"


class TestEvolutionHealth:
    """Tests for GET /helix/evolution/health."""

    def test_health_success(self, client):
        """Test health check success."""
        with patch("helix.api.routes.evolution.Deployer") as mock_deployer:
            mock_deployer.return_value.check_test_system_health = AsyncMock(
                return_value=DeployResult(
                    success=True,
                    message="Healthy",
                )
            )

            response = client.get("/helix/evolution/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
