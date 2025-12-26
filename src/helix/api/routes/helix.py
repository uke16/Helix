"""HELIX-specific API routes.

All project execution goes through UnifiedOrchestrator (ADR-022).
This module provides REST endpoints:
- POST /helix/execute - Start project execution
- GET /helix/jobs - List all jobs
- GET /helix/jobs/{job_id} - Get job status
- DELETE /helix/jobs/{job_id} - Stop/cancel a job
- POST /helix/discuss - Start consultant discussion (TODO)

See routes/stream.py for SSE streaming endpoint.
"""

import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models import (
    DiscussRequest,
    ExecuteRequest,
    JobInfo,
    JobStatus,
)
from ..job_manager import job_manager
from ..streaming import run_project_with_streaming

router = APIRouter(prefix="/helix", tags=["HELIX"])


@router.post("/discuss")
async def start_discussion(request: DiscussRequest) -> dict:
    """Start a consultant discussion.
    
    This initiates a conversation to define a project.
    Returns immediately with a session ID.
    """
    # TODO: Integrate with ConsultantMeeting
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
async def get_job(job_id: str) -> JobInfo:
    """Get job status."""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_info()


@router.delete("/jobs/{job_id}")
async def stop_job(job_id: str) -> dict:
    """Stop/cancel a running job.

    This marks the job as cancelled and stops emitting events.
    Note: This does not kill the underlying Claude process immediately,
    but prevents further phase execution.

    Args:
        job_id: Job ID to stop

    Returns:
        Status message
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
    from ..models import PhaseEvent
    await job_manager.emit_event(job_id, PhaseEvent(
        event_type="job_cancelled",
        data={"message": "Job cancelled by user"}
    ))

    return {
        "status": "cancelled",
        "job_id": job_id,
    }
