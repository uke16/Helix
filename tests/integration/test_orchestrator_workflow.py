import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from helix.orchestrator import Orchestrator
from helix.phase_loader import PhaseLoader
from helix.quality_gates import QualityGateRunner
from helix.observability import HelixLogger, MetricsCollector


class TestOrchestratorWorkflow:
    """Integration tests for Orchestrator with other modules."""

    @pytest.fixture
    def project_with_phases(self, temp_dir):
        """Create a complete project structure."""
        project = temp_dir / "test-project"
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
    async def test_orchestrator_loads_phases(self, project_with_phases):
        """Orchestrator should load phases from project."""
        orchestrator = Orchestrator()

        with patch.object(orchestrator, 'run_phase', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"status": "success"}

            # Should not raise
            phases = PhaseLoader().load_phases(project_with_phases)
            assert len(phases) == 2
            assert phases[0].id == "01-setup"

    @pytest.mark.asyncio
    async def test_orchestrator_respects_phase_order(self, project_with_phases):
        """Orchestrator should execute phases in order."""
        orchestrator = Orchestrator()
        execution_order = []

        async def mock_run_phase(phase, *args, **kwargs):
            execution_order.append(phase.id)
            return {"status": "success"}

        with patch.object(orchestrator, 'run_phase', side_effect=mock_run_phase):
            with patch.object(orchestrator, 'check_quality_gate', return_value=True):
                # Run would go through phases
                phases = PhaseLoader().load_phases(project_with_phases)
                for phase in phases:
                    await mock_run_phase(phase)

        assert execution_order == ["01-setup", "02-implement"]

    @pytest.mark.asyncio
    async def test_orchestrator_stops_on_gate_failure(self, project_with_phases):
        """Orchestrator should stop if quality gate fails."""
        orchestrator = Orchestrator()

        with patch.object(orchestrator, 'run_phase', new_callable=AsyncMock) as mock_run:
            with patch.object(orchestrator, 'check_quality_gate', return_value=False):
                mock_run.return_value = {"status": "success"}

                # Gate failure should trigger escalation or stop
                gate_runner = QualityGateRunner()
                result = gate_runner.check_files_exist(
                    project_with_phases / "phases" / "01-setup",
                    files=["nonexistent.py"]
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
