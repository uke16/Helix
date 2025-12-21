import pytest
from pathlib import Path
import json

from helix.observability.logger import HelixLogger, LogLevel, LogEntry


class TestHelixLogger:
    """Tests for HelixLogger."""

    def test_log_creates_entry(self, temp_dir):
        """Should create log entry."""
        logger = HelixLogger(temp_dir)
        logger.log(LogLevel.INFO, "Test message", phase="01-test")

        entries = logger.get_phase_logs("01-test")
        assert len(entries) >= 1
        assert entries[-1].message == "Test message"

    def test_log_file_change(self, temp_dir):
        """Should log file changes."""
        logger = HelixLogger(temp_dir)
        logger.log_file_change("01-test", temp_dir / "new.py", "created")

        entries = logger.get_phase_logs("01-test")
        assert any("new.py" in str(e.details) for e in entries)

    def test_log_phase_timing(self, temp_dir):
        """Should log phase start and end."""
        logger = HelixLogger(temp_dir)
        logger.log_phase_start("01-test")
        logger.log_phase_end("01-test", success=True, duration_seconds=5.0)

        entries = logger.get_phase_logs("01-test")
        assert any("start" in e.message.lower() for e in entries)
        assert any("end" in e.message.lower() or "complete" in e.message.lower() for e in entries)

    def test_jsonl_format(self, temp_dir):
        """Should write logs as JSONL."""
        logger = HelixLogger(temp_dir)
        logger.log(LogLevel.INFO, "Test", phase="01-test")

        log_file = temp_dir / "logs" / "project.jsonl"
        if log_file.exists():
            line = log_file.read_text().strip().split("\n")[-1]
            data = json.loads(line)
            assert "message" in data
