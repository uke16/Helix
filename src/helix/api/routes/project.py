"""Project API routes for HELIX v4.

All project execution uses UnifiedOrchestrator (ADR-022).
This module provides REST API endpoints for project management:
- POST /project/{name}/run - Start project execution via UnifiedOrchestrator
- GET /project/{name}/status - Get project status
- GET /projects - List all projects
- POST /project - Create a new project
- DELETE /project/{name} - Delete a project
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from ..orchestrator import UnifiedOrchestrator
from ..job_manager import job_manager, Job
from ..models import JobStatus, PhaseStatus, PhaseEvent
from ..streaming import run_project_with_streaming


router = APIRouter(prefix="/project", tags=["project"])


# Request/Response Models

class RunRequest(BaseModel):
    """Request body for running a project."""
    resume: bool = Field(default=False, description="Resume from last completed phase")
    dry_run: bool = Field(default=False, description="Don't execute, just simulate")
    timeout_per_phase: int = Field(default=600, description="Timeout per phase in seconds")
    phase_filter: list[str] | None = Field(default=None, description="Run only these phases")


class RunResponse(BaseModel):
    """Response for project run request."""
    status: str
    message: str
    project: str
    job_id: str


class CreateRequest(BaseModel):
    """Request body for creating a project."""
    name: str = Field(..., description="Project name")
    project_type: str = Field(default="simple", description="Project type")


class CreateResponse(BaseModel):
    """Response for project creation."""
    status: str
    project: str
    location: str
    phases: list[str]


class StatusResponse(BaseModel):
    """Response for project status."""
    project_id: str
    status: str
    total_phases: int
    completed_phases: int
    started_at: str | None
    completed_at: str | None
    error: str | None
    phases: dict[str, dict[str, Any]]


class ProjectSummary(BaseModel):
    """Summary of a project."""
    name: str
    status: str
    progress: str


# API Endpoints

@router.post("/{name}/run", response_model=RunResponse)
async def run_project(
    name: str,
    request: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Start project execution via UnifiedOrchestrator.

    Runs the project in the background using the unified orchestration
    pipeline (ADR-022). Returns job ID for tracking progress.

    Args:
        name: Project name.
        request: Run configuration.
        background_tasks: FastAPI background tasks.

    Returns:
        RunResponse with job_id for tracking.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    phases_file = project_dir / "phases.yaml"
    if not phases_file.exists():
        raise HTTPException(
            status_code=400,
            detail=f"No phases.yaml in project: {name}"
        )

    # Create job for tracking
    job = await job_manager.create_job()

    # Start execution in background via UnifiedOrchestrator
    background_tasks.add_task(
        run_project_with_streaming,
        job,
        project_dir,
        request.phase_filter,
    )

    return RunResponse(
        status="started",
        message=f"Project '{name}' execution started",
        project=name,
        job_id=job.job_id,
    )


@router.get("/{name}/status", response_model=StatusResponse)
async def get_status(name: str) -> StatusResponse:
    """Get project status.

    Args:
        name: Project name.

    Returns:
        Current project status from status.json.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Read status.json if it exists
    status_file = project_dir / "status.json"
    if status_file.exists():
        import json
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)

        return StatusResponse(
            project_id=name,
            status=status_data.get("status", "unknown"),
            total_phases=status_data.get("total_phases", 0),
            completed_phases=status_data.get("completed_phases", 0),
            started_at=status_data.get("started_at"),
            completed_at=status_data.get("completed_at"),
            error=status_data.get("error"),
            phases=status_data.get("phases", {}),
        )

    # No status file - return default
    return StatusResponse(
        project_id=name,
        status="pending",
        total_phases=0,
        completed_phases=0,
        started_at=None,
        completed_at=None,
        error=None,
        phases={},
    )


@router.get("s", response_model=list[ProjectSummary])
async def list_projects() -> list[ProjectSummary]:
    """List all projects.

    Returns:
        List of project summaries.
    """
    projects_dir = Path("projects/external")

    if not projects_dir.exists():
        return []

    projects = []

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue

        # Read status.json if available
        status_file = project_dir / "status.json"
        status = "pending"
        completed = 0
        total = 0

        if status_file.exists():
            import json
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                status = status_data.get("status", "pending")
                completed = status_data.get("completed_phases", 0)
                total = status_data.get("total_phases", 0)
            except (json.JSONDecodeError, IOError):
                pass

        progress = f"{completed}/{total}" if total > 0 else "-"

        projects.append(
            ProjectSummary(
                name=project_dir.name,
                status=status,
                progress=progress,
            )
        )

    return projects


@router.post("", response_model=CreateResponse)
async def create_project(request: CreateRequest) -> CreateResponse:
    """Create a new project.

    Args:
        request: Project creation request.

    Returns:
        CreateResponse with project details.
    """
    import yaml

    project_dir = Path(f"projects/external/{request.name}")

    if project_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Project already exists: {request.name}",
        )

    # Load phase types config
    config_path = Path("config/phase-types.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        project_types = config.get("project_types", {})
        default_phases = project_types.get(request.project_type, {}).get(
            "default_phases", ["consultant", "development", "review"]
        )
    else:
        default_phases = {
            "simple": ["consultant", "development", "review", "integration"],
            "complex": ["consultant", "feasibility", "planning", "development", "review", "integration"],
            "exploratory": ["consultant", "research", "decision"],
        }.get(request.project_type, ["consultant", "development", "review"])

    # Create project directory
    project_dir.mkdir(parents=True)

    # Create phases.yaml
    phases_yaml = {
        "project": {
            "name": request.name,
            "type": request.project_type,
        },
        "phases": [
            {"id": phase, "type": phase}
            for phase in default_phases
        ],
    }

    phases_file = project_dir / "phases.yaml"
    with open(phases_file, "w", encoding="utf-8") as f:
        yaml.dump(phases_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Create phase directories
    for phase in default_phases:
        phase_dir = project_dir / "phases" / phase
        (phase_dir / "input").mkdir(parents=True)
        (phase_dir / "output").mkdir(parents=True)

        # Create placeholder CLAUDE.md
        claude_md = phase_dir / "CLAUDE.md"
        claude_md.write_text(f"# Phase: {phase}\n\nTODO: Add phase instructions.\n", encoding="utf-8")

    return CreateResponse(
        status="created",
        project=request.name,
        location=str(project_dir),
        phases=default_phases,
    )


@router.delete("/{name}")
async def delete_project(name: str, force: bool = False) -> dict[str, str]:
    """Delete a project.

    Args:
        name: Project name.
        force: If True, delete even if project is running.

    Returns:
        Status message.
    """
    import shutil

    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    # Check if project is running
    if not force:
        status_file = project_dir / "status.json"
        if status_file.exists():
            import json
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                if status_data.get("status") == "running":
                    raise HTTPException(
                        status_code=409,
                        detail=f"Project '{name}' is currently running. Use force=true to delete.",
                    )
            except (json.JSONDecodeError, IOError):
                pass

    shutil.rmtree(project_dir)

    return {"status": "deleted", "project": name}


@router.post("/{name}/reset")
async def reset_project(name: str) -> dict[str, str]:
    """Reset project status.

    Clears the status file to allow re-running the project.

    Args:
        name: Project name.

    Returns:
        Status message.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    status_file = project_dir / "status.json"
    if status_file.exists():
        status_file.unlink()
        return {"status": "reset", "project": name}
    else:
        return {"status": "no_status_file", "project": name}
