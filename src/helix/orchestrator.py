"""Workflow Orchestrator for HELIX v4.

Manages the execution of project phases and quality gates.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .phase_loader import PhaseConfig, PhaseLoader
from .quality_gates import GateResult, QualityGateRunner
from .context_manager import ContextManager
from .template_engine import TemplateEngine
from .claude_runner import ClaudeRunner, ClaudeResult
from .escalation import EscalationManager, EscalationState, EscalationAction


@dataclass
class PhaseResult:
    """Result of executing a single phase.

    Attributes:
        phase_id: ID of the phase that was executed.
        status: Execution status (success, failed, skipped).
        started_at: When the phase started.
        completed_at: When the phase completed.
        claude_result: Result from Claude Code execution.
        gate_result: Result from quality gate check.
        escalation_actions: Any escalation actions taken.
        error: Error message if phase failed.
    """
    phase_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    claude_result: ClaudeResult | None = None
    gate_result: GateResult | None = None
    escalation_actions: list[EscalationAction] = field(default_factory=list)
    error: str | None = None


@dataclass
class ProjectResult:
    """Result of executing an entire project.

    Attributes:
        project_id: ID of the project.
        status: Overall status (success, failed, partial).
        started_at: When execution started.
        completed_at: When execution completed.
        phases: Results for each phase.
        total_phases: Total number of phases.
        completed_phases: Number of successfully completed phases.
    """
    project_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    phases: list[PhaseResult] = field(default_factory=list)
    total_phases: int = 0
    completed_phases: int = 0


class Orchestrator:
    """Orchestrates the execution of HELIX v4 project workflows.

    The Orchestrator manages the sequential execution of phases,
    handles quality gate checks, and coordinates escalation when
    gates fail.

    Example:
        orchestrator = Orchestrator()
        result = await orchestrator.run_project(Path("/path/to/project"))
        if result.status == "success":
            print(f"All {result.completed_phases} phases completed!")
    """

    MAX_GATE_RETRIES = 3

    def __init__(
        self,
        phase_loader: PhaseLoader | None = None,
        gate_runner: QualityGateRunner | None = None,
        context_manager: ContextManager | None = None,
        template_engine: TemplateEngine | None = None,
        claude_runner: ClaudeRunner | None = None,
        escalation_manager: EscalationManager | None = None,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            phase_loader: Phase configuration loader.
            gate_runner: Quality gate runner.
            context_manager: Context manager for skills.
            template_engine: Template engine for CLAUDE.md.
            claude_runner: Claude Code CLI runner.
            escalation_manager: Escalation handler.
        """
        self.phase_loader = phase_loader or PhaseLoader()
        self.gate_runner = gate_runner or QualityGateRunner()
        self.context_manager = context_manager or ContextManager()
        self.template_engine = template_engine or TemplateEngine()
        self.claude_runner = claude_runner or ClaudeRunner()
        self.escalation_manager = escalation_manager or EscalationManager()

    async def run_project(self, project_dir: Path) -> ProjectResult:
        """Run all phases of a project.

        Args:
            project_dir: Path to the project directory.

        Returns:
            ProjectResult with status and phase results.
        """
        started_at = datetime.now()
        project_id = project_dir.name

        phases = self.phase_loader.load_phases(project_dir)

        result = ProjectResult(
            project_id=project_id,
            status="running",
            started_at=started_at,
            total_phases=len(phases),
        )

        spec = self._load_project_spec(project_dir)

        for phase_config in phases:
            phase_dir = self.phase_loader.get_phase_dir(project_dir, phase_config)

            phase_result = await self.run_phase(phase_dir, phase_config, spec)
            result.phases.append(phase_result)

            if phase_result.status == "success":
                result.completed_phases += 1
            else:
                result.status = "failed"
                result.completed_at = datetime.now()
                return result

        result.status = "success"
        result.completed_at = datetime.now()
        return result

    async def run_phase(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
        spec: dict[str, Any] | None = None,
    ) -> PhaseResult:
        """Run a single phase.

        Args:
            phase_dir: Path to the phase directory.
            phase_config: Phase configuration.
            spec: Optional project spec dictionary.

        Returns:
            PhaseResult with execution details.
        """
        started_at = datetime.now()

        result = PhaseResult(
            phase_id=phase_config.id,
            status="running",
            started_at=started_at,
        )

        try:
            phase_dir.mkdir(parents=True, exist_ok=True)

            if spec:
                self.context_manager.prepare_phase_context(phase_dir, spec)
                await self._generate_claude_md(phase_dir, phase_config, spec)

            model = phase_config.config.get("model")
            claude_result = await self.claude_runner.run_phase(phase_dir, model=model)
            result.claude_result = claude_result

            if not claude_result.success:
                result.status = "failed"
                result.error = claude_result.error
                result.completed_at = datetime.now()
                return result

            if phase_config.quality_gate:
                gate_result = await self.check_quality_gate(
                    phase_dir, phase_config.quality_gate
                )
                result.gate_result = gate_result

                if not gate_result.passed:
                    escalation_result = await self._handle_gate_failure(
                        phase_dir, phase_config, gate_result
                    )
                    result.escalation_actions = escalation_result.actions
                    result.gate_result = escalation_result.final_gate_result

                    if not escalation_result.final_gate_result.passed:
                        result.status = "failed"
                        result.error = escalation_result.final_gate_result.message
                        result.completed_at = datetime.now()
                        return result

            result.status = "success"
            result.completed_at = datetime.now()

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now()

        return result

    async def check_quality_gate(
        self, phase_dir: Path, gate_config: dict[str, Any]
    ) -> GateResult:
        """Check a quality gate for a phase.

        Args:
            phase_dir: Path to the phase directory.
            gate_config: Gate configuration dictionary.

        Returns:
            GateResult from the gate check.
        """
        return await self.gate_runner.run_gate(phase_dir, gate_config)

    async def _handle_gate_failure(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
        gate_result: GateResult,
    ) -> "EscalationResult":
        """Handle a quality gate failure with escalation.

        Args:
            phase_dir: Path to the phase directory.
            phase_config: Phase configuration.
            gate_result: The failed gate result.

        Returns:
            EscalationResult with actions taken and final gate result.
        """
        actions: list[EscalationAction] = []
        current_gate_result = gate_result
        state = EscalationState(
            phase_id=phase_config.id,
            attempts=1,
            gate_results=[gate_result],
        )

        for attempt in range(self.MAX_GATE_RETRIES):
            action = await self.escalation_manager.handle_gate_failure(
                phase_dir, current_gate_result, state
            )
            actions.append(action)

            if action.action_type == "human_required":
                break

            if action.action_type in ("retry", "model_switch"):
                model = action.details.get("model") if action.action_type == "model_switch" else None
                claude_result = await self.claude_runner.run_phase(phase_dir, model=model)

                if claude_result.success:
                    current_gate_result = await self.check_quality_gate(
                        phase_dir, phase_config.quality_gate
                    )
                    state.gate_results.append(current_gate_result)
                    state.attempts += 1

                    if current_gate_result.passed:
                        break

        return EscalationResult(
            actions=actions,
            final_gate_result=current_gate_result,
        )

    async def _generate_claude_md(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
        spec: dict[str, Any],
    ) -> None:
        """Generate CLAUDE.md for a phase.

        Args:
            phase_dir: Path to the phase directory.
            phase_config: Phase configuration.
            spec: Project spec dictionary.
        """
        context = {
            **self.template_engine._build_context(spec),
            "phase_id": phase_config.id,
            "phase_name": phase_config.name,
            "phase_type": phase_config.type,
            "phase_config": phase_config.config,
        }

        template_name = phase_config.config.get("template", spec.get("meta", {}).get("language", "python"))
        content = self.template_engine.render_claude_md(template_name, context)

        claude_md_path = phase_dir / "CLAUDE.md"
        claude_md_path.write_text(content, encoding="utf-8")

    def _load_project_spec(self, project_dir: Path) -> dict[str, Any] | None:
        """Load project specification from ADR or spec.yaml.

        Priority:
        1. ADR-*.md files (new way - ADR as Single Source of Truth)
        2. spec.yaml (legacy fallback)

        Args:
            project_dir: Path to the project directory.

        Returns:
            Spec dictionary or None if not found.
        """
        # Try ADR first (Single Source of Truth)
        adr_files = list(project_dir.glob("ADR-*.md"))
        if not adr_files:
            adr_files = list(project_dir.glob("[0-9][0-9][0-9]-*.md"))
        
        if adr_files:
            try:
                from helix.adr import ADRParser
                parser = ADRParser()
                adr = parser.parse_file(adr_files[0])
                
                # Convert ADR to spec-compatible dict
                return {
                    "meta": {
                        "id": adr.metadata.adr_id,
                        "name": adr.metadata.title,
                        "domain": adr.metadata.domain,
                        "language": adr.metadata.language,
                    },
                    "context": {
                        "skills": adr.metadata.skills,
                    },
                    "output": {
                        "files": list(adr.metadata.files.create) + list(adr.metadata.files.modify),
                    },
                    "implementation": {
                        "summary": adr.sections.get("kontext", adr.sections.get("context", type("", (), {"content": ""})())).content if adr.sections else "",
                    },
                    # Keep reference to original ADR
                    "_adr": adr,
                    "_adr_path": str(adr_files[0]),
                }
            except Exception as e:
                # Log error but continue to spec.yaml fallback
                print(f"[ORCHESTRATOR] Warning: Could not parse ADR: {e}")
        
        # Fallback to spec.yaml (legacy)
        spec_path = project_dir / "spec.yaml"
        if not spec_path.exists():
            return None

        with open(spec_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def save_result(self, result: ProjectResult, output_path: Path) -> None:
        """Save a project result to JSON.

        Args:
            result: The project result to save.
            output_path: Path to save the result.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project_id": result.project_id,
            "status": result.status,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_phases": result.total_phases,
            "completed_phases": result.completed_phases,
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "status": p.status,
                    "started_at": p.started_at.isoformat(),
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                    "error": p.error,
                    "gate_result": {
                        "passed": p.gate_result.passed,
                        "gate_type": p.gate_result.gate_type,
                        "message": p.gate_result.message,
                    } if p.gate_result else None,
                }
                for p in result.phases
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


@dataclass
class EscalationResult:
    """Result of escalation handling.

    Attributes:
        actions: List of escalation actions taken.
        final_gate_result: The final gate result after escalation.
    """
    actions: list[EscalationAction]
    final_gate_result: GateResult
