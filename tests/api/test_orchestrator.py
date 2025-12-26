"""Tests for UnifiedOrchestrator.

Tests the central orchestration logic from helix.api.orchestrator.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from helix.api.orchestrator import (
    UnifiedOrchestrator,
    PhaseEvent,
    ProjectResult,
)
from helix.claude_runner import ClaudeResult
from helix.phase_loader import PhaseConfig
from helix.quality_gates import GateResult
from helix.evolution.verification import VerificationResult
from helix.escalation import EscalationAction, EscalationLevel, ActionType


class TestPhaseEvent:
    """Tests for PhaseEvent dataclass."""

    def test_create_phase_event(self):
        """Test creating a PhaseEvent with minimal data."""
        event = PhaseEvent(
            event_type="phase_start",
            phase_id="01-test",
        )
        assert event.event_type == "phase_start"
        assert event.phase_id == "01-test"
        assert event.data == {}
        assert isinstance(event.timestamp, datetime)

    def test_phase_event_with_data(self):
        """Test creating a PhaseEvent with additional data."""
        event = PhaseEvent(
            event_type="verification_failed",
            phase_id="02-impl",
            data={"missing_files": ["src/main.py"]},
        )
        assert event.event_type == "verification_failed"
        assert event.data["missing_files"] == ["src/main.py"]

    def test_phase_event_to_dict(self):
        """Test PhaseEvent serialization."""
        event = PhaseEvent(
            event_type="phase_complete",
            phase_id="01-test",
            data={"success": True},
        )
        d = event.to_dict()
        assert d["event_type"] == "phase_complete"
        assert d["phase_id"] == "01-test"
        assert d["data"]["success"] is True
        assert "timestamp" in d


class TestProjectResult:
    """Tests for ProjectResult dataclass."""

    def test_create_project_result_success(self):
        """Test creating a successful ProjectResult."""
        result = ProjectResult(
            success=True,
            phases_completed=3,
            phases_total=3,
        )
        assert result.success is True
        assert result.phases_completed == 3
        assert result.phases_total == 3
        assert result.errors == []

    def test_create_project_result_failure(self):
        """Test creating a failed ProjectResult."""
        result = ProjectResult(
            success=False,
            phases_completed=1,
            phases_total=3,
            errors=["Phase 02: Verification failed"],
        )
        assert result.success is False
        assert result.phases_completed == 1
        assert len(result.errors) == 1

    def test_project_result_to_dict(self):
        """Test ProjectResult serialization."""
        result = ProjectResult(
            success=True,
            phases_completed=2,
            phases_total=2,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["phases_completed"] == 2
        assert d["phases_total"] == 2
        assert "started_at" in d


class TestUnifiedOrchestratorInit:
    """Tests for UnifiedOrchestrator initialization."""

    def test_init_default(self):
        """Test creating UnifiedOrchestrator with defaults."""
        orchestrator = UnifiedOrchestrator()
        assert orchestrator.claude_runner is not None
        assert orchestrator.gate_runner is not None
        assert orchestrator.phase_loader is not None
        assert orchestrator.escalation_manager is not None

    def test_init_with_custom_components(self):
        """Test creating UnifiedOrchestrator with custom components."""
        mock_runner = MagicMock()
        mock_gate = MagicMock()
        mock_loader = MagicMock()
        mock_escalation = MagicMock()

        orchestrator = UnifiedOrchestrator(
            claude_runner=mock_runner,
            gate_runner=mock_gate,
            phase_loader=mock_loader,
            escalation_manager=mock_escalation,
        )

        assert orchestrator.claude_runner is mock_runner
        assert orchestrator.gate_runner is mock_gate
        assert orchestrator.phase_loader is mock_loader
        assert orchestrator.escalation_manager is mock_escalation


class TestUnifiedOrchestratorRunProject:
    """Tests for UnifiedOrchestrator.run_project()."""

    @pytest.fixture
    def mock_orchestrator(self, tmp_path):
        """Create an orchestrator with mocked components."""
        orchestrator = UnifiedOrchestrator()

        # Mock phase loader
        orchestrator.phase_loader = MagicMock()
        orchestrator.phase_loader.load_phases.return_value = [
            PhaseConfig(
                id="01-test",
                name="Test Phase",
                type="development",
                output=["output/result.py"],
            ),
        ]

        # Mock claude runner
        orchestrator.claude_runner = MagicMock()
        orchestrator.claude_runner.run_phase_streaming = AsyncMock(
            return_value=ClaudeResult(
                success=True,
                exit_code=0,
                stdout="Done",
                stderr="",
                duration_seconds=10.0,
            )
        )
        orchestrator.claude_runner.run_phase = AsyncMock(
            return_value=ClaudeResult(
                success=True,
                exit_code=0,
                stdout="Done",
                stderr="",
                duration_seconds=10.0,
            )
        )

        # Mock gate runner
        orchestrator.gate_runner = MagicMock()
        orchestrator.gate_runner.run_gate = AsyncMock(
            return_value=GateResult(
                passed=True,
                gate_type="files_exist",
                message="All files exist",
            )
        )

        # Mock escalation manager
        orchestrator.escalation_manager = MagicMock()

        return orchestrator

    @pytest.mark.asyncio
    async def test_run_project_success(self, mock_orchestrator, tmp_path):
        """Test successful project execution."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        # Mock verification to pass
        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True,
                found_files=["output/result.py"],
                message="All files verified",
            )
            MockVerifier.return_value = mock_verifier

            result = await mock_orchestrator.run_project(project_dir)

        assert result.success is True
        assert result.phases_completed == 1
        assert result.phases_total == 1
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_run_project_with_events(self, mock_orchestrator, tmp_path):
        """Test that events are emitted during execution."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        events: list[PhaseEvent] = []

        async def collect_events(event: PhaseEvent):
            events.append(event)

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True,
                found_files=["output/result.py"],
            )
            MockVerifier.return_value = mock_verifier

            await mock_orchestrator.run_project(project_dir, on_event=collect_events)

        # Check that events were collected
        event_types = [e.event_type for e in events]
        assert "project_start" in event_types
        assert "phase_start" in event_types
        assert "project_complete" in event_types

    @pytest.mark.asyncio
    async def test_run_project_verification_failure(self, mock_orchestrator, tmp_path):
        """Test handling of verification failure."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=False,
                missing_files=["output/result.py"],
                message="Missing files",
            )
            mock_verifier.write_retry_file = MagicMock()
            MockVerifier.return_value = mock_verifier

            result = await mock_orchestrator.run_project(project_dir)

        # Should fail after retries
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_run_project_claude_failure(self, mock_orchestrator, tmp_path):
        """Test handling of Claude execution failure."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        # Make Claude fail
        mock_orchestrator.claude_runner.run_phase = AsyncMock(
            return_value=ClaudeResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr="Claude failed",
                duration_seconds=5.0,
            )
        )

        result = await mock_orchestrator.run_project(project_dir)

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_run_project_with_phase_filter(self, mock_orchestrator, tmp_path):
        """Test running only specific phases."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)
        (project_dir / "phases" / "02-impl").mkdir(parents=True)

        # Add second phase
        mock_orchestrator.phase_loader.load_phases.return_value = [
            PhaseConfig(id="01-test", name="Test", type="development"),
            PhaseConfig(id="02-impl", name="Impl", type="development"),
        ]

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True,
                found_files=[],
            )
            MockVerifier.return_value = mock_verifier

            result = await mock_orchestrator.run_project(
                project_dir, phase_filter=["01-test"]
            )

        assert result.success is True
        assert result.phases_total == 1  # Only filtered phase

    @pytest.mark.asyncio
    async def test_run_project_missing_phases_file(self, mock_orchestrator, tmp_path):
        """Test error handling when phases.yaml is missing."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        mock_orchestrator.phase_loader.load_phases.side_effect = FileNotFoundError(
            "phases.yaml not found"
        )

        result = await mock_orchestrator.run_project(project_dir)

        assert result.success is False
        assert "Failed to load phases" in result.errors[0]


class TestUnifiedOrchestratorQualityGates:
    """Tests for quality gate handling."""

    @pytest.fixture
    def orchestrator_with_gate(self, tmp_path):
        """Create orchestrator with gate configuration."""
        orchestrator = UnifiedOrchestrator()

        orchestrator.phase_loader = MagicMock()
        orchestrator.phase_loader.load_phases.return_value = [
            PhaseConfig(
                id="01-test",
                name="Test Phase",
                type="development",
                quality_gate={"type": "files_exist", "files": ["output/test.py"]},
            ),
        ]

        orchestrator.claude_runner = MagicMock()
        orchestrator.claude_runner.run_phase = AsyncMock(
            return_value=ClaudeResult(
                success=True, exit_code=0, stdout="", stderr=""
            )
        )
        orchestrator.claude_runner.run_phase_streaming = AsyncMock(
            return_value=ClaudeResult(
                success=True, exit_code=0, stdout="", stderr=""
            )
        )

        orchestrator.gate_runner = MagicMock()
        orchestrator.escalation_manager = MagicMock()

        return orchestrator

    @pytest.mark.asyncio
    async def test_quality_gate_pass(self, orchestrator_with_gate, tmp_path):
        """Test that passing gates allow phase completion."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        orchestrator_with_gate.gate_runner.run_gate = AsyncMock(
            return_value=GateResult(
                passed=True,
                gate_type="files_exist",
                message="All files exist",
            )
        )

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True, found_files=[]
            )
            MockVerifier.return_value = mock_verifier

            events: list[PhaseEvent] = []
            async def collect(e: PhaseEvent):
                events.append(e)

            result = await orchestrator_with_gate.run_project(
                project_dir, on_event=collect
            )

        assert result.success is True
        assert any(e.event_type == "gate_passed" for e in events)

    @pytest.mark.asyncio
    async def test_quality_gate_fail_with_escalation(
        self, orchestrator_with_gate, tmp_path
    ):
        """Test that failing gates trigger escalation."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        orchestrator_with_gate.gate_runner.run_gate = AsyncMock(
            return_value=GateResult(
                passed=False,
                gate_type="files_exist",
                message="Missing files",
            )
        )

        # Escalation requires human
        orchestrator_with_gate.escalation_manager.handle_gate_failure = AsyncMock(
            return_value=EscalationAction(
                action_type=ActionType.HUMAN_REVIEW,
                level=EscalationLevel.STUFE_2,
                message="Human review required",
                requires_human=True,
            )
        )

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True, found_files=[]
            )
            MockVerifier.return_value = mock_verifier

            events: list[PhaseEvent] = []
            async def collect(e: PhaseEvent):
                events.append(e)

            result = await orchestrator_with_gate.run_project(
                project_dir, on_event=collect
            )

        assert result.success is False
        assert any(e.event_type == "gate_failed" for e in events)
        assert any(e.event_type == "escalation" for e in events)


class TestUnifiedOrchestratorStreaming:
    """Tests for streaming execution."""

    @pytest.mark.asyncio
    async def test_run_project_streaming_yields_events(self, tmp_path):
        """Test that streaming execution yields events."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "phases" / "01-test").mkdir(parents=True)

        orchestrator = UnifiedOrchestrator()
        orchestrator.phase_loader = MagicMock()
        orchestrator.phase_loader.load_phases.return_value = [
            PhaseConfig(id="01-test", name="Test", type="development"),
        ]

        orchestrator.claude_runner = MagicMock()
        orchestrator.claude_runner.run_phase_streaming = AsyncMock(
            return_value=ClaudeResult(
                success=True, exit_code=0, stdout="", stderr=""
            )
        )

        with patch("helix.api.orchestrator.PhaseVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_verifier.verify_phase_output.return_value = VerificationResult(
                success=True, found_files=[]
            )
            MockVerifier.return_value = mock_verifier

            events = []
            async for event in orchestrator.run_project_streaming(project_dir):
                events.append(event)

        assert len(events) > 0
        assert any(e.event_type == "project_start" for e in events)
        assert any(e.event_type == "project_result" for e in events)


class TestExpectedFilesExtraction:
    """Tests for _get_expected_files helper."""

    def test_get_expected_files_from_list(self):
        """Test extracting files from list output."""
        orchestrator = UnifiedOrchestrator()
        phase = PhaseConfig(
            id="01",
            name="Test",
            type="development",
            output=["src/main.py", "tests/test_main.py"],
        )
        files = orchestrator._get_expected_files(phase)
        assert files == ["src/main.py", "tests/test_main.py"]

    def test_get_expected_files_from_dict(self):
        """Test extracting files from dict output."""
        orchestrator = UnifiedOrchestrator()
        phase = PhaseConfig(
            id="01",
            name="Test",
            type="development",
            output={"files": ["output/result.json"]},
        )
        files = orchestrator._get_expected_files(phase)
        assert files == ["output/result.json"]

    def test_get_expected_files_empty(self):
        """Test handling empty output."""
        orchestrator = UnifiedOrchestrator()
        phase = PhaseConfig(id="01", name="Test", type="development")
        files = orchestrator._get_expected_files(phase)
        assert files == []
