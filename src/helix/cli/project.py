"""Project management CLI commands for HELIX v4.

Provides commands for creating, running, and managing projects:
- helix project create <name> [--type simple|complex|exploratory]
- helix project run <name> [--resume] [--dry-run]
- helix project status <name>
- helix project list
"""

import asyncio
from pathlib import Path

import click
import yaml


@click.group()
def project():
    """Project management commands.

    Manage HELIX projects including creation, execution, and status tracking.
    """
    pass


@project.command()
@click.argument("name")
@click.option(
    "--type",
    "project_type",
    default="simple",
    type=click.Choice(["simple", "complex", "exploratory"]),
    help="Project type determines default phases.",
)
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
def create(name: str, project_type: str, base_dir: str):
    """Create a new project.

    Creates a project directory with phases.yaml and phase subdirectories
    based on the selected project type.

    Example:
        helix project create my-feature --type simple
    """
    project_dir = Path(base_dir) / name

    if project_dir.exists():
        click.echo(f"Error: Project '{name}' already exists at {project_dir}", err=True)
        raise SystemExit(1)

    # Load phase types config
    config_path = Path("config/phase-types.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        project_types = config.get("project_types", {})
        default_phases = project_types.get(project_type, {}).get(
            "default_phases", ["consultant", "development", "review"]
        )
    else:
        # Fallback defaults
        default_phases = {
            "simple": ["consultant", "development", "review", "integration"],
            "complex": ["consultant", "feasibility", "planning", "development", "review", "integration"],
            "exploratory": ["consultant", "research", "decision"],
        }.get(project_type, ["consultant", "development", "review"])

    # Create project directory
    project_dir.mkdir(parents=True)

    # Create phases.yaml
    phases_yaml = {
        "project": {
            "name": name,
            "type": project_type,
        },
        "phases": [
            {"id": phase, "type": phase}
            for phase in default_phases
        ],
    }

    phases_file = project_dir / "phases.yaml"
    with open(phases_file, "w", encoding="utf-8") as f:
        yaml.dump(phases_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Create phase directories
    for phase in default_phases:
        phase_dir = project_dir / "phases" / phase
        (phase_dir / "input").mkdir(parents=True)
        (phase_dir / "output").mkdir(parents=True)

        # Create placeholder CLAUDE.md
        claude_md = phase_dir / "CLAUDE.md"
        claude_md.write_text(f"# Phase: {phase}\n\nTODO: Add phase instructions.\n", encoding="utf-8")

    click.echo(f"Created project '{name}' with type '{project_type}'")
    click.echo(f"Phases: {', '.join(default_phases)}")
    click.echo(f"Location: {project_dir}")


@project.command()
@click.argument("name")
@click.option("--resume", is_flag=True, help="Resume from last completed phase.")
@click.option("--dry-run", is_flag=True, help="Don't execute, just show what would happen.")
@click.option(
    "--timeout",
    default=600,
    type=int,
    help="Timeout per phase in seconds (default: 600).",
)
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
def run(name: str, resume: bool, dry_run: bool, timeout: int, base_dir: str):
    """Run a project.

    Executes all phases in sequence, handling data flow between phases
    and checking quality gates.

    Example:
        helix project run my-feature
        helix project run my-feature --resume
        helix project run my-feature --dry-run
    """
    from ..orchestrator.runner import OrchestratorRunner, RunConfig

    project_dir = Path(base_dir) / name

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found at {project_dir}", err=True)
        raise SystemExit(1)

    config = RunConfig(
        project_dir=project_dir,
        resume=resume,
        dry_run=dry_run,
        timeout_per_phase=timeout,
    )

    runner = OrchestratorRunner()

    click.echo(f"Running project '{name}'...")
    if dry_run:
        click.echo("[DRY RUN MODE]")
    if resume:
        click.echo("[RESUME MODE]")

    async def progress_callback(event: str, message: str, details: dict):
        """Handle progress events."""
        if event == "phase_started":
            click.echo(f"  Starting phase: {details.get('phase_id')}")
        elif event == "phase_completed":
            duration = details.get("duration", 0)
            click.echo(f"  Completed phase: {details.get('phase_id')} ({duration:.1f}s)")
        elif event == "phase_skipped":
            click.echo(f"  Skipped phase: {details.get('phase_id')} (already completed)")
        elif event == "phase_retry":
            click.echo(f"  Retrying phase: {details.get('phase_id')} ({details.get('error', 'unknown error')})")

    result = asyncio.run(runner.run(name, config, on_progress=progress_callback))

    if result.status == "completed":
        click.echo(f"Project completed! ({result.completed_phases}/{result.total_phases} phases)")
    elif result.status == "failed":
        click.echo(f"Project failed: {result.error}", err=True)
        raise SystemExit(1)
    else:
        click.echo(f"Project status: {result.status}")


@project.command()
@click.argument("name")
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
def status(name: str, base_dir: str):
    """Show project status.

    Displays the current status of a project including phase completion.

    Example:
        helix project status my-feature
    """
    from ..orchestrator.status import StatusTracker

    project_dir = Path(base_dir) / name

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found at {project_dir}", err=True)
        raise SystemExit(1)

    tracker = StatusTracker()
    project_status = tracker.load_or_create(project_dir)

    click.echo(f"Project: {name}")
    click.echo(f"Status: {project_status.status}")
    click.echo(f"Progress: {project_status.completed_phases}/{project_status.total_phases} phases")

    if project_status.started_at:
        click.echo(f"Started: {project_status.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if project_status.completed_at:
        click.echo(f"Completed: {project_status.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if project_status.error:
        click.echo(f"Error: {project_status.error}")

    if project_status.phases:
        click.echo("\nPhases:")
        for pid, phase in project_status.phases.items():
            icon = {
                "completed": "[OK]",
                "failed": "[FAIL]",
                "running": "[...]",
                "pending": "[   ]",
            }.get(phase.status, "[?]")

            line = f"  {icon} {pid}: {phase.status}"
            if phase.retries > 0:
                line += f" (retries: {phase.retries})"
            click.echo(line)

            if phase.error:
                click.echo(f"        Error: {phase.error}")


@project.command("list")
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
def list_projects(base_dir: str):
    """List all projects.

    Shows all projects with their current status.

    Example:
        helix project list
    """
    from ..orchestrator.status import StatusTracker

    projects_dir = Path(base_dir)

    if not projects_dir.exists():
        click.echo("No projects found.")
        return

    tracker = StatusTracker()

    click.echo("Projects:")
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue

        status = tracker.load_or_create(project_dir)

        icon = {
            "completed": "[OK]",
            "failed": "[FAIL]",
            "running": "[...]",
            "pending": "[   ]",
        }.get(status.status, "[?]")

        progress = f"{status.completed_phases}/{status.total_phases}" if status.total_phases > 0 else "-"
        click.echo(f"  {icon} {project_dir.name}: {status.status} ({progress})")


@project.command()
@click.argument("name")
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
@click.option("--force", is_flag=True, help="Force reset without confirmation.")
def reset(name: str, base_dir: str, force: bool):
    """Reset project status.

    Clears the status file to allow re-running the project from scratch.

    Example:
        helix project reset my-feature
    """
    from ..orchestrator.status import StatusTracker

    project_dir = Path(base_dir) / name

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found at {project_dir}", err=True)
        raise SystemExit(1)

    if not force:
        if not click.confirm(f"Reset status for project '{name}'?"):
            click.echo("Aborted.")
            return

    tracker = StatusTracker()
    if tracker.delete(project_dir):
        click.echo(f"Status reset for project '{name}'")
    else:
        click.echo(f"No status file found for project '{name}'")


@project.command()
@click.argument("name")
@click.option(
    "--base-dir",
    default="projects/external",
    help="Base directory for projects.",
)
@click.option("--force", is_flag=True, help="Force delete without confirmation.")
def delete(name: str, base_dir: str, force: bool):
    """Delete a project.

    Removes the entire project directory.

    Example:
        helix project delete my-feature
    """
    import shutil

    project_dir = Path(base_dir) / name

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found at {project_dir}", err=True)
        raise SystemExit(1)

    if not force:
        if not click.confirm(f"Delete project '{name}' and all its contents?"):
            click.echo("Aborted.")
            return

    shutil.rmtree(project_dir)
    click.echo(f"Deleted project '{name}'")
