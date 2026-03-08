"""Remote Control API routes for HELIX v4.

Provides REST endpoints for remote system management:
- GET  /remote-control/status       - System status overview
- GET  /remote-control/services     - Infrastructure service health
- POST /remote-control/spawn        - Spawn a Claude instance
- GET  /remote-control/instances    - List Claude instances
- GET  /remote-control/instances/{id} - Get instance details
- GET  /remote-control/instances/{id}/output - Get instance output
- DELETE /remote-control/instances/{id} - Kill an instance
- POST /remote-control/kill-all     - Kill all running instances
- POST /remote-control/cleanup      - Cleanup finished instances
- GET  /remote-control/logs         - Read log files
- POST /remote-control/command      - Run a control command
"""

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    SpawnClaudeRequest,
    ReadLogsRequest,
    ControlCommandRequest,
)
from ..remote_control import remote_control, InstanceStatus

router = APIRouter(prefix="/remote-control", tags=["Remote Control"])


@router.get("/status")
async def get_system_status() -> dict:
    """Get comprehensive system status.

    Returns API health, infrastructure services, active instances,
    and path validation results.
    """
    status = await remote_control.get_system_status()
    return status.to_dict()


@router.get("/services")
async def get_services() -> dict:
    """Get infrastructure service health checks.

    Checks TCP connectivity to PostgreSQL, Neo4j, Qdrant, and Redis.
    """
    status = await remote_control.get_system_status()
    return {
        "instance_type": status.instance_type,
        "services": [s.to_dict() for s in status.services],
        "all_healthy": all(
            s.health.value == "healthy" for s in status.services
        ),
    }


@router.post("/spawn")
async def spawn_claude(request: SpawnClaudeRequest) -> dict:
    """Spawn a new Claude CLI instance.

    Starts a Claude process in the background with the given prompt.
    Returns immediately with an instance ID for tracking.
    """
    try:
        instance = await remote_control.spawn_claude(
            prompt=request.prompt,
            working_dir=request.working_dir,
            timeout=request.timeout,
            system_prompt=request.system_prompt,
            output_format=request.output_format,
        )
        return instance.to_dict()
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.get("/instances")
async def list_instances(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all managed Claude instances."""
    status_filter = None
    if status:
        try:
            status_filter = InstanceStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {[s.value for s in InstanceStatus]}",
            )

    instances = await remote_control.list_instances(
        status_filter=status_filter,
        limit=limit,
    )
    return {
        "instances": instances,
        "count": len(instances),
    }


@router.get("/instances/{instance_id}")
async def get_instance(instance_id: str) -> dict:
    """Get details of a specific Claude instance."""
    instance = await remote_control.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance.to_dict()


@router.get("/instances/{instance_id}/output")
async def get_instance_output(instance_id: str) -> dict:
    """Get full stdout/stderr output of a Claude instance.

    Only returns output for completed/failed/killed instances.
    For running instances, stdout and stderr will be empty until completion.
    """
    output = await remote_control.get_instance_output(instance_id)
    if not output:
        raise HTTPException(status_code=404, detail="Instance not found")
    return output


@router.delete("/instances/{instance_id}")
async def kill_instance(instance_id: str) -> dict:
    """Kill a running Claude instance."""
    killed = await remote_control.kill_instance(instance_id)
    if not killed:
        instance = await remote_control.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        return {
            "killed": False,
            "instance_id": instance_id,
            "reason": f"Instance already in state: {instance.status.value}",
        }
    return {
        "killed": True,
        "instance_id": instance_id,
    }


@router.post("/kill-all")
async def kill_all_instances() -> dict:
    """Kill all running Claude instances.

    Emergency stop for all active instances.
    """
    killed = await remote_control.kill_all_instances()
    return {
        "killed_count": killed,
    }


@router.post("/cleanup")
async def cleanup_instances(
    max_age_seconds: int = Query(3600, ge=60, description="Max age of finished instances"),
) -> dict:
    """Remove finished instances older than max_age_seconds."""
    cleaned = await remote_control.cleanup_finished(max_age_seconds)
    return {
        "cleaned_count": cleaned,
    }


@router.get("/logs")
async def read_logs(
    log_type: str = Query("api", description="Log type: api, helix, helix-test"),
    lines: int = Query(100, ge=1, le=5000),
    search: str | None = Query(None, description="Filter lines containing this string"),
) -> dict:
    """Read HELIX log files.

    Returns the last N lines from the specified log file,
    optionally filtered by a search string.
    """
    return await remote_control.read_logs(
        log_type=log_type,
        lines=lines,
        search=search,
    )


@router.post("/command")
async def run_command(request: ControlCommandRequest) -> dict:
    """Run a HELIX control command.

    Only allows whitelisted commands: status, health, logs.
    """
    return await remote_control.run_control_command(request.command)
