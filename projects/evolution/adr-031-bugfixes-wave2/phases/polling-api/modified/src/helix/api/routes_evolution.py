"""Evolution API Routes.

REST API endpoints for the HELIX Self-Evolution System.

ADR-031 Fix 3: Added polling-friendly status endpoints as alternative to long SSE streams.

Endpoints:
- GET  /helix/evolution/projects           - List all evolution projects
- GET  /helix/evolution/projects/{name}    - Get project details
- GET  /helix/evolution/projects/{name}/status   - Polling-friendly status (ADR-031)
- GET  /helix/evolution/projects/{name}/logs/{phase_id} - Phase logs (ADR-031)
- POST /helix/evolution/projects/{name}/deploy    - Deploy to test
- POST /helix/evolution/projects/{name}/validate  - Run validation
- POST /helix/evolution/projects/{name}/integrate - Integrate to production
- POST /helix/evolution/projects/{name}/rollback  - Rollback
- POST /helix/evolution/sync-rag           - Sync RAG databases
- GET  /helix/evolution/sync-rag/status    - Get RAG sync status
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
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


class PollingStatusResponse(BaseModel):
    """Response for polling-friendly status endpoint.

    ADR-031 Fix 3: Provides lightweight status for polling clients.
    Recommended polling interval: 5 seconds.
    """
    status: str
    current_phase: Optional[str] = None
    phases: dict
    progress: int
    updated_at: Optional[str] = None
    error: Optional[str] = None


class PhaseLogsResponse(BaseModel):
    """Response for phase logs endpoint.

    ADR-031 Fix 3: Returns logs for debugging failed phases.
    """
    logs: list[str]
    log_file: Optional[str] = None


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
async def get_project(name: str, force: bool = False):
    """Get details of a specific project."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Bug 12 fix: Guard against re-running integrated projects
    from helix.evolution.project import EvolutionStatus
    if project.get_status() == EvolutionStatus.INTEGRATED and not force:
        raise HTTPException(
            status_code=400,
            detail="Project already integrated. Use force=true to re-run all phases."
        )

    return ProjectResponse(**project.to_dict())


@router.get("/projects/{name}/status", response_model=PollingStatusResponse)
async def get_project_status(name: str):
    """Get current project status (polling-friendly).

    ADR-031 Fix 3: Use this endpoint for status polling instead of long SSE streams.
    Recommended polling interval: 5 seconds.

    Returns:
        status: Project status (pending, developing, ready, integrated, failed)
        current_phase: Currently executing phase (if any)
        phases: Dict of phase_id -> phase_status
        progress: Completion percentage (0-100)
        updated_at: Last update timestamp
        error: Error message if failed
    """
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    status_data = project.get_status_data()

    # Calculate progress from phases
    phases = status_data.get("phases", {})
    total = len(phases)
    completed = sum(1 for p in phases.values() if p.get("status") == "completed")
    progress = int((completed / total * 100) if total > 0 else 0)

    return PollingStatusResponse(
        status=status_data.get("status", "unknown"),
        current_phase=status_data.get("current_phase"),
        phases=phases,
        progress=progress,
        updated_at=status_data.get("updated_at"),
        error=status_data.get("error"),
    )


@router.get("/projects/{name}/logs/{phase_id}", response_model=PhaseLogsResponse)
async def get_phase_logs(name: str, phase_id: str, tail: int = 100):
    """Get logs for a specific phase.

    ADR-031 Fix 3: Use for debugging when a phase fails.

    Args:
        name: Project name
        phase_id: Phase ID
        tail: Number of lines from end (default 100)

    Returns:
        logs: List of log lines
        log_file: Path to full log file
    """
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    log_file = project.path / "phases" / phase_id / "output" / "claude.log"

    if not log_file.exists():
        # Try alternative log locations
        alt_log_file = project.path / "phases" / phase_id / "claude.log"
        if alt_log_file.exists():
            log_file = alt_log_file
        else:
            return PhaseLogsResponse(logs=[], log_file=None)

    try:
        lines = log_file.read_text().splitlines()
        return PhaseLogsResponse(
            logs=lines[-tail:],
            log_file=str(log_file),
        )
    except Exception as e:
        return PhaseLogsResponse(
            logs=[f"Error reading log file: {str(e)}"],
            log_file=str(log_file),
        )


@router.post("/projects/{name}/deploy", response_model=DeployResponse)
async def deploy_project(name: str, request: DeployRequest = DeployRequest(), force: bool = False):
    """Deploy a project to the test system."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Bug 12 fix: Guard against re-running integrated projects
    from helix.evolution.project import EvolutionStatus
    if project.get_status() == EvolutionStatus.INTEGRATED and not force:
        raise HTTPException(
            status_code=400,
            detail="Project already integrated. Use force=true to re-run all phases."
        )

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
async def validate_project(name: str, force: bool = False):
    """Run validation on a deployed project."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Bug 12 fix: Guard against re-running integrated projects
    from helix.evolution.project import EvolutionStatus
    if project.get_status() == EvolutionStatus.INTEGRATED and not force:
        raise HTTPException(
            status_code=400,
            detail="Project already integrated. Use force=true to re-run all phases."
        )

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
async def integrate_project(name: str, force: bool = False):
    """Integrate a validated project into production."""
    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Bug 12 fix: Guard against re-running integrated projects
    from helix.evolution.project import EvolutionStatus
    if project.get_status() == EvolutionStatus.INTEGRATED and not force:
        raise HTTPException(
            status_code=400,
            detail="Project already integrated. Use force=true to re-run all phases."
        )

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


@router.post("/projects/{name}/run")
async def run_evolution_project(
    name: str,
    background_tasks: BackgroundTasks,
    auto_integrate: bool = False,
    force: bool = False,
):
    """Run complete evolution workflow for a project.

    This is the main entry point after the Consultant creates a project.
    It orchestrates the entire evolution pipeline:

    1. Execute: Run all phases (Developer, Reviewer, Documentation)
    2. Deploy: Copy to test system
    3. Validate: Run tests
    4. Integrate: Copy to production (if auto_integrate=True and tests pass)

    Args:
        name: Project name
        auto_integrate: If True, automatically integrate on successful validation

    Returns:
        Job ID for tracking progress via SSE
    """
    from ..streaming import run_evolution_pipeline
    from ..job_manager import job_manager

    manager = EvolutionProjectManager()
    project = manager.get_project(name)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Bug 12 fix: Guard against re-running integrated projects
    from helix.evolution.project import EvolutionStatus
    if project.get_status() == EvolutionStatus.INTEGRATED and not force:
        raise HTTPException(
            status_code=400,
            detail="Project already integrated. Use force=true to re-run all phases."
        )

    # Create job for tracking
    job = await job_manager.create_job()

    # Start pipeline in background
    background_tasks.add_task(
        run_evolution_pipeline,
        job,
        project,
        auto_integrate,
    )

    return {
        "job_id": job.job_id,
        "project": name,
        "status": "started",
        "message": "Evolution pipeline started. Use /helix/jobs/{job_id} to track progress.",
        "auto_integrate": auto_integrate,
    }
