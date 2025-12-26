"""Status Tracker for HELIX v4 Phase Orchestrator.

Provides persistent status tracking for project and phase execution
with support for resume capability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PhaseStatus:
    """Status of a single phase execution.

    Attributes:
        phase_id: Unique identifier for the phase.
        status: Current status (pending, running, completed, failed).
        started_at: When the phase started execution.
        completed_at: When the phase completed.
        retries: Number of retry attempts.
        error: Error message if phase failed.
    """

    phase_id: str
    status: str  # pending, running, completed, failed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retries": self.retries,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, phase_id: str, data: dict[str, Any]) -> "PhaseStatus":
        """Create from dictionary."""
        return cls(
            phase_id=phase_id,
            status=data.get("status", "pending"),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            retries=data.get("retries", 0),
            error=data.get("error"),
        )


@dataclass
class ProjectStatus:
    """Status of an entire project execution.

    Attributes:
        project_id: Unique identifier for the project.
        status: Overall status (pending, running, completed, failed).
        total_phases: Total number of phases in the project.
        completed_phases: Number of successfully completed phases.
        started_at: When the project execution started.
        completed_at: When the project execution completed.
        error: Error message if project failed.
        phases: Status of individual phases.
        project_dir: Path to the project directory.
    """

    project_id: str
    status: str  # pending, running, completed, failed
    total_phases: int = 0
    completed_phases: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    phases: dict[str, PhaseStatus] = field(default_factory=dict)
    project_dir: Path | None = None

    def is_phase_complete(self, phase_id: str) -> bool:
        """Check if a phase is completed.

        Args:
            phase_id: ID of the phase to check.

        Returns:
            True if the phase is completed successfully.
        """
        phase = self.phases.get(phase_id)
        return phase is not None and phase.status == "completed"

    def is_phase_failed(self, phase_id: str) -> bool:
        """Check if a phase has failed.

        Args:
            phase_id: ID of the phase to check.

        Returns:
            True if the phase has failed.
        """
        phase = self.phases.get(phase_id)
        return phase is not None and phase.status == "failed"

    def get_phase_status(self, phase_id: str) -> PhaseStatus | None:
        """Get the status of a specific phase.

        Args:
            phase_id: ID of the phase.

        Returns:
            PhaseStatus or None if phase not found.
        """
        return self.phases.get(phase_id)

    def mark_phase_started(self, phase_id: str) -> None:
        """Mark a phase as started.

        Args:
            phase_id: ID of the phase to mark.
        """
        if phase_id not in self.phases:
            self.phases[phase_id] = PhaseStatus(
                phase_id=phase_id,
                status="running",
                started_at=datetime.now(),
            )
        else:
            self.phases[phase_id].status = "running"
            self.phases[phase_id].started_at = datetime.now()

    def mark_phase_completed(self, phase_id: str) -> None:
        """Mark a phase as completed.

        Args:
            phase_id: ID of the phase to mark.
        """
        if phase_id not in self.phases:
            self.phases[phase_id] = PhaseStatus(
                phase_id=phase_id,
                status="completed",
                completed_at=datetime.now(),
            )
        else:
            self.phases[phase_id].status = "completed"
            self.phases[phase_id].completed_at = datetime.now()
        self.completed_phases = sum(
            1 for p in self.phases.values() if p.status == "completed"
        )

    def mark_phase_failed(self, phase_id: str, error: str | None = None) -> None:
        """Mark a phase as failed.

        Args:
            phase_id: ID of the phase to mark.
            error: Optional error message.
        """
        if phase_id not in self.phases:
            self.phases[phase_id] = PhaseStatus(
                phase_id=phase_id,
                status="failed",
                completed_at=datetime.now(),
                error=error,
            )
        else:
            self.phases[phase_id].status = "failed"
            self.phases[phase_id].completed_at = datetime.now()
            self.phases[phase_id].error = error

    def increment_phase_retries(self, phase_id: str) -> int:
        """Increment the retry counter for a phase.

        Args:
            phase_id: ID of the phase.

        Returns:
            New retry count.
        """
        if phase_id not in self.phases:
            self.phases[phase_id] = PhaseStatus(
                phase_id=phase_id,
                status="pending",
                retries=1,
            )
        else:
            self.phases[phase_id].retries += 1
        return self.phases[phase_id].retries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "project_id": self.project_id,
            "status": self.status,
            "total_phases": self.total_phases,
            "completed_phases": self.completed_phases,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "phases": {
                pid: phase.to_dict() for pid, phase in self.phases.items()
            },
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], project_dir: Path | None = None
    ) -> "ProjectStatus":
        """Create from dictionary.

        Args:
            data: Dictionary data from YAML.
            project_dir: Optional project directory path.

        Returns:
            ProjectStatus instance.
        """
        phases = {}
        for pid, pdata in data.get("phases", {}).items():
            phases[pid] = PhaseStatus.from_dict(pid, pdata)

        return cls(
            project_id=data.get("project_id", "unknown"),
            status=data.get("status", "pending"),
            total_phases=data.get("total_phases", 0),
            completed_phases=data.get("completed_phases", 0),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            error=data.get("error"),
            phases=phases,
            project_dir=project_dir,
        )


class StatusTracker:
    """Tracks and persists project execution status.

    The StatusTracker manages the persistence of project and phase
    status to a YAML file, enabling resume capability after failures
    or interruptions.

    Example:
        tracker = StatusTracker()
        status = tracker.load_or_create(project_dir)
        status.status = "running"
        status.mark_phase_started("01-consultant")
        tracker.save(status)

        # Later, after phase completes
        status.mark_phase_completed("01-consultant")
        tracker.save(status)
    """

    STATUS_FILE = "status.yaml"

    def __init__(self, status_file: str = "status.yaml") -> None:
        """Initialize the StatusTracker.

        Args:
            status_file: Name of the status file (default: status.yaml).
        """
        self.status_file = status_file

    def load_or_create(self, project_dir: Path) -> ProjectStatus:
        """Load existing status or create a new one.

        Args:
            project_dir: Path to the project directory.

        Returns:
            ProjectStatus instance, either loaded or newly created.
        """
        status_path = project_dir / self.status_file

        if status_path.exists():
            return self._load(status_path, project_dir)

        return ProjectStatus(
            project_id=project_dir.name,
            status="pending",
            project_dir=project_dir,
        )

    def load(self, project_dir: Path) -> ProjectStatus | None:
        """Load status from file if it exists.

        Args:
            project_dir: Path to the project directory.

        Returns:
            ProjectStatus or None if file doesn't exist.
        """
        status_path = project_dir / self.status_file

        if not status_path.exists():
            return None

        return self._load(status_path, project_dir)

    def _load(self, status_path: Path, project_dir: Path) -> ProjectStatus:
        """Load status from a YAML file.

        Args:
            status_path: Path to the status file.
            project_dir: Path to the project directory.

        Returns:
            ProjectStatus instance.
        """
        with open(status_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return ProjectStatus.from_dict(data, project_dir)

    def save(self, status: ProjectStatus) -> Path:
        """Save status to file.

        Args:
            status: ProjectStatus to save.

        Returns:
            Path to the saved status file.

        Raises:
            ValueError: If project_dir is not set on status.
        """
        if status.project_dir is None:
            raise ValueError("ProjectStatus.project_dir must be set to save status")

        status_path = status.project_dir / self.status_file
        status_path.parent.mkdir(parents=True, exist_ok=True)

        data = status.to_dict()

        with open(status_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return status_path

    def exists(self, project_dir: Path) -> bool:
        """Check if a status file exists.

        Args:
            project_dir: Path to the project directory.

        Returns:
            True if status file exists.
        """
        return (project_dir / self.status_file).exists()

    def delete(self, project_dir: Path) -> bool:
        """Delete the status file.

        Args:
            project_dir: Path to the project directory.

        Returns:
            True if file was deleted, False if it didn't exist.
        """
        status_path = project_dir / self.status_file
        if status_path.exists():
            status_path.unlink()
            return True
        return False
