"""Tests for tool_tracker module."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from helix.debug.tool_tracker import ToolTracker, ToolCall


@pytest.fixture
def tracker() -> ToolTracker:
    """Create a fresh ToolTracker instance."""
    return ToolTracker(phase_id="test-phase")


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_basic_call(self):
        """Test creating a basic ToolCall."""
        call = ToolCall(
            tool_use_id="tu_123",
            tool_name="Read",
            tool_input={"file_path": "/foo/bar.py"},
            started_at=datetime.now(),
        )
        assert call.tool_use_id == "tu_123"
        assert call.tool_name == "Read"
        assert call.is_pending()

    def test_completed_call(self):
        """Test a completed ToolCall."""
        now = datetime.now()
        call = ToolCall(
            tool_use_id="tu_123",
            tool_name="Read",
            tool_input={},
            started_at=now,
            completed_at=now,
            result="content",
            success=True,
            duration_ms=100.5,
        )
        assert not call.is_pending()
        assert call.success is True
        assert call.duration_ms == 100.5

    def test_to_dict(self):
        """Test converting to dictionary."""
        now = datetime.now()
        call = ToolCall(
            tool_use_id="tu_123",
            tool_name="Read",
            tool_input={"file_path": "/test"},
            started_at=now,
            completed_at=now,
            result="a" * 300,  # Long result
            success=True,
            duration_ms=50.0,
        )

        data = call.to_dict()

        assert data["tool_use_id"] == "tu_123"
        assert data["tool_name"] == "Read"
        assert data["tool_input"] == {"file_path": "/test"}
        assert data["success"] is True
        assert data["duration_ms"] == 50.0
        # Result should be truncated
        assert len(data["result_preview"]) == 200


class TestToolTracker:
    """Tests for ToolTracker class."""

    def test_start_tool(self, tracker: ToolTracker):
        """Test starting a tool call."""
        call = tracker.start_tool(
            tool_use_id="tu_1",
            tool_name="Read",
            tool_input={"file_path": "/test"},
        )

        assert call.tool_use_id == "tu_1"
        assert call.tool_name == "Read"
        assert call.is_pending()

    def test_end_tool(self, tracker: ToolTracker):
        """Test ending a tool call."""
        tracker.start_tool("tu_1", "Read", {})
        call = tracker.end_tool("tu_1", result="content", success=True)

        assert call is not None
        assert call.result == "content"
        assert call.success is True
        assert call.duration_ms is not None
        assert not call.is_pending()

    def test_end_unknown_tool(self, tracker: ToolTracker):
        """Ending unknown tool_use_id should return None."""
        result = tracker.end_tool("unknown_id")
        assert result is None

    def test_get_pending(self, tracker: ToolTracker):
        """Test getting pending calls."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.start_tool("tu_2", "Write", {})

        pending = tracker.get_pending()

        assert len(pending) == 2
        assert any(c.tool_use_id == "tu_1" for c in pending)
        assert any(c.tool_use_id == "tu_2" for c in pending)

    def test_get_all_calls(self, tracker: ToolTracker):
        """Test getting all completed calls."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.start_tool("tu_2", "Write", {})
        tracker.end_tool("tu_1")
        tracker.end_tool("tu_2")

        calls = tracker.get_all_calls()

        assert len(calls) == 2

    def test_get_calls_by_tool(self, tracker: ToolTracker):
        """Test filtering calls by tool name."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.start_tool("tu_2", "Write", {})
        tracker.start_tool("tu_3", "Read", {})
        tracker.end_tool("tu_1")
        tracker.end_tool("tu_2")
        tracker.end_tool("tu_3")

        read_calls = tracker.get_calls_by_tool("Read")

        assert len(read_calls) == 2
        assert all(c.tool_name == "Read" for c in read_calls)

    def test_get_stats_empty(self, tracker: ToolTracker):
        """Test stats with no calls."""
        stats = tracker.get_stats()

        assert stats["phase_id"] == "test-phase"
        assert stats["total_calls"] == 0
        assert stats["total_duration_ms"] == 0.0
        assert stats["by_tool"] == {}
        assert stats["most_used_tool"] is None
        assert stats["slowest_tool"] is None

    def test_get_stats_with_calls(self, tracker: ToolTracker):
        """Test stats with multiple calls."""
        # Simulate multiple Read calls
        for i in range(3):
            tracker.start_tool(f"tu_{i}", "Read", {})
            tracker.end_tool(f"tu_{i}")

        # One Write call
        tracker.start_tool("tu_write", "Write", {})
        tracker.end_tool("tu_write")

        stats = tracker.get_stats()

        assert stats["total_calls"] == 4
        assert stats["by_tool"]["Read"]["count"] == 3
        assert stats["by_tool"]["Write"]["count"] == 1
        assert stats["most_used_tool"] == "Read"

    def test_get_stats_with_failures(self, tracker: ToolTracker):
        """Test stats include failure counts."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.end_tool("tu_1", success=True)

        tracker.start_tool("tu_2", "Read", {})
        tracker.end_tool("tu_2", success=False)

        stats = tracker.get_stats()

        assert stats["by_tool"]["Read"]["failures"] == 1

    def test_get_recent(self, tracker: ToolTracker):
        """Test getting recent calls."""
        for i in range(10):
            tracker.start_tool(f"tu_{i}", f"Tool{i}", {})
            tracker.end_tool(f"tu_{i}")

        recent = tracker.get_recent(3)

        assert len(recent) == 3
        assert recent[0].tool_name == "Tool7"
        assert recent[2].tool_name == "Tool9"

    def test_get_failures(self, tracker: ToolTracker):
        """Test getting failed calls."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.end_tool("tu_1", success=True)

        tracker.start_tool("tu_2", "Write", {})
        tracker.end_tool("tu_2", success=False)

        tracker.start_tool("tu_3", "Bash", {})
        tracker.end_tool("tu_3", success=False)

        failures = tracker.get_failures()

        assert len(failures) == 2
        assert failures[0].tool_name == "Write"
        assert failures[1].tool_name == "Bash"

    def test_save_to_file(self, tracker: ToolTracker):
        """Test saving to JSONL file."""
        tracker.start_tool("tu_1", "Read", {"file": "/test"})
        tracker.end_tool("tu_1", result="content")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "calls.jsonl"
            tracker.save_to_file(file_path)

            assert file_path.exists()

            with open(file_path) as f:
                lines = f.readlines()

            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["tool_name"] == "Read"

    def test_save_summary(self, tracker: ToolTracker):
        """Test saving summary to JSON."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.end_tool("tu_1")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "summary.json"
            tracker.save_summary(file_path)

            assert file_path.exists()

            with open(file_path) as f:
                data = json.load(f)

            assert data["phase_id"] == "test-phase"
            assert data["total_calls"] == 1

    def test_load_from_file(self, tracker: ToolTracker):
        """Test loading from JSONL file."""
        # Save some calls
        tracker.start_tool("tu_1", "Read", {"file": "/test"})
        tracker.end_tool("tu_1", result="content", success=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "calls.jsonl"
            tracker.save_to_file(file_path)

            # Load into new tracker
            loaded = ToolTracker.load_from_file(file_path, phase_id="loaded-phase")

            assert loaded.phase_id == "loaded-phase"
            calls = loaded.get_all_calls()
            assert len(calls) == 1
            assert calls[0].tool_name == "Read"

    def test_clear(self, tracker: ToolTracker):
        """Test clearing all calls."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.start_tool("tu_2", "Write", {})
        tracker.end_tool("tu_1")

        tracker.clear()

        assert tracker.get_pending() == []
        assert tracker.get_all_calls() == []

    def test_pending_count_in_stats(self, tracker: ToolTracker):
        """Test that pending calls are counted in stats."""
        tracker.start_tool("tu_1", "Read", {})
        tracker.start_tool("tu_2", "Write", {})
        tracker.end_tool("tu_1")

        stats = tracker.get_stats()

        assert stats["total_calls"] == 1  # Only completed
        assert stats["pending_calls"] == 1  # One still pending

    def test_duration_calculation(self, tracker: ToolTracker):
        """Test that duration is calculated correctly."""
        import time

        tracker.start_tool("tu_1", "Read", {})
        time.sleep(0.01)  # 10ms
        call = tracker.end_tool("tu_1")

        assert call is not None
        assert call.duration_ms >= 10  # At least 10ms
