"""Calculate and track costs per phase and project.

This module provides cost calculation and tracking for HELIX phases,
using either direct cost data from Claude CLI or calculated costs
based on token usage and model pricing.

Usage:
    calc = CostCalculator(project_id="my-project")

    # Start a phase
    calc.start_phase("01-foundation", model="claude-sonnet-4")

    # Record usage (called when stream-json result event arrives)
    calc.record_usage(input_tokens=1500, output_tokens=800, cost_usd=0.0234)

    # End phase
    summary = calc.end_phase()

    # Get project totals
    totals = calc.get_project_totals()
    print(f"Total cost: ${totals['total_cost_usd']:.4f}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json
from pathlib import Path


# Cost per 1M tokens (USD) - Updated December 2024
MODEL_COSTS: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-sonnet-3.5": {"input": 3.00, "output": 15.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    # Default fallback
    "default": {"input": 3.00, "output": 15.00},
}


@dataclass
class PhaseCost:
    """Cost breakdown for a single phase.

    Attributes:
        phase_id: The HELIX phase identifier.
        model: The LLM model used.
        input_tokens: Total input tokens consumed.
        output_tokens: Total output tokens generated.
        cost_usd: Total cost in USD.
        started_at: When the phase started.
        completed_at: When the phase completed.
        tool_calls: Number of tool calls made.
    """

    phase_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    tool_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict.

        Returns:
            Dictionary with all cost data formatted for serialization.
        """
        return {
            "phase_id": self.phase_id,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_seconds": self.duration_seconds(),
            "tool_calls": self.tool_calls,
        }

    def duration_seconds(self) -> float | None:
        """Calculate phase duration in seconds.

        Returns:
            Duration in seconds, or None if phase not completed.
        """
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def cost_per_1k_tokens(self) -> float | None:
        """Calculate cost per 1000 tokens.

        Returns:
            Cost per 1K tokens, or None if no tokens used.
        """
        total_tokens = self.input_tokens + self.output_tokens
        if total_tokens == 0:
            return None
        return (self.cost_usd / total_tokens) * 1000


class CostCalculator:
    """Calculate and track costs for HELIX phases.

    This calculator tracks token usage and costs per phase, supporting
    both direct cost reporting from Claude CLI and calculated costs
    based on token counts and model pricing.

    Attributes:
        project_id: The HELIX project identifier.
        default_model: Default model to use for cost calculations.
        _phases: Dictionary of completed phases by phase_id.
        _current_phase: The currently active phase being tracked.

    Example:
        calc = CostCalculator(project_id="my-project")

        # Start a phase
        calc.start_phase("01-foundation", model="claude-sonnet-4")

        # Record usage (called when stream-json result event arrives)
        calc.record_usage(
            input_tokens=1500,
            output_tokens=800,
            cost_usd=0.0234
        )

        # End phase
        summary = calc.end_phase()

        # Get project totals
        totals = calc.get_project_totals()
        print(f"Total cost: ${totals['total_cost_usd']:.4f}")
    """

    def __init__(
        self,
        project_id: str,
        model: str = "claude-sonnet-4",
    ) -> None:
        """Initialize the cost calculator.

        Args:
            project_id: The HELIX project identifier.
            model: Default model for cost calculations.
        """
        self.project_id = project_id
        self.default_model = model
        self._phases: dict[str, PhaseCost] = {}
        self._current_phase: PhaseCost | None = None

    def start_phase(
        self,
        phase_id: str,
        model: str | None = None,
    ) -> PhaseCost:
        """Start tracking a new phase.

        Args:
            phase_id: The phase identifier to track.
            model: Optional model override for this phase.

        Returns:
            The created PhaseCost object.
        """
        phase = PhaseCost(
            phase_id=phase_id,
            model=model or self.default_model,
        )
        self._current_phase = phase
        return phase

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | None = None,
    ) -> None:
        """Record token usage for current phase.

        If cost_usd is provided (from Claude CLI), use it directly.
        Otherwise, calculate from tokens based on model pricing.

        Args:
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens generated.
            cost_usd: Direct cost from Claude CLI (preferred).
        """
        if not self._current_phase:
            return

        self._current_phase.input_tokens += input_tokens
        self._current_phase.output_tokens += output_tokens

        if cost_usd is not None:
            self._current_phase.cost_usd = cost_usd
        else:
            # Calculate from tokens
            self._current_phase.cost_usd = self._calculate_cost(
                input_tokens=self._current_phase.input_tokens,
                output_tokens=self._current_phase.output_tokens,
                model=self._current_phase.model,
            )

    def record_tool_call(self) -> None:
        """Record a tool call for current phase."""
        if self._current_phase:
            self._current_phase.tool_calls += 1

    def end_phase(self) -> PhaseCost | None:
        """End the current phase and return its cost data.

        Returns:
            The completed PhaseCost object, or None if no phase active.
        """
        if not self._current_phase:
            return None

        self._current_phase.completed_at = datetime.now()
        self._phases[self._current_phase.phase_id] = self._current_phase

        result = self._current_phase
        self._current_phase = None
        return result

    def get_phase(self, phase_id: str) -> PhaseCost | None:
        """Get cost data for a specific phase.

        Args:
            phase_id: The phase identifier to look up.

        Returns:
            PhaseCost for the phase, or None if not found.
        """
        return self._phases.get(phase_id)

    def get_current_phase(self) -> PhaseCost | None:
        """Get the current (in-progress) phase.

        Returns:
            The active PhaseCost, or None if no phase is active.
        """
        return self._current_phase

    def get_all_phases(self) -> list[PhaseCost]:
        """Get all completed phases.

        Returns:
            List of all PhaseCost objects.
        """
        return list(self._phases.values())

    def get_project_totals(self) -> dict[str, Any]:
        """Get aggregated cost data for the entire project.

        Returns:
            Dictionary with:
            - project_id: Project identifier
            - phases_completed: Number of phases tracked
            - total_input_tokens: Sum of all input tokens
            - total_output_tokens: Sum of all output tokens
            - total_tokens: Sum of all tokens
            - total_cost_usd: Total cost in USD
            - total_tool_calls: Total tool calls across phases
            - total_duration_seconds: Total execution time
            - cost_per_phase: Breakdown by phase ID
        """
        total_input = sum(p.input_tokens for p in self._phases.values())
        total_output = sum(p.output_tokens for p in self._phases.values())
        total_cost = sum(p.cost_usd for p in self._phases.values())
        total_tool_calls = sum(p.tool_calls for p in self._phases.values())
        total_duration = sum(
            p.duration_seconds() or 0 for p in self._phases.values()
        )

        return {
            "project_id": self.project_id,
            "phases_completed": len(self._phases),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 6),
            "total_tool_calls": total_tool_calls,
            "total_duration_seconds": round(total_duration, 2),
            "cost_per_phase": {
                pid: round(p.cost_usd, 6) for pid, p in self._phases.items()
            },
        }

    def save_to_file(self, file_path: Path) -> None:
        """Save project cost data to JSON file.

        Args:
            file_path: Path to write the JSON file.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project_id": self.project_id,
            "generated_at": datetime.now().isoformat(),
            "totals": self.get_project_totals(),
            "phases": {pid: p.to_dict() for pid, p in self._phases.items()},
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "CostCalculator":
        """Load cost data from JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            CostCalculator populated with the loaded data.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        calc = cls(project_id=data["project_id"])

        for phase_data in data.get("phases", {}).values():
            phase = PhaseCost(
                phase_id=phase_data["phase_id"],
                model=phase_data["model"],
                input_tokens=phase_data["input_tokens"],
                output_tokens=phase_data["output_tokens"],
                cost_usd=phase_data["cost_usd"],
                started_at=datetime.fromisoformat(phase_data["started_at"]),
                completed_at=(
                    datetime.fromisoformat(phase_data["completed_at"])
                    if phase_data.get("completed_at")
                    else None
                ),
                tool_calls=phase_data.get("tool_calls", 0),
            )
            calc._phases[phase.phase_id] = phase

        return calc

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> float:
        """Calculate cost in USD for given tokens and model.

        Uses MODEL_COSTS lookup with fuzzy matching for model names.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            model: Model name to look up pricing.

        Returns:
            Calculated cost in USD.
        """
        # Find matching model costs
        costs = MODEL_COSTS.get("default")

        model_lower = model.lower()
        for model_key, model_costs in MODEL_COSTS.items():
            if model_key in model_lower or model_lower in model_key:
                costs = model_costs
                break

        assert costs is not None  # default always exists

        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost

    def get_cost_for_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
    ) -> float:
        """Calculate cost for given token counts.

        Utility method for cost estimation without recording.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            model: Model name (defaults to calculator default).

        Returns:
            Estimated cost in USD.
        """
        return self._calculate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or self.default_model,
        )

    def clear(self) -> None:
        """Clear all tracked phases."""
        self._phases.clear()
        self._current_phase = None
