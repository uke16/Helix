"""Tests for PhaseExecutor."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from helix.orchestrator.phase_executor import PhaseExecutor, PhaseResult


@pytest.fixture
def temp_phase_dir():
    """Create a temporary phase directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        phase_dir = Path(tmpdir) / "phases" / "test-phase"
        (phase_dir / "input").mkdir(parents=True)
        (phase_dir / "output").mkdir(parents=True)
        (phase_dir / "CLAUDE.md").write_text("# Test Phase\n\nTest instructions.")
        yield phase_dir


@pytest.fixture
def mock_phase_config():
    """Create a mock phase configuration."""
    config = MagicMock()
    config.id = "test-phase"
    config.type = "development"
    config.config = {}
    config.quality_gate = {}
    return config


@pytest.fixture
def mock_claude_runner():
    """Create a mock Claude runner."""
    runner = MagicMock()

    async def mock_run_phase(*args, **kwargs):
        result = MagicMock()
        result.success = True
        result.exit_code = 0
        result.stdout = "Phase executed successfully"
        result.stderr = ""
        return result

    runner.run_phase = AsyncMock(side_effect=mock_run_phase)
    runner.run_phase_streaming = AsyncMock(side_effect=mock_run_phase)
    return runner


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""

    def test_creation(self):
        """Test PhaseResult creation."""
        result = PhaseResult(
            phase_id="test",
            success=True,
            started_at=datetime.now(),
        )

        assert result.phase_id == "test"
        assert result.success is True
        assert result.completed_at is None
        assert result.error is None
        assert result.has_plan is False

    def test_with_all_fields(self):
        """Test PhaseResult with all fields."""
        now = datetime.now()
        result = PhaseResult(
            phase_id="test",
            success=False,
            started_at=now,
            completed_at=now,
            duration_seconds=10.5,
            error="Test error",
            has_plan=True,
            plan_path=Path("/tmp/plan.yaml"),
            retries=2,
        )

        assert result.duration_seconds == 10.5
        assert result.error == "Test error"
        assert result.has_plan is True
        assert result.retries == 2


class TestPhaseExecutor:
    """Tests for PhaseExecutor."""

    def test_initialization(self):
        """Test executor initialization."""
        executor = PhaseExecutor()
        assert executor.DEFAULT_TIMEOUT == 600

    def test_initialization_with_runner(self, mock_claude_runner):
        """Test executor initialization with custom runner."""
        executor = PhaseExecutor(claude_runner=mock_claude_runner)
        assert executor.claude_runner == mock_claude_runner

    @pytest.mark.asyncio
    async def test_execute_dry_run(self, temp_phase_dir, mock_phase_config):
        """Test execution in dry run mode."""
        executor = PhaseExecutor()

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
            dry_run=True,
        )

        assert result.success is True
        assert result.phase_id == "test-phase"
        assert result.completed_at is not None
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_execute_with_runner(
        self, temp_phase_dir, mock_phase_config, mock_claude_runner
    ):
        """Test execution with Claude runner."""
        executor = PhaseExecutor(claude_runner=mock_claude_runner)

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
        )

        assert result.success is True
        mock_claude_runner.run_phase.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_failure(self, temp_phase_dir, mock_phase_config):
        """Test execution failure handling."""
        runner = MagicMock()

        async def mock_fail(*args, **kwargs):
            result = MagicMock()
            result.success = False
            result.stderr = "Execution failed"
            return result

        runner.run_phase = AsyncMock(side_effect=mock_fail)

        executor = PhaseExecutor(claude_runner=runner)

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
        )

        assert result.success is False
        assert result.error == "Execution failed"

    @pytest.mark.asyncio
    async def test_execute_timeout(self, temp_phase_dir, mock_phase_config):
        """Test timeout handling."""
        runner = MagicMock()

        async def mock_slow(*args, **kwargs):
            await asyncio.sleep(10)  # Will be interrupted
            result = MagicMock()
            result.success = True
            return result

        runner.run_phase = AsyncMock(side_effect=mock_slow)

        executor = PhaseExecutor(claude_runner=runner)

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
            timeout=1,  # 1 second timeout
        )

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_creates_directories(self, mock_phase_config, mock_claude_runner):
        """Test that execution creates required directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            phase_dir = Path(tmpdir) / "new-phase"
            # Don't create directories beforehand

            executor = PhaseExecutor(claude_runner=mock_claude_runner)

            result = await executor.execute(
                phase_dir=phase_dir,
                phase_config=mock_phase_config,
            )

            assert result.success is True
            assert (phase_dir / "input").exists()
            assert (phase_dir / "output").exists()

    @pytest.mark.asyncio
    async def test_execute_detects_plan(self, temp_phase_dir, mock_phase_config, mock_claude_runner):
        """Test that plan.yaml is detected."""
        # Create plan.yaml in output
        plan_path = temp_phase_dir / "output" / "plan.yaml"
        plan_path.write_text("decomposed_phases:\n  - id: sub1\n")

        executor = PhaseExecutor(claude_runner=mock_claude_runner)

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
        )

        assert result.success is True
        assert result.has_plan is True
        assert result.plan_path == plan_path

    @pytest.mark.asyncio
    async def test_execute_with_streaming(
        self, temp_phase_dir, mock_phase_config, mock_claude_runner
    ):
        """Test execution with output streaming callback."""
        executor = PhaseExecutor(claude_runner=mock_claude_runner)

        output_lines = []

        async def on_output(stream, line):
            output_lines.append((stream, line))

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=mock_phase_config,
            on_output=on_output,
        )

        assert result.success is True
        mock_claude_runner.run_phase_streaming.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_model(self, temp_phase_dir, mock_claude_runner):
        """Test execution with specific model."""
        config = MagicMock()
        config.id = "test-phase"
        config.type = "development"
        config.config = {"model": "opus"}
        config.quality_gate = {}

        executor = PhaseExecutor(claude_runner=mock_claude_runner)

        result = await executor.execute(
            phase_dir=temp_phase_dir,
            phase_config=config,
        )

        assert result.success is True
        # Verify model was passed
        call_kwargs = mock_claude_runner.run_phase.call_args[1]
        assert call_kwargs.get("model") == "opus"


class TestValidation:
    """Tests for phase validation."""

    @pytest.mark.asyncio
    async def test_validate_phase_setup_valid(self, temp_phase_dir):
        """Test validation of valid phase setup."""
        executor = PhaseExecutor()

        is_valid, error = await executor.validate_phase_setup(temp_phase_dir)

        assert is_valid is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_validate_phase_setup_missing_dir(self):
        """Test validation fails for missing directory."""
        executor = PhaseExecutor()

        is_valid, error = await executor.validate_phase_setup(
            Path("/nonexistent/path")
        )

        assert is_valid is False
        assert "does not exist" in error

    @pytest.mark.asyncio
    async def test_validate_phase_setup_missing_claude_md(self):
        """Test validation fails for missing CLAUDE.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            phase_dir = Path(tmpdir) / "phase"
            phase_dir.mkdir()
            # Don't create CLAUDE.md

            executor = PhaseExecutor()

            is_valid, error = await executor.validate_phase_setup(phase_dir)

            assert is_valid is False
            assert "CLAUDE.md" in error


class TestClaudeAvailability:
    """Tests for Claude CLI availability check."""

    @pytest.mark.asyncio
    async def test_check_availability_no_runner(self):
        """Test availability check when no runner configured."""
        executor = PhaseExecutor()
        executor.claude_runner = None

        available = await executor.check_claude_availability()

        assert available is False

    @pytest.mark.asyncio
    async def test_check_availability_with_runner(self, mock_claude_runner):
        """Test availability check with runner."""
        mock_claude_runner.check_availability = AsyncMock(return_value=True)

        executor = PhaseExecutor(claude_runner=mock_claude_runner)

        available = await executor.check_claude_availability()

        assert available is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
