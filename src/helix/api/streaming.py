"""SSE streaming utilities for HELIX API.

Thin wrapper around UnifiedOrchestrator - all orchestration logic lives there.
This module only handles:
- SSE event formatting
- Job management integration
- Event forwarding

See: ADR-022 for architectural decision.
"""

import asyncio
import json
import traceback
from pathlib import Path
from typing import AsyncGenerator

from .orchestrator import UnifiedOrchestrator, PhaseEvent as OrchestratorEvent
from .models import PhaseEvent, JobStatus, PhaseStatus
from .job_manager import job_manager, Job


def format_sse(event_type: str, data: dict) -> str:
    """Format data as SSE event.

    Args:
        event_type: Event type name
        data: Event data dictionary

    Returns:
        SSE-formatted string
    """
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def run_project_with_streaming(
    job: Job,
    project_path: Path,
    phase_filter: list[str] | None = None,
) -> None:
    """Run a HELIX project with streaming events via UnifiedOrchestrator.

    This is a thin wrapper that:
    1. Creates event callback for UnifiedOrchestrator
    2. Forwards events to job_manager for SSE streaming
    3. Updates job status based on results

    Args:
        job: Job instance for tracking
        project_path: Path to project directory
        phase_filter: Optional list of phase IDs to run
    """
    print(f"[STREAMING] Starting job {job.job_id} for {project_path}")

    try:
        await job_manager.update_job(job.job_id, status=JobStatus.RUNNING)

        # Emit start event
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="job_started",
            data={"project": str(project_path)}
        ))

        # Create orchestrator
        orchestrator = UnifiedOrchestrator()

        # Event callback - forwards orchestrator events to job manager
        async def on_event(event: OrchestratorEvent) -> None:
            """Forward orchestrator events to job manager."""
            # Map orchestrator event types to API event types
            event_type = event.event_type

            # Update job state based on event
            if event_type == "phase_start":
                await job_manager.update_job(job.job_id, current_phase=event.phase_id)

            # Convert to API PhaseEvent and emit
            api_event = PhaseEvent(
                event_type=event_type,
                phase_id=event.phase_id or None,
                data=event.data,
                timestamp=event.timestamp,
            )
            await job_manager.emit_event(job.job_id, api_event)

            # Record phase results
            if event_type == "phase_complete":
                await job_manager.add_phase_result(
                    job.job_id,
                    event.phase_id,
                    PhaseStatus.COMPLETED,
                    duration=event.data.get("duration", 0),
                )
            elif event_type == "phase_failed":
                await job_manager.add_phase_result(
                    job.job_id,
                    event.phase_id,
                    PhaseStatus.FAILED,
                    duration=event.data.get("duration", 0),
                )

        # Run project via UnifiedOrchestrator
        result = await orchestrator.run_project(
            project_path=project_path,
            on_event=on_event,
            phase_filter=phase_filter,
        )

        # Update job status based on result
        if result.success:
            print(f"[STREAMING] All phases completed!")
            await job_manager.update_job(job.job_id, status=JobStatus.COMPLETED)
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="job_completed",
                data={
                    "phases_completed": result.phases_completed,
                    "phases_total": result.phases_total,
                }
            ))
        else:
            error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
            print(f"[STREAMING] Job failed: {error_msg}")
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                error=error_msg[:500]
            )
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="job_failed",
                data={"error": error_msg[:500]}
            ))

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[STREAMING] ERROR: {error_msg}")
        await job_manager.update_job(
            job.job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="job_failed",
            data={"error": str(e)}
        ))


async def generate_sse_stream(job_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for a job.

    Args:
        job_id: Job ID to stream events for

    Yields:
        SSE-formatted event strings
    """
    async for event in job_manager.stream_events(job_id):
        yield format_sse(event.event_type, {
            "phase_id": event.phase_id,
            **event.data,
            "timestamp": event.timestamp.isoformat(),
        })


async def stream_project_execution(
    project_path: Path,
    phase_filter: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream project execution as SSE events.

    Convenience function that creates a job and streams events directly.
    Useful for simple streaming without job management.

    Args:
        project_path: Path to project directory
        phase_filter: Optional list of phase IDs to run

    Yields:
        SSE-formatted event strings
    """
    orchestrator = UnifiedOrchestrator()

    async for event in orchestrator.run_project_streaming(project_path, phase_filter):
        yield format_sse(event.event_type, {
            "phase_id": event.phase_id,
            **event.data,
            "timestamp": event.timestamp.isoformat(),
        })
