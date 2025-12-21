import pytest
from click.testing import CliRunner

from helix.cli.main import cli


class TestCLI:
    """Tests for CLI commands."""

    def test_cli_version(self):
        """Should show version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "4.0.0" in result.output

    def test_cli_help(self):
        """Should show help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "HELIX" in result.output

    def test_new_command_help(self):
        """Should show new command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "--help"])

        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_status_missing_project(self):
        """Should error on missing project."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "/nonexistent/path"])

        assert result.exit_code != 0
