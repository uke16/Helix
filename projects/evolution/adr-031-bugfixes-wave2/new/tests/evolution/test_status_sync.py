"""Tests for StatusSynchronizer.

ADR-031: Fix 1 - Status Synchronization Tests

These tests verify that the StatusSynchronizer correctly:
1. Persists phase status to status.json on each update
2. Uses atomic writes for crash safety
3. Tracks phase progress correctly
4. Handles edge cases like missing files and corrupted data
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from helix.evolution.status_sync import (
    StatusSynchronizer,
    PhaseStatus,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test-project"
        project_path.mkdir()
        yield project_path


@pytest.fixture
def sync(temp_project):
    """Create a StatusSynchronizer with temp project."""
    return StatusSynchronizer(temp_project)


class TestPhaseStatus:
    """Tests for PhaseStatus dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        status = PhaseStatus(
            phase_id="test-phase",
            status="running",
            started_at=datetime(2025, 1, 1, 12, 0, 0),
            completed_at=None,
            error=None
        )

        data = status.to_dict()

        assert data["status"] == "running"
        assert data["started_at"] == "2025-01-01T12:00:00"
        assert data["completed_at"] is None
        assert data["error"] is None

    def test_to_dict_with_error(self):
        """Test conversion with error."""
        status = PhaseStatus(
            phase_id="failed-phase",
            status="failed",
            started_at=datetime(2025, 1, 1, 12, 0, 0),
            completed_at=datetime(2025, 1, 1, 12, 5, 0),
            error="Something went wrong"
        )

        data = status.to_dict()

        assert data["status"] == "failed"
        assert data["error"] == "Something went wrong"
        assert data["completed_at"] == "2025-01-01T12:05:00"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "status": "completed",
            "started_at": "2025-01-01T12:00:00",
            "completed_at": "2025-01-01T12:10:00"
        }

        status = PhaseStatus.from_dict("my-phase", data)

        assert status.phase_id == "my-phase"
        assert status.status == "completed"
        assert status.started_at == datetime(2025, 1, 1, 12, 0, 0)
        assert status.completed_at == datetime(2025, 1, 1, 12, 10, 0)

    def test_from_dict_with_invalid_dates(self):
        """Test that invalid dates are handled gracefully."""
        data = {
            "status": "running",
            "started_at": "invalid-date",
            "completed_at": None
        }

        status = PhaseStatus.from_dict("test", data)

        assert status.status == "running"
        assert status.started_at is None  # Invalid date becomes None

    def test_from_dict_minimal(self):
        """Test creation from minimal dictionary."""
        data = {"status": "pending"}

        status = PhaseStatus.from_dict("test", data)

        assert status.phase_id == "test"
        assert status.status == "pending"
        assert status.started_at is None
        assert status.completed_at is None
        assert status.error is None


class TestStatusSynchronizer:
    """Tests for StatusSynchronizer class."""

    def test_init_creates_default_status(self, temp_project):
        """Test that initialization creates default status if none exists."""
        sync = StatusSynchronizer(temp_project)

        status = sync.get_status()

        assert status["status"] == "pending"
        assert status["current_phase"] is None
        assert status["phases"] == {}
        assert "created_at" in status
        assert "updated_at" in status

    def test_init_loads_existing_status(self, temp_project):
        """Test that initialization loads existing status.json."""
        # Create existing status file
        status_file = temp_project / "status.json"
        existing_status = {
            "status": "developing",
            "current_phase": "phase-1",
            "phases": {"phase-1": {"status": "running"}},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }
        status_file.write_text(json.dumps(existing_status))

        sync = StatusSynchronizer(temp_project)
        status = sync.get_status()

        assert status["status"] == "developing"
        assert status["current_phase"] == "phase-1"
        assert status["phases"]["phase-1"]["status"] == "running"

    def test_init_handles_corrupted_status(self, temp_project):
        """Test that corrupted status.json is handled gracefully."""
        status_file = temp_project / "status.json"
        status_file.write_text("{ invalid json }")

        sync = StatusSynchronizer(temp_project)
        status = sync.get_status()

        # Should fall back to defaults
        assert status["status"] == "pending"
        assert status["phases"] == {}

    def test_start_phase(self, sync, temp_project):
        """Test starting a phase."""
        sync.start_phase("phase-1")

        # Verify in-memory state
        status = sync.get_status()
        assert status["status"] == "developing"
        assert status["current_phase"] == "phase-1"
        assert status["phases"]["phase-1"]["status"] == "running"
        assert "started_at" in status["phases"]["phase-1"]

        # Verify persisted to disk
        disk_status = json.loads((temp_project / "status.json").read_text())
        assert disk_status["phases"]["phase-1"]["status"] == "running"

    def test_complete_phase(self, sync, temp_project):
        """Test completing a phase."""
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")

        status = sync.get_status()
        assert status["current_phase"] is None
        assert status["phases"]["phase-1"]["status"] == "completed"
        assert "completed_at" in status["phases"]["phase-1"]

        # Verify persisted
        disk_status = json.loads((temp_project / "status.json").read_text())
        assert disk_status["phases"]["phase-1"]["status"] == "completed"

    def test_complete_uninitialized_phase(self, sync):
        """Test completing a phase that wasn't started."""
        sync.complete_phase("unknown-phase")

        status = sync.get_status()
        assert status["phases"]["unknown-phase"]["status"] == "completed"

    def test_fail_phase(self, sync, temp_project):
        """Test failing a phase."""
        sync.start_phase("phase-1")
        sync.fail_phase("phase-1", "Syntax error in module.py")

        status = sync.get_status()
        assert status["status"] == "failed"
        assert status["current_phase"] is None
        assert status["error"] == "Syntax error in module.py"
        assert status["phases"]["phase-1"]["status"] == "failed"
        assert status["phases"]["phase-1"]["error"] == "Syntax error in module.py"

        # Verify persisted
        disk_status = json.loads((temp_project / "status.json").read_text())
        assert disk_status["status"] == "failed"
        assert disk_status["phases"]["phase-1"]["status"] == "failed"

    def test_mark_ready(self, sync):
        """Test marking project as ready."""
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")
        sync.mark_ready()

        status = sync.get_status()
        assert status["status"] == "ready"
        assert status["current_phase"] is None
        assert status["error"] is None

    def test_mark_integrated(self, sync):
        """Test marking project as integrated."""
        sync.mark_ready()
        sync.mark_integrated()

        status = sync.get_status()
        assert status["status"] == "integrated"

    def test_initialize_phases(self, sync):
        """Test initializing multiple phases."""
        sync.initialize_phases(["phase-1", "phase-2", "phase-3"])

        status = sync.get_status()
        assert len(status["phases"]) == 3
        assert all(
            status["phases"][p]["status"] == "pending"
            for p in ["phase-1", "phase-2", "phase-3"]
        )

    def test_initialize_phases_preserves_existing(self, sync):
        """Test that initialize_phases doesn't overwrite existing phases."""
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")

        sync.initialize_phases(["phase-1", "phase-2"])

        status = sync.get_status()
        # phase-1 should still be completed
        assert status["phases"]["phase-1"]["status"] == "completed"
        # phase-2 should be pending
        assert status["phases"]["phase-2"]["status"] == "pending"

    def test_get_phase_status(self, sync):
        """Test getting individual phase status."""
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")

        phase_status = sync.get_phase_status("phase-1")

        assert phase_status is not None
        assert phase_status.phase_id == "phase-1"
        assert phase_status.status == "completed"
        assert phase_status.completed_at is not None

    def test_get_phase_status_not_found(self, sync):
        """Test getting status for non-existent phase."""
        phase_status = sync.get_phase_status("nonexistent")
        assert phase_status is None

    def test_get_progress_empty(self, sync):
        """Test progress with no phases."""
        progress = sync.get_progress()

        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["percentage"] == 0

    def test_get_progress(self, sync):
        """Test progress calculation."""
        sync.initialize_phases(["p1", "p2", "p3", "p4"])
        sync.start_phase("p1")
        sync.complete_phase("p1")
        sync.start_phase("p2")
        sync.complete_phase("p2")
        sync.start_phase("p3")

        progress = sync.get_progress()

        assert progress["total"] == 4
        assert progress["completed"] == 2
        assert progress["running"] == 1
        assert progress["pending"] == 1
        assert progress["failed"] == 0
        assert progress["percentage"] == 50

    def test_get_progress_with_failure(self, sync):
        """Test progress calculation with failed phase."""
        sync.initialize_phases(["p1", "p2", "p3", "p4"])
        sync.start_phase("p1")
        sync.complete_phase("p1")
        sync.start_phase("p2")
        sync.fail_phase("p2", "error")

        progress = sync.get_progress()

        assert progress["total"] == 4
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["pending"] == 2
        assert progress["percentage"] == 50  # (1 completed + 1 failed) / 4

    def test_reset(self, sync):
        """Test resetting status."""
        sync.initialize_phases(["p1", "p2"])
        sync.start_phase("p1")
        sync.complete_phase("p1")
        sync.start_phase("p2")
        sync.fail_phase("p2", "error")

        sync.reset()

        status = sync.get_status()
        assert status["status"] == "pending"
        assert status["current_phase"] is None
        assert status["error"] is None
        assert all(
            status["phases"][p]["status"] == "pending"
            for p in ["p1", "p2"]
        )

    def test_atomic_write(self, temp_project):
        """Test that writes are atomic (temp file + rename)."""
        sync = StatusSynchronizer(temp_project)

        # Mock rename to track it was called
        with patch.object(Path, 'rename') as mock_rename:
            # Need to actually call through to make the test work
            mock_rename.side_effect = lambda target: Path.rename(
                temp_project / "status.json.tmp", target
            )
            sync.start_phase("test")

        # Temp file should not exist after successful write
        temp_file = temp_project / "status.json.tmp"
        assert not temp_file.exists()

        # Main file should exist
        assert (temp_project / "status.json").exists()

    def test_file_permissions(self, temp_project):
        """Test that status.json has correct permissions (0644)."""
        sync = StatusSynchronizer(temp_project)
        sync.start_phase("test")

        status_file = temp_project / "status.json"
        mode = status_file.stat().st_mode & 0o777

        assert mode == 0o644

    def test_updates_timestamp(self, sync):
        """Test that updated_at is updated on each save."""
        sync.start_phase("phase-1")
        first_update = sync.get_status()["updated_at"]

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        sync.complete_phase("phase-1")
        second_update = sync.get_status()["updated_at"]

        assert second_update > first_update

    def test_get_status_reloads_from_disk(self, temp_project):
        """Test that get_status() reloads from disk."""
        sync = StatusSynchronizer(temp_project)
        sync.start_phase("phase-1")

        # Modify the file directly (simulating another process)
        status_file = temp_project / "status.json"
        data = json.loads(status_file.read_text())
        data["phases"]["phase-1"]["status"] = "completed"
        status_file.write_text(json.dumps(data))

        # get_status should reload from disk
        status = sync.get_status()
        assert status["phases"]["phase-1"]["status"] == "completed"

    def test_multiple_phases_sequence(self, sync):
        """Test executing multiple phases in sequence."""
        phases = ["init", "build", "test", "deploy"]
        sync.initialize_phases(phases)

        for phase in phases:
            sync.start_phase(phase)
            sync.complete_phase(phase)

        sync.mark_ready()

        status = sync.get_status()
        assert status["status"] == "ready"
        assert all(
            status["phases"][p]["status"] == "completed"
            for p in phases
        )

        progress = sync.get_progress()
        assert progress["percentage"] == 100

    def test_creates_project_directory(self):
        """Test that sync creates project directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "new-project"
            # Don't create the directory

            sync = StatusSynchronizer(project_path)
            sync.start_phase("test")

            assert project_path.exists()
            assert (project_path / "status.json").exists()


class TestIntegration:
    """Integration tests for StatusSynchronizer."""

    def test_restart_recovery(self, temp_project):
        """Test that status is recovered after simulated restart."""
        # First session: start some phases
        sync1 = StatusSynchronizer(temp_project)
        sync1.initialize_phases(["p1", "p2", "p3"])
        sync1.start_phase("p1")
        sync1.complete_phase("p1")
        sync1.start_phase("p2")
        # Simulate crash (don't complete p2)

        # Second session: new sync object
        sync2 = StatusSynchronizer(temp_project)
        status = sync2.get_status()

        # p1 should still be completed
        assert status["phases"]["p1"]["status"] == "completed"
        # p2 should still be running (as it was when we "crashed")
        assert status["phases"]["p2"]["status"] == "running"
        # p3 should still be pending
        assert status["phases"]["p3"]["status"] == "pending"

    def test_pipeline_complete_workflow(self, temp_project):
        """Test complete pipeline workflow."""
        sync = StatusSynchronizer(temp_project)

        # Initialize
        phases = ["analysis", "implementation", "testing"]
        sync.initialize_phases(phases)

        # Execute each phase
        for phase in phases:
            progress_before = sync.get_progress()
            sync.start_phase(phase)

            # Verify phase is running
            assert sync.get_phase_status(phase).status == "running"

            sync.complete_phase(phase)

            # Verify progress increased
            progress_after = sync.get_progress()
            assert progress_after["completed"] > progress_before["completed"]

        # Mark ready
        sync.mark_ready()
        assert sync.get_status()["status"] == "ready"

        # Mark integrated
        sync.mark_integrated()
        assert sync.get_status()["status"] == "integrated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
