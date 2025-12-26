"""CLI API Client - calls HELIX API for project execution.

This module provides async HTTP functions to interact with the HELIX API.
All orchestration logic lives in the API; the CLI is just a thin client.

See: ADR-022 for architectural decision.
"""

import asyncio
import json
import sys
from typing import AsyncGenerator, Optional

import httpx

# Default API base URL
API_BASE = "http://localhost:8001"


class APIError(Exception):
    """API request failed."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


async def check_api_health(base_url: str = API_BASE) -> bool:
    """Check if the API is running and healthy.

    Args:
        base_url: API base URL

    Returns:
        True if API is healthy, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{base_url}/")
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def start_job(
    project_path: str,
    base_url: str = API_BASE,
) -> str:
    """Start a project execution job.

    Args:
        project_path: Path to the project directory
        base_url: API base URL

    Returns:
        job_id string

    Raises:
        APIError: If API request fails
    """
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            f"{base_url}/helix/execute",
            json={"project_path": project_path},
        )

        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            raise APIError(response.status_code, detail)

        job = response.json()
        return job["job_id"]


async def run_project(
    project_path: str,
    background: bool = False,
    base_url: str = API_BASE,
) -> AsyncGenerator[dict, None]:
    """Run a project via the API and stream events.

    Args:
        project_path: Path to the project directory
        background: If True, just start the job (for background use start_job directly)
        base_url: API base URL

    Yields:
        SSE events as dicts

    Raises:
        APIError: If API request fails
    """
    job_id = await start_job(project_path, base_url)

    if background:
        # Yield a single event with the job_id for background mode
        yield {"event_type": "job_queued", "data": {"job_id": job_id}}
        return

    # Stream events
    async for event in stream_job_events(job_id, base_url):
        yield event


async def stream_job_events(
    job_id: str,
    base_url: str = API_BASE,
) -> AsyncGenerator[dict, None]:
    """Stream SSE events for a job.

    Args:
        job_id: Job ID to stream events for
        base_url: API base URL

    Yields:
        Event dictionaries with event_type and data
    """
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET",
            f"{base_url}/helix/stream/{job_id}",
        ) as response:
            if response.status_code != 200:
                raise APIError(response.status_code, "Failed to connect to stream")

            event_type = None
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = {"raw": data_str}

                    yield {
                        "event_type": event_type or "message",
                        "data": data,
                    }

                    # Check for terminal events
                    if event_type in ("job_completed", "job_failed", "job_cancelled"):
                        return


async def list_jobs(
    limit: int = 20,
    base_url: str = API_BASE,
) -> list[dict]:
    """List recent jobs.

    Args:
        limit: Maximum number of jobs to return
        base_url: API base URL

    Returns:
        List of job info dictionaries
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/helix/jobs",
            params={"limit": limit},
        )

        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            raise APIError(response.status_code, detail)

        return response.json()


async def get_job(
    job_id: str,
    base_url: str = API_BASE,
) -> dict:
    """Get job status.

    Args:
        job_id: Job ID to get status for
        base_url: API base URL

    Returns:
        Job info dictionary
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/helix/jobs/{job_id}")

        if response.status_code == 404:
            raise APIError(404, f"Job not found: {job_id}")
        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            raise APIError(response.status_code, detail)

        return response.json()


async def get_logs(
    job_id: str,
    base_url: str = API_BASE,
) -> list[dict]:
    """Get logs for a job (non-streaming).

    Args:
        job_id: Job ID to get logs for
        base_url: API base URL

    Returns:
        List of log entries from job history
    """
    job = await get_job(job_id, base_url)
    return job.get("events", [])


async def stop_job(
    job_id: str,
    base_url: str = API_BASE,
) -> dict:
    """Stop a running job.

    Args:
        job_id: Job ID to stop
        base_url: API base URL

    Returns:
        Status response dictionary
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{base_url}/helix/jobs/{job_id}")

        if response.status_code == 404:
            raise APIError(404, f"Job not found: {job_id}")
        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            raise APIError(response.status_code, detail)

        return response.json()


def print_event(event: dict) -> None:
    """Print an SSE event to stdout with formatting.

    Args:
        event: Event dictionary with event_type and data
    """
    event_type = event.get("event_type", "unknown")
    data = event.get("data", {})

    # Color codes
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"
    DIM = "\033[2m"

    if event_type == "job_started":
        print(f"{BLUE}-> Starting project: {data.get('project', 'unknown')}{RESET}")

    elif event_type == "phase_start":
        phase_id = event.get("phase_id") or data.get("phase_id", "?")
        print(f"\n{BLUE}-> Phase: {phase_id}{RESET}")

    elif event_type == "phase_output":
        output = data.get("output", "")
        if output:
            for line in output.splitlines():
                print(f"   {DIM}{line}{RESET}")

    elif event_type == "phase_complete":
        phase_id = event.get("phase_id") or data.get("phase_id", "?")
        duration = data.get("duration", 0)
        print(f"{GREEN}   ✓ Phase {phase_id} completed ({duration:.1f}s){RESET}")

    elif event_type == "phase_failed":
        phase_id = event.get("phase_id") or data.get("phase_id", "?")
        error = data.get("error", "Unknown error")
        print(f"{RED}   ✗ Phase {phase_id} failed: {error}{RESET}")

    elif event_type == "job_completed":
        phases = data.get("phases_completed", 0)
        total = data.get("phases_total", 0)
        print(f"\n{GREEN}✓ Project completed ({phases}/{total} phases){RESET}")

    elif event_type == "job_failed":
        error = data.get("error", "Unknown error")
        print(f"\n{RED}✗ Project failed: {error}{RESET}")

    elif event_type == "job_cancelled":
        print(f"\n{YELLOW}⚠ Job cancelled{RESET}")

    else:
        # Generic event
        print(f"{DIM}[{event_type}] {json.dumps(data)}{RESET}")
