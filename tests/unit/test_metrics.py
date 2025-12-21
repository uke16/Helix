import pytest

from helix.observability.metrics import MetricsCollector, PhaseMetrics, ProjectMetrics


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_start_project(self, temp_dir):
        """Should start project tracking."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")

        assert collector.current_project is not None
        assert collector.current_project.project_id == "test-project"

    def test_record_tokens(self, temp_dir):
        """Should record token usage."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        collector.record_tokens(input_tokens=100, output_tokens=50, model="gpt-4o")

        assert collector.current_phase.input_tokens == 100
        assert collector.current_phase.output_tokens == 50

    def test_calculate_cost(self, temp_dir):
        """Should calculate costs correctly."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        collector.record_tokens(input_tokens=1000000, output_tokens=500000, model="gpt-4o-mini")

        # gpt-4o-mini: $0.15/1M input, $0.60/1M output
        # Expected: 0.15 + 0.30 = 0.45
        assert collector.current_phase.cost_usd == pytest.approx(0.45, rel=0.1)

    def test_end_phase(self, temp_dir):
        """Should finalize phase metrics."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        metrics = collector.end_phase(success=True)

        assert isinstance(metrics, PhaseMetrics)
        assert metrics.end_time is not None
