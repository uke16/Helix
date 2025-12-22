"""Tests for ADR Parser.

Tests cover:
- Parsing valid ADR files
- Parsing ADRs without optional fields
- Error handling for malformed YAML
- Error handling for missing frontmatter
- Section extraction
- Acceptance criteria checkbox extraction
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
    ADRMetadata,
    ADRSection,
    ADRFiles,
    ADRStatus,
    ComponentType,
    Classification,
    ChangeScope,
    AcceptanceCriterion,
)


# --- Test Fixtures ---

@pytest.fixture
def parser() -> ADRParser:
    """Create a fresh parser instance."""
    return ADRParser()


@pytest.fixture
def valid_adr_content() -> str:
    """A complete valid ADR following the v2 template."""
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
          - ADR-069
        ---

        # ADR-086: ADR-Template v2

        ## Status
        Proposed

        ## Kontext
        Aktuelles Problem beim Schreiben von ADRs.

        ## Entscheidung
        Wir führen ein erweitertes ADR-Template v2 ein.

        ## Implementation
        Die Implementation dieses ADRs umfasst mehrere Schritte.

        ## Dokumentation
        Diese Section beschreibt die Doku-Anforderungen.

        ## Akzeptanzkriterien
        - [ ] Das ADR enthält einen vollständigen YAML-Header
        - [x] Das ADR enthält die Sections in korrekter Reihenfolge
        - [ ] Die Implementation-Section beschreibt konkrete Schritte

        ## Konsequenzen
        Vorteile und Nachteile der Entscheidung.

        ## Referenzen
        - ADR-067: Pre-loaded Context System
        - ADR-069: Structured Change Classification
    ''').strip()


@pytest.fixture
def minimal_adr_content() -> str:
    """A minimal valid ADR with only required fields."""
    return dedent('''
        ---
        adr_id: "001"
        title: Minimal ADR
        status: Proposed
        ---

        # ADR-001: Minimal ADR

        ## Status
        Proposed

        ## Kontext
        Some context.

        ## Entscheidung
        Some decision.
    ''').strip()


# --- Tests for parse_string ---

class TestParseString:
    """Tests for ADRParser.parse_string()"""

    def test_parse_valid_adr(self, parser: ADRParser, valid_adr_content: str):
        """Test parsing a complete valid ADR."""
        adr = parser.parse_string(valid_adr_content)

        assert isinstance(adr, ADRDocument)
        assert adr.metadata.adr_id == "086"
        assert adr.metadata.title == "ADR-Template v2 mit Implementation"
        assert adr.metadata.status == ADRStatus.PROPOSED
        assert adr.metadata.project_type == "helix_internal"
        assert adr.metadata.component_type == ComponentType.DOCS
        assert adr.metadata.classification == Classification.UPDATE
        assert adr.metadata.change_scope == ChangeScope.DOCS

    def test_parse_files_metadata(self, parser: ADRParser, valid_adr_content: str):
        """Test that files metadata is correctly parsed."""
        adr = parser.parse_string(valid_adr_content)

        assert "path/to/new/file.py" in adr.metadata.files.create
        assert "path/to/existing/file.py" in adr.metadata.files.modify
        assert "docs/architecture/feature-x.md" in adr.metadata.files.docs

    def test_parse_depends_on(self, parser: ADRParser, valid_adr_content: str):
        """Test that depends_on is correctly parsed."""
        adr = parser.parse_string(valid_adr_content)

        assert "ADR-067" in adr.metadata.depends_on
        assert "ADR-069" in adr.metadata.depends_on

    def test_parse_minimal_adr(self, parser: ADRParser, minimal_adr_content: str):
        """Test parsing an ADR with only required fields."""
        adr = parser.parse_string(minimal_adr_content)

        assert adr.metadata.adr_id == "001"
        assert adr.metadata.title == "Minimal ADR"
        assert adr.metadata.status == ADRStatus.PROPOSED
        assert adr.metadata.project_type == "helix_internal"  # default
        assert adr.metadata.component_type is None
        assert adr.metadata.classification is None
        assert adr.metadata.change_scope is None
        assert adr.metadata.files.create == []
        assert adr.metadata.files.modify == []
        assert adr.metadata.files.docs == []
        assert adr.metadata.depends_on == []

    def test_parse_all_statuses(self, parser: ADRParser):
        """Test parsing all valid status values."""
        statuses = [
            ("Proposed", ADRStatus.PROPOSED),
            ("Accepted", ADRStatus.ACCEPTED),
            ("Implemented", ADRStatus.IMPLEMENTED),
            ("Superseded", ADRStatus.SUPERSEDED),
            ("Rejected", ADRStatus.REJECTED),
        ]

        for status_str, expected_enum in statuses:
            content = dedent(f'''
                ---
                adr_id: "001"
                title: Test ADR
                status: {status_str}
                ---

                ## Status
                {status_str}
            ''').strip()

            adr = parser.parse_string(content)
            assert adr.metadata.status == expected_enum, f"Failed for status: {status_str}"

    def test_parse_all_component_types(self, parser: ADRParser):
        """Test parsing all valid component_type values."""
        component_types = [
            "TOOL", "NODE", "AGENT", "PROCESS", "SERVICE",
            "SKILL", "PROMPT", "CONFIG", "DOCS", "MISC"
        ]

        for comp_type in component_types:
            content = dedent(f'''
                ---
                adr_id: "001"
                title: Test ADR
                status: Proposed
                component_type: {comp_type}
                ---

                ## Status
                Proposed
            ''').strip()

            adr = parser.parse_string(content)
            assert adr.metadata.component_type == ComponentType(comp_type)

    def test_parse_all_classifications(self, parser: ADRParser):
        """Test parsing all valid classification values."""
        classifications = ["NEW", "UPDATE", "FIX", "REFACTOR", "DEPRECATE"]

        for classification in classifications:
            content = dedent(f'''
                ---
                adr_id: "001"
                title: Test ADR
                status: Proposed
                classification: {classification}
                ---

                ## Status
                Proposed
            ''').strip()

            adr = parser.parse_string(content)
            assert adr.metadata.classification == Classification(classification)

    def test_parse_all_change_scopes(self, parser: ADRParser):
        """Test parsing all valid change_scope values."""
        change_scopes = ["major", "minor", "config", "docs", "hotfix"]

        for scope in change_scopes:
            content = dedent(f'''
                ---
                adr_id: "001"
                title: Test ADR
                status: Proposed
                change_scope: {scope}
                ---

                ## Status
                Proposed
            ''').strip()

            adr = parser.parse_string(content)
            assert adr.metadata.change_scope == ChangeScope(scope)


# --- Tests for Section Parsing ---

class TestSectionParsing:
    """Tests for markdown section parsing."""

    def test_parse_all_sections(self, parser: ADRParser, valid_adr_content: str):
        """Test that all sections are extracted."""
        adr = parser.parse_string(valid_adr_content)

        expected_sections = [
            "ADR-086: ADR-Template v2",  # H1 title
            "Status",
            "Kontext",
            "Entscheidung",
            "Implementation",
            "Dokumentation",
            "Akzeptanzkriterien",
            "Konsequenzen",
            "Referenzen"
        ]

        for section_name in expected_sections:
            assert section_name in adr.sections, f"Missing section: {section_name}"

    def test_section_content(self, parser: ADRParser, valid_adr_content: str):
        """Test that section content is correctly extracted."""
        adr = parser.parse_string(valid_adr_content)

        kontext = adr.sections["Kontext"]
        assert "Aktuelles Problem" in kontext.content
        assert kontext.level == 2

    def test_section_with_subsections(self, parser: ADRParser):
        """Test parsing sections that have subsections."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            ---

            ## Main Section

            Main content.

            ### Subsection 1

            Subsection 1 content.

            ### Subsection 2

            Subsection 2 content.

            ## Another Main Section

            More content.
        ''').strip()

        adr = parser.parse_string(content)

        # Should have all sections
        assert "Main Section" in adr.sections
        assert "Subsection 1" in adr.sections
        assert "Subsection 2" in adr.sections
        assert "Another Main Section" in adr.sections

        # Check levels
        assert adr.sections["Main Section"].level == 2
        assert adr.sections["Subsection 1"].level == 3
        assert adr.sections["Subsection 2"].level == 3

    def test_empty_section(self, parser: ADRParser):
        """Test parsing a section with no content."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            ---

            ## Empty Section

            ## Next Section

            Has content.
        ''').strip()

        adr = parser.parse_string(content)

        assert adr.sections["Empty Section"].content == ""
        assert "Has content" in adr.sections["Next Section"].content


# --- Tests for Acceptance Criteria ---

class TestAcceptanceCriteria:
    """Tests for acceptance criteria extraction."""

    def test_extract_acceptance_criteria(self, parser: ADRParser, valid_adr_content: str):
        """Test extracting acceptance criteria checkboxes."""
        adr = parser.parse_string(valid_adr_content)

        assert len(adr.acceptance_criteria) == 3

        # Check unchecked criterion
        criterion1 = adr.acceptance_criteria[0]
        assert "vollständigen YAML-Header" in criterion1.text
        assert criterion1.checked is False

        # Check checked criterion
        criterion2 = adr.acceptance_criteria[1]
        assert "Sections in korrekter Reihenfolge" in criterion2.text
        assert criterion2.checked is True

        # Check another unchecked criterion
        criterion3 = adr.acceptance_criteria[2]
        assert "Implementation-Section" in criterion3.text
        assert criterion3.checked is False

    def test_acceptance_criteria_various_formats(self, parser: ADRParser):
        """Test acceptance criteria with various checkbox formats."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            ---

            ## Akzeptanzkriterien

            - [ ] Unchecked with space
            - [x] Checked lowercase
            - [X] Checked uppercase
            - [ ] Another unchecked
        ''').strip()

        adr = parser.parse_string(content)

        assert len(adr.acceptance_criteria) == 4
        assert adr.acceptance_criteria[0].checked is False
        assert adr.acceptance_criteria[1].checked is True
        assert adr.acceptance_criteria[2].checked is True
        assert adr.acceptance_criteria[3].checked is False

    def test_no_acceptance_criteria_section(self, parser: ADRParser, minimal_adr_content: str):
        """Test ADR without Akzeptanzkriterien section."""
        adr = parser.parse_string(minimal_adr_content)
        assert adr.acceptance_criteria == []


# --- Tests for Error Handling ---

class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_yaml_frontmatter(self, parser: ADRParser):
        """Test error when no YAML frontmatter present."""
        content = dedent('''
            # ADR-001: No Frontmatter

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "No YAML frontmatter found" in str(exc_info.value)

    def test_invalid_yaml(self, parser: ADRParser):
        """Test error for malformed YAML."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            invalid yaml: [unclosed bracket
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "Invalid YAML" in str(exc_info.value)

    def test_missing_required_adr_id(self, parser: ADRParser):
        """Test error when adr_id is missing."""
        content = dedent('''
            ---
            title: Test
            status: Proposed
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "adr_id" in str(exc_info.value)

    def test_missing_required_title(self, parser: ADRParser):
        """Test error when title is missing."""
        content = dedent('''
            ---
            adr_id: "001"
            status: Proposed
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "title" in str(exc_info.value)

    def test_missing_required_status(self, parser: ADRParser):
        """Test error when status is missing."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "status" in str(exc_info.value)

    def test_invalid_status(self, parser: ADRParser):
        """Test error for invalid status value."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: InvalidStatus
            ---

            ## Status
            Invalid
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "Invalid status" in str(exc_info.value)
        assert "InvalidStatus" in str(exc_info.value)

    def test_invalid_component_type(self, parser: ADRParser):
        """Test error for invalid component_type value."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            component_type: INVALID_TYPE
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "Invalid component_type" in str(exc_info.value)

    def test_invalid_classification(self, parser: ADRParser):
        """Test error for invalid classification value."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            classification: INVALID
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "Invalid classification" in str(exc_info.value)

    def test_invalid_change_scope(self, parser: ADRParser):
        """Test error for invalid change_scope value."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            change_scope: invalid_scope
            ---

            ## Status
            Proposed
        ''').strip()

        with pytest.raises(ADRParseError) as exc_info:
            parser.parse_string(content)

        assert "Invalid change_scope" in str(exc_info.value)


# --- Tests for parse_file ---

class TestParseFile:
    """Tests for ADRParser.parse_file()"""

    def test_parse_file_not_found(self, parser: ADRParser):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/path/adr.md"))

    def test_parse_file_success(self, parser: ADRParser, tmp_path: Path, valid_adr_content: str):
        """Test successfully parsing a file from disk."""
        # Create a temporary file
        adr_file = tmp_path / "test-adr.md"
        adr_file.write_text(valid_adr_content)

        # Parse it
        adr = parser.parse_file(adr_file)

        assert adr.file_path == adr_file
        assert adr.metadata.adr_id == "086"
        assert adr.raw_content == valid_adr_content


# --- Tests for Edge Cases ---

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_numeric_adr_id(self, parser: ADRParser):
        """Test that numeric adr_id is converted to string."""
        content = dedent('''
            ---
            adr_id: 86
            title: Test
            status: Proposed
            ---

            ## Status
            Proposed
        ''').strip()

        adr = parser.parse_string(content)
        assert adr.metadata.adr_id == "86"
        assert isinstance(adr.metadata.adr_id, str)

    def test_files_as_single_string(self, parser: ADRParser):
        """Test that single file strings are converted to lists."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            files:
              create: single_file.py
              modify: another_file.py
            ---

            ## Status
            Proposed
        ''').strip()

        adr = parser.parse_string(content)
        assert adr.metadata.files.create == ["single_file.py"]
        assert adr.metadata.files.modify == ["another_file.py"]

    def test_depends_on_as_single_string(self, parser: ADRParser):
        """Test that single depends_on string is converted to list."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            depends_on: ADR-001
            ---

            ## Status
            Proposed
        ''').strip()

        adr = parser.parse_string(content)
        assert adr.metadata.depends_on == ["ADR-001"]

    def test_empty_optional_fields(self, parser: ADRParser):
        """Test parsing with empty optional fields."""
        content = dedent('''
            ---
            adr_id: "001"
            title: Test
            status: Proposed
            component_type:
            classification:
            change_scope:
            files:
            depends_on:
            ---

            ## Status
            Proposed
        ''').strip()

        adr = parser.parse_string(content)
        assert adr.metadata.component_type is None
        assert adr.metadata.classification is None
        assert adr.metadata.change_scope is None
        assert adr.metadata.files.create == []
        assert adr.metadata.depends_on == []

    def test_special_characters_in_content(self, parser: ADRParser):
        """Test parsing content with special characters."""
        content = dedent('''
            ---
            adr_id: "001"
            title: "Test with 'quotes' and special: chars"
            status: Proposed
            ---

            ## Kontext

            Content with special chars: `code`, **bold**, *italic*

            ```python
            def example():
                return "string with 'quotes'"
            ```
        ''').strip()

        adr = parser.parse_string(content)
        assert "Test with 'quotes'" in adr.metadata.title
        assert "```python" in adr.sections["Kontext"].content

    def test_multiline_yaml_values(self, parser: ADRParser):
        """Test parsing multiline YAML values."""
        content = dedent('''
            ---
            adr_id: "001"
            title: >
              This is a long title
              that spans multiple lines
            status: Proposed
            ---

            ## Status
            Proposed
        ''').strip()

        adr = parser.parse_string(content)
        assert "long title" in adr.metadata.title

    def test_preserve_raw_content(self, parser: ADRParser, valid_adr_content: str):
        """Test that raw_content preserves original content."""
        adr = parser.parse_string(valid_adr_content)
        assert adr.raw_content == valid_adr_content


# --- Integration Test with Real ADR ---

class TestRealADRParsing:
    """Integration tests with ADR content similar to real ADRs."""

    def test_parse_adr086_like_content(self, parser: ADRParser):
        """Test parsing content similar to the actual ADR-086."""
        content = dedent('''
            ---
            adr_id: "086"
            title: ADR-Template v2 mit Implementation, Dokumentation & Akzeptanzkriterien
            status: Implemented

            project_type: helix_internal
            component_type: DOCS
            classification: UPDATE
            change_scope: docs

            files:
              create: []
              modify:
                - adr/000-adr-index.md
                - adr/086-adr-template-v2.md
                - docs/architecture/context-and-classification-system.md
                - skills/development/change-process/SKILL.md
                - skills/development/documentation-guide/SKILL.md
              docs:
                - adr/086-adr-template-v2.md
                - docs/architecture/context-and-classification-system.md

            depends_on:
              - ADR-067
              - ADR-069
              - ADR-071
            ---

            # ADR-086: ADR-Template v2

            ## Status
            Implemented

            ## Kontext

            Aktuelles Problem beim Schreiben von ADRs:

            1. **Fehlende konkrete Code-Beispiele**
            2. **Unklare Dokumentationsanforderungen**
            3. **Keine expliziten Akzeptanzkriterien**

            ## Entscheidung

            Wir führen ein **erweitertes ADR-Template v2** ein.

            ## Implementation

            ### 1. Neuer Standard-YAML-Header

            ```yaml
            ---
            adr_number: NNN
            title: Kurzer Titel
            status: Proposed
            ---
            ```

            ## Dokumentation

            | Datei | Änderung |
            |-------|----------|
            | `adr/000-adr-index.md` | Eintrag hinzufügen |

            ## Akzeptanzkriterien

            ### 1. Template-Struktur

            - [x] Das ADR enthält einen vollständigen YAML-Header
            - [x] Das ADR enthält die Sections in korrekter Reihenfolge

            ### 2. Implementation-Section

            - [ ] Die Implementation-Section beschreibt konkrete Schritte
            - [ ] Es gibt mindestens ein Code-Beispiel

            ## Konsequenzen

            **Vorteile:**
            - Developer bekommen klareres Bild

            **Nachteile:**
            - Höherer Initialaufwand

            ## Referenzen

            - ADR-067: Pre-loaded Context System
            - ADR-069: Structured Change Classification
        ''').strip()

        adr = parser.parse_string(content)

        # Verify metadata
        assert adr.metadata.adr_id == "086"
        assert adr.metadata.status == ADRStatus.IMPLEMENTED
        assert adr.metadata.component_type == ComponentType.DOCS
        assert len(adr.metadata.depends_on) == 3

        # Verify sections
        assert "Kontext" in adr.sections
        assert "Implementation" in adr.sections
        assert "Dokumentation" in adr.sections
        assert "Akzeptanzkriterien" in adr.sections

        # Verify acceptance criteria
        # Should find 4 criteria (2 checked, 2 unchecked)
        assert len(adr.acceptance_criteria) == 4
        checked_count = sum(1 for c in adr.acceptance_criteria if c.checked)
        assert checked_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
