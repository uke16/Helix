"""Tests for Sub-Agent Verification module.

Tests the verification loop, feedback channel, and escalation handling.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

from helix.verification.sub_agent import SubAgentVerifier, VerificationResult
from helix.verification.feedback import FeedbackChannel, EscalationHandler


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_success_result(self):
        """Test creating a successful verification result."""
        result = VerificationResult(
            success=True,
            checks_passed=["File exists", "Syntax valid"],
        )
        assert result.success is True
        assert len(result.checks_passed) == 2
        assert result.errors == []
        assert result.feedback is None

    def test_failure_result(self):
        """Test creating a failed verification result."""
        result = VerificationResult(
            success=False,
            feedback="Please fix the syntax error",
            errors=["Syntax error on line 42"],
        )
        assert result.success is False
        assert result.feedback == "Please fix the syntax error"
        assert len(result.errors) == 1


class TestSubAgentVerifier:
    """Tests for SubAgentVerifier class."""

    def test_init_default_retries(self):
        """Test verifier initializes with default max_retries."""
        verifier = SubAgentVerifier()
        assert verifier.max_retries == 3

    def test_init_custom_retries(self):
        """Test verifier initializes with custom max_retries."""
        verifier = SubAgentVerifier(max_retries=5)
        assert verifier.max_retries == 5

    @pytest.mark.asyncio
    async def test_verify_phase_success(self):
        """Test successful phase verification."""
        verifier = SubAgentVerifier()

        # Mock the runner
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_json = {
            "success": True,
            "errors": [],
            "checks_passed": ["File exists"],
            "feedback": None,
        }
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch.object(verifier.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            result = await verifier.verify_phase(
                phase_output=Path("/tmp/test"),
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True
            assert "File exists" in result.checks_passed

    @pytest.mark.asyncio
    async def test_verify_phase_failure(self):
        """Test failed phase verification."""
        verifier = SubAgentVerifier()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_json = {
            "success": False,
            "errors": ["Missing file: test.py"],
            "checks_passed": [],
            "feedback": "Create test.py file",
        }
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch.object(verifier.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            result = await verifier.verify_phase(
                phase_output=Path("/tmp/test"),
                quality_gate={"type": "syntax_check"},
            )

            assert result.success is False
            assert "Missing file: test.py" in result.errors
            assert result.feedback == "Create test.py file"

    def test_parse_result_with_json_output(self):
        """Test parsing result when output_json is available."""
        verifier = SubAgentVerifier()

        mock_result = MagicMock()
        mock_result.output_json = {
            "success": True,
            "errors": [],
            "checks_passed": ["Check 1"],
            "feedback": None,
        }

        result = verifier._parse_result(mock_result)
        assert result.success is True

    def test_parse_result_from_stdout(self):
        """Test parsing result from stdout JSON block."""
        verifier = SubAgentVerifier()

        mock_result = MagicMock()
        mock_result.output_json = None
        mock_result.stdout = '''Some text
```json
{"success": false, "errors": ["Error 1"], "checks_passed": [], "feedback": "Fix it"}
```
More text'''
        mock_result.success = True
        mock_result.stderr = ""

        result = verifier._parse_result(mock_result)
        assert result.success is False
        assert "Error 1" in result.errors

    def test_parse_result_fallback(self):
        """Test parsing result fallback to exit code."""
        verifier = SubAgentVerifier()

        mock_result = MagicMock()
        mock_result.output_json = None
        mock_result.stdout = "No JSON here"
        mock_result.success = True
        mock_result.stderr = ""

        result = verifier._parse_result(mock_result)
        assert result.success is True
        assert "Verification agent did not return structured output" in result.feedback


class TestFeedbackChannel:
    """Tests for FeedbackChannel class."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_send_feedback(self):
        """Test sending feedback creates file."""
        channel = FeedbackChannel(self.temp_dir)

        success = await channel.send("Fix the error", attempt=1)

        assert success is True
        assert channel.feedback_path.exists()
        content = channel.feedback_path.read_text()
        assert "Attempt**: 1/3" in content
        assert "Fix the error" in content

    @pytest.mark.asyncio
    async def test_send_feedback_with_errors(self):
        """Test sending feedback with error list."""
        channel = FeedbackChannel(self.temp_dir)

        success = await channel.send(
            "Multiple issues found",
            attempt=2,
            errors=["Error 1", "Error 2"],
        )

        assert success is True
        content = channel.feedback_path.read_text()
        assert "Error 1" in content
        assert "Error 2" in content

    def test_clear_feedback(self):
        """Test clearing feedback removes file."""
        channel = FeedbackChannel(self.temp_dir)
        channel.feedback_path.write_text("test")

        assert channel.has_pending_feedback() is True

        channel.clear()

        assert channel.has_pending_feedback() is False
        assert not channel.feedback_path.exists()

    def test_get_attempt_number(self):
        """Test extracting attempt number from feedback."""
        channel = FeedbackChannel(self.temp_dir)
        channel.feedback_path.write_text("**Attempt**: 2/3\n")

        assert channel.get_attempt_number() == 2

    def test_get_attempt_number_no_file(self):
        """Test attempt number when no feedback file."""
        channel = FeedbackChannel(self.temp_dir)

        assert channel.get_attempt_number() == 0


class TestEscalationHandler:
    """Tests for EscalationHandler class."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_escalate(self):
        """Test creating escalation report."""
        handler = EscalationHandler(self.temp_dir)

        success = await handler.escalate(
            phase_id="02-development",
            errors=["Syntax error", "Missing import"],
            attempts=3,
        )

        assert success is True
        assert handler.has_escalation() is True

        content = handler.escalation_path.read_text()
        assert "02-development" in content
        assert "Syntax error" in content
        assert "3" in content

    def test_clear_escalation(self):
        """Test clearing escalation removes file."""
        handler = EscalationHandler(self.temp_dir)
        handler.escalation_path.write_text("test")

        handler.clear_escalation()

        assert handler.has_escalation() is False


class TestVerificationIntegration:
    """Integration tests for the verification system."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_verification_loop_success_first_try(self):
        """Test verification loop succeeds on first try."""
        verifier = SubAgentVerifier(max_retries=3)
        feedback = FeedbackChannel(self.temp_dir)

        # Mock successful verification
        with patch.object(
            verifier, "verify_phase", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = VerificationResult(
                success=True,
                checks_passed=["All checks passed"],
            )

            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir / "output",
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True
            assert attempts == 1
            mock_verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_verification_loop_success_after_retry(self):
        """Test verification loop succeeds after retries."""
        verifier = SubAgentVerifier(max_retries=3)

        # Mock: fail twice, then succeed
        call_count = 0

        async def mock_verify(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return VerificationResult(
                    success=False,
                    feedback="Still failing",
                    errors=["Error"],
                )
            return VerificationResult(success=True)

        with patch.object(verifier, "verify_phase", side_effect=mock_verify):
            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir / "output",
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True
            assert attempts == 3

    @pytest.mark.asyncio
    async def test_verification_loop_exhausted(self):
        """Test verification loop fails after all retries."""
        verifier = SubAgentVerifier(max_retries=3)

        # Mock: always fail
        with patch.object(
            verifier, "verify_phase", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = VerificationResult(
                success=False,
                feedback="Persistent error",
                errors=["Cannot fix this"],
            )

            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir / "output",
                quality_gate={"type": "files_exist"},
            )

            assert result.success is False
            assert attempts == 3
            assert mock_verify.call_count == 3
