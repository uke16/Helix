"""Escalation System for HELIX v4.

Implements 2-stage escalation for handling failures.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .quality_gates import GateResult


class EscalationLevel(Enum):
    """Escalation level enumeration."""
    NONE = 0
    STUFE_1 = 1
    STUFE_2 = 2


class ActionType(Enum):
    """Types of escalation actions."""
    RETRY = "retry"
    MODEL_SWITCH = "model_switch"
    PLAN_REVERT = "plan_revert"
    PROVIDE_HINTS = "provide_hints"
    HUMAN_REVIEW = "human_review"
    ABORT = "abort"


@dataclass
class EscalationState:
    """Current state of escalation for a phase.

    Attributes:
        phase_id: ID of the phase being escalated.
        level: Current escalation level.
        attempt_count: Number of attempts at current level.
        total_attempts: Total attempts across all levels.
        failure_history: List of previous failures.
        context: Additional context for decision making.
    """
    phase_id: str
    level: EscalationLevel = EscalationLevel.NONE
    attempt_count: int = 0
    total_attempts: int = 0
    failure_history: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationAction:
    """An action to take in response to escalation.

    Attributes:
        action_type: Type of action to take.
        level: Escalation level this action is part of.
        parameters: Action-specific parameters.
        message: Human-readable description of the action.
        requires_human: Whether human intervention is needed.
    """
    action_type: ActionType
    level: EscalationLevel
    parameters: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    requires_human: bool = False


class EscalationManager:
    """Manages escalation for phase failures.

    Implements a 2-stage escalation system:

    Stufe 1 (Consultant-Autonomous):
    - Model switching (try different/more capable model)
    - Plan reversion (revert to previous working state)
    - Providing hints (add context/hints for retry)

    Stufe 2 (Human-in-the-Loop):
    - Request human review and decision
    - Provide full context for human decision

    Example:
        manager = EscalationManager()
        state = EscalationState(phase_id="01-foundation")

        action = await manager.handle_gate_failure(
            phase_dir=Path("/project/phases/01-foundation"),
            gate_result=gate_result,
            state=state
        )

        if action.requires_human:
            # Wait for human input
            pass
        else:
            # Execute action automatically
            pass
    """

    MAX_STUFE_1_ATTEMPTS = 3
    MAX_STUFE_2_ATTEMPTS = 2

    MODEL_ESCALATION_PATH = [
        "claude-3-haiku",
        "claude-3-sonnet",
        "claude-3-opus",
    ]

    def __init__(
        self,
        max_stufe_1_attempts: int | None = None,
        max_stufe_2_attempts: int | None = None,
    ) -> None:
        """Initialize the EscalationManager.

        Args:
            max_stufe_1_attempts: Max attempts at Stufe 1.
            max_stufe_2_attempts: Max attempts at Stufe 2.
        """
        self.max_stufe_1_attempts = max_stufe_1_attempts or self.MAX_STUFE_1_ATTEMPTS
        self.max_stufe_2_attempts = max_stufe_2_attempts or self.MAX_STUFE_2_ATTEMPTS

    async def handle_gate_failure(
        self,
        phase_dir: Path,
        gate_result: GateResult,
        state: EscalationState,
    ) -> EscalationAction:
        """Handle a quality gate failure.

        Args:
            phase_dir: Path to the phase directory.
            gate_result: The failed gate result.
            state: Current escalation state.

        Returns:
            EscalationAction to take.
        """
        state.failure_history.append({
            "timestamp": datetime.now().isoformat(),
            "gate_type": gate_result.gate_type,
            "message": gate_result.message,
            "details": gate_result.details,
            "level": state.level.value,
            "attempt": state.attempt_count,
        })

        self._save_escalation_state(phase_dir, state)

        if state.level == EscalationLevel.NONE:
            state.level = EscalationLevel.STUFE_1
            state.attempt_count = 0

        if state.level == EscalationLevel.STUFE_1:
            state.attempt_count += 1
            state.total_attempts += 1

            if state.attempt_count <= self.max_stufe_1_attempts:
                return await self.trigger_stufe_1(phase_dir, state)
            else:
                state.level = EscalationLevel.STUFE_2
                state.attempt_count = 0

        if state.level == EscalationLevel.STUFE_2:
            state.attempt_count += 1
            state.total_attempts += 1

            if state.attempt_count <= self.max_stufe_2_attempts:
                return await self.trigger_stufe_2(phase_dir, state)
            else:
                return EscalationAction(
                    action_type=ActionType.ABORT,
                    level=EscalationLevel.STUFE_2,
                    message="Maximum escalation attempts exceeded. Aborting phase.",
                    requires_human=True,
                )

        return EscalationAction(
            action_type=ActionType.ABORT,
            level=state.level,
            message="Unexpected escalation state",
            requires_human=True,
        )

    async def trigger_stufe_1(
        self,
        phase_dir: Path,
        state: EscalationState,
    ) -> EscalationAction:
        """Execute Stufe 1 (consultant-autonomous) escalation.

        Args:
            phase_dir: Path to the phase directory.
            state: Current escalation state.

        Returns:
            EscalationAction for Stufe 1.
        """
        strategy = self._select_stufe_1_strategy(state)

        if strategy == "model_switch":
            new_model = self._get_next_model(state)
            return EscalationAction(
                action_type=ActionType.MODEL_SWITCH,
                level=EscalationLevel.STUFE_1,
                parameters={"model": new_model},
                message=f"Switching to more capable model: {new_model}",
                requires_human=False,
            )

        elif strategy == "plan_revert":
            return EscalationAction(
                action_type=ActionType.PLAN_REVERT,
                level=EscalationLevel.STUFE_1,
                parameters={"revert_to": "last_successful"},
                message="Reverting to last successful state and retrying",
                requires_human=False,
            )

        elif strategy == "provide_hints":
            hints = self._generate_hints(state)
            return EscalationAction(
                action_type=ActionType.PROVIDE_HINTS,
                level=EscalationLevel.STUFE_1,
                parameters={"hints": hints},
                message="Providing additional hints for retry",
                requires_human=False,
            )

        return EscalationAction(
            action_type=ActionType.RETRY,
            level=EscalationLevel.STUFE_1,
            message=f"Retry attempt {state.attempt_count}",
            requires_human=False,
        )

    async def trigger_stufe_2(
        self,
        phase_dir: Path,
        state: EscalationState,
    ) -> EscalationAction:
        """Execute Stufe 2 (human-in-the-loop) escalation.

        Args:
            phase_dir: Path to the phase directory.
            state: Current escalation state.

        Returns:
            EscalationAction for Stufe 2.
        """
        review_request = self._create_review_request(phase_dir, state)
        self._save_review_request(phase_dir, review_request)

        return EscalationAction(
            action_type=ActionType.HUMAN_REVIEW,
            level=EscalationLevel.STUFE_2,
            parameters={"review_request": review_request},
            message="Human review required. Please check escalation/review-request.json",
            requires_human=True,
        )

    def _select_stufe_1_strategy(self, state: EscalationState) -> str:
        """Select the best Stufe 1 strategy based on state.

        Args:
            state: Current escalation state.

        Returns:
            Strategy name.
        """
        attempt = state.attempt_count

        if attempt == 1:
            return "retry"
        elif attempt == 2:
            return "model_switch"
        elif attempt == 3:
            return "provide_hints"

        return "retry"

    def _get_next_model(self, state: EscalationState) -> str:
        """Get the next model in the escalation path.

        Args:
            state: Current escalation state.

        Returns:
            Model spec for the next model.
        """
        current_model = state.context.get("current_model", self.MODEL_ESCALATION_PATH[0])

        try:
            current_index = self.MODEL_ESCALATION_PATH.index(current_model)
            next_index = min(current_index + 1, len(self.MODEL_ESCALATION_PATH) - 1)
            return self.MODEL_ESCALATION_PATH[next_index]
        except ValueError:
            return self.MODEL_ESCALATION_PATH[-1]

    def _generate_hints(self, state: EscalationState) -> list[str]:
        """Generate hints based on failure history.

        Args:
            state: Current escalation state.

        Returns:
            List of hint strings.
        """
        hints = []

        for failure in state.failure_history:
            gate_type = failure.get("gate_type", "")
            details = failure.get("details", {})

            if gate_type == "files_exist":
                missing = details.get("missing", [])
                if missing:
                    hints.append(f"Ensure these files are created: {', '.join(missing)}")

            elif gate_type == "syntax_check":
                errors = details.get("errors", [])
                for error in errors[:3]:
                    hints.append(
                        f"Fix syntax error in {error.get('file')}: {error.get('message')}"
                    )

            elif gate_type == "tests_pass":
                hints.append("Review test failures and fix the failing tests")
                stderr = details.get("stderr", "")
                if "AssertionError" in stderr:
                    hints.append("Check assertions in tests - expected values may be wrong")

        if not hints:
            hints.append("Review the CLAUDE.md requirements carefully")
            hints.append("Check for any missing or incomplete implementations")

        return hints[:5]

    def _create_review_request(
        self,
        phase_dir: Path,
        state: EscalationState,
    ) -> dict[str, Any]:
        """Create a human review request.

        Args:
            phase_dir: Path to the phase directory.
            state: Current escalation state.

        Returns:
            Review request dictionary.
        """
        return {
            "phase_id": state.phase_id,
            "phase_dir": str(phase_dir),
            "created_at": datetime.now().isoformat(),
            "escalation_level": "stufe_2",
            "total_attempts": state.total_attempts,
            "failure_summary": self._summarize_failures(state),
            "failure_history": state.failure_history,
            "requested_actions": [
                "Review the failure history",
                "Provide guidance or fix the issue",
                "Respond by creating escalation/human-response.json",
            ],
            "response_schema": {
                "action": "retry | skip | abort | manual_fix",
                "guidance": "Optional guidance for retry",
                "notes": "Optional notes",
            },
        }

    def _summarize_failures(self, state: EscalationState) -> str:
        """Create a summary of failures.

        Args:
            state: Current escalation state.

        Returns:
            Summary string.
        """
        if not state.failure_history:
            return "No failures recorded"

        gate_types = set(f.get("gate_type", "unknown") for f in state.failure_history)
        return f"Failed {len(state.failure_history)} times. Gate types: {', '.join(gate_types)}"

    def _save_escalation_state(self, phase_dir: Path, state: EscalationState) -> None:
        """Save escalation state to disk.

        Args:
            phase_dir: Path to the phase directory.
            state: Escalation state to save.
        """
        escalation_dir = phase_dir / "escalation"
        escalation_dir.mkdir(parents=True, exist_ok=True)

        state_file = escalation_dir / "state.json"
        state_data = {
            "phase_id": state.phase_id,
            "level": state.level.value,
            "attempt_count": state.attempt_count,
            "total_attempts": state.total_attempts,
            "failure_history": state.failure_history,
            "context": state.context,
            "updated_at": datetime.now().isoformat(),
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def _save_review_request(
        self, phase_dir: Path, review_request: dict[str, Any]
    ) -> None:
        """Save review request to disk.

        Args:
            phase_dir: Path to the phase directory.
            review_request: Review request data.
        """
        escalation_dir = phase_dir / "escalation"
        escalation_dir.mkdir(parents=True, exist_ok=True)

        request_file = escalation_dir / "review-request.json"
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump(review_request, f, indent=2)

    def load_escalation_state(self, phase_dir: Path) -> EscalationState | None:
        """Load escalation state from disk.

        Args:
            phase_dir: Path to the phase directory.

        Returns:
            EscalationState or None if not found.
        """
        state_file = phase_dir / "escalation" / "state.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return EscalationState(
                phase_id=data["phase_id"],
                level=EscalationLevel(data["level"]),
                attempt_count=data["attempt_count"],
                total_attempts=data["total_attempts"],
                failure_history=data.get("failure_history", []),
                context=data.get("context", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def load_human_response(self, phase_dir: Path) -> dict[str, Any] | None:
        """Load human response from disk.

        Args:
            phase_dir: Path to the phase directory.

        Returns:
            Response dictionary or None if not found.
        """
        response_file = phase_dir / "escalation" / "human-response.json"
        if not response_file.exists():
            return None

        try:
            with open(response_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
