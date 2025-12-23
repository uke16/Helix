"""Track tool calls with timing, parameters, and results.

This module provides tracking for all tool calls made during a Claude CLI
execution. It records start/end times, parameters, and results for analysis.

Usage:
    tracker = ToolTracker(phase_id="01-foundation")

    # On tool_use event
    tracker.start_tool(tool_use_id, tool_name, tool_input)

    # On tool_result event
    tracker.end_tool(tool_use_id, result)

    # Get summary
    stats = tracker.get_stats()
    print(f"Total calls: {stats['total_calls']}")
    print(f"Most used: {stats['most_used_tool']}")

    # Save to file
    tracker.save_to_file(phase_dir / "logs" / "tool-calls.jsonl")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json
from pathlib import Path


@dataclass
class ToolCall:
    """A tracked tool call with full context.

    Attributes:
        tool_use_id: Unique ID from Claude CLI linking tool_use to tool_result.
        tool_name: Name of the tool (Read, Write, Bash, etc.).
        tool_input: Input parameters passed to the tool.
        started_at: When the tool call was initiated.
        completed_at: When the tool result was received.
        result: The tool result content (may be truncated).
        success: Whether the tool call succeeded.
        duration_ms: Time from start to completion in milliseconds.
    """

    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None = None
    result: str | None = None
    success: bool | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict.

        Returns:
            Dictionary suitable for JSON serialization. Large results
            are truncated to 200 characters for the preview.
        """
        return {
            "tool_use_id": self.tool_use_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result_preview": self.result[:200] if self.result else None,
            "success": self.success,
            "duration_ms": self.duration_ms,
        }

    def is_pending(self) -> bool:
        """Check if this tool call is still pending.

        Returns:
            True if the tool call has not completed yet.
        """
        return self.completed_at is None


class ToolTracker:
    """Track all tool calls for a phase execution.

    This tracker monitors tool calls from start to completion, calculating
    timing metrics and aggregating statistics per tool type.

    Attributes:
        phase_id: The HELIX phase ID being tracked.
        _pending: Dictionary of in-progress tool calls by tool_use_id.
        _completed: List of completed tool calls.

    Example:
        tracker = ToolTracker(phase_id="01-foundation")

        # On tool_use event from stream parser
        tracker.start_tool(
            tool_use_id="tu_123",
            tool_name="Read",
            tool_input={"file_path": "/foo/bar.py"}
        )

        # On tool_result event
        tracker.end_tool(
            tool_use_id="tu_123",
            result="file contents here..."
        )

        # Get statistics
        stats = tracker.get_stats()
        print(f"Total calls: {stats['total_calls']}")
        print(f"Most used: {stats['most_used_tool']}")
    """

    def __init__(self, phase_id: str) -> None:
        """Initialize the tool tracker.

        Args:
            phase_id: The HELIX phase identifier for this tracking session.
        """
        self.phase_id = phase_id
        self._pending: dict[str, ToolCall] = {}  # tool_use_id -> ToolCall
        self._completed: list[ToolCall] = []

    def start_tool(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> ToolCall:
        """Record the start of a tool call.

        Args:
            tool_use_id: Unique ID from Claude CLI.
            tool_name: Name of the tool being called.
            tool_input: Parameters passed to the tool.

        Returns:
            The created ToolCall object.
        """
        call = ToolCall(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            started_at=datetime.now(),
        )
        self._pending[tool_use_id] = call
        return call

    def end_tool(
        self,
        tool_use_id: str,
        result: str | None = None,
        success: bool = True,
    ) -> ToolCall | None:
        """Record the completion of a tool call.

        Args:
            tool_use_id: The unique ID of the tool call to complete.
            result: The result content (may be truncated by caller).
            success: Whether the tool call succeeded.

        Returns:
            The completed ToolCall object, or None if tool_use_id not found.
        """
        if tool_use_id not in self._pending:
            return None

        call = self._pending.pop(tool_use_id)
        call.completed_at = datetime.now()
        call.result = result
        call.success = success
        call.duration_ms = (call.completed_at - call.started_at).total_seconds() * 1000

        self._completed.append(call)
        return call

    def get_pending(self) -> list[ToolCall]:
        """Get all pending (in-progress) tool calls.

        Returns:
            List of ToolCalls that have not completed yet.
        """
        return list(self._pending.values())

    def get_all_calls(self) -> list[ToolCall]:
        """Get all completed tool calls.

        Returns:
            List of completed ToolCall objects in completion order.
        """
        return self._completed.copy()

    def get_calls_by_tool(self, tool_name: str) -> list[ToolCall]:
        """Get all calls for a specific tool.

        Args:
            tool_name: The tool name to filter by.

        Returns:
            List of ToolCalls for the specified tool.
        """
        return [c for c in self._completed if c.tool_name == tool_name]

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about tool usage.

        Returns:
            Dictionary with:
            - phase_id: The phase being tracked
            - total_calls: Total completed tool calls
            - total_duration_ms: Sum of all call durations
            - by_tool: Per-tool breakdown with count, duration, failures
            - most_used_tool: Tool with most calls
            - slowest_tool: Tool with highest average duration
            - pending_calls: Number of calls still in progress
        """
        if not self._completed:
            return {
                "phase_id": self.phase_id,
                "total_calls": 0,
                "total_duration_ms": 0.0,
                "by_tool": {},
                "most_used_tool": None,
                "slowest_tool": None,
                "pending_calls": len(self._pending),
            }

        by_tool: dict[str, dict[str, Any]] = {}

        for call in self._completed:
            name = call.tool_name
            if name not in by_tool:
                by_tool[name] = {
                    "count": 0,
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "failures": 0,
                }

            by_tool[name]["count"] += 1
            if call.duration_ms:
                by_tool[name]["total_duration_ms"] += call.duration_ms
            if call.success is False:
                by_tool[name]["failures"] += 1

        # Calculate averages
        for name in by_tool:
            count = by_tool[name]["count"]
            if count > 0:
                by_tool[name]["avg_duration_ms"] = (
                    by_tool[name]["total_duration_ms"] / count
                )

        # Find most used and slowest
        most_used = max(by_tool.keys(), key=lambda t: by_tool[t]["count"])
        slowest = max(by_tool.keys(), key=lambda t: by_tool[t]["avg_duration_ms"])

        total_duration = sum(
            c.duration_ms for c in self._completed if c.duration_ms is not None
        )

        return {
            "phase_id": self.phase_id,
            "total_calls": len(self._completed),
            "total_duration_ms": total_duration,
            "by_tool": by_tool,
            "most_used_tool": most_used,
            "slowest_tool": slowest,
            "pending_calls": len(self._pending),
        }

    def get_recent(self, n: int = 5) -> list[ToolCall]:
        """Get the n most recent tool calls.

        Args:
            n: Number of recent calls to return.

        Returns:
            List of the n most recent completed ToolCalls.
        """
        return self._completed[-n:]

    def get_failures(self) -> list[ToolCall]:
        """Get all failed tool calls.

        Returns:
            List of ToolCalls where success is False.
        """
        return [c for c in self._completed if c.success is False]

    def save_to_file(self, file_path: Path) -> None:
        """Save all tool calls to JSONL file.

        Each line is a JSON object representing one tool call.

        Args:
            file_path: Path to write the JSONL file.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for call in self._completed:
                f.write(json.dumps(call.to_dict(), ensure_ascii=False) + "\n")

    def save_summary(self, file_path: Path) -> None:
        """Save statistics summary to JSON file.

        Args:
            file_path: Path to write the JSON file.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: Path, phase_id: str | None = None) -> "ToolTracker":
        """Load tool calls from JSONL file.

        Args:
            file_path: Path to the JSONL file.
            phase_id: Phase ID to use. If None, uses filename.

        Returns:
            ToolTracker populated with the loaded tool calls.
        """
        if phase_id is None:
            phase_id = file_path.stem

        tracker = cls(phase_id)

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                data = json.loads(line)
                call = ToolCall(
                    tool_use_id=data["tool_use_id"],
                    tool_name=data["tool_name"],
                    tool_input=data["tool_input"],
                    started_at=datetime.fromisoformat(data["started_at"]),
                    completed_at=(
                        datetime.fromisoformat(data["completed_at"])
                        if data.get("completed_at")
                        else None
                    ),
                    result=data.get("result_preview"),
                    success=data.get("success"),
                    duration_ms=data.get("duration_ms"),
                )
                tracker._completed.append(call)

        return tracker

    def clear(self) -> None:
        """Clear all tracked tool calls."""
        self._pending.clear()
        self._completed.clear()
