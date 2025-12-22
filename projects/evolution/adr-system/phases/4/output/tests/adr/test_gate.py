"""Tests for ADR Quality Gate.

Tests the ADRQualityGate class which integrates ADR validation
with the HELIX quality gate system.

Run with: pytest tests/adr/test_gate.py -v

Note: Import paths are set up in conftest.py
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from helix.adr.gate import ADRQualityGate, register_adr_gate
from helix.adr.parser import ADRParser
from helix.adr.validator import ADRValidator
from helix.quality_gates import GateResult, QualityGateRunner


# Valid ADR content for testing
VALID_ADR_CONTENT = """\
---
adr_id: "001"
title: Test Feature
status: Proposed
component_type: TOOL
classification: NEW
change_scope: minor
files:
  create:
    - src/new_feature.py
  modify:
    - src/existing.py
  docs:
    - docs/feature.md
depends_on:
  - ADR-000
---

# ADR-001: Test Feature

## Status

:yellow_circle: **Proposed** - Under review

## Kontext

This is the context section explaining why we need this change.
It provides background and motivation for the decision.

## Entscheidung

We decide to implement a new feature that does X, Y, and Z.
This is the best approach because of reasons A, B, and C.

## Implementation

### Phase 1: Setup

1. Create the base structure
2. Implement core functionality

### Phase 2: Integration

1. Integrate with existing system
2. Add error handling

## Dokumentation

- docs/feature.md - Main documentation for the feature

## Akzeptanzkriterien

- [ ] Feature is implemented
- [ ] Tests are passing
- [ ] Documentation is updated
- [ ] Code is reviewed

## Konsequenzen

### Vorteile

- Better performance
- Cleaner code

### Nachteile

- Additional complexity

## Referenzen

- ADR-000: Previous decision
- docs/architecture.md
"""

# Invalid ADR: Missing required sections
INVALID_ADR_MISSING_SECTIONS = """\
---
adr_id: "002"
title: Incomplete ADR
status: Proposed
---

# ADR-002: Incomplete ADR

## Status

:yellow_circle: **Proposed**

## Kontext

Some context here.

## Entscheidung

Some decision.
"""

# Invalid ADR: No acceptance criteria
INVALID_ADR_NO_CRITERIA = """\
---
adr_id: "003"
title: No Criteria
status: Proposed
---

# ADR-003: No Criteria

## Status

:yellow_circle: **Proposed**

## Kontext

Context section with enough content here.

## Entscheidung

Decision section with enough content.

## Implementation

Implementation details here.

## Dokumentation

- docs/some-doc.md

## Akzeptanzkriterien

No checkboxes here, just text.

## Konsequenzen

Some consequences.
"""


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_adr_file(temp_dir: Path) -> Path:
    """Create a valid ADR file for testing."""
    adr_path = temp_dir / "adr" / "001-test-feature.md"
    adr_path.parent.mkdir(parents=True, exist_ok=True)
    adr_path.write_text(VALID_ADR_CONTENT, encoding="utf-8")
    return adr_path


@pytest.fixture
def invalid_adr_missing_sections(temp_dir: Path) -> Path:
    """Create an ADR file with missing required sections."""
    adr_path = temp_dir / "adr" / "002-incomplete.md"
    adr_path.parent.mkdir(parents=True, exist_ok=True)
    adr_path.write_text(INVALID_ADR_MISSING_SECTIONS, encoding="utf-8")
    return adr_path


@pytest.fixture
def invalid_adr_no_criteria(temp_dir: Path) -> Path:
    """Create an ADR file with no acceptance criteria checkboxes."""
    adr_path = temp_dir / "adr" / "003-no-criteria.md"
    adr_path.parent.mkdir(parents=True, exist_ok=True)
    adr_path.write_text(INVALID_ADR_NO_CRITERIA, encoding="utf-8")
    return adr_path


@pytest.fixture
def gate() -> ADRQualityGate:
    """Create an ADRQualityGate instance."""
    return ADRQualityGate()


class TestADRQualityGate:
    """Tests for ADRQualityGate class."""

    def test_init_default(self):
        """Test default initialization creates parser and validator."""
        gate = ADRQualityGate()
        assert gate.parser is not None
        assert gate.validator is not None
        assert isinstance(gate.parser, ADRParser)
        assert isinstance(gate.validator, ADRValidator)

    def test_init_custom_parser_validator(self):
        """Test initialization with custom parser and validator."""
        custom_parser = ADRParser()
        custom_validator = ADRValidator()
        gate = ADRQualityGate(parser=custom_parser, validator=custom_validator)
        assert gate.parser is custom_parser
        assert gate.validator is custom_validator

    def test_check_valid_adr_passes(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test that a valid ADR passes the gate."""
        result = gate.check(temp_dir, str(valid_adr_file.relative_to(temp_dir)))

        assert result.passed is True
        assert result.gate_type == "adr_valid"
        assert "passed" in result.message.lower()
        assert result.details["error_count"] == 0
        assert "adr_info" in result.details
        assert result.details["adr_info"]["adr_id"] == "001"
        assert result.details["adr_info"]["title"] == "Test Feature"

    def test_check_valid_adr_absolute_path(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test that absolute paths are handled correctly."""
        result = gate.check(temp_dir, str(valid_adr_file))

        assert result.passed is True
        assert result.gate_type == "adr_valid"

    def test_check_missing_sections_fails(self, gate: ADRQualityGate, invalid_adr_missing_sections: Path, temp_dir: Path):
        """Test that ADR with missing sections fails the gate."""
        result = gate.check(temp_dir, str(invalid_adr_missing_sections.relative_to(temp_dir)))

        assert result.passed is False
        assert result.gate_type == "adr_valid"
        assert "failed" in result.message.lower()
        assert result.details["error_count"] > 0
        assert len(result.details["errors"]) > 0

        # Check that missing sections are reported
        errors_text = " ".join(result.details["errors"])
        assert "Implementation" in errors_text or "Dokumentation" in errors_text

    def test_check_no_criteria_fails(self, gate: ADRQualityGate, invalid_adr_no_criteria: Path, temp_dir: Path):
        """Test that ADR without acceptance criteria checkboxes fails."""
        result = gate.check(temp_dir, str(invalid_adr_no_criteria.relative_to(temp_dir)))

        assert result.passed is False
        assert result.gate_type == "adr_valid"
        assert result.details["error_count"] > 0

        # Check that missing criteria is reported
        errors_text = " ".join(result.details["errors"])
        assert "criteria" in errors_text.lower() or "checkbox" in errors_text.lower()

    def test_check_nonexistent_file_fails(self, gate: ADRQualityGate, temp_dir: Path):
        """Test that nonexistent file causes gate to fail."""
        result = gate.check(temp_dir, "adr/nonexistent.md")

        assert result.passed is False
        assert result.gate_type == "adr_valid"
        assert result.details["error_count"] > 0
        assert "not found" in result.details["errors"][0].lower()

    def test_check_returns_warnings_but_passes(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test that warnings are included but don't cause failure."""
        # The valid ADR has all recommended fields, but let's create one without
        minimal_valid_adr = """\
---
adr_id: "004"
title: Minimal ADR
status: Proposed
---

# ADR-004: Minimal ADR

## Status

Proposed

## Kontext

Context with enough content here to pass validation check.

## Entscheidung

Decision with enough content here to pass validation check.

## Implementation

Implementation steps with enough content here.

## Dokumentation

- docs/minimal.md

## Akzeptanzkriterien

- [ ] First criterion
- [ ] Second criterion
- [ ] Third criterion

## Konsequenzen

Consequences with enough content here.
"""
        minimal_path = temp_dir / "adr" / "004-minimal.md"
        minimal_path.parent.mkdir(parents=True, exist_ok=True)
        minimal_path.write_text(minimal_valid_adr, encoding="utf-8")

        result = gate.check(temp_dir, str(minimal_path.relative_to(temp_dir)))

        # Should pass despite warnings about recommended fields
        assert result.passed is True
        assert result.details["warning_count"] >= 0  # May have warnings

    def test_check_includes_adr_metadata(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test that ADR metadata is included in result details."""
        result = gate.check(temp_dir, str(valid_adr_file.relative_to(temp_dir)))

        assert "adr_info" in result.details
        adr_info = result.details["adr_info"]
        assert adr_info["adr_id"] == "001"
        assert adr_info["title"] == "Test Feature"
        assert adr_info["status"] == "Proposed"


class TestADRQualityGateMultiple:
    """Tests for check_multiple method."""

    def test_check_multiple_all_valid(self, gate: ADRQualityGate, temp_dir: Path):
        """Test checking multiple valid ADR files."""
        # Create two valid ADR files
        adr1_path = temp_dir / "adr" / "001-first.md"
        adr2_path = temp_dir / "adr" / "002-second.md"
        adr1_path.parent.mkdir(parents=True, exist_ok=True)

        adr1_content = VALID_ADR_CONTENT
        adr2_content = VALID_ADR_CONTENT.replace('adr_id: "001"', 'adr_id: "002"').replace(
            "Test Feature", "Second Feature"
        )

        adr1_path.write_text(adr1_content, encoding="utf-8")
        adr2_path.write_text(adr2_content, encoding="utf-8")

        result = gate.check_multiple(temp_dir, [
            str(adr1_path.relative_to(temp_dir)),
            str(adr2_path.relative_to(temp_dir)),
        ])

        assert result.passed is True
        assert result.gate_type == "adr_valid"
        assert result.details["files_checked"] == 2
        assert result.details["valid_count"] == 2
        assert result.details["invalid_count"] == 0

    def test_check_multiple_one_invalid(self, gate: ADRQualityGate, valid_adr_file: Path, invalid_adr_missing_sections: Path, temp_dir: Path):
        """Test that one invalid file causes overall failure."""
        result = gate.check_multiple(temp_dir, [
            str(valid_adr_file.relative_to(temp_dir)),
            str(invalid_adr_missing_sections.relative_to(temp_dir)),
        ])

        assert result.passed is False
        assert result.gate_type == "adr_valid"
        assert result.details["files_checked"] == 2
        assert result.details["valid_count"] == 1
        assert result.details["invalid_count"] == 1
        assert "1 of 2" in result.message or "1" in result.message

    def test_check_multiple_all_invalid(self, gate: ADRQualityGate, invalid_adr_missing_sections: Path, invalid_adr_no_criteria: Path, temp_dir: Path):
        """Test that all invalid files are reported."""
        result = gate.check_multiple(temp_dir, [
            str(invalid_adr_missing_sections.relative_to(temp_dir)),
            str(invalid_adr_no_criteria.relative_to(temp_dir)),
        ])

        assert result.passed is False
        assert result.details["files_checked"] == 2
        assert result.details["invalid_count"] == 2
        assert len(result.details["errors"]) > 0

    def test_check_multiple_empty_list(self, gate: ADRQualityGate, temp_dir: Path):
        """Test that empty file list passes."""
        result = gate.check_multiple(temp_dir, [])

        assert result.passed is True
        assert result.gate_type == "adr_valid"
        assert result.details["files_checked"] == 0

    def test_check_multiple_file_results_detail(self, gate: ADRQualityGate, valid_adr_file: Path, invalid_adr_missing_sections: Path, temp_dir: Path):
        """Test that file_results contains per-file details."""
        result = gate.check_multiple(temp_dir, [
            str(valid_adr_file.relative_to(temp_dir)),
            str(invalid_adr_missing_sections.relative_to(temp_dir)),
        ])

        assert "file_results" in result.details
        file_results = result.details["file_results"]
        assert len(file_results) == 2

        # Find each file's result
        valid_result = None
        invalid_result = None
        for fr in file_results:
            if "001" in fr["file"]:
                valid_result = fr
            elif "002" in fr["file"]:
                invalid_result = fr

        assert valid_result is not None
        assert valid_result["status"] == "valid"
        assert valid_result["error_count"] == 0

        assert invalid_result is not None
        assert invalid_result["status"] == "invalid"
        assert invalid_result["error_count"] > 0


class TestRegisterADRGate:
    """Tests for register_adr_gate function."""

    def test_register_extends_runner(self):
        """Test that register_adr_gate extends the runner."""
        runner = QualityGateRunner()
        original_run_gate = runner.run_gate

        register_adr_gate(runner)

        # run_gate should be replaced
        assert runner.run_gate is not original_run_gate

    def test_registered_gate_handles_adr_valid_single(self, valid_adr_file: Path, temp_dir: Path):
        """Test that registered gate handles adr_valid with single file."""
        runner = QualityGateRunner()
        register_adr_gate(runner)

        gate_config = {
            "type": "adr_valid",
            "file": str(valid_adr_file.relative_to(temp_dir)),
        }

        result = asyncio.run(runner.run_gate(temp_dir, gate_config))

        assert result.passed is True
        assert result.gate_type == "adr_valid"

    def test_registered_gate_handles_adr_valid_multiple(self, temp_dir: Path):
        """Test that registered gate handles adr_valid with multiple files."""
        # Create two valid ADR files
        adr1_path = temp_dir / "adr" / "001-first.md"
        adr2_path = temp_dir / "adr" / "002-second.md"
        adr1_path.parent.mkdir(parents=True, exist_ok=True)

        adr1_content = VALID_ADR_CONTENT
        adr2_content = VALID_ADR_CONTENT.replace('adr_id: "001"', 'adr_id: "002"')

        adr1_path.write_text(adr1_content, encoding="utf-8")
        adr2_path.write_text(adr2_content, encoding="utf-8")

        runner = QualityGateRunner()
        register_adr_gate(runner)

        gate_config = {
            "type": "adr_valid",
            "files": [
                str(adr1_path.relative_to(temp_dir)),
                str(adr2_path.relative_to(temp_dir)),
            ],
        }

        result = asyncio.run(runner.run_gate(temp_dir, gate_config))

        assert result.passed is True
        assert result.details["files_checked"] == 2

    def test_registered_gate_delegates_other_types(self, temp_dir: Path):
        """Test that other gate types are delegated to original implementation."""
        runner = QualityGateRunner()
        register_adr_gate(runner)

        # Create test files
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        gate_config = {
            "type": "files_exist",
            "files": ["test.py"],
        }

        result = asyncio.run(runner.run_gate(temp_dir, gate_config))

        # Should use original files_exist implementation
        assert result.gate_type == "files_exist"
        assert result.passed is True


class TestGateResultFormat:
    """Tests for GateResult format and structure."""

    def test_result_structure_on_success(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test that success result has expected structure."""
        result = gate.check(temp_dir, str(valid_adr_file.relative_to(temp_dir)))

        assert isinstance(result, GateResult)
        assert hasattr(result, "passed")
        assert hasattr(result, "gate_type")
        assert hasattr(result, "message")
        assert hasattr(result, "details")

        # Check details structure
        assert "files_checked" in result.details
        assert "error_count" in result.details
        assert "warning_count" in result.details
        assert "errors" in result.details
        assert "warnings" in result.details

    def test_result_structure_on_failure(self, gate: ADRQualityGate, invalid_adr_missing_sections: Path, temp_dir: Path):
        """Test that failure result has expected structure."""
        result = gate.check(temp_dir, str(invalid_adr_missing_sections.relative_to(temp_dir)))

        assert isinstance(result, GateResult)
        assert result.passed is False
        assert result.details["error_count"] > 0
        assert len(result.details["errors"]) > 0

    def test_message_format_on_success(self, gate: ADRQualityGate, valid_adr_file: Path, temp_dir: Path):
        """Test success message format."""
        result = gate.check(temp_dir, str(valid_adr_file.relative_to(temp_dir)))

        assert "passed" in result.message.lower() or "valid" in result.message.lower()

    def test_message_format_on_failure(self, gate: ADRQualityGate, invalid_adr_missing_sections: Path, temp_dir: Path):
        """Test failure message format."""
        result = gate.check(temp_dir, str(invalid_adr_missing_sections.relative_to(temp_dir)))

        assert "failed" in result.message.lower() or "error" in result.message.lower()
        assert "0" not in result.message or result.details["error_count"] > 0
