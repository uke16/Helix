"""Tests for ADR Validator.

Tests cover:
- Validating complete valid ADRs
- Validating ADRs with missing required sections
- Validating ADRs with missing recommended header fields
- Validation of acceptance criteria
- Consistency checks between header and body
- Error handling for parse errors
- Completion status calculation
"""

import pytest
from pathlib import Path
from textwrap import dedent

# Import from the new location
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from helix.adr.parser import (
    ADRParser,
    ADRParseError,
    ADRDocument,
)

from helix.adr.validator import (
    ADRValidator,
    ValidationResult,
    ValidationIssue,
    IssueLevel,
    IssueCategory,
)


# --- Test Fixtures ---

@pytest.fixture
def validator() -> ADRValidator:
    """Create a fresh validator instance."""
    return ADRValidator()


@pytest.fixture
def valid_complete_adr() -> str:
    """A complete valid ADR with all required and recommended fields/sections."""
    return dedent('''
        ---
        adr_id: "086"
        title: ADR-Template v2 mit Implementation
        status: Proposed

        project_type: helix_internal
        component_type: DOCS
        classification: UPDATE
        change_scope: docs

        files:
          create:
            - path/to/new/file.py
          modify:
            - path/to/existing/file.py
          docs:
            - docs/architecture/feature-x.md

        depends_on:
          - ADR-067
        ---

        # ADR-086: ADR-Template v2

        ## Status
        Proposed

        ## Kontext
        Aktuelles Problem beim Schreiben von ADRs. Wir brauchen eine bessere Struktur.

        ## Entscheidung
        Wir führen ein erweitertes ADR-Template v2 ein mit klaren Richtlinien.

        ## Implementation
        Die Implementation dieses ADRs umfasst mehrere Schritte und Änderungen.

        ## Dokumentation
        Diese Section beschreibt die Doku-Anforderungen.
        - docs/architecture/feature-x.md

        ## Akzeptanzkriterien
        - [ ] Das ADR enthält einen vollständigen YAML-Header
        - [x] Das ADR enthält die Sections in korrekter Reihenfolge
        - [ ] Die Implementation-Section beschreibt konkrete Schritte

        ## Konsequenzen
        Vorteile und Nachteile der Entscheidung werden hier beschrieben.
    ''').strip()


@pytest.fixture
def minimal_valid_adr() -> str:
    """A minimal valid ADR with only required fields and sections."""
    return dedent('''
        ---
        adr_id: "001"
        title: Minimal ADR
        status: Proposed
        ---

        # ADR-001: Minimal ADR

        ## Kontext
        Some context about the problem.

        ## Entscheidung
        Some decision that was made.

        ## Implementation
        How we will implement this.

        ## Dokumentation
        Documentation requirements.

        ## Akzeptanzkriterien
        - [ ] First criterion
        - [ ] Second criterion
        - [ ] Third criterion

        ## Konsequenzen
        What happens as a result.
    ''').strip()


@pytest.fixture
def adr_missing_sections() -> str:
    """An ADR missing required sections."""
    return dedent('''
        ---
        adr_id: "002"
        title: Incomplete ADR
        status: Proposed
        ---

        # ADR-002: Incomplete ADR

        ## Kontext
        Some context about the problem.

        ## Entscheidung
        Some decision that was made.

        ## Akzeptanzkriterien
        - [ ] First criterion
    ''').strip()


@pytest.fixture
def adr_empty_sections() -> str:
    """An ADR with empty required sections."""
    return dedent('''
        ---
        adr_id: "003"
        title: Empty Sections ADR
        status: Proposed
        ---

        ## Kontext


        ## Entscheidung


        ## Implementation
        Valid content here.

        ## Dokumentation


        ## Akzeptanzkriterien
        - [ ] Criterion

        ## Konsequenzen

    ''').strip()


@pytest.fixture
def adr_no_acceptance_criteria() -> str:
    """An ADR with no acceptance criteria checkboxes."""
    return dedent('''
        ---
        adr_id: "004"
        title: No Criteria ADR
        status: Proposed
        ---

        ## Kontext
        Some context.

        ## Entscheidung
        Some decision.

        ## Implementation
        Some implementation.

        ## Dokumentation
        Some docs.

        ## Akzeptanzkriterien
        This section has no checkboxes, just text.

        ## Konsequenzen
        Some consequences.
    ''').strip()


# --- Tests for Valid ADRs ---

class TestValidADRs:
    """Tests for valid ADR validation."""

    def test_complete_adr_is_valid(self, validator: ADRValidator, valid_complete_adr: str):
        """Test that a complete valid ADR passes validation."""
        result = validator.validate_string(valid_complete_adr)

        assert result.valid is True
        assert result.error_count == 0
        assert result.adr is not None
        assert result.adr.metadata.adr_id == "086"

    def test_minimal_valid_adr_has_warnings(self, validator: ADRValidator, minimal_valid_adr: str):
        """Test that minimal ADR is valid but has warnings for missing recommended fields."""
        result = validator.validate_string(minimal_valid_adr)

        assert result.valid is True
        assert result.error_count == 0
        # Should have warnings for missing component_type, classification, change_scope
        assert result.warning_count >= 3

        # Check that warnings are for recommended fields
        warning_messages = [w.message for w in result.warnings]
        assert any("component_type" in msg for msg in warning_messages)
        assert any("classification" in msg for msg in warning_messages)
        assert any("change_scope" in msg for msg in warning_messages)

    def test_valid_adr_returns_parsed_document(self, validator: ADRValidator, valid_complete_adr: str):
        """Test that valid ADR includes the parsed document in result."""
        result = validator.validate_string(valid_complete_adr)

        assert result.adr is not None
        assert result.adr.metadata.adr_id == "086"
        assert result.adr.metadata.title == "ADR-Template v2 mit Implementation"
        assert "Kontext" in result.adr.sections


# --- Tests for Missing Sections ---

class TestMissingSections:
    """Tests for ADRs missing required sections."""

    def test_missing_required_sections(self, validator: ADRValidator, adr_missing_sections: str):
        """Test that missing required sections cause validation errors."""
        result = validator.validate_string(adr_missing_sections)

        assert result.valid is False
        assert result.error_count > 0

        # Check for specific missing sections
        error_messages = [e.message for e in result.errors]
        assert any("Implementation" in msg for msg in error_messages)
        assert any("Dokumentation" in msg for msg in error_messages)
        assert any("Konsequenzen" in msg for msg in error_messages)

    def test_missing_section_error_category(self, validator: ADRValidator, adr_missing_sections: str):
        """Test that missing section errors have correct category."""
        result = validator.validate_string(adr_missing_sections)

        missing_section_errors = [
            e for e in result.errors
            if e.category == IssueCategory.MISSING_SECTION
        ]
        assert len(missing_section_errors) >= 3  # Implementation, Dokumentation, Konsequenzen


# --- Tests for Empty Sections ---

class TestEmptySections:
    """Tests for ADRs with empty sections."""

    def test_empty_sections_generate_warnings(self, validator: ADRValidator, adr_empty_sections: str):
        """Test that empty sections generate warnings (not errors)."""
        result = validator.validate_string(adr_empty_sections)

        # Empty sections are warnings, not errors (ADR is still valid)
        empty_section_warnings = [
            w for w in result.warnings
            if w.category == IssueCategory.EMPTY_SECTION
        ]
        assert len(empty_section_warnings) >= 1

    def test_empty_section_warning_message(self, validator: ADRValidator, adr_empty_sections: str):
        """Test that empty section warnings have meaningful messages."""
        result = validator.validate_string(adr_empty_sections)

        empty_warnings = [w for w in result.warnings if w.category == IssueCategory.EMPTY_SECTION]
        for warning in empty_warnings:
            assert "minimal content" in warning.message.lower() or "chars" in warning.message


# --- Tests for Acceptance Criteria ---

class TestAcceptanceCriteria:
    """Tests for acceptance criteria validation."""

    def test_no_criteria_causes_error(self, validator: ADRValidator, adr_no_acceptance_criteria: str):
        """Test that missing acceptance criteria causes an error."""
        result = validator.validate_string(adr_no_acceptance_criteria)

        assert result.valid is False
        criteria_errors = [
            e for e in result.errors
            if e.category == IssueCategory.MISSING_CRITERIA
        ]
        assert len(criteria_errors) == 1
        assert "No acceptance criteria" in criteria_errors[0].message

    def test_few_criteria_causes_warning(self, validator: ADRValidator):
        """Test that having less than 3 criteria causes a warning."""
        content = dedent('''
            ---
            adr_id: "005"
            title: Few Criteria ADR
            status: Proposed
            ---

            ## Kontext
            Some context.

            ## Entscheidung
            Some decision.

            ## Implementation
            Some implementation.

            ## Dokumentation
            Some docs.

            ## Akzeptanzkriterien
            - [ ] Only one criterion
            - [ ] And another

            ## Konsequenzen
            Some consequences.
        ''').strip()

        result = validator.validate_string(content)

        few_criteria_warnings = [
            w for w in result.warnings
            if w.category == IssueCategory.FEW_CRITERIA
        ]
        assert len(few_criteria_warnings) == 1
        assert "2" in few_criteria_warnings[0].message  # Shows the count

    def test_sufficient_criteria_no_warning(self, validator: ADRValidator, minimal_valid_adr: str):
        """Test that 3+ criteria don't generate warnings about criteria count."""
        result = validator.validate_string(minimal_valid_adr)

        few_criteria_warnings = [
            w for w in result.warnings
            if w.category == IssueCategory.FEW_CRITERIA
        ]
        assert len(few_criteria_warnings) == 0


# --- Tests for Consistency Checks ---

class TestConsistencyChecks:
    """Tests for header/body consistency validation."""

    def test_docs_file_not_in_section_warning(self, validator: ADRValidator):
        """Test warning when files.docs contains files not mentioned in Dokumentation section."""
        content = dedent('''
            ---
            adr_id: "006"
            title: Inconsistent ADR
            status: Proposed
            files:
              docs:
                - docs/missing-file.md
                - docs/another-missing.md
            ---

            ## Kontext
            Some context.

            ## Entscheidung
            Some decision.

            ## Implementation
            Some implementation.

            ## Dokumentation
            This section mentions nothing about the files.

            ## Akzeptanzkriterien
            - [ ] First criterion
            - [ ] Second criterion
            - [ ] Third criterion

            ## Konsequenzen
            Some consequences.
        ''').strip()

        result = validator.validate_string(content)

        inconsistent_warnings = [
            w for w in result.warnings
            if w.category == IssueCategory.INCONSISTENT
        ]
        assert len(inconsistent_warnings) >= 1
        assert any("missing-file.md" in w.message for w in inconsistent_warnings)

    def test_docs_file_mentioned_no_warning(self, validator: ADRValidator, valid_complete_adr: str):
        """Test no warning when files.docs are mentioned in Dokumentation section."""
        result = validator.validate_string(valid_complete_adr)

        inconsistent_warnings = [
            w for w in result.warnings
            if w.category == IssueCategory.INCONSISTENT
        ]
        assert len(inconsistent_warnings) == 0


# --- Tests for Parse Errors ---

class TestParseErrors:
    """Tests for handling parse errors."""

    def test_invalid_yaml_returns_error(self, validator: ADRValidator):
        """Test that invalid YAML returns a parse error."""
        content = dedent('''
            ---
            adr_id: "007"
            title: Test
            invalid yaml: [unclosed bracket
            ---

            ## Kontext
            Content.
        ''').strip()

        result = validator.validate_string(content)

        assert result.valid is False
        assert result.error_count == 1
        assert result.errors[0].category == IssueCategory.PARSE_ERROR
        assert result.adr is None

    def test_missing_frontmatter_returns_error(self, validator: ADRValidator):
        """Test that missing YAML frontmatter returns a parse error."""
        content = dedent('''
            # ADR without frontmatter

            ## Kontext
            Content.
        ''').strip()

        result = validator.validate_string(content)

        assert result.valid is False
        assert result.errors[0].category == IssueCategory.PARSE_ERROR

    def test_missing_required_field_returns_error(self, validator: ADRValidator):
        """Test that missing required field returns a parse error."""
        content = dedent('''
            ---
            adr_id: "008"
            title: Test
            ---

            ## Status
            Missing status field in header.
        ''').strip()

        result = validator.validate_string(content)

        assert result.valid is False
        assert result.errors[0].category == IssueCategory.PARSE_ERROR


# --- Tests for File Validation ---

class TestFileValidation:
    """Tests for validate_file method."""

    def test_validate_nonexistent_file(self, validator: ADRValidator):
        """Test error when file doesn't exist."""
        result = validator.validate_file(Path("/nonexistent/path/adr.md"))

        assert result.valid is False
        assert result.error_count == 1
        assert result.errors[0].category == IssueCategory.PARSE_ERROR
        assert "not found" in result.errors[0].message

    def test_validate_file_from_disk(self, validator: ADRValidator, tmp_path: Path, valid_complete_adr: str):
        """Test validating a file from disk."""
        adr_file = tmp_path / "test-adr.md"
        adr_file.write_text(valid_complete_adr)

        result = validator.validate_file(adr_file)

        assert result.valid is True
        assert result.adr is not None
        assert result.adr.file_path == adr_file


# --- Tests for ValidationResult ---

class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_result_str_representation(self, validator: ADRValidator, valid_complete_adr: str):
        """Test string representation of validation result."""
        result = validator.validate_string(valid_complete_adr)

        result_str = str(result)
        assert "VALID" in result_str
        assert "0 errors" in result_str

    def test_result_invalid_str(self, validator: ADRValidator, adr_missing_sections: str):
        """Test string representation of invalid result."""
        result = validator.validate_string(adr_missing_sections)

        result_str = str(result)
        assert "INVALID" in result_str

    def test_errors_property(self, validator: ADRValidator, adr_missing_sections: str):
        """Test errors property returns only errors."""
        result = validator.validate_string(adr_missing_sections)

        for issue in result.errors:
            assert issue.level == IssueLevel.ERROR

    def test_warnings_property(self, validator: ADRValidator, minimal_valid_adr: str):
        """Test warnings property returns only warnings."""
        result = validator.validate_string(minimal_valid_adr)

        for issue in result.warnings:
            assert issue.level == IssueLevel.WARNING


# --- Tests for ValidationIssue ---

class TestValidationIssue:
    """Tests for ValidationIssue class."""

    def test_issue_str_with_location(self):
        """Test issue string representation with location."""
        issue = ValidationIssue(
            level=IssueLevel.ERROR,
            category=IssueCategory.MISSING_SECTION,
            message="Required section missing: ## Kontext",
            location="Markdown body",
        )

        issue_str = str(issue)
        assert "[ERROR]" in issue_str
        assert "## Kontext" in issue_str
        assert "Markdown body" in issue_str

    def test_issue_str_without_location(self):
        """Test issue string representation without location."""
        issue = ValidationIssue(
            level=IssueLevel.WARNING,
            category=IssueCategory.MISSING_RECOMMENDED_FIELD,
            message="Recommended field missing: component_type",
        )

        issue_str = str(issue)
        assert "[WARNING]" in issue_str
        assert "component_type" in issue_str


# --- Tests for Helper Methods ---

class TestHelperMethods:
    """Tests for validator helper methods."""

    def test_get_completion_status(self, validator: ADRValidator, valid_complete_adr: str):
        """Test getting acceptance criteria completion status."""
        result = validator.validate_string(valid_complete_adr)
        adr = result.adr

        status = validator.get_completion_status(adr)

        assert status["total"] == 3
        assert status["checked"] == 1
        assert status["unchecked"] == 2
        assert status["completion_percent"] == pytest.approx(33.3, rel=0.1)

    def test_get_completion_status_empty(self, validator: ADRValidator, adr_no_acceptance_criteria: str):
        """Test completion status with no criteria."""
        # Parse directly since validation will fail
        parser = ADRParser()
        adr = parser.parse_string(adr_no_acceptance_criteria)

        status = validator.get_completion_status(adr)

        assert status["total"] == 0
        assert status["checked"] == 0
        assert status["completion_percent"] == 0

    def test_get_unchecked_criteria(self, validator: ADRValidator, valid_complete_adr: str):
        """Test getting list of unchecked criteria."""
        result = validator.validate_string(valid_complete_adr)
        adr = result.adr

        unchecked = validator.get_unchecked_criteria(adr)

        assert len(unchecked) == 2
        assert "YAML-Header" in unchecked[0]
        assert "Implementation-Section" in unchecked[1]

    def test_get_unchecked_criteria_all_checked(self, validator: ADRValidator):
        """Test unchecked criteria when all are checked."""
        content = dedent('''
            ---
            adr_id: "009"
            title: All Checked ADR
            status: Implemented
            ---

            ## Kontext
            Context here.

            ## Entscheidung
            Decision here.

            ## Implementation
            Implementation details.

            ## Dokumentation
            Docs here.

            ## Akzeptanzkriterien
            - [x] First done
            - [x] Second done
            - [x] Third done

            ## Konsequenzen
            Consequences here.
        ''').strip()

        result = validator.validate_string(content)
        unchecked = validator.get_unchecked_criteria(result.adr)

        assert len(unchecked) == 0


# --- Tests for Section Name Matching ---

class TestSectionNameMatching:
    """Tests for case-insensitive section name matching."""

    def test_lowercase_section_names(self, validator: ADRValidator):
        """Test that lowercase section names are matched."""
        content = dedent('''
            ---
            adr_id: "010"
            title: Lowercase Sections
            status: Proposed
            ---

            ## kontext
            Context here.

            ## entscheidung
            Decision here.

            ## implementation
            Implementation details.

            ## dokumentation
            Docs here.

            ## akzeptanzkriterien
            - [ ] First criterion
            - [ ] Second criterion
            - [ ] Third criterion

            ## konsequenzen
            Consequences here.
        ''').strip()

        result = validator.validate_string(content)

        # Should not have missing section errors
        missing_section_errors = [
            e for e in result.errors
            if e.category == IssueCategory.MISSING_SECTION
        ]
        assert len(missing_section_errors) == 0


# --- Tests for Custom Parser ---

class TestCustomParser:
    """Tests for using custom parser instance."""

    def test_custom_parser(self, valid_complete_adr: str):
        """Test validator with custom parser instance."""
        custom_parser = ADRParser()
        validator = ADRValidator(parser=custom_parser)

        result = validator.validate_string(valid_complete_adr)

        assert result.valid is True
        assert validator.parser is custom_parser


# --- Integration Tests ---

class TestIntegration:
    """Integration tests for complete validation workflow."""

    def test_full_validation_workflow(self, tmp_path: Path):
        """Test complete validation workflow from file creation to validation."""
        # Create a complete ADR file
        adr_content = dedent('''
            ---
            adr_id: "INT-001"
            title: Integration Test ADR
            status: Proposed
            component_type: SERVICE
            classification: NEW
            change_scope: major
            files:
              create:
                - src/new_service.py
              docs:
                - docs/new-service.md
            ---

            # ADR-INT-001: Integration Test

            ## Status
            Proposed

            ## Kontext
            This is a test context for integration testing of the validator.

            ## Entscheidung
            We decided to test the validator with a complete ADR document.

            ## Implementation
            Implementation steps:
            1. Create the ADR file
            2. Run the validator
            3. Check the results

            ## Dokumentation
            Documentation updates:
            - docs/new-service.md

            ## Akzeptanzkriterien
            - [ ] Validator parses the ADR correctly
            - [ ] All required sections are detected
            - [ ] No false positives for errors

            ## Konsequenzen
            This test verifies the validator works correctly.

            ## Referenzen
            - ADR-086: Template reference
        ''').strip()

        # Write to file
        adr_file = tmp_path / "int-test-adr.md"
        adr_file.write_text(adr_content)

        # Validate
        validator = ADRValidator()
        result = validator.validate_file(adr_file)

        # Assertions
        assert result.valid is True
        assert result.error_count == 0
        assert result.adr.metadata.adr_id == "INT-001"
        assert result.adr.metadata.component_type.value == "SERVICE"
        assert len(result.adr.acceptance_criteria) == 3

        # Check completion status
        status = validator.get_completion_status(result.adr)
        assert status["total"] == 3
        assert status["checked"] == 0
        assert status["completion_percent"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
