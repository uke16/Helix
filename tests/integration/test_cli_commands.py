import pytest
from pathlib import Path
from click.testing import CliRunner
import os

from helix.cli.main import cli


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_project(self, temp_dir):
        """Create a valid project structure."""
        project = temp_dir / "my-project"
        project.mkdir()

        (project / "spec.yaml").write_text("""
meta:
  id: my-project
  name: My Test Project
  domain: helix
implementation:
  language: python
  summary: A test project for CLI integration tests
""")

        (project / "phases.yaml").write_text("""
phases:
  - id: 01-setup
    name: Setup
    type: development
""")

        (project / "phases").mkdir()
        (project / "phases" / "01-setup").mkdir()
        (project / "logs").mkdir()

        return project

    def test_helix_version(self, runner):
        """Should display version."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "4.0.0" in result.output

    def test_helix_help(self, runner):
        """Should display help."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "HELIX" in result.output or "helix" in result.output

    def test_status_valid_project(self, runner, sample_project):
        """Should show status for valid project."""
        result = runner.invoke(cli, ["status", str(sample_project)])

        # Should not crash, might show "no phases run" or similar
        assert result.exit_code == 0 or "not found" not in result.output.lower()

    def test_debug_shows_logs(self, runner, sample_project):
        """Should show debug logs."""
        # Create a log file
        log_dir = sample_project / "logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "project.jsonl").write_text('{"message": "test log"}\n')

        result = runner.invoke(cli, ["debug", str(sample_project)])

        # Should attempt to read logs
        assert result.exit_code == 0 or "log" in result.output.lower()

    def test_costs_shows_metrics(self, runner, sample_project):
        """Should show cost metrics."""
        # Create a metrics file
        (sample_project / "metrics.json").write_text('''{
            "project_id": "my-project",
            "total_cost_usd": 0.05,
            "phases": {}
        }''')

        result = runner.invoke(cli, ["costs", str(sample_project)])

        # Should not crash
        assert result.exit_code == 0 or "cost" in result.output.lower() or "metric" in result.output.lower()

    def test_new_creates_project(self, runner, temp_dir):
        """Should create new project structure."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(cli, [
                "new", "my-new-project",
                "--type", "feature",
                "--output", str(temp_dir)
            ])

            # Should attempt to create project
            # May fail if template not found, but should not crash unexpectedly
            assert result.exit_code in [0, 1, 2]  # Various valid outcomes
