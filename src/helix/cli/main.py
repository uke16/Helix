"""HELIX v4 CLI Entry Point.

This module provides the main Click group for the HELIX CLI.
"""

import click

from .commands import run, status, debug, costs, new


@click.group()
@click.version_option(version="4.0.0", prog_name="helix")
def cli() -> None:
    """HELIX v4 - AI Development Orchestration System.

    HELIX orchestrates AI-powered development workflows through phases,
    quality gates, and intelligent escalation.
    """
    pass


# Register all commands
cli.add_command(run)
cli.add_command(status)
cli.add_command(debug)
cli.add_command(costs)
cli.add_command(new)


if __name__ == "__main__":
    cli()
