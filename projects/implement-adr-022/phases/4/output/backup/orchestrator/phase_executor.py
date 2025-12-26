"""Phase Executor for HELIX v4.

Executes individual phases using Claude Code CLI with timeout handling,
retry logic, and quality gate integration.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

# Conditional imports
try:
    from ..claude_runner import ClaudeRunner, ClaudeResult
    from ..quality_gates import GateResult
except ImportError:
    ClaudeRunner = None  # type: ignore
    ClaudeResult = None  # type: ignore
    GateResult = None  # type: ignore


# Type alias for output callback
OutputCallback = Callable[[str, str], Awaitable[None]]


@dataclass
class PhaseResult:
    """Result of executing a single phase.

    Attributes:
        phase_id: ID of the phase that was executed.
        success: Whether the phase completed successfully.
        started_at: When the phase started.
        completed_at: When the phase completed.
        duration_seconds: Execution duration in seconds.
        claude_result: Result from Claude Code execution.
        gate_result: Result from quality gate check.
        error: Error message if phase failed.
        has_plan: Whether the phase produced a plan.yaml.
        plan_path: Path to the plan.yaml if generated.
        retries: Number of retry attempts.
    """

    phase_id: str
    success: bool
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    claude_result: Any | None = None
    gate_result: Any | None = None
    error: str | None = None
    has_plan: bool = False
    plan_path: Path | None = None
    retries: int = 0


class PhaseExecutor:
    """Executes individual phases via Claude Code CLI.

    The PhaseExecutor handles:
    - Claude Code CLI invocation with proper environment
    - Timeout handling
    - Output collection
    - Plan detection for decompose phases

    Example:
        executor = PhaseExecutor()
        result = await executor.execute(
            phase_dir=Path("phases/01-consultant"),
            phase_config=config,
            timeout=600,
        )
        if result.success:
            print(f"Phase completed in {result.duration_seconds}s")
    """

    DEFAULT_TIMEOUT = 600  # 10 minutes

    def __init__(
        self,
        claude_runner: Any | None = None,
    ) -> None:
        """Initialize the PhaseExecutor.

        Args:
            claude_runner: Claude Code CLI runner instance.
        """
        self.claude_runner = claude_runner

        # Lazy initialize claude_runner if not provided
        if self.claude_runner is None:
            try:
                from ..claude_runner import ClaudeRunner
                self.claude_runner = ClaudeRunner()
            except ImportError:
                pass

    async def execute(
        self,
        phase_dir: Path,
        phase_config: Any,
        timeout: int | None = None,
        dry_run: bool = False,
        on_output: OutputCallback | None = None,
    ) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase_dir: Directory for phase execution.
            phase_config: Phase configuration object.
            timeout: Maximum execution time in seconds.
            dry_run: If True, don't actually run Claude CLI.
            on_output: Optional callback for live output streaming.

        Returns:
            PhaseResult with execution details.
        """
        import time

        start_time = time.time()
        started_at = datetime.now()
        timeout = timeout or self.DEFAULT_TIMEOUT

        result = PhaseResult(
            phase_id=phase_config.id,
            success=False,
            started_at=started_at,
        )

        # Ensure phase directory exists
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / "input").mkdir(exist_ok=True)
        (phase_dir / "output").mkdir(exist_ok=True)

        if dry_run:
            # Simulate execution
            await asyncio.sleep(0.1)
            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time
            result.claude_result = self._create_dry_run_result()
            return result

        if self.claude_runner is None:
            result.error = "Claude runner not available"
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time
            return result

        try:
            # Get model from phase config if specified
            model = None
            if hasattr(phase_config, "config") and phase_config.config:
                model = phase_config.config.get("model")

            # Run Claude Code CLI
            if on_output:
                claude_result = await asyncio.wait_for(
                    self.claude_runner.run_phase_streaming(
                        phase_dir,
                        on_output=on_output,
                        model=model,
                    ),
                    timeout=timeout,
                )
            else:
                claude_result = await asyncio.wait_for(
                    self.claude_runner.run_phase(
                        phase_dir,
                        model=model,
                    ),
                    timeout=timeout,
                )

            result.claude_result = claude_result

            if not claude_result.success:
                result.error = (
                    claude_result.stderr
                    if hasattr(claude_result, "stderr")
                    else "Claude execution failed"
                )
                result.completed_at = datetime.now()
                result.duration_seconds = time.time() - start_time
                return result

            # Check for plan output (decompose phases)
            plan_path = phase_dir / "output" / "plan.yaml"
            if plan_path.exists():
                result.has_plan = True
                result.plan_path = plan_path

            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time

        except asyncio.TimeoutError:
            result.error = f"Phase timed out after {timeout} seconds"
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time

        except Exception as e:
            result.error = str(e)
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time

        return result

    def _create_dry_run_result(self) -> Any:
        """Create a simulated result for dry run mode."""
        try:
            from ..claude_runner import ClaudeResult
            return ClaudeResult(
                success=True,
                exit_code=0,
                stdout="[DRY RUN] Phase execution simulated",
                stderr="",
            )
        except ImportError:
            # Create a simple result object
            class DryRunResult:
                success = True
                exit_code = 0
                stdout = "[DRY RUN] Phase execution simulated"
                stderr = ""

            return DryRunResult()

    async def validate_phase_setup(self, phase_dir: Path) -> tuple[bool, str]:
        """Validate that a phase is properly set up for execution.

        Args:
            phase_dir: Path to the phase directory.

        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check directory exists
        if not phase_dir.exists():
            return False, f"Phase directory does not exist: {phase_dir}"

        # Check CLAUDE.md exists
        claude_md = phase_dir / "CLAUDE.md"
        if not claude_md.exists():
            return False, f"CLAUDE.md not found in {phase_dir}"

        # Check input directory exists
        input_dir = phase_dir / "input"
        if not input_dir.exists():
            input_dir.mkdir(parents=True)

        # Check output directory exists
        output_dir = phase_dir / "output"
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        return True, ""

    async def check_claude_availability(self) -> bool:
        """Check if Claude CLI is available.

        Returns:
            True if Claude CLI is available and working.
        """
        if self.claude_runner is None:
            return False

        if hasattr(self.claude_runner, "check_availability"):
            return await self.claude_runner.check_availability()

        return True
