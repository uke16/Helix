"""HELIX v4 CLI Commands.

This module contains all CLI commands for the HELIX system.
Commands use the HELIX API (ADR-022) instead of direct orchestrator calls.
"""

import asyncio
import functools
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click


def handle_error(func):
    """Decorator to handle errors gracefully without showing tracebacks."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            click.secho(f"✗ File not found: {e.filename}", fg="red")
            sys.exit(1)
        except json.JSONDecodeError as e:
            click.secho(f"✗ Invalid JSON: {e.msg}", fg="red")
            sys.exit(1)
        except Exception as e:
            click.secho(f"✗ Error: {str(e)}", fg="red")
            sys.exit(1)
    return wrapper


def require_api(func):
    """Decorator to check if API is running before executing command."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from .api_client import check_api_health

        if not asyncio.run(check_api_health()):
            click.secho("✗ HELIX API is not running", fg="red")
            click.secho("  Start it with: uvicorn helix.api.main:app --port 8001", fg="yellow")
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--phase", "-p", help="Start from specific phase")
@click.option("--model", "-m", default="claude-opus-4", help="LLM model to use")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--background", "-bg", is_flag=True, help="Run in background, return job ID")
@handle_error
def run(project_path: str, phase: Optional[str], model: str, dry_run: bool, background: bool) -> None:
    """Run a HELIX project workflow.

    PROJECT_PATH is the path to the project directory containing ADR and phases.yaml.
    """
    project = Path(project_path).resolve()

    click.secho(f"-> Loading project: {project.name}", fg="blue")

    if dry_run:
        click.secho("-> Dry run mode - showing planned execution", fg="yellow")
        _show_dry_run(project, phase)
        return

    # Check API is running
    from .api_client import check_api_health, run_project, print_event, APIError

    if not asyncio.run(check_api_health()):
        click.secho("✗ HELIX API is not running", fg="red")
        click.secho("  Start it with: uvicorn helix.api.main:app --port 8001", fg="yellow")
        click.secho("  Or use: ./scripts/helix run <project>", fg="yellow")
        sys.exit(1)

    click.secho(f"-> Using model: {model}", fg="blue")
    if phase:
        click.secho(f"-> Starting from phase: {phase}", fg="blue")

    async def execute():
        try:
            if background:
                # Use start_job directly for background mode
                from .api_client import start_job
                job_id = await start_job(str(project))
                click.secho(f"-> Job started: {job_id}", fg="green")
                click.echo(f"   Track with: helix logs {job_id}")
                return

            # Stream events
            async for event in run_project(str(project), background=False):
                print_event(event)
        except APIError as e:
            click.secho(f"✗ API error: {e.detail}", fg="red")
            sys.exit(1)

    try:
        asyncio.run(execute())
    except KeyboardInterrupt:
        click.secho("\n-> Workflow interrupted by user", fg="yellow")
        sys.exit(130)


def _show_dry_run(project: Path, start_phase: Optional[str]) -> None:
    """Display what would be executed in dry-run mode."""
    from helix.phase_loader import PhaseLoader

    loader = PhaseLoader()
    phases = loader.load_phases(project)

    started = start_phase is None
    click.echo()
    click.echo(f"{'Phase':<25} {'Description':<40} {'Status'}")
    click.echo("-" * 80)

    for phase in phases:
        if phase.name == start_phase:
            started = True

        status = "-> would run" if started else "  skipped"
        status_color = "green" if started else "white"
        click.echo(f"{phase.name:<25} {phase.name[:38]:<40} ", nl=False)
        click.secho(status, fg=status_color)

    click.echo()


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@handle_error
def status(project_path: str) -> None:
    """Show project status and progress.

    PROJECT_PATH is the path to the project directory.
    """
    from helix.phase_loader import PhaseLoader
    from helix.quality_gates import GateChecker

    project = Path(project_path).resolve()

    click.secho(f"-> Project: {project.name}", fg="blue")
    click.echo()

    # Load phases and check status
    loader = PhaseLoader()
    phases = loader.load_phases(project)
    gate_checker = GateChecker(project)

    # Determine current phase from state file
    state_file = project / ".helix" / "state.json"
    current_phase = None
    completed_phases = []

    if state_file.exists():
        state = json.loads(state_file.read_text())
        current_phase = state.get("current_phase")
        completed_phases = state.get("completed_phases", [])

    click.echo(f"{'Phase':<25} {'Status':<15} {'Gate'}")
    click.echo("-" * 55)

    for phase in phases:
        if phase.name in completed_phases:
            phase_status = "completed"
            status_color = "green"
            gate_status = "✓ passed"
            gate_color = "green"
        elif phase.name == current_phase:
            phase_status = "in_progress"
            status_color = "yellow"
            gate_status = "pending"
            gate_color = "white"
        else:
            phase_status = "pending"
            status_color = "white"
            gate_status = "-"
            gate_color = "white"

        click.secho(f"{phase.name:<25} ", nl=False)
        click.secho(f"{phase_status:<15} ", fg=status_color, nl=False)
        click.secho(gate_status, fg=gate_color)

    click.echo()

    # Show summary
    completed_count = len(completed_phases)
    total_count = len(phases)
    progress = (completed_count / total_count * 100) if total_count > 0 else 0

    click.echo(f"Progress: {completed_count}/{total_count} phases ({progress:.0f}%)")

    if current_phase:
        click.secho(f"Current: {current_phase}", fg="yellow")


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.argument("phase", required=False)
@click.option("--tail", "-n", default=50, help="Number of log lines")
@handle_error
def debug(project_path: str, phase: Optional[str], tail: int) -> None:
    """Show debug logs for a project or phase.

    PROJECT_PATH is the path to the project directory.
    PHASE is an optional phase name to filter logs.
    """
    from helix.observability import HelixLogger

    project = Path(project_path).resolve()
    logger = HelixLogger(project)

    if phase:
        click.secho(f"-> Logs for phase: {phase}", fg="blue")
        log_file = project / ".helix" / "logs" / f"{phase}.log"
    else:
        click.secho(f"-> Logs for project: {project.name}", fg="blue")
        log_file = project / ".helix" / "logs" / "helix.log"

    if not log_file.exists():
        click.secho(f"Warning: No logs found at: {log_file}", fg="yellow")
        return

    click.echo()

    # Read and display last N lines
    lines = log_file.read_text().splitlines()
    display_lines = lines[-tail:] if len(lines) > tail else lines

    for line in display_lines:
        # Color code based on log level
        if "ERROR" in line or "CRITICAL" in line:
            click.secho(line, fg="red")
        elif "WARNING" in line:
            click.secho(line, fg="yellow")
        elif "INFO" in line:
            click.echo(line)
        else:
            click.secho(line, fg="white", dim=True)

    click.echo()
    click.secho(f"Showing last {len(display_lines)} of {len(lines)} lines", dim=True)


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--detailed", "-d", is_flag=True, help="Show per-phase breakdown")
@handle_error
def costs(project_path: str, detailed: bool) -> None:
    """Show token usage and costs.

    PROJECT_PATH is the path to the project directory.
    """
    from helix.observability import MetricsCollector

    project = Path(project_path).resolve()
    collector = MetricsCollector(project)

    click.secho(f"-> Costs for project: {project.name}", fg="blue")
    click.echo()

    metrics = collector.get_metrics()

    if not metrics:
        click.secho("Warning: No metrics data found", fg="yellow")
        return

    total_input = metrics.get("total_input_tokens", 0)
    total_output = metrics.get("total_output_tokens", 0)
    total_cost = metrics.get("total_cost", 0.0)

    click.echo("Summary")
    click.echo("-" * 40)
    click.echo(f"Input tokens:  {total_input:>15,}")
    click.echo(f"Output tokens: {total_output:>15,}")
    click.echo(f"Total tokens:  {total_input + total_output:>15,}")
    click.echo()
    click.secho(f"Total cost:    ${total_cost:>14,.4f}", fg="green" if total_cost < 10 else "yellow")

    if detailed and "phases" in metrics:
        click.echo()
        click.echo(f"{'Phase':<25} {'Input':<12} {'Output':<12} {'Cost'}")
        click.echo("-" * 60)

        for phase_name, phase_data in metrics["phases"].items():
            input_tokens = phase_data.get("input_tokens", 0)
            output_tokens = phase_data.get("output_tokens", 0)
            cost = phase_data.get("cost", 0.0)

            click.echo(
                f"{phase_name:<25} {input_tokens:<12,} {output_tokens:<12,} ${cost:.4f}"
            )


@click.command()
@click.argument("project_name")
@click.option(
    "--type",
    "-t",
    "project_type",
    default="feature",
    type=click.Choice(["feature", "bugfix", "documentation", "research"]),
)
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@handle_error
def new(project_name: str, project_type: str, output: Optional[str]) -> None:
    """Create a new HELIX project from template.

    PROJECT_NAME is the name for the new project.
    """
    output_dir = Path(output) if output else Path.cwd()
    project_dir = output_dir / project_name

    if project_dir.exists():
        click.secho(f"✗ Directory already exists: {project_dir}", fg="red")
        sys.exit(1)

    click.secho(f"-> Creating new {project_type} project: {project_name}", fg="blue")

    # Create project structure
    project_dir.mkdir(parents=True)
    (project_dir / ".helix").mkdir()
    (project_dir / ".helix" / "logs").mkdir()

    # Create spec.yaml
    spec_content = f"""# HELIX Project Specification
# Generated: {datetime.now().isoformat()}

name: {project_name}
type: {project_type}
version: "1.0.0"

description: |
  Add your project description here.

goals:
  - Define your project goals

requirements:
  - List your requirements

constraints:
  - Any constraints or limitations
"""
    (project_dir / "spec.yaml").write_text(spec_content)

    # Create phases.yaml based on project type
    phases_content = _get_phases_template(project_type)
    (project_dir / "phases.yaml").write_text(phases_content)

    # Create initial state
    state = {
        "created_at": datetime.now().isoformat(),
        "current_phase": None,
        "completed_phases": [],
    }
    (project_dir / ".helix" / "state.json").write_text(json.dumps(state, indent=2))

    click.secho("✓ Project created successfully", fg="green")
    click.echo()
    click.echo("Project structure:")
    click.echo(f"  {project_dir}/")
    click.echo("  ├── spec.yaml")
    click.echo("  ├── phases.yaml")
    click.echo("  └── .helix/")
    click.echo("      ├── state.json")
    click.echo("      └── logs/")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Edit {project_dir}/spec.yaml to define your project")
    click.echo(f"  2. Customize {project_dir}/phases.yaml if needed")
    click.echo(f"  3. Run: helix run {project_dir}")


def _get_phases_template(project_type: str) -> str:
    """Get phases.yaml template based on project type."""
    templates = {
        "feature": """# HELIX Phases Configuration

phases:
  - name: 01-analysis
    description: Analyze requirements and existing codebase
    skills:
      - code_analysis
      - requirements_gathering

  - name: 02-design
    description: Design the feature architecture
    skills:
      - architecture
      - api_design

  - name: 03-implementation
    description: Implement the feature
    skills:
      - coding
      - testing

  - name: 04-testing
    description: Write and run tests
    skills:
      - unit_testing
      - integration_testing

  - name: 05-documentation
    description: Document the feature
    skills:
      - documentation
""",
        "bugfix": """# HELIX Phases Configuration

phases:
  - name: 01-investigation
    description: Investigate and reproduce the bug
    skills:
      - debugging
      - code_analysis

  - name: 02-root-cause
    description: Identify root cause
    skills:
      - debugging
      - code_analysis

  - name: 03-fix
    description: Implement the fix
    skills:
      - coding

  - name: 04-testing
    description: Verify fix and add regression tests
    skills:
      - unit_testing
      - integration_testing
""",
        "documentation": """# HELIX Phases Configuration

phases:
  - name: 01-analysis
    description: Analyze what needs to be documented
    skills:
      - code_analysis

  - name: 02-outline
    description: Create documentation outline
    skills:
      - documentation

  - name: 03-writing
    description: Write documentation
    skills:
      - documentation
      - technical_writing

  - name: 04-review
    description: Review and refine
    skills:
      - documentation
""",
        "research": """# HELIX Phases Configuration

phases:
  - name: 01-scope
    description: Define research scope and questions
    skills:
      - research

  - name: 02-investigation
    description: Investigate and gather information
    skills:
      - research
      - code_analysis

  - name: 03-analysis
    description: Analyze findings
    skills:
      - research
      - analysis

  - name: 04-report
    description: Create research report
    skills:
      - documentation
      - technical_writing
""",
    }
    return templates.get(project_type, templates["feature"])


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--request", "-r", help="Path to request.md file or direct request text")
@click.option("--model", "-m", default="claude-opus-4", help="LLM model for consultant")
@handle_error
def discuss(project_path: str, request: Optional[str], model: str) -> None:
    """Start a consultant meeting for a project.

    PROJECT_PATH is the path to the project directory.

    The consultant will analyze the request, consult domain experts,
    and generate ADR and phases.yaml.
    """
    from helix.consultant import ConsultantMeeting, ExpertManager
    from helix.llm_client import LLMClient

    project = Path(project_path).resolve()

    # Load request
    if request and Path(request).exists():
        user_request = Path(request).read_text()
    elif request:
        user_request = request
    else:
        request_file = project / "input" / "request.md"
        if not request_file.exists():
            click.secho("✗ No request provided. Use --request or create input/request.md", fg="red")
            sys.exit(1)
        user_request = request_file.read_text()

    click.secho(f"-> Starting consultant meeting for: {project.name}", fg="blue")
    click.secho(f"-> Using model: {model}", fg="blue")

    llm_client = LLMClient()
    expert_manager = ExpertManager()
    meeting = ConsultantMeeting(llm_client, expert_manager)

    async def run_meeting():
        result = await meeting.run(project, user_request)
        return result

    try:
        result = asyncio.run(run_meeting())

        click.secho("\n✓ Consultant meeting completed!", fg="green")
        click.secho(f"  -> Experts consulted: {', '.join(result.experts_consulted)}", fg="white")
        click.secho(f"  -> Duration: {result.duration_seconds:.1f}s", fg="white")

        if result.spec:
            click.secho(f"  -> Created: spec.yaml", fg="green")
        if result.phases:
            click.secho(f"  -> Created: phases.yaml", fg="green")
        if result.adr_path:
            click.secho(f"  -> Created: {result.adr_path.name}", fg="green")

        click.secho(f"\n-> Next step: helix run {project_path}", fg="blue")

    except Exception as e:
        click.secho(f"✗ Meeting failed: {e}", fg="red")
        sys.exit(1)


@click.command()
@click.option("--limit", "-n", default=20, help="Number of jobs to show")
@require_api
@handle_error
def jobs(limit: int) -> None:
    """List recent jobs from the API.

    Shows job ID, status, project, and timestamps.
    """
    from .api_client import list_jobs

    jobs_list = asyncio.run(list_jobs(limit=limit))

    if not jobs_list:
        click.secho("No jobs found", fg="yellow")
        return

    click.echo()
    click.echo(f"{'JOB ID':<36} {'STATUS':<12} {'PROJECT':<30} {'STARTED'}")
    click.echo("-" * 100)

    for job in jobs_list:
        job_id = job.get("job_id", "?")
        status_val = job.get("status", "unknown")
        project = job.get("project_path", "?")
        if len(project) > 28:
            project = "..." + project[-25:]
        started = job.get("started_at", "?")
        if started and started != "?":
            # Parse and format timestamp
            try:
                dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                started = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                pass

        # Color status
        status_colors = {
            "pending": "white",
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
        }
        color = status_colors.get(status_val, "white")

        click.echo(f"{job_id:<36} ", nl=False)
        click.secho(f"{status_val:<12} ", fg=color, nl=False)
        click.echo(f"{project:<30} {started}")

    click.echo()


@click.command()
@click.argument("job_id")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (stream)")
@require_api
@handle_error
def logs(job_id: str, follow: bool) -> None:
    """Show logs for a specific job.

    JOB_ID is the job identifier from 'helix jobs'.
    """
    from .api_client import get_job, stream_job_events, print_event, APIError

    async def show_logs():
        try:
            if follow:
                click.secho(f"-> Streaming logs for job: {job_id}", fg="blue")
                click.echo("   (Press Ctrl+C to stop)")
                click.echo()
                async for event in stream_job_events(job_id):
                    print_event(event)
            else:
                job = await get_job(job_id)
                click.secho(f"-> Job: {job_id}", fg="blue")
                click.echo(f"   Status: {job.get('status', 'unknown')}")
                click.echo(f"   Project: {job.get('project_path', 'unknown')}")

                phases = job.get("phases", [])
                if phases:
                    click.echo()
                    click.echo("Phases:")
                    for phase in phases:
                        phase_id = phase.get("phase_id", "?")
                        phase_status = phase.get("status", "?")
                        duration = phase.get("duration", 0)

                        status_color = "green" if phase_status == "completed" else "red" if phase_status == "failed" else "white"
                        click.echo(f"   ", nl=False)
                        click.secho(f"{phase_status:<12}", fg=status_color, nl=False)
                        click.echo(f" {phase_id} ({duration:.1f}s)")

                error = job.get("error")
                if error:
                    click.echo()
                    click.secho(f"Error: {error}", fg="red")

        except APIError as e:
            click.secho(f"✗ {e.detail}", fg="red")
            sys.exit(1)

    try:
        asyncio.run(show_logs())
    except KeyboardInterrupt:
        click.echo()


@click.command()
@click.argument("job_id")
@require_api
@handle_error
def stop(job_id: str) -> None:
    """Stop a running job.

    JOB_ID is the job identifier from 'helix jobs'.
    """
    from .api_client import stop_job, APIError

    async def do_stop():
        try:
            result = await stop_job(job_id)
            status_val = result.get("status", "unknown")

            if status_val == "cancelled":
                click.secho(f"✓ Job {job_id} cancelled", fg="green")
            elif status_val == "already_stopped":
                click.secho(f"Job {job_id} was already stopped ({result.get('job_status', '?')})", fg="yellow")
            else:
                click.echo(f"Result: {result}")
        except APIError as e:
            click.secho(f"✗ {e.detail}", fg="red")
            sys.exit(1)

    asyncio.run(do_stop())
