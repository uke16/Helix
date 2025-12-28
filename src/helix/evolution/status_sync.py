"""Unified status synchronization for Evolution Pipeline.

ADR-031: Fix 1 - Status Synchronization

This module ensures JobState (in-memory) and status.json (on-disk) are always in sync.
It provides a single source of truth for phase status during pipeline execution.

Root Cause (from ADR-031):
    The Evolution Pipeline had two parallel, non-synchronized status tracking systems:
    1. In-Memory JobState - Used by API /helix/jobs/{id}
    2. On-Disk status.json - Used for project restart recovery

    streaming.py sent SSE events but updated neither JobState nor status.json,
    causing status.json to show phases as "pending" even after completion.

Solution:
    StatusSynchronizer acts as the single entry point for all status updates.
    All phase state changes (start, complete, fail) are immediately persisted
    to status.json with atomic writes for crash safety.

Usage:
    sync = StatusSynchronizer(project_path)
    sync.start_phase("phase-1")
    # ... phase execution ...
    sync.complete_phase("phase-1")
    # or
    sync.fail_phase("phase-1", "Error message")
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhaseStatus:
    """Status of a single phase.

    Attributes:
        phase_id: Unique identifier for the phase
        status: Current status (pending, running, completed, failed)
        started_at: Timestamp when phase started execution
        completed_at: Timestamp when phase completed (success or failure)
        error: Error message if phase failed
    """

    phase_id: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, phase_id: str, data: dict) -> "PhaseStatus":
        """Create PhaseStatus from dictionary.

        Args:
            phase_id: The phase identifier
            data: Dictionary with status data

        Returns:
            PhaseStatus instance
        """
        started_at = None
        completed_at = None

        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                pass

        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            phase_id=phase_id,
            status=data.get("status", "pending"),
            started_at=started_at,
            completed_at=completed_at,
            error=data.get("error")
        )


class StatusSynchronizer:
    """Keeps JobState and status.json in sync.

    Single source of truth: status.json
    JobState is derived from status.json on load.

    This class provides atomic writes (temp file + rename) for crash safety,
    ensuring that the status file is never left in a corrupted state even if
    the process is killed mid-write.

    Usage:
        sync = StatusSynchronizer(project_path)
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")
        sync.fail_phase("phase-1", "Error message")

    Thread Safety:
        This class is NOT thread-safe. If multiple threads need to update
        status, external synchronization is required.
    """

    # File permission for status.json (rw-r--r--)
    STATUS_FILE_PERMISSION = 0o644

    def __init__(self, project_path: Path):
        """Initialize StatusSynchronizer.

        Args:
            project_path: Path to the evolution project directory.
                         Must contain (or will contain) status.json.
        """
        self.project_path = Path(project_path)
        self.status_file = self.project_path / "status.json"
        self._status_data: dict = self._load_status()

    def _load_status(self) -> dict:
        """Load status from disk.

        Returns:
            Status dictionary. If file doesn't exist, returns default status.
        """
        if self.status_file.exists():
            try:
                return json.loads(self.status_file.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load status.json: {e}, using defaults")
                return self._default_status()
        return self._default_status()

    def _default_status(self) -> dict:
        """Create default status structure.

        Returns:
            Default status dictionary for a new project.
        """
        return {
            "status": "pending",
            "current_phase": None,
            "phases": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error": None
        }

    def _save_status(self) -> None:
        """Save status to disk with atomic write.

        Uses temp file + rename pattern for crash safety:
        1. Write to status.json.tmp
        2. Rename to status.json (atomic on POSIX)
        3. Normalize permissions to 0644

        Raises:
            IOError: If write or rename fails
        """
        self._status_data["updated_at"] = datetime.now().isoformat()

        # Ensure project directory exists
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp, then rename
        temp_file = self.status_file.with_suffix(".json.tmp")
        try:
            temp_file.write_text(json.dumps(self._status_data, indent=2))
            temp_file.rename(self.status_file)

            # Normalize permissions (Fix 2 integration)
            try:
                self.status_file.chmod(self.STATUS_FILE_PERMISSION)
            except OSError as e:
                logger.warning(f"Failed to set permissions on status.json: {e}")

            logger.debug(f"Status saved: {self._status_data['status']}")
        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise IOError(f"Failed to save status: {e}") from e

    def initialize_phases(self, phase_ids: list[str]) -> None:
        """Initialize all phases as pending.

        Call this at the start of pipeline execution to set up the phases dict.

        Args:
            phase_ids: List of phase IDs to initialize
        """
        for phase_id in phase_ids:
            if phase_id not in self._status_data["phases"]:
                self._status_data["phases"][phase_id] = {
                    "status": "pending"
                }
        self._save_status()
        logger.info(f"Initialized {len(phase_ids)} phases")

    def start_phase(self, phase_id: str) -> None:
        """Mark phase as running.

        Updates both project status to 'developing' and phase status to 'running'.

        Args:
            phase_id: ID of the phase to start
        """
        self._status_data["status"] = "developing"
        self._status_data["current_phase"] = phase_id
        self._status_data["phases"][phase_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat()
        }
        self._save_status()
        logger.info(f"Phase started: {phase_id}")

    def complete_phase(self, phase_id: str) -> None:
        """Mark phase as completed.

        Updates phase status to 'completed' and clears current_phase.
        Project status remains 'developing' until mark_ready() is called.

        Args:
            phase_id: ID of the phase that completed
        """
        if phase_id in self._status_data["phases"]:
            phase_data = self._status_data["phases"][phase_id]
            phase_data["status"] = "completed"
            phase_data["completed_at"] = datetime.now().isoformat()
        else:
            # Phase wasn't initialized, create it as completed
            self._status_data["phases"][phase_id] = {
                "status": "completed",
                "completed_at": datetime.now().isoformat()
            }
        self._status_data["current_phase"] = None
        self._save_status()
        logger.info(f"Phase completed: {phase_id}")

    def fail_phase(self, phase_id: str, error: str) -> None:
        """Mark phase as failed.

        Updates phase status to 'failed', sets error message, and marks
        the entire project as failed.

        Args:
            phase_id: ID of the phase that failed
            error: Error message describing the failure
        """
        if phase_id in self._status_data["phases"]:
            phase_data = self._status_data["phases"][phase_id]
            phase_data["status"] = "failed"
            phase_data["error"] = error
            phase_data["completed_at"] = datetime.now().isoformat()
        else:
            self._status_data["phases"][phase_id] = {
                "status": "failed",
                "error": error,
                "completed_at": datetime.now().isoformat()
            }
        self._status_data["current_phase"] = None
        self._status_data["status"] = "failed"
        self._status_data["error"] = error
        self._save_status()
        logger.error(f"Phase failed: {phase_id} - {error}")

    def mark_ready(self) -> None:
        """Mark project as ready for validation/integration.

        Call this after all phases have completed successfully.
        """
        self._status_data["status"] = "ready"
        self._status_data["current_phase"] = None
        self._status_data["error"] = None
        self._save_status()
        logger.info("Project marked as ready")

    def mark_integrated(self) -> None:
        """Mark project as successfully integrated.

        Call this after successful validation and integration.
        """
        self._status_data["status"] = "integrated"
        self._status_data["current_phase"] = None
        self._status_data["error"] = None
        self._save_status()
        logger.info("Project marked as integrated")

    def get_status(self) -> dict:
        """Get current status (always reads from disk for consistency).

        Reloads status.json to get the latest state, ensuring consistency
        even if another process has modified the file.

        Returns:
            Current status dictionary
        """
        self._status_data = self._load_status()
        return self._status_data.copy()

    def get_phase_status(self, phase_id: str) -> Optional[PhaseStatus]:
        """Get status for a specific phase.

        Args:
            phase_id: ID of the phase

        Returns:
            PhaseStatus object or None if phase not found
        """
        phases = self._status_data.get("phases", {})
        if phase_id not in phases:
            return None
        return PhaseStatus.from_dict(phase_id, phases[phase_id])

    def get_progress(self) -> dict:
        """Get progress information for polling.

        Returns:
            Dictionary with:
                - total: Total number of phases
                - completed: Number of completed phases
                - failed: Number of failed phases
                - pending: Number of pending phases
                - running: Number of running phases
                - percentage: Completion percentage (0-100)
        """
        phases = self._status_data.get("phases", {})
        total = len(phases)

        if total == 0:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "running": 0,
                "percentage": 0
            }

        status_counts = {
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "running": 0
        }

        for phase_data in phases.values():
            status = phase_data.get("status", "pending")
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["pending"] += 1

        # Calculate percentage (completed + failed = done)
        done = status_counts["completed"] + status_counts["failed"]
        percentage = int((done / total) * 100)

        return {
            "total": total,
            "completed": status_counts["completed"],
            "failed": status_counts["failed"],
            "pending": status_counts["pending"],
            "running": status_counts["running"],
            "percentage": percentage
        }

    def reset(self) -> None:
        """Reset all phases to pending state.

        Useful for retrying a failed pipeline from the beginning.
        """
        for phase_id in self._status_data.get("phases", {}):
            self._status_data["phases"][phase_id] = {"status": "pending"}

        self._status_data["status"] = "pending"
        self._status_data["current_phase"] = None
        self._status_data["error"] = None
        self._save_status()
        logger.info("Status reset to pending")
