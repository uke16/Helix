"""
Evolution API routes for HELIX v4 Self-Evolution System.

This module provides REST API endpoints for managing evolution projects,
including deploying to test, validation, integration, and RAG sync.

Endpoints:
    GET    /helix/evolution/projects              - List all evolution projects
    GET    /helix/evolution/projects/{name}       - Get project details
    POST   /helix/evolution/projects/{name}/deploy    - Deploy to test system
    POST   /helix/evolution/projects/{name}/validate  - Run validation
    POST   /helix/evolution/projects/{name}/integrate - Integrate to production
    POST   /helix/evolution/projects/{name}/rollback  - Rollback changes
    POST   /helix/evolution/sync-rag              - Sync RAG embeddings
    GET    /helix/evolution/status                - Get overall evolution status
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from helix.evolution.project import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
)
from helix.evolution.deployer import Deployer, DeploymentResult
from helix.evolution.validator import Validator, FullValidationResult
from helix.evolution.integrator import Integrator, IntegrationResult
from helix.evolution.rag_sync import RAGSync, SyncResult


router = APIRouter(prefix="/helix/evolution", tags=["Evolution"])


# Request/Response Models

class DeployRequest(BaseModel):
    """Request for deploying a project to test system."""

    full_deploy: bool = Field(
        default=True,
        description="If True, runs sync + deploy + restart. If False, just deploys files."
    )


class ValidateRequest(BaseModel):
    """Request for validating a deployed project."""

    skip_e2e: bool = Field(
        default=False,
        description="If True, skips E2E tests (only runs syntax + unit tests)."
    )


class IntegrateRequest(BaseModel):
    """Request for integrating a project into production."""

    commit: bool = Field(
        default=True,
        description="If True, commits the integrated changes to git."
    )
    restart: bool = Field(
        default=True,
        description="If True, restarts the production API after integration."
    )


class RollbackRequest(BaseModel):
    """Request for rolling back changes."""

    target: str = Field(
        default="test",
        description="Target to rollback: 'test' for test system, 'production' for production."
    )
    tag: str | None = Field(
        default=None,
        description="Optional git tag to rollback to (production only)."
    )


class SyncRAGRequest(BaseModel):
    """Request for syncing RAG embeddings."""

    collections: list[str] | None = Field(
        default=None,
        description="Optional list of collection names to sync. If None, syncs all."
    )


class ProjectListResponse(BaseModel):
    """Response for listing projects."""

    projects: list[dict[str, Any]]
    count: int


class StatusResponse(BaseModel):
    """Response for evolution status."""

    test_system: dict[str, Any]
    production_system: dict[str, Any]
    rag_sync: dict[str, Any]
    active_deployment: dict[str, Any] | None


# Endpoints

@router.get("/projects")
async def list_evolution_projects(
    status: str | None = Query(
        default=None,
        description="Filter by status (pending, developing, ready, deployed, integrated, failed)"
    ),
) -> ProjectListResponse:
    """
    List all evolution projects.

    Returns a list of all evolution projects with their current status.
    Can be filtered by status.
    """
    manager = EvolutionProjectManager()

    if status:
        try:
            filter_status = EvolutionStatus(status)
            projects = manager.get_projects_by_status(filter_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in EvolutionStatus]}"
            )
    else:
        projects = manager.list_projects()

    return ProjectListResponse(
        projects=[p.to_dict() for p in projects],
        count=len(projects),
    )


@router.get("/projects/{name}")
async def get_evolution_project(name: str) -> dict[str, Any]:
    """
    Get details of a specific evolution project.

    Returns full project information including files, status, and metadata.
    """
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Evolution project not found: {name}"
        )

    # Include additional details
    result = project.to_dict()

    # Add conflict information
    conflicts = manager.check_conflicts(project)
    result["conflicts"] = conflicts

    # Try to include spec and phases info
    try:
        result["spec"] = project.get_spec()
    except FileNotFoundError:
        result["spec"] = None

    try:
        result["phases"] = project.get_phases()
    except FileNotFoundError:
        result["phases"] = None

    return result


@router.post("/projects/{name}/deploy")
async def deploy_project(name: str, request: DeployRequest | None = None) -> dict[str, Any]:
    """
    Deploy an evolution project to the test system.

    Copies project files to helix-v4-test and restarts the test API.

    Steps (full_deploy=True):
    1. Sync test system with production (git fetch + reset)
    2. Copy new and modified files
    3. Restart test API

    Steps (full_deploy=False):
    1. Copy new and modified files only
    """
    if request is None:
        request = DeployRequest()

    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Evolution project not found: {name}"
        )

    # Check project status
    if project.status not in {EvolutionStatus.READY, EvolutionStatus.PENDING, EvolutionStatus.DEVELOPING}:
        raise HTTPException(
            status_code=400,
            detail=f"Project cannot be deployed in {project.status.value} status. "
                   f"Expected: pending, developing, or ready"
        )

    # Check for conflicts
    conflicts = manager.check_conflicts(project)
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail=f"Project has conflicts with other projects: {conflicts}"
        )

    deployer = Deployer()

    if request.full_deploy:
        result = await deployer.full_deploy(project)
    else:
        result = await deployer.deploy(project)

    if result.success:
        # Update project status
        project.update_status(EvolutionStatus.DEPLOYED)

    return result.to_dict()


@router.post("/projects/{name}/validate")
async def validate_project(name: str, request: ValidateRequest | None = None) -> dict[str, Any]:
    """
    Validate a deployed evolution project.

    Runs validation checks on the test system:
    1. Syntax check on all Python files
    2. Unit tests (pytest)
    3. E2E tests against test API (optional)

    The project must be deployed before validation.
    """
    if request is None:
        request = ValidateRequest()

    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Evolution project not found: {name}"
        )

    # Check project status
    if project.status != EvolutionStatus.DEPLOYED:
        raise HTTPException(
            status_code=400,
            detail=f"Project must be deployed before validation. Current status: {project.status.value}"
        )

    validator = Validator()
    result = await validator.full_validation(project, skip_e2e=request.skip_e2e)

    if result.success:
        # Update project status to ready (for integration)
        project.update_status(EvolutionStatus.READY)
    else:
        # Update project status to failed
        failed_checks = [r.check_name for r in result.results if r.status.value == "failed"]
        project.update_status(
            EvolutionStatus.FAILED,
            error=f"Validation failed: {', '.join(failed_checks)}"
        )

    return result.to_dict()


@router.post("/projects/{name}/integrate")
async def integrate_project(name: str, request: IntegrateRequest | None = None) -> dict[str, Any]:
    """
    Integrate an evolution project into production.

    Copies validated files from the evolution project to helix-v4 (production).

    Steps:
    1. Create git backup tag for rollback capability
    2. Copy new and modified files to production
    3. Commit changes (optional)
    4. Restart production API (optional)

    The project should be validated (status: ready) before integration.
    """
    if request is None:
        request = IntegrateRequest()

    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Evolution project not found: {name}"
        )

    # Check project status - allow both READY and DEPLOYED
    if project.status not in {EvolutionStatus.READY, EvolutionStatus.DEPLOYED}:
        raise HTTPException(
            status_code=400,
            detail=f"Project must be ready or deployed for integration. Current status: {project.status.value}"
        )

    integrator = Integrator()
    result = await integrator.full_integration(
        project,
        commit=request.commit,
        restart=request.restart,
    )

    if result.success:
        # Update project status
        project.update_status(EvolutionStatus.INTEGRATED)
    else:
        # Update project status to failed
        project.update_status(
            EvolutionStatus.FAILED,
            error=f"Integration failed: {result.message}"
        )

    return result.to_dict()


@router.post("/projects/{name}/rollback")
async def rollback_project(name: str, request: RollbackRequest | None = None) -> dict[str, Any]:
    """
    Rollback changes from an evolution project.

    For test system: Resets to clean state (git reset + clean).
    For production: Resets to specified tag or last backup tag.
    """
    if request is None:
        request = RollbackRequest()

    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Evolution project not found: {name}"
        )

    if request.target == "test":
        deployer = Deployer()
        result = await deployer.rollback()

        if result.success:
            # Reset project status back to ready
            project.update_status(EvolutionStatus.READY)

        return result.to_dict()

    elif request.target == "production":
        integrator = Integrator()
        result = await integrator.rollback(tag=request.tag)

        if result.success:
            # Reset project status
            project.update_status(EvolutionStatus.FAILED, error="Rolled back from production")

        return result.to_dict()

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rollback target: {request.target}. Valid values: test, production"
        )


@router.post("/sync-rag")
async def sync_rag(request: SyncRAGRequest | None = None) -> dict[str, Any]:
    """
    Sync RAG embeddings from production to test system.

    Copies Qdrant collections from production (port 6333) to test (port 6335).
    This ensures the test system has realistic embeddings for testing RAG features.
    """
    if request is None:
        request = SyncRAGRequest()

    rag_sync = RAGSync()
    result = await rag_sync.sync_collections(collections=request.collections)

    return result.to_dict()


@router.get("/status")
async def get_evolution_status() -> StatusResponse:
    """
    Get the overall status of the evolution system.

    Returns status information for:
    - Test system (helix-v4-test)
    - Production system (helix-v4)
    - RAG sync status
    - Currently deployed project (if any)
    """
    deployer = Deployer()
    integrator = Integrator()
    rag_sync = RAGSync()
    manager = EvolutionProjectManager()

    # Get test system status
    test_status = await deployer.get_test_system_status()

    # Get production status
    production_status = await integrator.get_integration_status()

    # Get RAG sync status
    rag_status = await rag_sync.get_sync_status()

    # Get active deployment
    active_project = manager.get_active_deployment()
    active_deployment = active_project.to_dict() if active_project else None

    return StatusResponse(
        test_system=test_status,
        production_system=production_status,
        rag_sync=rag_status,
        active_deployment=active_deployment,
    )


@router.get("/sync-rag/status")
async def get_rag_sync_status() -> dict[str, Any]:
    """
    Get the current RAG sync status.

    Shows the state of both production and test Qdrant instances
    and whether they are in sync.
    """
    rag_sync = RAGSync()
    return await rag_sync.get_sync_status()


@router.get("/sync-rag/verify")
async def verify_rag_sync() -> dict[str, Any]:
    """
    Verify that RAG data is properly synced.

    Checks for:
    - Missing collections in test
    - Extra collections in test
    - Point count mismatches
    """
    rag_sync = RAGSync()
    return await rag_sync.verify_sync()


@router.get("/backup-tags")
async def list_backup_tags() -> dict[str, list[str]]:
    """
    List all pre-evolution backup tags.

    These tags can be used for rollback operations.
    """
    integrator = Integrator()
    tags = await integrator.list_backup_tags()

    return {"tags": tags}
