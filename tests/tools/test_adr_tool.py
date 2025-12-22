"""Tests for ADR tool."""

import pytest
from pathlib import Path
import tempfile
import shutil

from helix.tools.adr_tool import (
    validate_adr,
    finalize_adr,
    get_next_adr_number,
    ADRToolResult,
    HELIX_ROOT,
    ADR_DIR,
)


class TestValidateADR:
    """Test ADR validation."""
    
    def test_validate_existing_adr(self):
        """Test validating an existing ADR."""
        result = validate_adr(ADR_DIR / "011-post-phase-verification.md")
        assert result.success is True
        assert result.adr_id == "011"
        assert "Post-Phase" in result.adr_title
    
    def test_validate_nonexistent_file(self):
        """Test validating a non-existent file."""
        result = validate_adr("/nonexistent/file.md")
        assert result.success is False
        assert "not found" in result.message.lower() or "not exist" in result.message.lower()
    
    def test_validate_invalid_content(self, tmp_path):
        """Test validating invalid ADR content."""
        invalid_file = tmp_path / "invalid.md"
        invalid_file.write_text("# Just a title\nNo YAML frontmatter")
        
        result = validate_adr(invalid_file)
        assert result.success is False
        assert len(result.errors) > 0


class TestFinalizeADR:
    """Test ADR finalization."""
    
    def test_finalize_already_in_place(self):
        """Test finalizing an ADR that's already in adr/."""
        result = finalize_adr(ADR_DIR / "011-post-phase-verification.md")
        # Should succeed since it's already in place
        assert result.success is True
        assert "already" in result.message.lower() or result.final_path is not None


class TestGetNextADRNumber:
    """Test next ADR number detection."""
    
    def test_get_next_number(self):
        """Test getting next ADR number."""
        next_num = get_next_adr_number()
        assert next_num >= 13  # We have ADRs up to 012
        assert isinstance(next_num, int)
