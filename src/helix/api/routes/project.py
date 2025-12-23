"""Project API routes for HELIX v4.

Provides REST API endpoints for project management:
- POST /project/{name}/run - Start project execution
- GET /project/{name}/status - Get project status
- GET /projects - List all projects
- POST /project - Create a new project
- DELETE /project/{name} - Delete a project
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# Lazy imports to avoid circular dependencies
_runner = None
_tracker = None


def _get_runner():
    """Lazy load OrchestratorRunner."""
    global _runner
    if _runner is None:
        from ...orchestrator.runner import OrchestratorRunner
        _runner = OrchestratorRunner()
    return _runner


def _get_tracker():
    """Lazy load StatusTracker."""
    global _tracker
    if _tracker is None:
        from ...orchestrator.status import StatusTracker
        _tracker = StatusTracker()
    return _tracker


router = APIRouter(prefix="/project", tags=["project"])


# Request/Response Models

class RunRequest(BaseModel):
    """Request body for running a project."""
    resume: bool = Field(default=False, description="Resume from last completed phase")
    dry_run: bool = Field(default=False, description="Don't execute, just simulate")
    timeout_per_phase: int = Field(default=600, description="Timeout per phase in seconds")


class RunResponse(BaseModel):
    """Response for project run request."""
    status: str
    message: str
    project: str


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


# Background task for running projects

async def run_project_background(name: str, resume: bool, dry_run: bool, timeout: int):
    """Background task to run a project."""
    from ...orchestrator.runner import OrchestratorRunner, RunConfig

    runner = OrchestratorRunner()
    project_dir = Path(f"projects/external/{name}")

    config = RunConfig(
        project_dir=project_dir,
        resume=resume,
        dry_run=dry_run,
        timeout_per_phase=timeout,
    )

    await runner.run(name, config)


# API Endpoints

@router.post("/{name}/run", response_model=RunResponse)
async def run_project(
    name: str,
    request: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Start project execution.

    Runs the project in the background and returns immediately.

    Args:
        name: Project name.
        request: Run configuration.
        background_tasks: FastAPI background tasks.

    Returns:
        RunResponse with status.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    background_tasks.add_task(
        run_project_background,
        name,
        request.resume,
        request.dry_run,
        request.timeout_per_phase,
    )

    return RunResponse(
        status="started",
        message=f"Project '{name}' execution started in background",
        project=name,
    )


@router.get("/{name}/status", response_model=StatusResponse)
async def get_status(name: str) -> StatusResponse:
    """Get project status.

    Args:
        name: Project name.

    Returns:
        Current project status.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    tracker = _get_tracker()
    status = tracker.load_or_create(project_dir)

    return StatusResponse(
        project_id=status.project_id,
        status=status.status,
        total_phases=status.total_phases,
        completed_phases=status.completed_phases,
        started_at=status.started_at.isoformat() if status.started_at else None,
        completed_at=status.completed_at.isoformat() if status.completed_at else None,
        error=status.error,
        phases={
            pid: {
                "status": p.status,
                "started_at": p.started_at.isoformat() if p.started_at else None,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                "retries": p.retries,
                "error": p.error,
            }
            for pid, p in status.phases.items()
        },
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

    tracker = _get_tracker()
    projects = []

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue

        status = tracker.load_or_create(project_dir)
        progress = (
            f"{status.completed_phases}/{status.total_phases}"
            if status.total_phases > 0
            else "-"
        )

        projects.append(
            ProjectSummary(
                name=project_dir.name,
                status=status.status,
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
        tracker = _get_tracker()
        status = tracker.load(project_dir)
        if status and status.status == "running":
            raise HTTPException(
                status_code=409,
                detail=f"Project '{name}' is currently running. Use force=true to delete.",
            )

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

    tracker = _get_tracker()
    if tracker.delete(project_dir):
        return {"status": "reset", "project": name}
    else:
        return {"status": "no_status_file", "project": name}
