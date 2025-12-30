"""Audit logging for hardware station operations.

ADR-032: Phase 1 - Hardware Server

Provides structured audit logging for all station operations including
locking, connections, flashing, and other hardware interactions.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    station: str
    operation: str
    session_id: str
    result: str
    duration_ms: int
    details: Optional[dict] = None


class AuditLogger:
    """Thread-safe audit logger for station operations."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            log_dir: Directory for audit logs (default: ./logs/audit)
        """
        self._lock = threading.Lock()
        self._log_dir = log_dir or Path(__file__).parent / "logs" / "audit"
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Configure Python logging
        self._logger = logging.getLogger("helix.hardware.audit")
        self._logger.setLevel(logging.INFO)

        # Add file handler if not already configured
        if not self._logger.handlers:
            handler = logging.FileHandler(self._log_dir / "audit.log")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(message)s"
            ))
            self._logger.addHandler(handler)

    def log(
        self,
        station: str,
        operation: str,
        session_id: str,
        result: str,
        duration_ms: int,
        details: Optional[dict] = None
    ) -> AuditEntry:
        """Log a station operation.

        Args:
            station: Name of the station
            operation: Operation performed (acquire, release, connect, etc.)
            session_id: Session identifier
            result: Result of operation (success, failure, timeout, etc.)
            duration_ms: Duration in milliseconds
            details: Optional additional details

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            station=station,
            operation=operation,
            session_id=session_id,
            result=result,
            duration_ms=duration_ms,
            details=details
        )

        with self._lock:
            # Log to file
            self._logger.info(json.dumps(asdict(entry)))

            # Also write to daily log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            daily_file = self._log_dir / f"audit-{date_str}.jsonl"
            with open(daily_file, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Get recent audit entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent audit entries (newest first)
        """
        entries = []

        with self._lock:
            # Read from today's log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            daily_file = self._log_dir / f"audit-{date_str}.jsonl"

            if daily_file.exists():
                with open(daily_file, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

        # Return newest first, limited
        return list(reversed(entries[-limit:]))

    def get_station_history(self, station: str, limit: int = 50) -> list[dict]:
        """Get audit history for a specific station.

        Args:
            station: Station name to filter by
            limit: Maximum number of entries

        Returns:
            List of audit entries for the station
        """
        all_entries = self.get_recent(limit=1000)
        station_entries = [e for e in all_entries if e.get("station") == station]
        return station_entries[:limit]


# Global audit logger instance
audit = AuditLogger()
