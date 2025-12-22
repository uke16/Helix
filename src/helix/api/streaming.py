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
from helix.evolution.project import EvolutionProject, EvolutionStatus
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
                    
                    # Load ADR for project context (replaces spec.yaml)
                    adr_language = "python"
                    adr_domain = None
                    adr_files_create = []
                    adr_files_modify = []
                    
                    adr_files = list(project_path.glob("ADR-*.md"))
                    if not adr_files:
                        adr_files = list(project_path.glob("[0-9][0-9][0-9]-*.md"))
                    
                    if adr_files:
                        try:
                            from helix.adr import ADRParser
                            parser = ADRParser()
                            adr = parser.parse_file(adr_files[0])
                            adr_language = adr.metadata.language or "python"
                            adr_domain = adr.metadata.domain
                            adr_files_create = list(adr.metadata.files.create)
                            adr_files_modify = list(adr.metadata.files.modify)
                        except Exception as e:
                            print(f"[STREAMING] Warning: Could not parse ADR: {e}")
                    
                    context = {
                        "phase_id": phase.id,
                        "phase_name": phase.name,
                        "phase_type": phase.type,
                        "phase_description": getattr(phase, 'description', '') or "",
                        "phase_output": getattr(phase, 'output', []) or [],
                        "project_path": str(project_path),
                        # ADR-based context
                        "adr_language": adr_language,
                        "adr_domain": adr_domain,
                        "adr_files_create": adr_files_create,
                        "adr_files_modify": adr_files_modify,
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
                    
                    # Use language from ADR for template selection
                    if adr_language and adr_language != "python":
                        if phase_type == "development":
                            template_name = f"developer/{adr_language}"
                    
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
            
            # Run phase with streaming (with retry on verification failure)
            max_retries = 2
            retry_count = 0
            
            while retry_count <= max_retries:
                print(f"[STREAMING] Starting run_phase_streaming for {phase.id}" + 
                      (f" (retry {retry_count})" if retry_count > 0 else ""))
                
                result = await runner.run_phase_streaming(
                    phase_dir=phase_dir,
                    on_output=on_output,
                    timeout=600,
                )
                print(f"[STREAMING] Phase {phase.id} completed: success={result.success}")
                
                if not result.success:
                    # Claude failed, no point in verifying
                    break
                
                # === POST-PHASE VERIFICATION (ADR-011) ===
                from helix.evolution.verification import PhaseVerifier
                
                # Get expected files from phase config
                expected_files = getattr(phase, 'output', None)
                if expected_files:
                    verifier = PhaseVerifier(project_path)
                    verify_result = verifier.verify_phase_output(
                        phase_id=phase.id,
                        phase_dir=phase_dir,
                        expected_files=expected_files,
                    )
                    
                    if not verify_result.success:
                        # Emit verification failure event
                        await job_manager.emit_event(job.job_id, PhaseEvent(
                            event_type="verification_failed",
                            phase_id=phase.id,
                            data={
                                "missing_files": verify_result.missing_files,
                                "syntax_errors": verify_result.syntax_errors,
                                "message": verify_result.message,
                                "retry": retry_count + 1,
                                "max_retries": max_retries,
                            }
                        ))
                        
                        if retry_count < max_retries:
                            # Write error file for Claude to see
                            verifier.write_retry_file(phase_dir, verify_result, retry_count + 1)
                            print(f"[STREAMING] Verification failed, retrying ({retry_count + 1}/{max_retries})")
                            
                            # Emit retry event
                            await job_manager.emit_event(job.job_id, PhaseEvent(
                                event_type="phase_retry",
                                phase_id=phase.id,
                                data={"retry_number": retry_count + 1, "max_retries": max_retries}
                            ))
                            
                            retry_count += 1
                            continue
                        else:
                            # Max retries reached
                            print(f"[STREAMING] Verification failed after {max_retries} retries")
                            result.success = False
                            result.stderr = verify_result.message
                            break
                    else:
                        # Verification passed
                        await job_manager.emit_event(job.job_id, PhaseEvent(
                            event_type="verification_passed",
                            phase_id=phase.id,
                            data={"found_files": verify_result.found_files}
                        ))
                
                # Success - exit retry loop
                break
            # === END VERIFICATION ===
            
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


async def run_evolution_pipeline(
    job: Job,
    project: "EvolutionProject",
    auto_integrate: bool = False,
) -> None:
    """Run the complete evolution pipeline.
    
    Steps:
    1. Execute all phases
    2. Deploy to test system
    3. Validate (run tests)
    4. Integrate to production (if auto_integrate and tests pass)
    
    Args:
        job: Job for tracking progress
        project: Evolution project to run
        auto_integrate: Whether to auto-integrate on success
    """
    from helix.evolution.deployer import Deployer
    from helix.evolution.validator import Validator
    from helix.evolution.integrator import Integrator
    
    try:
        await job_manager.update_job(job.job_id, status=JobStatus.RUNNING)
        
        # Emit pipeline start
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_started",
            data={"project": project.name, "auto_integrate": auto_integrate}
        ))
        
        # Step 1: Execute pending phases only (Bug 11 fix)
        status_data = project.get_status_data()
        phases_completed = status_data.get("phases_completed", [])
        
        # Load all phase IDs from phases.yaml
        loader = PhaseLoader()
        all_phases = loader.load_phases(project.path)
        all_phase_ids = [p.id for p in all_phases]
        
        # Calculate pending phases
        pending_phases = [pid for pid in all_phase_ids if pid not in phases_completed]
        
        if not pending_phases:
            # All phases already complete - skip to deploy
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_skipped",
                data={"step": "execute", "message": "All phases already completed, skipping to deploy"}
            ))
        else:
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_started",
                data={"step": "execute", "message": f"Executing {len(pending_phases)} pending phases: {pending_phases}"}
            ))
            
            project_path = project.path
            await run_project_with_streaming(job, project_path, phase_filter=pending_phases)
        
        # Check if execution succeeded
        job_info = await job_manager.get_job(job.job_id)
        if job_info.status == JobStatus.FAILED:
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="pipeline_failed",
                data={"step": "execute", "message": "Phase execution failed"}
            ))
            return
        
        # Step 2: Deploy to test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "deploy", "message": "Deploying to test system..."}
        ))
        
        deployer = Deployer()
        deploy_result = await deployer.full_deploy(project)
        
        if not deploy_result.success:
            await job_manager.update_job(job.job_id, status=JobStatus.FAILED, error=deploy_result.error)
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="pipeline_failed",
                data={"step": "deploy", "message": deploy_result.message}
            ))
            return
        
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "deploy", "files_copied": deploy_result.files_copied}
        ))
        
        # Step 3: Validate
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "validate", "message": "Running validation..."}
        ))
        
        validator = Validator()
        validate_result = await validator.full_validation()
        
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={
                "step": "validate",
                "success": validate_result.success,
                "passed": validate_result.passed,
                "failed": validate_result.failed,
                "message": validate_result.message,
            }
        ))
        
        # Step 4: Integrate (if enabled and validation passed)
        if validate_result.success and auto_integrate:
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_started",
                data={"step": "integrate", "message": "Integrating to production..."}
            ))
            
            integrator = Integrator()
            integrate_result = await integrator.full_integration(project)
            
            if integrate_result.success:
                await job_manager.emit_event(job.job_id, PhaseEvent(
                    event_type="step_completed",
                    data={"step": "integrate", "message": "Successfully integrated"}
                ))
                project.set_status(EvolutionStatus.INTEGRATED)
            else:
                await job_manager.emit_event(job.job_id, PhaseEvent(
                    event_type="step_failed",
                    data={"step": "integrate", "message": integrate_result.message}
                ))
                project.set_status(EvolutionStatus.FAILED, error=integrate_result.error)
        
        elif not validate_result.success:
            project.set_status(EvolutionStatus.FAILED, error="Validation failed")
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="pipeline_failed",
                data={"step": "validate", "message": "Validation failed - not integrating"}
            ))
        
        else:
            # Validation passed but auto_integrate is False
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="pipeline_completed",
                data={
                    "message": "Validation passed. Call /integrate to complete.",
                    "validation": {
                        "passed": validate_result.passed,
                        "failed": validate_result.failed,
                    }
                }
            ))
        
        # Mark job as completed
        await job_manager.update_job(job.job_id, status=JobStatus.COMPLETED)
        
    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        print(f"[PIPELINE] {error_msg}")
        traceback.print_exc()
        
        await job_manager.update_job(job.job_id, status=JobStatus.FAILED, error=error_msg)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_error",
            data={"error": error_msg}
        ))
