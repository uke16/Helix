"""Unified Orchestrator for HELIX API.

This is the SINGLE source of truth for project execution.
All entry points (CLI, WebUI, API) use this orchestrator.

Consolidates:
- Quality Gates from orchestrator_legacy.py
- Verification from streaming.py (PhaseVerifier from evolution/verification.py)
- Event callbacks for SSE streaming
- Escalation from orchestrator_legacy.py

See: ADR-022 for architectural decision.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Awaitable

from helix.claude_runner import ClaudeRunner, ClaudeResult
from helix.phase_loader import PhaseLoader, PhaseConfig
from helix.quality_gates import QualityGateRunner, GateResult
from helix.evolution.verification import PhaseVerifier, VerificationResult
from helix.escalation import (
    EscalationManager,
    EscalationState,
    EscalationAction,
    EscalationLevel,
    ActionType,
)


@dataclass
class PhaseEvent:
    """Event emitted during phase execution.

    Used for SSE streaming and progress tracking.

    Attributes:
        event_type: Type of event (phase_start, phase_complete, verification_failed, etc.)
        phase_id: ID of the phase this event relates to (empty for project-level events)
        data: Additional event data
        timestamp: When the event occurred
    """
    event_type: str
    phase_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "phase_id": self.phase_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProjectResult:
    """Result of project execution.

    Attributes:
        success: Whether the project completed successfully
        phases_completed: Number of phases that completed successfully
        phases_total: Total number of phases in the project
        errors: List of error messages if any phases failed
        started_at: When execution started
        completed_at: When execution completed
        phase_results: Detailed results for each phase
    """
    success: bool
    phases_completed: int
    phases_total: int
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    phase_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "phases_completed": self.phases_completed,
            "phases_total": self.phases_total,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "phase_results": self.phase_results,
        }


# Type alias for event callback
EventCallback = Callable[[PhaseEvent], Awaitable[None]]


class UnifiedOrchestrator:
    """The one and only orchestrator for HELIX.

    Consolidates all orchestration logic from:
    - orchestrator_legacy.py (Quality Gates, Escalation)
    - streaming.py (Verification, Events)

    Used by:
    - API (/helix/execute)
    - CLI (via API)
    - Open WebUI (via API)

    Example:
        orchestrator = UnifiedOrchestrator()

        # Simple execution
        result = await orchestrator.run_project(Path("projects/my-feature"))

        # With event streaming
        async def handle_event(event: PhaseEvent):
            print(f"{event.event_type}: {event.phase_id}")

        result = await orchestrator.run_project(
            Path("projects/my-feature"),
            on_event=handle_event
        )
    """

    MAX_RETRIES = 2

    def __init__(
        self,
        claude_runner: ClaudeRunner | None = None,
        gate_runner: QualityGateRunner | None = None,
        phase_loader: PhaseLoader | None = None,
        escalation_manager: EscalationManager | None = None,
    ) -> None:
        """Initialize the UnifiedOrchestrator.

        Args:
            claude_runner: ClaudeRunner instance for executing Claude CLI
            gate_runner: QualityGateRunner for quality gate checks
            phase_loader: PhaseLoader for loading phase configurations
            escalation_manager: EscalationManager for handling failures
        """
        self.claude_runner = claude_runner or ClaudeRunner()
        self.gate_runner = gate_runner or QualityGateRunner()
        self.phase_loader = phase_loader or PhaseLoader()
        self.escalation_manager = escalation_manager or EscalationManager()

    async def run_project(
        self,
        project_path: Path,
        on_event: EventCallback | None = None,
        phase_filter: list[str] | None = None,
    ) -> ProjectResult:
        """Execute a project with full feature set.

        Features:
        - Phase execution via ClaudeRunner
        - Post-phase verification (ADR-011)
        - Quality gates with escalation (ADR-004)
        - Event streaming for progress updates

        Args:
            project_path: Path to project directory
            on_event: Optional callback for progress events
            phase_filter: Optional list of phase IDs to run (run all if None)

        Returns:
            ProjectResult with execution details
        """
        project_path = Path(project_path)
        started_at = datetime.now(timezone.utc)

        # Emit project start event
        await self._emit_event(on_event, PhaseEvent(
            event_type="project_start",
            data={"project_path": str(project_path)}
        ))

        # Load phases
        try:
            phases = self.phase_loader.load_phases(project_path)
        except FileNotFoundError as e:
            return ProjectResult(
                success=False,
                phases_completed=0,
                phases_total=0,
                errors=[f"Failed to load phases: {e}"],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        # Apply phase filter if provided
        if phase_filter:
            phases = [p for p in phases if p.id in phase_filter]

        errors: list[str] = []
        completed = 0
        phase_results: list[dict[str, Any]] = []

        # Create verifier for this project
        verifier = PhaseVerifier(project_path)

        for phase in phases:
            phase_dir = project_path / "phases" / phase.id
            phase_dir.mkdir(parents=True, exist_ok=True)

            # Emit phase start event
            await self._emit_event(on_event, PhaseEvent(
                event_type="phase_start",
                phase_id=phase.id,
                data={"name": phase.name, "type": phase.type}
            ))

            # Execute phase with retry loop
            phase_success = False
            phase_error: str | None = None

            for attempt in range(self.MAX_RETRIES + 1):
                # 1. Run Claude
                claude_result = await self._run_claude_phase(
                    phase_dir, phase, on_event
                )

                if not claude_result.success:
                    phase_error = f"Claude execution failed: {claude_result.stderr[:200]}"
                    await self._emit_event(on_event, PhaseEvent(
                        event_type="claude_failed",
                        phase_id=phase.id,
                        data={"error": phase_error, "attempt": attempt + 1}
                    ))
                    continue  # Retry

                # 2. Verify output (ADR-011)
                expected_files = self._get_expected_files(phase)
                if expected_files:
                    verify_result = verifier.verify_phase_output(
                        phase_id=phase.id,
                        phase_dir=phase_dir,
                        expected_files=expected_files,
                    )

                    if not verify_result.success:
                        await self._emit_event(on_event, PhaseEvent(
                            event_type="verification_failed",
                            phase_id=phase.id,
                            data={
                                "missing_files": verify_result.missing_files,
                                "syntax_errors": verify_result.syntax_errors,
                                "attempt": attempt + 1,
                                "max_retries": self.MAX_RETRIES,
                            }
                        ))

                        if attempt < self.MAX_RETRIES:
                            # Write retry context for next attempt
                            verifier.write_retry_file(
                                phase_dir, verify_result, attempt + 1
                            )
                            continue  # Retry
                        else:
                            phase_error = verify_result.message
                            break  # Max retries reached
                    else:
                        await self._emit_event(on_event, PhaseEvent(
                            event_type="verification_passed",
                            phase_id=phase.id,
                            data={"found_files": verify_result.found_files}
                        ))

                # 3. Quality Gate (if defined)
                if phase.quality_gate:
                    gate_result = await self._check_quality_gate(
                        phase_dir, phase, on_event
                    )

                    if not gate_result.passed:
                        await self._emit_event(on_event, PhaseEvent(
                            event_type="gate_failed",
                            phase_id=phase.id,
                            data={
                                "gate_type": gate_result.gate_type,
                                "message": gate_result.message,
                            }
                        ))

                        # Handle escalation (ADR-004)
                        escalation_action = await self._handle_escalation(
                            phase_dir, phase, gate_result, on_event
                        )

                        if escalation_action.requires_human:
                            phase_error = f"Requires human intervention: {escalation_action.message}"
                            break

                        if attempt < self.MAX_RETRIES:
                            continue  # Retry based on escalation
                        else:
                            phase_error = gate_result.message
                            break
                    else:
                        await self._emit_event(on_event, PhaseEvent(
                            event_type="gate_passed",
                            phase_id=phase.id,
                            data={"gate_type": gate_result.gate_type}
                        ))

                # Phase succeeded!
                phase_success = True
                break

            # Record phase result
            phase_result_data = {
                "phase_id": phase.id,
                "success": phase_success,
                "error": phase_error,
            }
            phase_results.append(phase_result_data)

            if phase_success:
                completed += 1
                await self._emit_event(on_event, PhaseEvent(
                    event_type="phase_complete",
                    phase_id=phase.id,
                    data={"success": True}
                ))
            else:
                errors.append(f"Phase {phase.id}: {phase_error}")
                await self._emit_event(on_event, PhaseEvent(
                    event_type="phase_failed",
                    phase_id=phase.id,
                    data={"error": phase_error}
                ))
                break  # Stop on first failure

        completed_at = datetime.now(timezone.utc)
        success = len(errors) == 0 and completed == len(phases)

        # Emit project complete event
        await self._emit_event(on_event, PhaseEvent(
            event_type="project_complete",
            data={
                "success": success,
                "phases_completed": completed,
                "phases_total": len(phases),
            }
        ))

        return ProjectResult(
            success=success,
            phases_completed=completed,
            phases_total=len(phases),
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
            phase_results=phase_results,
        )

    async def run_project_streaming(
        self,
        project_path: Path,
        phase_filter: list[str] | None = None,
    ) -> AsyncGenerator[PhaseEvent, None]:
        """Run project and yield events as SSE stream.

        This is a convenience method that wraps run_project() with
        an async generator interface for SSE streaming.

        Args:
            project_path: Path to project directory
            phase_filter: Optional list of phase IDs to run

        Yields:
            PhaseEvent objects as execution progresses
        """
        event_queue: asyncio.Queue[PhaseEvent] = asyncio.Queue()

        async def collect_event(event: PhaseEvent) -> None:
            await event_queue.put(event)

        # Start execution in background
        result_task = asyncio.create_task(
            self.run_project(project_path, on_event=collect_event, phase_filter=phase_filter)
        )

        # Yield events as they come
        while not result_task.done():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

        # Drain remaining events
        while not event_queue.empty():
            yield await event_queue.get()

        # Yield final result event
        result = await result_task
        yield PhaseEvent(
            event_type="project_result",
            data=result.to_dict()
        )

    async def _emit_event(
        self,
        on_event: EventCallback | None,
        event: PhaseEvent,
    ) -> None:
        """Emit an event if callback is provided.

        Args:
            on_event: Optional event callback
            event: Event to emit
        """
        if on_event:
            await on_event(event)

    async def _run_claude_phase(
        self,
        phase_dir: Path,
        phase: PhaseConfig,
        on_event: EventCallback | None,
    ) -> ClaudeResult:
        """Run Claude CLI for a phase.

        Args:
            phase_dir: Phase working directory
            phase: Phase configuration
            on_event: Optional event callback for output streaming

        Returns:
            ClaudeResult from execution
        """
        model = phase.config.get("model")

        if on_event:
            # Stream output via events
            async def output_callback(stream: str, line: str) -> None:
                await self._emit_event(on_event, PhaseEvent(
                    event_type="output",
                    phase_id=phase.id,
                    data={"stream": stream, "text": line}
                ))

            return await self.claude_runner.run_phase_streaming(
                phase_dir=phase_dir,
                on_output=output_callback,
                model=model,
                timeout=600,
            )
        else:
            return await self.claude_runner.run_phase(
                phase_dir=phase_dir,
                model=model,
                timeout=600,
            )

    async def _check_quality_gate(
        self,
        phase_dir: Path,
        phase: PhaseConfig,
        on_event: EventCallback | None,
    ) -> GateResult:
        """Check quality gate for a phase.

        Args:
            phase_dir: Phase working directory
            phase: Phase configuration
            on_event: Optional event callback

        Returns:
            GateResult from gate check
        """
        await self._emit_event(on_event, PhaseEvent(
            event_type="gate_check_start",
            phase_id=phase.id,
            data={"gate_config": phase.quality_gate}
        ))

        return await self.gate_runner.run_gate(phase_dir, phase.quality_gate)

    async def _handle_escalation(
        self,
        phase_dir: Path,
        phase: PhaseConfig,
        gate_result: GateResult,
        on_event: EventCallback | None,
    ) -> EscalationAction:
        """Handle a quality gate failure with escalation.

        Args:
            phase_dir: Phase working directory
            phase: Phase configuration
            gate_result: Failed gate result
            on_event: Optional event callback

        Returns:
            EscalationAction to take
        """
        state = EscalationState(
            phase_id=phase.id,
            level=EscalationLevel.NONE,
        )

        action = await self.escalation_manager.handle_gate_failure(
            phase_dir, gate_result, state
        )

        await self._emit_event(on_event, PhaseEvent(
            event_type="escalation",
            phase_id=phase.id,
            data={
                "action_type": action.action_type.value,
                "level": action.level.value,
                "message": action.message,
                "requires_human": action.requires_human,
            }
        ))

        return action

    def _get_expected_files(self, phase: PhaseConfig) -> list[str]:
        """Get expected output files from phase configuration.

        Args:
            phase: Phase configuration

        Returns:
            List of expected file paths
        """
        output = phase.output
        if isinstance(output, list):
            return output
        elif isinstance(output, dict):
            return output.get("files", [])
        return []
