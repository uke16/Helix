"""Phase Orchestrator Runner for HELIX v4.

Manages the automatic execution of project phases including:
- Phase execution via Claude Code CLI
- Quality gate checking
- Data flow between phases
- Status tracking with resume capability
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

import yaml

from .status import StatusTracker, ProjectStatus, PhaseStatus
from .phase_executor import PhaseExecutor, PhaseResult
from .data_flow import DataFlowManager

# Conditional imports - these may not exist yet in the main helix package
try:
    from ..phase_loader import PhaseConfig, PhaseLoader
    from ..quality_gates import QualityGateRunner, GateResult
except ImportError:
    # Fallback for standalone testing
    PhaseConfig = Any  # type: ignore
    PhaseLoader = Any  # type: ignore
    QualityGateRunner = Any  # type: ignore
    GateResult = Any  # type: ignore


# Type alias for progress callback
ProgressCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


@dataclass
class RunConfig:
    """Configuration for an orchestrator run.

    Attributes:
        project_dir: Path to the project directory.
        resume: Whether to resume from last completed phase.
        dry_run: If True, don't actually run Claude CLI.
        timeout_per_phase: Maximum time per phase in seconds.
        max_retries: Maximum retry attempts per phase.
        parallel: Whether to run independent phases in parallel (future).
    """

    project_dir: Path
    resume: bool = False
    dry_run: bool = False
    timeout_per_phase: int = 600  # 10 minutes
    max_retries: int = 3
    parallel: bool = False


class OrchestratorRunner:
    """Runs projects automatically with phase orchestration.

    The OrchestratorRunner extends the base Orchestrator concept with:
    - Automatic data flow between phases (output -> input)
    - Persistent status tracking for resume capability
    - CLI integration for project management
    - Configurable timeouts and retry logic

    Example:
        runner = OrchestratorRunner()
        config = RunConfig(project_dir=Path("projects/external/my-feature"))
        result = await runner.run("my-feature", config)

        if result.status == "completed":
            print(f"Project completed! ({result.completed_phases}/{result.total_phases} phases)")
        else:
            print(f"Project failed: {result.error}")
    """

    def __init__(
        self,
        phase_loader: Any | None = None,
        phase_executor: PhaseExecutor | None = None,
        data_flow: DataFlowManager | None = None,
        status_tracker: StatusTracker | None = None,
        gate_runner: Any | None = None,
    ) -> None:
        """Initialize the OrchestratorRunner.

        Args:
            phase_loader: Phase configuration loader.
            phase_executor: Executor for running individual phases.
            data_flow: Manager for data flow between phases.
            status_tracker: Status tracker for persistence.
            gate_runner: Quality gate runner.
        """
        self.phase_loader = phase_loader
        self.executor = phase_executor or PhaseExecutor()
        self.data_flow = data_flow or DataFlowManager()
        self.status_tracker = status_tracker or StatusTracker()
        self.gate_runner = gate_runner

        # Lazy initialize phase_loader if not provided
        if self.phase_loader is None:
            try:
                from ..phase_loader import PhaseLoader
                self.phase_loader = PhaseLoader()
            except ImportError:
                pass

        # Lazy initialize gate_runner if not provided
        if self.gate_runner is None:
            try:
                from ..quality_gates import QualityGateRunner
                self.gate_runner = QualityGateRunner()
            except ImportError:
                pass

    async def run(
        self,
        project_name: str,
        config: RunConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ProjectStatus:
        """Run a project to completion.

        Executes all phases in sequence, handling data flow between phases,
        quality gate checks, and retry logic.

        Args:
            project_name: Name of the project to run.
            config: Optional run configuration.
            on_progress: Optional callback for progress updates.

        Returns:
            ProjectStatus with final execution state.
        """
        # Determine project directory
        if config is None:
            project_dir = Path(f"projects/external/{project_name}")
            config = RunConfig(project_dir=project_dir)
        else:
            project_dir = config.project_dir

        # Load or create status
        status = self.status_tracker.load_or_create(project_dir)
        status.project_dir = project_dir

        # Check if already completed (and not resuming)
        if not config.resume and status.status == "completed":
            return status

        # Load phases
        phases = self._load_phases(project_dir)
        if not phases:
            status.status = "failed"
            status.error = "No phases found in phases.yaml"
            self.status_tracker.save(status)
            return status

        # Initialize status
        status.status = "running"
        status.total_phases = len(phases)
        if status.started_at is None:
            status.started_at = datetime.now()
        self.status_tracker.save(status)

        # Create phase queue
        phase_queue: deque[Any] = deque(phases)

        # Notify progress
        if on_progress:
            await on_progress(
                "project_started",
                f"Starting project '{project_name}' with {len(phases)} phases",
                {"project_id": project_name, "total_phases": len(phases)},
            )

        # Main execution loop
        while phase_queue:
            phase = phase_queue.popleft()

            # Skip completed phases on resume
            if config.resume and status.is_phase_complete(phase.id):
                if on_progress:
                    await on_progress(
                        "phase_skipped",
                        f"Skipping completed phase: {phase.id}",
                        {"phase_id": phase.id},
                    )
                continue

            # Mark phase as started
            status.mark_phase_started(phase.id)
            self.status_tracker.save(status)

            if on_progress:
                await on_progress(
                    "phase_started",
                    f"Starting phase: {phase.id}",
                    {"phase_id": phase.id, "phase_type": phase.type},
                )

            # Prepare inputs from previous phases
            await self.data_flow.prepare_phase_inputs(project_dir, phase, status)

            # Get phase directory
            phase_dir = self._get_phase_dir(project_dir, phase)

            # Execute phase
            result = await self.executor.execute(
                phase_dir=phase_dir,
                phase_config=phase,
                timeout=config.timeout_per_phase,
                dry_run=config.dry_run,
            )

            # Check quality gates if configured
            if result.success and phase.quality_gate and self.gate_runner:
                gate_result = await self._check_gates(phase_dir, phase.quality_gate)
                result.gate_result = gate_result

                if not gate_result.passed:
                    result.success = False
                    result.error = gate_result.message

            # Handle result
            if result.success:
                status.mark_phase_completed(phase.id)
                self.status_tracker.save(status)

                if on_progress:
                    await on_progress(
                        "phase_completed",
                        f"Phase completed: {phase.id}",
                        {"phase_id": phase.id, "duration": result.duration_seconds},
                    )

                # Handle decompose phases (planning phases that generate new phases)
                if hasattr(phase, "config") and phase.config.get("decompose"):
                    plan_path = phase_dir / "output" / "plan.yaml"
                    if plan_path.exists():
                        new_phases = self._parse_plan(plan_path)
                        for new_phase in reversed(new_phases):
                            phase_queue.appendleft(new_phase)
                        status.total_phases += len(new_phases)
                        self.status_tracker.save(status)

            else:
                # Phase failed - check for retry
                retries = status.increment_phase_retries(phase.id)

                if retries < config.max_retries:
                    # Retry the phase
                    phase_queue.appendleft(phase)
                    self.status_tracker.save(status)

                    if on_progress:
                        await on_progress(
                            "phase_retry",
                            f"Retrying phase: {phase.id} (attempt {retries + 1}/{config.max_retries})",
                            {"phase_id": phase.id, "retry": retries, "error": result.error},
                        )
                    continue

                # Max retries exceeded - fail
                status.mark_phase_failed(phase.id, result.error)
                status.status = "failed"
                status.error = f"Phase '{phase.id}' failed after {config.max_retries} retries: {result.error}"
                status.completed_at = datetime.now()
                self.status_tracker.save(status)

                if on_progress:
                    await on_progress(
                        "project_failed",
                        f"Project failed at phase: {phase.id}",
                        {"phase_id": phase.id, "error": result.error},
                    )

                return status

        # All phases completed
        status.status = "completed"
        status.completed_at = datetime.now()
        self.status_tracker.save(status)

        if on_progress:
            await on_progress(
                "project_completed",
                f"Project completed! ({status.completed_phases}/{status.total_phases} phases)",
                {
                    "completed_phases": status.completed_phases,
                    "total_phases": status.total_phases,
                },
            )

        return status

    def _load_phases(self, project_dir: Path) -> list[Any]:
        """Load phases from phases.yaml.

        Args:
            project_dir: Path to the project directory.

        Returns:
            List of PhaseConfig objects.
        """
        if self.phase_loader:
            try:
                return self.phase_loader.load_phases(project_dir)
            except FileNotFoundError:
                return []

        # Fallback: manual loading if PhaseLoader not available
        phases_file = project_dir / "phases.yaml"
        if not phases_file.exists():
            return []

        with open(phases_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        phases_data = data.get("phases", [])
        return [self._create_phase_config(p) for p in phases_data]

    def _create_phase_config(self, phase_data: dict[str, Any]) -> Any:
        """Create a PhaseConfig-like object from dictionary.

        Args:
            phase_data: Phase configuration dictionary.

        Returns:
            PhaseConfig or compatible object.
        """
        try:
            from ..phase_loader import PhaseConfig
            return PhaseConfig(
                id=phase_data.get("id", ""),
                name=phase_data.get("name", phase_data.get("id", "")),
                type=phase_data.get("type", "development"),
                config=phase_data.get("config", {}),
                input=phase_data.get("input", {}),
                output=phase_data.get("output", {}),
                quality_gate=phase_data.get("quality_gate", {}),
            )
        except ImportError:
            # Create a simple namespace object
            class SimplePhaseConfig:
                pass

            config = SimplePhaseConfig()
            config.id = phase_data.get("id", "")
            config.name = phase_data.get("name", phase_data.get("id", ""))
            config.type = phase_data.get("type", "development")
            config.config = phase_data.get("config", {})
            config.input = phase_data.get("input", {})
            config.output = phase_data.get("output", {})
            config.quality_gate = phase_data.get("quality_gate", {})
            # Add input_from for data flow
            config.config["input_from"] = phase_data.get("input_from", [])
            return config

    def _get_phase_dir(self, project_dir: Path, phase: Any) -> Path:
        """Get the directory for a phase.

        Args:
            project_dir: Path to the project directory.
            phase: Phase configuration.

        Returns:
            Path to the phase directory.
        """
        if self.phase_loader and hasattr(self.phase_loader, "get_phase_dir"):
            return self.phase_loader.get_phase_dir(project_dir, phase)
        return project_dir / "phases" / phase.id

    async def _check_gates(
        self, phase_dir: Path, gate_config: dict[str, Any]
    ) -> Any:
        """Check quality gates for a phase.

        Args:
            phase_dir: Path to the phase directory.
            gate_config: Gate configuration.

        Returns:
            GateResult from the check.
        """
        if self.gate_runner:
            return await self.gate_runner.run_gate(phase_dir, gate_config)

        # Fallback: create a passing result
        class PassingResult:
            passed = True
            gate_type = "none"
            message = "No gate runner configured"
            details = {}

        return PassingResult()

    def _parse_plan(self, plan_path: Path) -> list[Any]:
        """Parse a plan.yaml file into phase configs.

        Args:
            plan_path: Path to the plan.yaml file.

        Returns:
            List of PhaseConfig objects from the plan.
        """
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = yaml.safe_load(f) or {}

        phases = []
        for phase_def in plan.get("decomposed_phases", []):
            phases.append(
                self._create_phase_config({
                    "id": phase_def.get("id"),
                    "name": phase_def.get("description", phase_def.get("id")),
                    "type": phase_def.get("type", "development"),
                    "config": phase_def,
                    "quality_gate": phase_def.get("gate", {}),
                    "input_from": phase_def.get("depends_on", []),
                })
            )

        return phases

    async def get_status(self, project_name: str) -> ProjectStatus | None:
        """Get the current status of a project.

        Args:
            project_name: Name of the project.

        Returns:
            ProjectStatus or None if project doesn't exist.
        """
        project_dir = Path(f"projects/external/{project_name}")
        if not project_dir.exists():
            return None
        return self.status_tracker.load(project_dir)

    def list_projects(self, projects_base: Path | None = None) -> list[ProjectStatus]:
        """List all projects with their status.

        Args:
            projects_base: Base directory for projects.

        Returns:
            List of ProjectStatus for all projects.
        """
        if projects_base is None:
            projects_base = Path("projects/external")

        if not projects_base.exists():
            return []

        statuses = []
        for project_dir in sorted(projects_base.iterdir()):
            if project_dir.is_dir():
                status = self.status_tracker.load_or_create(project_dir)
                status.project_dir = project_dir
                statuses.append(status)

        return statuses
