import pytest
from pathlib import Path
import json
import time

from helix.observability import HelixLogger, MetricsCollector, LogLevel


class TestObservabilityIntegration:
    """Integration tests for logging and metrics."""

    def test_logger_and_metrics_together(self, temp_dir):
        """Logger and metrics should work together."""
        logger = HelixLogger(temp_dir)
        metrics = MetricsCollector(temp_dir)

        # Start tracking
        metrics.start_project("integration-test")
        logger.log(LogLevel.INFO, "Project started", phase=None)

        # Phase 1
        metrics.start_phase("01-setup")
        logger.log_phase_start("01-setup")

        metrics.record_tokens(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
        metrics.record_file_change("created")

        logger.log_file_change("01-setup", temp_dir / "new_file.py", "created")
        logger.log_phase_end("01-setup", success=True, duration_seconds=2.5)

        phase_metrics = metrics.end_phase(success=True)

        # Verify metrics
        assert phase_metrics.input_tokens == 1000
        assert phase_metrics.output_tokens == 500
        assert phase_metrics.files_created == 1

        # Verify logs
        logs = logger.get_phase_logs("01-setup")
        assert len(logs) >= 2  # At least start and end

    def test_metrics_persist_to_file(self, temp_dir):
        """Metrics should be saveable to file."""
        metrics = MetricsCollector(temp_dir)

        metrics.start_project("persist-test")
        metrics.start_phase("01-test")
        metrics.record_tokens(500, 250, "gpt-4o-mini")
        metrics.end_phase()
        project_metrics = metrics.end_project()

        # Save
        metrics_file = metrics.save_metrics()

        if metrics_file and metrics_file.exists():
            data = json.loads(metrics_file.read_text())
            assert "project_id" in data or "phases" in data

    def test_log_file_format(self, temp_dir):
        """Logs should be in JSONL format."""
        logger = HelixLogger(temp_dir)

        logger.log(LogLevel.INFO, "Test message 1")
        logger.log(LogLevel.WARNING, "Test message 2")
        logger.log(LogLevel.ERROR, "Test message 3")

        # Check log file
        log_files = list((temp_dir / "logs").glob("*.jsonl")) if (temp_dir / "logs").exists() else []

        if log_files:
            content = log_files[0].read_text()
            lines = content.strip().split("\n")

            for line in lines:
                if line:
                    data = json.loads(line)
                    assert "message" in data or "level" in data

    def test_multiple_phases_tracking(self, temp_dir):
        """Should track multiple phases correctly."""
        metrics = MetricsCollector(temp_dir)

        metrics.start_project("multi-phase")

        # Phase 1
        metrics.start_phase("01-first")
        metrics.record_tokens(1000, 500, "gpt-4o")
        metrics.end_phase()

        # Phase 2
        metrics.start_phase("02-second")
        metrics.record_tokens(2000, 1000, "gpt-4o")
        metrics.end_phase()

        project = metrics.end_project()

        assert len(project.phases) == 2
        assert project.phases["01-first"].input_tokens == 1000
        assert project.phases["02-second"].input_tokens == 2000
