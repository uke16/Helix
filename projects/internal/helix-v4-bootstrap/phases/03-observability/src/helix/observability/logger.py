"""
HELIX v4 Observability - Logger Module

3-Ebenen Logging:
- Phase-Logs: Tool-Calls, Dateien, Errors pro Phase
- Projekt-Logs: Aggregiert über alle Phasen
- System-Logs: Globale Events (Startup, Shutdown, Crashes)
"""

from enum import Enum
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import threading
from typing import Any


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    phase: str | None
    message: str
    details: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "phase": self.phase,
            "message": self.message,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """Create LogEntry from dict."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=LogLevel(data["level"]),
            phase=data.get("phase"),
            message=data["message"],
            details=data.get("details"),
        )


class HelixLogger:
    """Thread-safe logger for HELIX v4 with 3-level logging."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self._lock = threading.Lock()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure log directories exist."""
        logs_dir = self.project_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_phase_directories(self, phase: str) -> Path:
        """Ensure phase log directories exist and return the path."""
        phase_logs_dir = self.project_dir / "phases" / phase / "logs"
        phase_logs_dir.mkdir(parents=True, exist_ok=True)
        return phase_logs_dir

    def _write_jsonl(self, file_path: Path, data: dict) -> None:
        """Write a single JSON line to a file (thread-safe)."""
        with self._lock:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _read_jsonl(self, file_path: Path) -> list[dict]:
        """Read all JSON lines from a file."""
        if not file_path.exists():
            return []
        entries = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def log(
        self,
        level: LogLevel,
        message: str,
        phase: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Log a message at the specified level."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            phase=phase,
            message=message,
            details=details,
        )
        entry_dict = entry.to_dict()

        # Always write to project log
        project_log = self.project_dir / "logs" / "project.jsonl"
        self._write_jsonl(project_log, entry_dict)

        # Write to phase log if phase is specified
        if phase:
            phase_logs_dir = self._ensure_phase_directories(phase)
            phase_log = phase_logs_dir / "phase.jsonl"
            self._write_jsonl(phase_log, entry_dict)

    def log_tool_call(
        self, phase: str, tool: str, args: dict, result: str
    ) -> None:
        """Log a tool call."""
        phase_logs_dir = self._ensure_phase_directories(phase)
        tool_calls_log = phase_logs_dir / "tool-calls.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "args": args,
            "result": result,
        }
        self._write_jsonl(tool_calls_log, entry)

        # Also log to phase and project logs
        self.log(
            LogLevel.DEBUG,
            f"Tool call: {tool}",
            phase=phase,
            details={"tool": tool, "args": args},
        )

    def log_file_change(
        self, phase: str, file_path: Path, change_type: str
    ) -> None:
        """Log a file change (created, modified, deleted)."""
        phase_logs_dir = self._ensure_phase_directories(phase)
        files_changed_path = phase_logs_dir / "files-changed.json"

        # Read existing changes
        with self._lock:
            if files_changed_path.exists():
                with open(files_changed_path, "r", encoding="utf-8") as f:
                    changes = json.load(f)
            else:
                changes = {"files": []}

            # Add new change
            changes["files"].append({
                "timestamp": datetime.now().isoformat(),
                "path": str(file_path),
                "change_type": change_type,
            })

            # Write back
            with open(files_changed_path, "w", encoding="utf-8") as f:
                json.dump(changes, f, indent=2, ensure_ascii=False)

        # Also log to phase and project logs
        self.log(
            LogLevel.INFO,
            f"File {change_type}: {file_path}",
            phase=phase,
            details={"file_path": str(file_path), "change_type": change_type},
        )

    def log_phase_start(self, phase: str) -> None:
        """Log the start of a phase."""
        self.log(
            LogLevel.INFO,
            f"Phase started: {phase}",
            phase=phase,
            details={"event": "phase_start"},
        )

    def log_phase_end(
        self, phase: str, success: bool, duration_seconds: float
    ) -> None:
        """Log the end of a phase."""
        status = "success" if success else "failure"
        self.log(
            LogLevel.INFO,
            f"Phase ended: {phase} ({status})",
            phase=phase,
            details={
                "event": "phase_end",
                "success": success,
                "duration_seconds": duration_seconds,
            },
        )

    def log_error(
        self, phase: str, error: Exception, context: dict | None = None
    ) -> None:
        """Log an error with context."""
        details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if context:
            details["context"] = context

        self.log(
            LogLevel.ERROR,
            f"Error in phase {phase}: {error}",
            phase=phase,
            details=details,
        )

    def get_phase_logs(self, phase: str) -> list[LogEntry]:
        """Get all log entries for a specific phase."""
        phase_log = self.project_dir / "phases" / phase / "logs" / "phase.jsonl"
        entries = self._read_jsonl(phase_log)
        return [LogEntry.from_dict(e) for e in entries]

    def get_project_logs(self) -> list[LogEntry]:
        """Get all project log entries."""
        project_log = self.project_dir / "logs" / "project.jsonl"
        entries = self._read_jsonl(project_log)
        return [LogEntry.from_dict(e) for e in entries]

    def write_claude_stdout(self, phase: str, content: str) -> None:
        """Write Claude Code stdout to phase log."""
        phase_logs_dir = self._ensure_phase_directories(phase)
        stdout_log = phase_logs_dir / "claude-stdout.log"
        with self._lock:
            with open(stdout_log, "a", encoding="utf-8") as f:
                f.write(content)

    def write_claude_stderr(self, phase: str, content: str) -> None:
        """Write Claude Code stderr to phase log."""
        phase_logs_dir = self._ensure_phase_directories(phase)
        stderr_log = phase_logs_dir / "claude-stderr.log"
        with self._lock:
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(content)
