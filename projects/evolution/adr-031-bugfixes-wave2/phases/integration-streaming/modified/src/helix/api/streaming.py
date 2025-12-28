"""SSE streaming utilities for HELIX API.

Thin wrapper around UnifiedOrchestrator - all orchestration logic lives there.
This module only handles:
- SSE event formatting
- Job management integration
- Event forwarding
- Status synchronization (ADR-031)

See: ADR-022 for architectural decision.
See: ADR-031 for status synchronization integration.
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
            """Forward orchestrator events to job manager.

            ADR-030 Fix 2: Sync phase status to JobState.
            - Records phase start with RUNNING status
            - Updates phase with completion status and duration
            """
            # Map orchestrator event types to API event types
            event_type = event.event_type

            # Update job state based on event - ADR-030 Fix 2
            if event_type == "phase_start":
                await job_manager.update_job(job.job_id, current_phase=event.phase_id)
                # Record phase start with RUNNING status
                await job_manager.start_phase(
                    job.job_id,
                    event.phase_id,
                    phase_name=event.data.get("name"),
                )

            # Convert to API PhaseEvent and emit
            api_event = PhaseEvent(
                event_type=event_type,
                phase_id=event.phase_id or None,
                data=event.data,
                timestamp=event.timestamp,
            )
            await job_manager.emit_event(job.job_id, api_event)

            # Record phase results - updates existing phase entry
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


# ============================================================================
# Evolution Pipeline - ADR-030 / ADR-031
# ============================================================================

from helix.evolution import (
    Deployer,
    Validator,
    Integrator,
    EvolutionStatus,
)
from helix.evolution.project import EvolutionProject
from helix.evolution.status_sync import StatusSynchronizer


async def run_evolution_pipeline(
    job: Job,
    project: EvolutionProject,
    auto_integrate: bool = False,
    force: bool = False,
) -> None:
    """Run complete evolution pipeline with streaming events.

    Pipeline steps:
    1. Pre-checks (force, concurrent execution)
    2. Execute all project phases (via UnifiedOrchestrator)
    3. Deploy to test system (via Deployer)
    4. Validate in test system (via Validator)
    5. Integrate to production (via Integrator) - if auto_integrate=True

    ADR-031 Integration:
    This function now uses StatusSynchronizer to keep status.json in sync
    with in-memory JobState. All phase state changes are immediately
    persisted to disk for crash recovery.

    Args:
        job: Job instance for tracking
        project: EvolutionProject to execute
        auto_integrate: Whether to automatically integrate on successful validation
        force: Whether to force re-run on already integrated projects
    """
    print(f"[EVOLUTION] Starting pipeline for {project.name}")

    # ADR-031: Initialize StatusSynchronizer for unified status tracking
    status_sync = StatusSynchronizer(project.path)

    try:
        # Pre-check: Already integrated?
        current_status = project.get_status()
        if not force and current_status == EvolutionStatus.INTEGRATED:
            await _emit_pipeline_failed(job.job_id, "pre-check",
                "Project already integrated. Use force=true to re-run.")
            return

        # Pre-check: Already running?
        if current_status in [EvolutionStatus.DEVELOPING, EvolutionStatus.VALIDATING]:
            await _emit_pipeline_failed(job.job_id, "pre-check",
                f"Pipeline already running (status: {current_status.value})")
            return

        # Mark as developing
        project.set_status(EvolutionStatus.DEVELOPING)

        await job_manager.update_job(job.job_id, status=JobStatus.RUNNING)

        # Emit pipeline start event
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_started",
            data={
                "project": project.name,
                "auto_integrate": auto_integrate,
            }
        ))

        # Step 1: Execute project phases
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "execute", "description": "Executing project phases"}
        ))

        orchestrator = UnifiedOrchestrator()

        async def on_phase_event(event: OrchestratorEvent) -> None:
            """Forward orchestrator events and sync status to disk.

            ADR-030 Fix 2: Sync phase status to JobState.
            ADR-031 Fix 1: Sync phase status to status.json via StatusSynchronizer.
            """
            event_type = event.event_type

            # Record phase start with RUNNING status
            if event_type == "phase_start":
                await job_manager.update_job(job.job_id, current_phase=event.phase_id)
                await job_manager.start_phase(
                    job.job_id,
                    event.phase_id,
                    phase_name=event.data.get("name"),
                )
                # ADR-031: Sync to status.json
                status_sync.start_phase(event.phase_id)

            # Record phase completion
            elif event_type == "phase_complete":
                await job_manager.add_phase_result(
                    job.job_id,
                    event.phase_id,
                    PhaseStatus.COMPLETED,
                    duration=event.data.get("duration", 0),
                )
                # ADR-031: Sync to status.json
                status_sync.complete_phase(event.phase_id)

            elif event_type == "phase_failed":
                await job_manager.add_phase_result(
                    job.job_id,
                    event.phase_id,
                    PhaseStatus.FAILED,
                    duration=event.data.get("duration", 0),
                )
                # ADR-031: Sync to status.json
                error_msg = event.data.get("error", "Unknown error")
                status_sync.fail_phase(event.phase_id, error_msg)

            api_event = PhaseEvent(
                event_type=event_type,
                phase_id=event.phase_id or None,
                data=event.data,
                timestamp=event.timestamp,
            )
            await job_manager.emit_event(job.job_id, api_event)

        result = await orchestrator.run_project(
            project_path=project.path,
            on_event=on_phase_event,
        )

        if not result.success:
            project.set_status(EvolutionStatus.FAILED)
            error_msg = "; ".join(result.errors) if result.errors else "Phase execution failed"
            await _emit_pipeline_failed(job.job_id, "execute", error_msg)
            return

        # ADR-031: Mark as ready in status.json
        status_sync.mark_ready()
        project.set_status(EvolutionStatus.READY)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "execute", "phases_completed": result.phases_completed}
        ))

        # Step 2: Deploy to test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "deploy", "description": "Deploying to test system"}
        ))

        deployer = Deployer()
        deploy_result = await deployer.full_deploy(project)

        if not deploy_result.success:
            project.set_status(EvolutionStatus.FAILED)
            await _emit_pipeline_failed(job.job_id, "deploy", deploy_result.error or deploy_result.message)
            return

        project.set_status(EvolutionStatus.DEPLOYED)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "deploy", "files_copied": deploy_result.files_copied}
        ))

        # Step 3: Validate in test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "validate", "description": "Running validation suite"}
        ))

        project.set_status(EvolutionStatus.VALIDATING)
        validator = Validator()
        validation_result = await validator.full_validation()

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="validation_result",
            data={
                "success": validation_result.success,
                "passed": validation_result.passed,
                "failed": validation_result.failed,
                "errors": validation_result.errors[:5] if validation_result.errors else [],
            }
        ))

        if not validation_result.success:
            # Rollback test system
            await deployer.rollback()
            project.set_status(EvolutionStatus.FAILED)
            error_summary = "; ".join(validation_result.errors[:3]) if validation_result.errors else "Validation failed"
            await _emit_pipeline_failed(job.job_id, "validate", error_summary)
            return

        project.set_status(EvolutionStatus.DEPLOYED)  # Back to deployed after validation
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "validate", "passed": validation_result.passed}
        ))

        # Step 4: Integrate to production (if auto_integrate)
        if auto_integrate:
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_started",
                data={"step": "integrate", "description": "Integrating to production"}
            ))

            integrator = Integrator()
            integration_result = await integrator.full_integration(project)

            if not integration_result.success:
                project.set_status(EvolutionStatus.FAILED)
                await _emit_pipeline_failed(job.job_id, "integrate",
                    integration_result.error or integration_result.message)
                return

            # ADR-031: Mark as integrated in status.json
            status_sync.mark_integrated()
            project.set_status(EvolutionStatus.INTEGRATED)
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_completed",
                data={
                    "step": "integrate",
                    "files_integrated": integration_result.files_integrated,
                    "backup_tag": integration_result.backup_tag,
                }
            ))

        # Pipeline complete
        await job_manager.update_job(job.job_id, status=JobStatus.COMPLETED)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_completed",
            data={
                "project": project.name,
                "integrated": auto_integrate,
            }
        ))
        print(f"[EVOLUTION] Pipeline completed for {project.name}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[EVOLUTION] Pipeline error: {error_msg}")
        try:
            project.set_status(EvolutionStatus.FAILED)
        except:
            pass
        await job_manager.update_job(
            job.job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_failed",
            data={"error": str(e)}
        ))


async def _emit_pipeline_failed(job_id: str, step: str, error: str) -> None:
    """Emit pipeline failure event and update job status."""
    print(f"[EVOLUTION] Pipeline failed at {step}: {error}")
    await job_manager.update_job(
        job_id,
        status=JobStatus.FAILED,
        error=f"Failed at {step}: {error}"
    )
    await job_manager.emit_event(job_id, PhaseEvent(
        event_type="pipeline_failed",
        data={"step": step, "error": error}
    ))
