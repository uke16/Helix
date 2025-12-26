"""Integration tests for orchestrator workflow with other modules.

Updated to use UnifiedOrchestrator from helix.api.orchestrator (ADR-022).
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from helix.api.orchestrator import UnifiedOrchestrator
from helix.phase_loader import PhaseLoader
from helix.quality_gates import QualityGateRunner
from helix.observability import HelixLogger, MetricsCollector


class TestOrchestratorWorkflow:
    """Integration tests for UnifiedOrchestrator with other modules."""

    @pytest.fixture
    def project_with_phases(self, tmp_path):
        """Create a complete project structure."""
        project = tmp_path / "test-project"
        project.mkdir()

        # spec.yaml
        (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Integration Project
  domain: helix
implementation:
  language: python
  summary: Integration test project
""")

        # phases.yaml
        (project / "phases.yaml").write_text("""
phases:
  - id: 01-setup
    name: Setup Phase
    type: development
    template: developer/python.md
    quality_gate:
      type: files_exist
      files:
        - setup.py

  - id: 02-implement
    name: Implementation Phase
    type: development
    template: developer/python.md
    quality_gate:
      type: syntax_check
""")

        # Create phase directories
        (project / "phases" / "01-setup").mkdir(parents=True)
        (project / "phases" / "02-implement").mkdir(parents=True)

        return project

    @pytest.mark.asyncio
    async def test_phase_loader_loads_phases(self, project_with_phases):
        """PhaseLoader should load phases from project."""
        # Should not raise
        phases = PhaseLoader().load_phases(project_with_phases)
        assert len(phases) == 2
        assert phases[0].id == "01-setup"
        assert phases[1].id == "02-implement"

    @pytest.mark.asyncio
    async def test_quality_gate_checks_files_exist(self, project_with_phases):
        """QualityGateRunner should check if files exist."""
        gate_runner = QualityGateRunner()
        result = gate_runner.check_files_exist(
            project_with_phases / "phases" / "01-setup",
            expected=["nonexistent.py"]
        )
        assert not result.passed

    @pytest.mark.asyncio
    async def test_orchestrator_with_logging(self, project_with_phases):
        """Orchestrator should integrate with logging."""
        logger = HelixLogger(project_with_phases)
        metrics = MetricsCollector(project_with_phases)

        metrics.start_project("test-project")
        metrics.start_phase("01-setup")

        logger.log_phase_start("01-setup")
        logger.log_phase_end("01-setup", success=True, duration_seconds=1.5)

        phase_metrics = metrics.end_phase(success=True)

        assert phase_metrics.phase_id == "01-setup"

        logs = logger.get_phase_logs("01-setup")
        assert len(logs) >= 2  # start + end
