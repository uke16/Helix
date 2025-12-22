"""
Unit tests for Evolution API routes.

Tests cover all endpoints in the evolution API:
- Project listing and retrieval
- Deploy, validate, integrate, rollback workflows
- RAG sync operations
- Status endpoints
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router
from helix.api.routes.evolution import router

# Import models for mocking
from helix.evolution.project import EvolutionProject, EvolutionProjectManager, EvolutionStatus
from helix.evolution.deployer import Deployer, DeploymentResult, DeploymentStatus
from helix.evolution.validator import (
    Validator,
    FullValidationResult,
    ValidationResult,
    ValidationStatus,
)
from helix.evolution.integrator import Integrator, IntegrationResult, IntegrationStatus
from helix.evolution.rag_sync import RAGSync, SyncResult, SyncStatus, CollectionSyncResult


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# Fixtures

@pytest.fixture
def mock_project() -> EvolutionProject:
    """Create a mock evolution project."""
    return EvolutionProject(
        name="test-feature",
        session_id="session-123",
        status=EvolutionStatus.READY,
        path=Path("/home/aiuser01/helix-v4/projects/evolution/test-feature"),
        created_at=datetime(2024, 1, 15, 10, 0, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def mock_project_deployed() -> EvolutionProject:
    """Create a mock deployed project."""
    return EvolutionProject(
        name="test-feature",
        session_id="session-123",
        status=EvolutionStatus.DEPLOYED,
        path=Path("/home/aiuser01/helix-v4/projects/evolution/test-feature"),
        created_at=datetime(2024, 1, 15, 10, 0, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def mock_deployment_result() -> DeploymentResult:
    """Create a mock successful deployment result."""
    return DeploymentResult(
        success=True,
        status=DeploymentStatus.COMPLETED,
        message="Deployed successfully",
        files_copied=["new:src/helix/new_file.py"],
        started_at=datetime(2024, 1, 15, 12, 0, 0),
        completed_at=datetime(2024, 1, 15, 12, 1, 0),
    )


@pytest.fixture
def mock_validation_result() -> FullValidationResult:
    """Create a mock successful validation result."""
    return FullValidationResult(
        success=True,
        results=[
            ValidationResult(
                check_name="syntax_check",
                status=ValidationStatus.PASSED,
                message="All files passed syntax check",
                duration_seconds=1.5,
            ),
            ValidationResult(
                check_name="unit_tests",
                status=ValidationStatus.PASSED,
                message="All tests passed (50 tests)",
                duration_seconds=30.0,
            ),
        ],
        started_at=datetime(2024, 1, 15, 12, 0, 0),
        completed_at=datetime(2024, 1, 15, 12, 0, 32),
    )


@pytest.fixture
def mock_integration_result() -> IntegrationResult:
    """Create a mock successful integration result."""
    return IntegrationResult(
        success=True,
        status=IntegrationStatus.COMPLETED,
        message="Integration completed",
        backup_tag="pre-evolution-test-feature-20240115-120000",
        files_integrated=["new:src/helix/new_file.py"],
        started_at=datetime(2024, 1, 15, 12, 0, 0),
        completed_at=datetime(2024, 1, 15, 12, 2, 0),
    )


@pytest.fixture
def mock_sync_result() -> SyncResult:
    """Create a mock successful sync result."""
    return SyncResult(
        success=True,
        status=SyncStatus.COMPLETED,
        message="Synced 2 collections, 1000 total points",
        collections_synced=[
            CollectionSyncResult(
                collection_name="documents",
                success=True,
                points_synced=800,
            ),
            CollectionSyncResult(
                collection_name="code",
                success=True,
                points_synced=200,
            ),
        ],
        started_at=datetime(2024, 1, 15, 12, 0, 0),
        completed_at=datetime(2024, 1, 15, 12, 5, 0),
    )


# Test: List Projects

class TestListProjects:
    """Tests for GET /helix/evolution/projects endpoint."""

    def test_list_projects_empty(self):
        """Test listing projects when none exist."""
        with patch.object(EvolutionProjectManager, "list_projects", return_value=[]):
            response = client.get("/helix/evolution/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["count"] == 0

    def test_list_projects_with_projects(self, mock_project):
        """Test listing projects when some exist."""
        with patch.object(EvolutionProjectManager, "list_projects", return_value=[mock_project]):
            response = client.get("/helix/evolution/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["projects"][0]["name"] == "test-feature"
        assert data["projects"][0]["status"] == "ready"

    def test_list_projects_filter_by_status(self, mock_project):
        """Test filtering projects by status."""
        with patch.object(
            EvolutionProjectManager, "get_projects_by_status", return_value=[mock_project]
        ) as mock_method:
            response = client.get("/helix/evolution/projects?status=ready")

        assert response.status_code == 200
        mock_method.assert_called_once_with(EvolutionStatus.READY)

    def test_list_projects_invalid_status(self):
        """Test filtering with invalid status."""
        response = client.get("/helix/evolution/projects?status=invalid")

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]


# Test: Get Project

class TestGetProject:
    """Tests for GET /helix/evolution/projects/{name} endpoint."""

    def test_get_project_found(self, mock_project):
        """Test getting an existing project."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(EvolutionProjectManager, "check_conflicts", return_value={}):
                with patch.object(mock_project, "get_spec", return_value={"name": "test"}):
                    with patch.object(mock_project, "get_phases", return_value={"phases": []}):
                        response = client.get("/helix/evolution/projects/test-feature")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-feature"
        assert data["status"] == "ready"
        assert data["conflicts"] == {}

    def test_get_project_not_found(self):
        """Test getting a non-existent project."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=None):
            response = client.get("/helix/evolution/projects/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# Test: Deploy Project

class TestDeployProject:
    """Tests for POST /helix/evolution/projects/{name}/deploy endpoint."""

    def test_deploy_project_success(self, mock_project, mock_deployment_result):
        """Test successful project deployment."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(EvolutionProjectManager, "check_conflicts", return_value={}):
                with patch.object(
                    Deployer, "full_deploy", new_callable=AsyncMock, return_value=mock_deployment_result
                ):
                    with patch.object(mock_project, "update_status"):
                        response = client.post("/helix/evolution/projects/test-feature/deploy")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"

    def test_deploy_project_not_found(self):
        """Test deploying non-existent project."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=None):
            response = client.post("/helix/evolution/projects/nonexistent/deploy")

        assert response.status_code == 404

    def test_deploy_project_wrong_status(self, mock_project):
        """Test deploying project in wrong status."""
        mock_project.status = EvolutionStatus.INTEGRATED

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            response = client.post("/helix/evolution/projects/test-feature/deploy")

        assert response.status_code == 400
        assert "cannot be deployed" in response.json()["detail"]

    def test_deploy_project_with_conflicts(self, mock_project):
        """Test deploying project with conflicts."""
        conflicts = {"other-project": ["src/helix/file.py"]}

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(EvolutionProjectManager, "check_conflicts", return_value=conflicts):
                response = client.post("/helix/evolution/projects/test-feature/deploy")

        assert response.status_code == 409
        assert "conflicts" in response.json()["detail"]


# Test: Validate Project

class TestValidateProject:
    """Tests for POST /helix/evolution/projects/{name}/validate endpoint."""

    def test_validate_project_success(self, mock_project_deployed, mock_validation_result):
        """Test successful project validation."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project_deployed):
            with patch.object(
                Validator, "full_validation", new_callable=AsyncMock, return_value=mock_validation_result
            ):
                with patch.object(mock_project_deployed, "update_status"):
                    response = client.post("/helix/evolution/projects/test-feature/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["passed_count"] == 2

    def test_validate_project_not_deployed(self, mock_project):
        """Test validating non-deployed project."""
        mock_project.status = EvolutionStatus.PENDING

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            response = client.post("/helix/evolution/projects/test-feature/validate")

        assert response.status_code == 400
        assert "must be deployed" in response.json()["detail"]

    def test_validate_project_skip_e2e(self, mock_project_deployed, mock_validation_result):
        """Test validation with skip_e2e option."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project_deployed):
            with patch.object(
                Validator, "full_validation", new_callable=AsyncMock, return_value=mock_validation_result
            ) as mock_validate:
                with patch.object(mock_project_deployed, "update_status"):
                    response = client.post(
                        "/helix/evolution/projects/test-feature/validate",
                        json={"skip_e2e": True}
                    )

        assert response.status_code == 200
        mock_validate.assert_called_once_with(mock_project_deployed, skip_e2e=True)


# Test: Integrate Project

class TestIntegrateProject:
    """Tests for POST /helix/evolution/projects/{name}/integrate endpoint."""

    def test_integrate_project_success(self, mock_project, mock_integration_result):
        """Test successful project integration."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(
                Integrator, "full_integration", new_callable=AsyncMock, return_value=mock_integration_result
            ):
                with patch.object(mock_project, "update_status"):
                    response = client.post("/helix/evolution/projects/test-feature/integrate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["backup_tag"] is not None

    def test_integrate_project_wrong_status(self, mock_project):
        """Test integrating project in wrong status."""
        mock_project.status = EvolutionStatus.PENDING

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            response = client.post("/helix/evolution/projects/test-feature/integrate")

        assert response.status_code == 400
        assert "must be ready or deployed" in response.json()["detail"]


# Test: Rollback Project

class TestRollbackProject:
    """Tests for POST /helix/evolution/projects/{name}/rollback endpoint."""

    def test_rollback_test_system(self, mock_project, mock_deployment_result):
        """Test rolling back test system."""
        mock_deployment_result.status = DeploymentStatus.ROLLED_BACK

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(
                Deployer, "rollback", new_callable=AsyncMock, return_value=mock_deployment_result
            ):
                with patch.object(mock_project, "update_status"):
                    response = client.post(
                        "/helix/evolution/projects/test-feature/rollback",
                        json={"target": "test"}
                    )

        assert response.status_code == 200

    def test_rollback_production(self, mock_project, mock_integration_result):
        """Test rolling back production."""
        mock_integration_result.status = IntegrationStatus.ROLLED_BACK

        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            with patch.object(
                Integrator, "rollback", new_callable=AsyncMock, return_value=mock_integration_result
            ):
                with patch.object(mock_project, "update_status"):
                    response = client.post(
                        "/helix/evolution/projects/test-feature/rollback",
                        json={"target": "production", "tag": "pre-evolution-20240115"}
                    )

        assert response.status_code == 200

    def test_rollback_invalid_target(self, mock_project):
        """Test rollback with invalid target."""
        with patch.object(EvolutionProjectManager, "get_project", return_value=mock_project):
            response = client.post(
                "/helix/evolution/projects/test-feature/rollback",
                json={"target": "invalid"}
            )

        assert response.status_code == 400
        assert "Invalid rollback target" in response.json()["detail"]


# Test: RAG Sync

class TestSyncRAG:
    """Tests for POST /helix/evolution/sync-rag endpoint."""

    def test_sync_rag_all_collections(self, mock_sync_result):
        """Test syncing all RAG collections."""
        with patch.object(
            RAGSync, "sync_collections", new_callable=AsyncMock, return_value=mock_sync_result
        ) as mock_sync:
            response = client.post("/helix/evolution/sync-rag")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_points_synced"] == 1000
        mock_sync.assert_called_once_with(collections=None)

    def test_sync_rag_specific_collections(self, mock_sync_result):
        """Test syncing specific collections."""
        with patch.object(
            RAGSync, "sync_collections", new_callable=AsyncMock, return_value=mock_sync_result
        ) as mock_sync:
            response = client.post(
                "/helix/evolution/sync-rag",
                json={"collections": ["documents"]}
            )

        assert response.status_code == 200
        mock_sync.assert_called_once_with(collections=["documents"])


# Test: Status Endpoints

class TestStatusEndpoints:
    """Tests for status endpoints."""

    def test_get_evolution_status(self, mock_project):
        """Test getting overall evolution status."""
        test_status = {"exists": True, "api_running": True}
        prod_status = {"exists": True, "api_running": True}
        rag_status = {"in_sync": True}

        with patch.object(
            Deployer, "get_test_system_status", new_callable=AsyncMock, return_value=test_status
        ):
            with patch.object(
                Integrator, "get_integration_status", new_callable=AsyncMock, return_value=prod_status
            ):
                with patch.object(
                    RAGSync, "get_sync_status", new_callable=AsyncMock, return_value=rag_status
                ):
                    with patch.object(
                        EvolutionProjectManager, "get_active_deployment", return_value=mock_project
                    ):
                        response = client.get("/helix/evolution/status")

        assert response.status_code == 200
        data = response.json()
        assert "test_system" in data
        assert "production_system" in data
        assert "rag_sync" in data
        assert data["active_deployment"] is not None

    def test_get_rag_sync_status(self):
        """Test getting RAG sync status."""
        status = {
            "production": {"healthy": True, "collections": ["docs"]},
            "test": {"healthy": True, "collections": ["docs"]},
            "in_sync": True,
        }

        with patch.object(RAGSync, "get_sync_status", new_callable=AsyncMock, return_value=status):
            response = client.get("/helix/evolution/sync-rag/status")

        assert response.status_code == 200
        assert response.json()["in_sync"] is True

    def test_verify_rag_sync(self):
        """Test verifying RAG sync."""
        verification = {
            "verified": True,
            "production_collections": ["docs"],
            "test_collections": ["docs"],
            "missing_in_test": [],
            "extra_in_test": [],
            "point_count_mismatches": [],
        }

        with patch.object(RAGSync, "verify_sync", new_callable=AsyncMock, return_value=verification):
            response = client.get("/helix/evolution/sync-rag/verify")

        assert response.status_code == 200
        assert response.json()["verified"] is True

    def test_list_backup_tags(self):
        """Test listing backup tags."""
        tags = ["pre-evolution-feature1-20240115", "pre-evolution-feature2-20240114"]

        with patch.object(Integrator, "list_backup_tags", new_callable=AsyncMock, return_value=tags):
            response = client.get("/helix/evolution/backup-tags")

        assert response.status_code == 200
        assert response.json()["tags"] == tags


# Integration Tests (Optional - require actual system)

class TestIntegrationTests:
    """
    Integration tests that require the actual HELIX system.

    These tests are marked with pytest.mark.integration and are skipped
    by default. Run with: pytest -m integration
    """

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires actual HELIX system")
    def test_full_evolution_workflow(self):
        """Test complete evolution workflow: deploy -> validate -> integrate."""
        # This would test the full workflow against a real system
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires actual Qdrant instances")
    def test_real_rag_sync(self):
        """Test RAG sync against real Qdrant instances."""
        pass
