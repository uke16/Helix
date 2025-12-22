"""Evolution API Routes.

REST API endpoints for the HELIX Self-Evolution System.

Endpoints:
- GET  /helix/evolution/projects           - List all evolution projects
- GET  /helix/evolution/projects/{name}    - Get project details
- POST /helix/evolution/projects/{name}/deploy    - Deploy to test
- POST /helix/evolution/projects/{name}/validate  - Run validation
- POST /helix/evolution/projects/{name}/integrate - Integrate to production
- POST /helix/evolution/projects/{name}/rollback  - Rollback
- POST /helix/evolution/sync-rag           - Sync RAG databases
- GET  /helix/evolution/sync-rag/status    - Get RAG sync status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from helix.evolution import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    EvolutionError,
    Deployer,
    Validator,
    Integrator,
    RAGSync,
)


router = APIRouter(prefix="/helix/evolution", tags=["evolution"])


# Request/Response Models
class ProjectResponse(BaseModel):
    """Response for a single project."""
    name: str
    path: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_phase: Optional[str] = None
    error: Optional[str] = None
    files: dict


class ProjectListResponse(BaseModel):
    """Response for list of projects."""
    projects: list[ProjectResponse]
    total: int


class DeployRequest(BaseModel):
    """Request for deploy operation."""
    full_deploy: bool = True


class DeployResponse(BaseModel):
    """Response for deploy operation."""
    success: bool
    message: str
    files_copied: int = 0
    error: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response for validation operation."""
    success: bool
    level: str
    message: str
    passed: int = 0
    failed: int = 0
    errors: list[str] = []


class IntegrationResponse(BaseModel):
    """Response for integration operation."""
    success: bool
    message: str
    backup_tag: Optional[str] = None
    files_integrated: int = 0
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Response for RAG sync operation."""
    success: bool
    status: str
    message: str
    collections_synced: int = 0
    points_synced: int = 0
    error: Optional[str] = None
    details: Optional[dict] = None


# Endpoints
@router.get("/projects", response_model=ProjectListResponse)
async def list_projects():
    """List all evolution projects."""
    manager = EvolutionProjectManager()
    projects = manager.list_projects()
    
    return ProjectListResponse(
        projects=[ProjectResponse(**p.to_dict()) for p in projects],
        total=len(projects),
    )


@router.get("/projects/{name}", response_model=ProjectResponse)
async def get_project(name: str):
    """Get details of a specific project."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)
    
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")
    
    return ProjectResponse(**project.to_dict())


@router.post("/projects/{name}/deploy", response_model=DeployResponse)
async def deploy_project(name: str, request: DeployRequest = DeployRequest()):
    """Deploy a project to the test system."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)
    
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")
    
    deployer = Deployer()
    
    if request.full_deploy:
        result = await deployer.full_deploy(project)
    else:
        result = await deployer.deploy(project)
    
    return DeployResponse(
        success=result.success,
        message=result.message,
        files_copied=result.files_copied,
        error=result.error,
    )


@router.post("/projects/{name}/validate", response_model=ValidationResponse)
async def validate_project(name: str):
    """Run validation on a deployed project."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)
    
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")
    
    # Check project is deployed
    if project.get_status() != EvolutionStatus.DEPLOYED:
        raise HTTPException(
            status_code=400,
            detail=f"Project must be deployed first (current status: {project.get_status().value})"
        )
    
    validator = Validator()
    result = await validator.full_validation()
    
    return ValidationResponse(
        success=result.success,
        level=result.level.value,
        message=result.message,
        passed=result.passed,
        failed=result.failed,
        errors=result.errors,
    )


@router.post("/projects/{name}/integrate", response_model=IntegrationResponse)
async def integrate_project(name: str):
    """Integrate a validated project into production."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)
    
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")
    
    integrator = Integrator()
    result = await integrator.full_integration(project)
    
    return IntegrationResponse(
        success=result.success,
        message=result.message,
        backup_tag=result.backup_tag,
        files_integrated=result.files_integrated,
        error=result.error,
    )


@router.post("/projects/{name}/rollback", response_model=IntegrationResponse)
async def rollback_project(name: str):
    """Rollback a failed integration."""
    integrator = Integrator()
    result = await integrator.rollback()
    
    return IntegrationResponse(
        success=result.success,
        message=result.message,
        backup_tag=result.backup_tag,
        error=result.error,
    )


@router.post("/sync-rag", response_model=SyncResponse)
async def sync_rag():
    """Sync RAG databases from production to test."""
    rag_sync = RAGSync()
    result = await rag_sync.sync_all_collections()
    
    return SyncResponse(
        success=result.success,
        status=result.status.value,
        message=result.message,
        collections_synced=result.collections_synced,
        points_synced=result.points_synced,
        error=result.error,
        details=result.details,
    )


@router.get("/sync-rag/status", response_model=SyncResponse)
async def get_rag_sync_status():
    """Get RAG sync status."""
    rag_sync = RAGSync()
    result = await rag_sync.get_sync_status()
    
    return SyncResponse(
        success=result.success,
        status=result.status.value,
        message=result.message,
        collections_synced=result.collections_synced,
        details=result.details,
    )


@router.get("/health")
async def evolution_health():
    """Health check for evolution system."""
    # Check if test system is accessible
    deployer = Deployer()
    test_health = await deployer.check_test_system_health()
    
    return {
        "status": "healthy" if test_health.success else "degraded",
        "test_system": {
            "healthy": test_health.success,
            "message": test_health.message,
        },
    }
