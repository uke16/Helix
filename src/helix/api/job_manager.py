"""Job manager for HELIX API - manages async job execution."""

import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator
from dataclasses import dataclass, field

from .models import JobStatus, PhaseStatus, JobInfo, PhaseEvent


@dataclass
class Job:
    """Internal job representation."""
    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_phase: str | None = None
    phases: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    def to_info(self) -> JobInfo:
        """Convert to API model."""
        return JobInfo(
            job_id=self.job_id,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            current_phase=self.current_phase,
            phases=self.phases,
            error=self.error,
        )


class JobManager:
    """Manages HELIX job execution and streaming.
    
    This is an in-memory implementation. For production,
    replace with PostgreSQL-backed storage.
    """
    
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
    
    async def create_job(self) -> Job:
        """Create a new job."""
        job_id = str(uuid.uuid4())[:8]
        job = Job(job_id=job_id)
        
        async with self._lock:
            self._jobs[job_id] = job
        
        return job
    
    async def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    async def update_job(
        self,
        job_id: str,
        status: JobStatus | None = None,
        current_phase: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        async with self._lock:
            if status:
                job.status = status
                if status == JobStatus.RUNNING and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    job.completed_at = datetime.utcnow()
            
            if current_phase is not None:
                job.current_phase = current_phase
            
            if error is not None:
                job.error = error
    
    async def start_phase(
        self,
        job_id: str,
        phase_id: str,
        phase_name: str | None = None,
    ) -> None:
        """Record phase start - ADR-030 Fix 2.

        Adds phase to job's phases list with RUNNING status.
        Called when a phase begins execution.
        """
        job = self._jobs.get(job_id)
        if not job:
            return

        async with self._lock:
            # Check if phase already exists (avoid duplicates)
            for phase in job.phases:
                if phase["phase_id"] == phase_id:
                    # Update existing phase to running
                    phase["status"] = PhaseStatus.RUNNING.value
                    phase["started_at"] = datetime.utcnow().isoformat()
                    return

            # Add new phase entry
            job.phases.append({
                "phase_id": phase_id,
                "name": phase_name or phase_id,
                "status": PhaseStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "duration_seconds": None,
                "output_files": [],
            })

    async def add_phase_result(
        self,
        job_id: str,
        phase_id: str,
        status: PhaseStatus,
        duration: float,
        output_files: list[str] | None = None,
    ) -> None:
        """Update phase with completion result - ADR-030 Fix 2.

        Updates existing phase entry or creates one if missing.
        Called when a phase completes or fails.
        """
        job = self._jobs.get(job_id)
        if not job:
            return

        async with self._lock:
            # Find existing phase entry
            for phase in job.phases:
                if phase["phase_id"] == phase_id:
                    phase["status"] = status.value
                    phase["duration_seconds"] = duration
                    phase["output_files"] = output_files or []
                    phase["completed_at"] = datetime.utcnow().isoformat()
                    return

            # If phase wasn't started, add it now (fallback)
            job.phases.append({
                "phase_id": phase_id,
                "name": phase_id,
                "status": status.value,
                "duration_seconds": duration,
                "output_files": output_files or [],
                "completed_at": datetime.utcnow().isoformat(),
            })
    
    async def emit_event(self, job_id: str, event: PhaseEvent) -> None:
        """Emit event to job's stream."""
        job = self._jobs.get(job_id)
        if job:
            await job.event_queue.put(event)
    
    async def stream_events(
        self, job_id: str
    ) -> AsyncGenerator[PhaseEvent, None]:
        """Stream events for a job."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        while True:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    job.event_queue.get(), 
                    timeout=30.0
                )
                yield event
                
                # Stop if job completed or failed
                if event.event_type in ("job_completed", "job_failed"):
                    break
                    
            except asyncio.TimeoutError:
                # Send keepalive
                yield PhaseEvent(
                    event_type="keepalive",
                    data={"status": job.status.value}
                )
                
                # Check if job is done
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    break
    
    async def list_jobs(self, limit: int = 20) -> list[JobInfo]:
        """List recent jobs."""
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True
        )[:limit]
        return [j.to_info() for j in jobs]


# Global instance
job_manager = JobManager()
