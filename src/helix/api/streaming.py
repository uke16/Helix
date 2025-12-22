"""SSE streaming utilities for HELIX API."""

import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from helix.claude_runner import ClaudeRunner
from helix.phase_loader import PhaseLoader
import yaml
from helix.template_engine import TemplateEngine
from .models import PhaseEvent, JobStatus, PhaseStatus
from .job_manager import job_manager, Job


def format_sse(event_type: str, data: dict) -> str:
    """Format data as SSE event."""
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def run_project_with_streaming(
    job: Job,
    project_path: Path,
    phase_filter: list[str] | None = None,
) -> None:
    """Run a HELIX project with streaming events."""
    print(f"[STREAMING] Starting job {job.job_id} for {project_path}")
    
    try:
        await job_manager.update_job(job.job_id, status=JobStatus.RUNNING)
        
        # Emit start event
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="job_started",
            data={"project": str(project_path)}
        ))
        
        # Load phases
        print(f"[STREAMING] Loading phases from {project_path}")
        loader = PhaseLoader()
        phases = loader.load_phases(project_path)
        print(f"[STREAMING] Loaded {len(phases)} phases")
        
        if phase_filter:
            phases = [p for p in phases if p.id in phase_filter]
        
        # Set NVM path for Claude CLI
        nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
        os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"
        print(f"[STREAMING] PATH updated with NVM")
        
        # Create runner with explicit path
        runner = ClaudeRunner(
            claude_cmd="/home/aiuser01/helix-v4/control/claude-wrapper.sh",
            use_stdbuf=True
        )
        print(f"[STREAMING] ClaudeRunner created")
        
        # Check availability
        available = await runner.check_availability()
        print(f"[STREAMING] Claude available: {available}")
        
        if not available:
            raise RuntimeError("Claude CLI not available")
        
        # Run each phase
        for phase in phases:
            phase_dir = project_path / "phases" / phase.id
            phase_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate CLAUDE.md if not exists
            claude_md = phase_dir / "CLAUDE.md"
            if not claude_md.exists():
                print(f"[STREAMING] Generating CLAUDE.md for phase {phase.id}")
                try:
                    template_engine = TemplateEngine()
                    spec_path = project_path / "spec.yaml"
                    spec = {}
                    if spec_path.exists():
                        with open(spec_path) as spec_file:
                            spec = yaml.safe_load(spec_file) or {}
                    
                    context = {
                        "phase_id": phase.id,
                        "phase_name": phase.name,
                        "phase_type": phase.type,
                        "phase_description": getattr(phase, 'description', '') or "",
                        "project_path": str(project_path),
                        **spec,
                    }
                    
                    # Map phase type to template path
                    phase_type = phase.type if phase.type else "development"
                    type_to_template = {
                        "development": "developer/python",
                        "documentation": "documentation/technical",
                        "review": "reviewer/code",
                        "consultant": "consultant/session",
                    }
                    template_name = type_to_template.get(phase_type, "developer/python")
                    
                    # Check if spec has language preference
                    if spec.get("meta", {}).get("language"):
                        lang = spec["meta"]["language"]
                        if phase_type == "development":
                            template_name = f"developer/{lang}"
                    
                    claude_content = template_engine.render_claude_md(template_name, context)
                    claude_md.write_text(claude_content, encoding="utf-8")
                    print(f"[STREAMING] CLAUDE.md generated for {phase.id}")
                except Exception as e:
                    print(f"[STREAMING] Warning: Could not generate CLAUDE.md: {e}")
            
            print(f"[STREAMING] Running phase {phase.id} in {phase_dir}")
            
            await job_manager.update_job(job.job_id, current_phase=phase.id)
            
            # Emit phase start
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="phase_start",
                phase_id=phase.id,
                data={"name": phase.name, "type": phase.type}
            ))
            
            # Output callback
            async def on_output(stream: str, line: str) -> None:
                print(f"[{phase.id}][{stream}] {line}")
                await job_manager.emit_event(job.job_id, PhaseEvent(
                    event_type="output",
                    phase_id=phase.id,
                    data={"stream": stream, "text": line}
                ))
            
            # Run phase with streaming
            print(f"[STREAMING] Starting run_phase_streaming for {phase.id}")
            result = await runner.run_phase_streaming(
                phase_dir=phase_dir,
                on_output=on_output,
                timeout=600,
            )
            print(f"[STREAMING] Phase {phase.id} completed: success={result.success}")
            
            # Record result
            status = PhaseStatus.COMPLETED if result.success else PhaseStatus.FAILED
            await job_manager.add_phase_result(
                job.job_id,
                phase.id,
                status,
                result.duration_seconds,
            )
            
            # Emit phase end
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="phase_end",
                phase_id=phase.id,
                data={
                    "success": result.success,
                    "duration": result.duration_seconds,
                    "exit_code": result.exit_code,
                }
            ))
            
            if not result.success:
                print(f"[STREAMING] Phase failed: {result.stderr[:200]}")
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    error=result.stderr[:500]
                )
                await job_manager.emit_event(job.job_id, PhaseEvent(
                    event_type="job_failed",
                    data={"error": result.stderr[:500]}
                ))
                return
        
        # All phases completed
        print(f"[STREAMING] All phases completed!")
        await job_manager.update_job(job.job_id, status=JobStatus.COMPLETED)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="job_completed",
            data={"phases_completed": len(phases)}
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
    """Generate SSE stream for a job."""
    async for event in job_manager.stream_events(job_id):
        yield format_sse(event.event_type, {
            "phase_id": event.phase_id,
            **event.data,
            "timestamp": event.timestamp.isoformat(),
        })
