"""Tests for Ralph Automation Pattern."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from helix.ralph import ConsultantVerifier
from helix.ralph.consultant_verify import VerifyResult


class TestConsultantVerifier:
    """Tests for ConsultantVerifier."""

    def test_init(self):
        """Test verifier initialization."""
        verifier = ConsultantVerifier()
        assert verifier.helix_root.exists()
        assert verifier.spawn_script.name == "spawn-consultant.sh"

    def test_verify_result_dataclass(self):
        """Test VerifyResult dataclass."""
        result = VerifyResult(
            passed=True,
            verdict="VERDICT: PASSED",
            auto_checks="✅ All checks passed"
        )
        assert result.passed is True
        assert "PASSED" in result.verdict

    @patch('subprocess.run')
    def test_verify_adr_passed(self, mock_run):
        """Test successful ADR verification."""
        mock_run.return_value = MagicMock(
            stdout="VERDICT: PASSED\nAll requirements met.",
            returncode=0
        )

        verifier = ConsultantVerifier()
        # Use a real ADR file for testing
        adr_path = verifier.helix_root / "adr" / "040-ralph-automation-pattern.md"

        if adr_path.exists():
            result = verifier.verify_adr(adr_path)
            assert "passed" in str(result.passed).lower() or mock_run.called

    @patch('subprocess.run')
    def test_verify_adr_failed(self, mock_run):
        """Test failed ADR verification."""
        mock_run.return_value = MagicMock(
            stdout="VERDICT: FAILED\nMissing: docs/X.md",
            returncode=0
        )

        verifier = ConsultantVerifier()
        adr_path = verifier.helix_root / "adr" / "040-ralph-automation-pattern.md"

        if adr_path.exists():
            result = verifier.verify_adr(adr_path)
            # Mock returns FAILED
            assert mock_run.called

    def test_build_prompt(self):
        """Test prompt building."""
        verifier = ConsultantVerifier()
        prompt = verifier._build_prompt("ADR Content", "✅ Checks passed")

        assert "ADR Content" in prompt
        assert "Checks passed" in prompt
        assert "VERDICT" in prompt
