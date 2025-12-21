"""SSE streaming routes for HELIX API."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..job_manager import job_manager
from ..streaming import generate_sse_stream

router = APIRouter(prefix="/helix", tags=["Streaming"])


@router.get("/stream/{job_id}")
async def stream_job(job_id: str):
    """Stream job progress via SSE.
    
    Connect to this endpoint to receive real-time updates:
    - phase_start: A phase is starting
    - output: Live output from Claude Code
    - file_created: A file was created
    - phase_end: A phase completed
    - job_completed: All phases done
    - job_failed: Execution failed
    - keepalive: Connection keepalive (every 30s)
    
    Example usage:
        curl -N http://localhost:8001/helix/stream/{job_id}
        
    Or in JavaScript:
        const eventSource = new EventSource('/helix/stream/{job_id}');
        eventSource.addEventListener('output', (e) => {
            console.log(JSON.parse(e.data));
        });
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StreamingResponse(
        generate_sse_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
