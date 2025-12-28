"""HELIX API Routes - ADR-030 Fix 2: Job Status with Phases.

This module provides the job status endpoint that now includes phase information.

ADR-030 Fix 2 Implementation:
- GET /helix/jobs/{job_id} returns phases array with full phase information
- Each phase includes: id, name, status, started_at, completed_at, duration_seconds
- Phases are tracked in JobState during execution via streaming.py

Response Format:
{
    "job_id": "abc123",
    "status": "running",
    "phases": [
        {
            "phase_id": "phase-1",
            "name": "Development Phase",
            "status": "completed",
            "started_at": "2024-12-28T10:00:00",
            "completed_at": "2024-12-28T10:05:00",
            "duration_seconds": 300.0,
            "output_files": ["src/module.py"]
        },
        {
            "phase_id": "phase-2",
            "name": "Test Phase",
            "status": "running",
            "started_at": "2024-12-28T10:05:01"
        }
    ],
    "current_phase": "phase-2",
    "created_at": "2024-12-28T09:59:00",
    "started_at": "2024-12-28T10:00:00"
}

Integration with streaming.py:
- On phase_start: job_manager.start_phase() - adds phase with RUNNING status
- On phase_complete/failed: job_manager.add_phase_result() - updates completion info

See Also:
- job_manager.py - Phase tracking methods (start_phase, add_phase_result)
- streaming.py - Event handling that syncs phase status
- models.py - JobInfo model with phases field
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks

from .models import (
    DiscussRequest,
    ExecuteRequest,
    JobInfo,
    JobStatus,
    PhaseEvent,
)
from .job_manager import job_manager
from .streaming import run_project_with_streaming

router = APIRouter(prefix="/helix", tags=["HELIX"])


@router.post("/discuss")
async def start_discussion(request: DiscussRequest) -> dict:
    """Start a consultant discussion.

    This initiates a conversation to define a project.
    Returns immediately with a session ID.
    """
    return {
        "status": "acknowledged",
        "message": request.message,
        "project_type": request.project_type,
        "hint": "Full consultant integration coming soon. Use /execute for now.",
    }


@router.post("/execute")
async def execute_project(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
) -> JobInfo:
    """Execute a HELIX project.

    Starts project execution in background.
    Returns job ID for tracking progress.
    """
    project_path = Path(request.project_path)

    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {request.project_path}"
        )

    phases_file = project_path / "phases.yaml"
    if not phases_file.exists():
        raise HTTPException(
            status_code=400,
            detail=f"No phases.yaml in project: {request.project_path}"
        )

    # Create job
    job = await job_manager.create_job()

    # Start execution in background
    background_tasks.add_task(
        run_project_with_streaming,
        job,
        project_path,
        request.phase_filter,
    )

    return job.to_info()


@router.get("/jobs")
async def list_jobs(limit: int = 20) -> list[JobInfo]:
    """List recent jobs."""
    return await job_manager.list_jobs(limit)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobInfo:
    """Get job status including phase information.

    ADR-030 Fix 2: This endpoint now returns full phase details.

    The phases list is populated during execution via:
    - streaming.py calls job_manager.start_phase() on phase_start events
    - streaming.py calls job_manager.add_phase_result() on completion/failure

    Each phase entry contains:
    - phase_id: Phase identifier
    - name: Human-readable phase name
    - status: Phase status (pending/running/completed/failed)
    - started_at: ISO timestamp when phase started
    - completed_at: ISO timestamp when phase completed (if done)
    - duration_seconds: Execution time in seconds
    - output_files: List of files created by the phase
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # job.to_info() includes phases list - ADR-030 Fix 2
    return job.to_info()


@router.delete("/jobs/{job_id}")
async def stop_job(job_id: str) -> dict:
    """Stop/cancel a running job.

    This marks the job as cancelled and stops emitting events.
    Note: This does not kill the underlying Claude process immediately,
    but prevents further phase execution.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        return {
            "status": "already_stopped",
            "job_id": job_id,
            "job_status": job.status.value,
        }

    # Mark as cancelled
    await job_manager.update_job(job_id, status=JobStatus.CANCELLED)

    # Emit cancellation event
    await job_manager.emit_event(job_id, PhaseEvent(
        event_type="job_cancelled",
        data={"message": "Job cancelled by user"}
    ))

    return {
        "status": "cancelled",
        "job_id": job_id,
    }
