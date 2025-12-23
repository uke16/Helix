"""HELIX v4 Phase Orchestrator Package.

This package provides automatic project execution with:
- Phase orchestration and sequencing
- Data flow between phases
- Status tracking with resume capability
- Quality gate integration

Usage:
    from helix.orchestrator import OrchestratorRunner, RunConfig

    runner = OrchestratorRunner()
    config = RunConfig(
        project_dir=Path("projects/external/my-feature"),
        resume=False,
    )
    result = await runner.run("my-feature", config)
"""

from .status import StatusTracker, ProjectStatus, PhaseStatus
from .runner import OrchestratorRunner, RunConfig
from .phase_executor import PhaseExecutor, PhaseResult
from .data_flow import DataFlowManager

__all__ = [
    # Core classes
    "OrchestratorRunner",
    "RunConfig",
    # Status tracking
    "StatusTracker",
    "ProjectStatus",
    "PhaseStatus",
    # Phase execution
    "PhaseExecutor",
    "PhaseResult",
    # Data flow
    "DataFlowManager",
]
