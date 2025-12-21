"""
HELIX v4 Observability - Metrics Module

Token & Cost Tracking für Projekte und Phasen.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import threading
from typing import Any


# Token-zu-Kosten Mapping (pro 1M Tokens)
COST_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}


def calculate_cost(
    input_tokens: int, output_tokens: int, model: str
) -> float:
    """Calculate cost in USD for given tokens and model."""
    # Normalize model name (handle variations)
    model_lower = model.lower()

    # Find matching model
    costs = None
    for model_key in COST_PER_1M_TOKENS:
        if model_key in model_lower or model_lower in model_key:
            costs = COST_PER_1M_TOKENS[model_key]
            break

    if costs is None:
        # Default to claude-sonnet-4 if model not found
        costs = COST_PER_1M_TOKENS["claude-sonnet-4"]

    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]

    return input_cost + output_cost


@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""

    phase_id: str
    start_time: datetime
    end_time: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    files_created: int = 0
    files_modified: int = 0
    retries: int = 0
    escalations: int = 0
    success: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "phase_id": self.phase_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "tool_calls": self.tool_calls,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "retries": self.retries,
            "escalations": self.escalations,
            "success": self.success,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhaseMetrics":
        """Create PhaseMetrics from dict."""
        return cls(
            phase_id=data["phase_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
            tool_calls=data.get("tool_calls", 0),
            files_created=data.get("files_created", 0),
            files_modified=data.get("files_modified", 0),
            retries=data.get("retries", 0),
            escalations=data.get("escalations", 0),
            success=data.get("success"),
        )

    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class ProjectMetrics:
    """Metrics for an entire project."""

    project_id: str
    start_time: datetime
    end_time: datetime | None = None
    phases: dict[str, PhaseMetrics] = field(default_factory=dict)
    total_cost_usd: float = 0.0

    def add_phase(self, phase: PhaseMetrics) -> None:
        """Add a phase's metrics to the project."""
        self.phases[phase.phase_id] = phase
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate total cost from all phases."""
        self.total_cost_usd = sum(p.cost_usd for p in self.phases.values())

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of project metrics."""
        total_input_tokens = sum(p.input_tokens for p in self.phases.values())
        total_output_tokens = sum(p.output_tokens for p in self.phases.values())
        total_tool_calls = sum(p.tool_calls for p in self.phases.values())
        total_files_created = sum(p.files_created for p in self.phases.values())
        total_files_modified = sum(p.files_modified for p in self.phases.values())
        total_retries = sum(p.retries for p in self.phases.values())
        total_escalations = sum(p.escalations for p in self.phases.values())

        successful_phases = sum(1 for p in self.phases.values() if p.success is True)
        failed_phases = sum(1 for p in self.phases.values() if p.success is False)

        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "project_id": self.project_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "total_phases": len(self.phases),
            "successful_phases": successful_phases,
            "failed_phases": failed_phases,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_tool_calls": total_tool_calls,
            "total_files_created": total_files_created,
            "total_files_modified": total_files_modified,
            "total_retries": total_retries,
            "total_escalations": total_escalations,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "project_id": self.project_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "phases": {k: v.to_dict() for k, v in self.phases.items()},
            "total_cost_usd": self.total_cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMetrics":
        """Create ProjectMetrics from dict."""
        phases = {
            k: PhaseMetrics.from_dict(v)
            for k, v in data.get("phases", {}).items()
        }
        return cls(
            project_id=data["project_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            phases=phases,
            total_cost_usd=data.get("total_cost_usd", 0.0),
        )


class MetricsCollector:
    """Thread-safe metrics collector for HELIX v4."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.current_project: ProjectMetrics | None = None
        self.current_phase: PhaseMetrics | None = None
        self._lock = threading.Lock()

    def _metrics_file(self) -> Path:
        """Get the path to the metrics file."""
        return self.project_dir / "logs" / "metrics.json"

    def start_project(self, project_id: str) -> None:
        """Start tracking a new project."""
        with self._lock:
            self.current_project = ProjectMetrics(
                project_id=project_id,
                start_time=datetime.now(),
            )

    def end_project(self) -> ProjectMetrics | None:
        """End the current project and return its metrics."""
        with self._lock:
            if self.current_project is None:
                return None

            self.current_project.end_time = datetime.now()
            self.current_project._recalculate_totals()

            result = self.current_project
            self.current_project = None
            return result

    def start_phase(self, phase_id: str) -> None:
        """Start tracking a new phase."""
        with self._lock:
            self.current_phase = PhaseMetrics(
                phase_id=phase_id,
                start_time=datetime.now(),
            )

    def end_phase(self, success: bool = True) -> PhaseMetrics | None:
        """End the current phase and return its metrics."""
        with self._lock:
            if self.current_phase is None:
                return None

            self.current_phase.end_time = datetime.now()
            self.current_phase.success = success

            # Add to project if tracking
            if self.current_project is not None:
                self.current_project.add_phase(self.current_phase)

            result = self.current_phase
            self.current_phase = None
            return result

    def record_tokens(
        self, input_tokens: int, output_tokens: int, model: str
    ) -> None:
        """Record token usage and calculate cost."""
        with self._lock:
            if self.current_phase is None:
                return

            self.current_phase.input_tokens += input_tokens
            self.current_phase.output_tokens += output_tokens

            cost = calculate_cost(input_tokens, output_tokens, model)
            self.current_phase.cost_usd += cost

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        with self._lock:
            if self.current_phase is None:
                return
            self.current_phase.tool_calls += 1

    def record_file_change(self, change_type: str) -> None:
        """Record a file change (created or modified)."""
        with self._lock:
            if self.current_phase is None:
                return

            if change_type == "created":
                self.current_phase.files_created += 1
            elif change_type == "modified":
                self.current_phase.files_modified += 1

    def record_retry(self) -> None:
        """Record a retry attempt."""
        with self._lock:
            if self.current_phase is None:
                return
            self.current_phase.retries += 1

    def record_escalation(self) -> None:
        """Record an escalation."""
        with self._lock:
            if self.current_phase is None:
                return
            self.current_phase.escalations += 1

    def save_metrics(self) -> Path:
        """Save current project metrics to file."""
        with self._lock:
            if self.current_project is None:
                raise ValueError("No project currently being tracked")

            metrics_file = self._metrics_file()
            metrics_file.parent.mkdir(parents=True, exist_ok=True)

            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.current_project.to_dict(), f, indent=2, ensure_ascii=False)

            return metrics_file

    def load_metrics(self) -> ProjectMetrics | None:
        """Load project metrics from file."""
        metrics_file = self._metrics_file()

        if not metrics_file.exists():
            return None

        with open(metrics_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ProjectMetrics.from_dict(data)
