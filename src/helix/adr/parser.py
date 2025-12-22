"""ADR Parser for HELIX v4.

This module provides parsing functionality for Architecture Decision Records
following the ADR-086 Template v2 format. It extracts YAML frontmatter metadata
and parses markdown sections including acceptance criteria checkboxes.

Example:
    >>> from helix.adr.parser import ADRParser
    >>> parser = ADRParser()
    >>> adr = parser.parse_file(Path("adr/001-feature.md"))
    >>> print(adr.metadata.adr_id)  # "001"
    >>> print(adr.metadata.status)  # ADRStatus.PROPOSED
    >>> print(adr.sections["Kontext"].content)

See Also:
    - ADR-086: ADR-Template v2 from HELIX v3
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class ADRStatus(Enum):
    """Valid ADR status values per ADR-086 template.

    Attributes:
        PROPOSED: Initial draft, under discussion
        ACCEPTED: Decision made, ready for implementation
        IMPLEMENTED: Fully implemented and validated
        SUPERSEDED: Replaced by a newer ADR
        REJECTED: Decision rejected, not implemented
    """
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    IMPLEMENTED = "Implemented"
    SUPERSEDED = "Superseded"
    REJECTED = "Rejected"


class ComponentType(Enum):
    """Valid component types per ADR-069.

    Used to classify what type of HELIX component the ADR affects.
    """
    TOOL = "TOOL"
    NODE = "NODE"
    AGENT = "AGENT"
    PROCESS = "PROCESS"
    SERVICE = "SERVICE"
    SKILL = "SKILL"
    PROMPT = "PROMPT"
    CONFIG = "CONFIG"
    DOCS = "DOCS"
    MISC = "MISC"


class Classification(Enum):
    """Change classification types per ADR-069.

    Describes the nature of the change.
    """
    NEW = "NEW"
    UPDATE = "UPDATE"
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    DEPRECATE = "DEPRECATE"


class ChangeScope(Enum):
    """Change scope levels per ADR-069.

    Describes the impact/size of the change.
    """
    MAJOR = "major"
    MINOR = "minor"
    CONFIG = "config"
    DOCS = "docs"
    HOTFIX = "hotfix"


@dataclass
class ADRFiles:
    """Files affected by an ADR.

    Attributes:
        create: New files to be created
        modify: Existing files to be modified
        docs: Documentation files to be updated
    """
    create: list[str] = field(default_factory=list)
    modify: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)


@dataclass
class ADRMetadata:
    """YAML header metadata from an ADR document.

    Contains all structured metadata extracted from the YAML frontmatter.

    Attributes:
        adr_id: Unique identifier (e.g., "086")
        title: ADR title
        status: Current status (Proposed, Accepted, etc.)
        project_type: Either "helix_internal" or "external"
        component_type: Type of component affected
        classification: Type of change (NEW, UPDATE, etc.)
        change_scope: Scope of change (major, minor, etc.)
        files: Files affected by the ADR
        depends_on: List of ADR IDs this depends on
        domain: Domain for skill loading (e.g., "helix", "pdm")
        language: Programming language (e.g., "python", "typescript")
        skills: Explicit list of skills to include
    """
    adr_id: str
    title: str
    status: ADRStatus
    project_type: str = "helix_internal"
    component_type: Optional[ComponentType] = None
    classification: Optional[Classification] = None
    change_scope: Optional[ChangeScope] = None
    files: ADRFiles = field(default_factory=ADRFiles)
    depends_on: list[str] = field(default_factory=list)
    # Project context (replaces spec.yaml meta section)
    domain: Optional[str] = None
    language: str = "python"
    skills: list[str] = field(default_factory=list)


@dataclass
class AcceptanceCriterion:
    """Single acceptance criterion with checkbox state.

    Represents a checkbox item from the Akzeptanzkriterien section.

    Attributes:
        text: The criterion text (without checkbox markup)
        checked: Whether the checkbox is checked
        line_number: Line number in the source file
    """
    text: str
    checked: bool = False
    line_number: int = 0


@dataclass
class ADRSection:
    """A parsed markdown section.

    Represents a heading and its content from the markdown body.

    Attributes:
        name: Section heading (e.g., "Kontext", "Implementation")
        content: Raw markdown content under the heading
        level: Heading level (1 for #, 2 for ##, etc.)
        line_start: Starting line number in source file
    """
    name: str
    content: str
    level: int = 2
    line_start: int = 0


@dataclass
class ADRDocument:
    """Complete parsed ADR document.

    Contains all parsed information from an ADR file.

    Attributes:
        file_path: Path to the source file
        metadata: Parsed YAML header metadata
        sections: Dict mapping section names to ADRSection objects
        acceptance_criteria: List of extracted acceptance criteria
        raw_content: Original file content
    """
    file_path: Path
    metadata: ADRMetadata
    sections: dict[str, ADRSection]
    acceptance_criteria: list[AcceptanceCriterion]
    raw_content: str


class ADRParseError(Exception):
    """Raised when ADR parsing fails.

    Attributes:
        message: Error description
        file_path: Path to the file that failed to parse
        line: Line number where error occurred (if applicable)
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        line: int = 0
    ):
        self.file_path = file_path
        self.line = line
        super().__init__(message)

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.line > 0:
            parts.append(f"Line: {self.line}")
        return " | ".join(parts)


class ADRParser:
    """Parse ADR documents in v2 format.

    Extracts YAML frontmatter and markdown sections from ADR files.
    Supports the ADR-086 template format from HELIX v3.

    Example:
        >>> parser = ADRParser()
        >>> adr = parser.parse_file(Path("adr/001-feature.md"))
        >>> print(adr.metadata.title)
        >>> print(adr.sections["Kontext"].content)

    See Also:
        ADR-086: ADR-Template v2
    """

    # Regex for YAML frontmatter (--- delimited)
    YAML_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL | re.MULTILINE
    )

    # Regex for markdown headings
    HEADING_PATTERN = re.compile(
        r'^(#{1,6})\s+(.+)$',
        re.MULTILINE
    )

    # Regex for checkbox items
    CHECKBOX_PATTERN = re.compile(
        r'^\s*-\s*\[([ xX])\]\s*(.+)$',
        re.MULTILINE
    )

    def parse_file(self, file_path: Path) -> ADRDocument:
        """Parse an ADR file from disk.

        Args:
            file_path: Path to the ADR markdown file.

        Returns:
            Parsed ADRDocument with metadata and sections.

        Raises:
            ADRParseError: If the file cannot be parsed.
            FileNotFoundError: If the file doesn't exist.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"ADR file not found: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ADRParseError(
                f"Failed to read file: {e}",
                file_path=file_path
            ) from e

        return self.parse_string(content, file_path)

    def parse_string(
        self,
        content: str,
        file_path: Optional[Path] = None
    ) -> ADRDocument:
        """Parse ADR content from a string.

        Args:
            content: Raw ADR content (YAML header + Markdown body).
            file_path: Optional path for error messages.

        Returns:
            Parsed ADRDocument.

        Raises:
            ADRParseError: If the content cannot be parsed.
        """
        if file_path is None:
            file_path = Path("<string>")

        # Extract YAML header and markdown body
        try:
            yaml_data, markdown = self._extract_yaml_header(content, file_path)
        except ADRParseError:
            raise
        except Exception as e:
            raise ADRParseError(
                f"Failed to extract YAML header: {e}",
                file_path=file_path
            ) from e

        # Parse metadata
        try:
            metadata = self._parse_metadata(yaml_data, file_path)
        except ADRParseError:
            raise
        except Exception as e:
            raise ADRParseError(
                f"Failed to parse metadata: {e}",
                file_path=file_path
            ) from e

        # Parse sections
        try:
            sections = self._parse_sections(markdown, file_path)
        except ADRParseError:
            raise
        except Exception as e:
            raise ADRParseError(
                f"Failed to parse sections: {e}",
                file_path=file_path
            ) from e

        # Extract acceptance criteria from the Akzeptanzkriterien section
        # and any subsections that follow it (until the next level-2 heading)
        acceptance_criteria = self._extract_all_acceptance_criteria(sections)

        return ADRDocument(
            file_path=file_path,
            metadata=metadata,
            sections=sections,
            acceptance_criteria=acceptance_criteria,
            raw_content=content
        )

    def _extract_yaml_header(
        self,
        content: str,
        file_path: Path
    ) -> tuple[dict, str]:
        """Extract YAML frontmatter from content.

        Args:
            content: Full ADR content
            file_path: Path for error messages

        Returns:
            Tuple of (yaml_dict, remaining_markdown)

        Raises:
            ADRParseError: If no valid YAML frontmatter found
        """
        match = self.YAML_PATTERN.match(content)

        if not match:
            raise ADRParseError(
                "No YAML frontmatter found. ADR must start with '---'",
                file_path=file_path,
                line=1
            )

        yaml_content = match.group(1)
        markdown = content[match.end():]

        try:
            yaml_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            # Extract line number from YAML error if available
            line = 1
            if hasattr(e, 'problem_mark') and e.problem_mark:
                line = e.problem_mark.line + 1
            raise ADRParseError(
                f"Invalid YAML in frontmatter: {e}",
                file_path=file_path,
                line=line
            ) from e

        if not isinstance(yaml_data, dict):
            raise ADRParseError(
                "YAML frontmatter must be a mapping/dict",
                file_path=file_path,
                line=1
            )

        return yaml_data, markdown

    def _parse_metadata(
        self,
        yaml_data: dict,
        file_path: Path
    ) -> ADRMetadata:
        """Convert YAML dict to ADRMetadata dataclass.

        Args:
            yaml_data: Parsed YAML dictionary
            file_path: Path for error messages

        Returns:
            ADRMetadata instance

        Raises:
            ADRParseError: If required fields are missing or invalid
        """
        # Required fields
        adr_id = yaml_data.get("adr_id")
        if not adr_id:
            raise ADRParseError(
                "Missing required field 'adr_id' in YAML header",
                file_path=file_path
            )

        title = yaml_data.get("title")
        if not title:
            raise ADRParseError(
                "Missing required field 'title' in YAML header",
                file_path=file_path
            )

        # Parse status
        status_str = yaml_data.get("status")
        if not status_str:
            raise ADRParseError(
                "Missing required field 'status' in YAML header",
                file_path=file_path
            )

        try:
            status = ADRStatus(status_str)
        except ValueError:
            valid_statuses = [s.value for s in ADRStatus]
            raise ADRParseError(
                f"Invalid status '{status_str}'. Valid values: {valid_statuses}",
                file_path=file_path
            )

        # Optional fields
        project_type = yaml_data.get("project_type", "helix_internal")

        # Parse component_type (optional)
        component_type = None
        if "component_type" in yaml_data and yaml_data["component_type"]:
            try:
                component_type = ComponentType(yaml_data["component_type"])
            except ValueError:
                valid_types = [t.value for t in ComponentType]
                raise ADRParseError(
                    f"Invalid component_type '{yaml_data['component_type']}'. "
                    f"Valid values: {valid_types}",
                    file_path=file_path
                )

        # Parse classification (optional)
        classification = None
        if "classification" in yaml_data and yaml_data["classification"]:
            try:
                classification = Classification(yaml_data["classification"])
            except ValueError:
                valid_class = [c.value for c in Classification]
                raise ADRParseError(
                    f"Invalid classification '{yaml_data['classification']}'. "
                    f"Valid values: {valid_class}",
                    file_path=file_path
                )

        # Parse change_scope (optional)
        change_scope = None
        if "change_scope" in yaml_data and yaml_data["change_scope"]:
            try:
                change_scope = ChangeScope(yaml_data["change_scope"])
            except ValueError:
                valid_scopes = [s.value for s in ChangeScope]
                raise ADRParseError(
                    f"Invalid change_scope '{yaml_data['change_scope']}'. "
                    f"Valid values: {valid_scopes}",
                    file_path=file_path
                )

        # Parse files
        files_data = yaml_data.get("files", {})
        if not isinstance(files_data, dict):
            files_data = {}

        files = ADRFiles(
            create=self._ensure_list(files_data.get("create", [])),
            modify=self._ensure_list(files_data.get("modify", [])),
            docs=self._ensure_list(files_data.get("docs", []))
        )

        # Parse depends_on
        depends_on = self._ensure_list(yaml_data.get("depends_on", []))

        # Parse project context (replaces spec.yaml)
        # Can be at top level or in 'meta' section
        meta = yaml_data.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        
        domain = yaml_data.get("domain") or meta.get("domain")
        language = yaml_data.get("language") or meta.get("language", "python")
        skills = self._ensure_list(
            yaml_data.get("skills") or meta.get("skills", [])
        )

        return ADRMetadata(
            adr_id=str(adr_id),
            title=str(title),
            status=status,
            project_type=str(project_type),
            component_type=component_type,
            classification=classification,
            change_scope=change_scope,
            files=files,
            depends_on=depends_on,
            domain=domain,
            language=str(language),
            skills=skills,
        )

    def _ensure_list(self, value) -> list[str]:
        """Ensure value is a list of strings.

        Args:
            value: Value that should be a list

        Returns:
            List of strings
        """
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _parse_sections(
        self,
        markdown: str,
        file_path: Path
    ) -> dict[str, ADRSection]:
        """Parse markdown into sections by heading.

        Args:
            markdown: Markdown content (without YAML header)
            file_path: Path for error messages

        Returns:
            Dict mapping section names to ADRSection objects
        """
        sections: dict[str, ADRSection] = {}
        lines = markdown.split('\n')

        # Calculate line offset (after YAML header)
        # Count lines in original content up to markdown start
        yaml_lines = 0

        current_section: Optional[ADRSection] = None
        current_content_lines: list[str] = []

        for i, line in enumerate(lines):
            line_number = yaml_lines + i + 1
            heading_match = self.HEADING_PATTERN.match(line)

            if heading_match:
                # Save previous section if exists
                if current_section is not None:
                    current_section.content = '\n'.join(current_content_lines).strip()
                    sections[current_section.name] = current_section

                # Start new section
                level = len(heading_match.group(1))
                name = heading_match.group(2).strip()

                current_section = ADRSection(
                    name=name,
                    content="",
                    level=level,
                    line_start=line_number
                )
                current_content_lines = []
            elif current_section is not None:
                current_content_lines.append(line)

        # Save last section
        if current_section is not None:
            current_section.content = '\n'.join(current_content_lines).strip()
            sections[current_section.name] = current_section

        return sections

    def _extract_all_acceptance_criteria(
        self,
        sections: dict[str, ADRSection]
    ) -> list[AcceptanceCriterion]:
        """Extract acceptance criteria from Akzeptanzkriterien and its subsections.

        ADRs may have acceptance criteria directly in the Akzeptanzkriterien section,
        or they may be organized into subsections (h3, h4) under Akzeptanzkriterien.
        This method collects criteria from the main section and all subsections
        that appear before the next level-2 heading.

        Args:
            sections: Dict of all parsed sections

        Returns:
            List of AcceptanceCriterion objects from all relevant sections
        """
        criteria: list[AcceptanceCriterion] = []

        # First, get the Akzeptanzkriterien section
        akz_section = sections.get("Akzeptanzkriterien")
        if not akz_section:
            return criteria

        akz_line_start = akz_section.line_start

        # Extract from main section
        criteria.extend(
            self._extract_acceptance_criteria(
                akz_section.content,
                akz_section.line_start
            )
        )

        # Find all sections that are subsections of Akzeptanzkriterien
        # (they start after Akzeptanzkriterien and have level > 2)
        for section_name, section in sections.items():
            if section.line_start <= akz_line_start:
                # This section is before Akzeptanzkriterien
                continue

            if section.level <= 2:
                # This is a sibling or parent section (like Konsequenzen)
                # Check if it comes after our section - we need to stop
                # But we can't know the order without more info, so we
                # check if this appears to be a child section by level
                continue

            # This is a potential subsection (h3 or lower)
            # Check if it's a direct child by looking at the line numbers
            # and whether a level-2 section has started between them
            is_subsection = True
            for other_name, other_section in sections.items():
                if other_section.level == 2 and other_section.line_start > akz_line_start and other_section.line_start < section.line_start:
                    # There's a level-2 section between Akzeptanzkriterien
                    # and this section, so it's not a subsection
                    is_subsection = False
                    break

            if is_subsection:
                criteria.extend(
                    self._extract_acceptance_criteria(
                        section.content,
                        section.line_start
                    )
                )

        return criteria

    def _extract_acceptance_criteria(
        self,
        section_content: str,
        line_offset: int
    ) -> list[AcceptanceCriterion]:
        """Extract acceptance criteria checkboxes from section.

        Args:
            section_content: Content of the Akzeptanzkriterien section
            line_offset: Starting line number of the section

        Returns:
            List of AcceptanceCriterion objects
        """
        criteria: list[AcceptanceCriterion] = []
        lines = section_content.split('\n')

        for i, line in enumerate(lines):
            match = self.CHECKBOX_PATTERN.match(line)
            if match:
                checkbox_state = match.group(1)
                text = match.group(2).strip()
                checked = checkbox_state.lower() == 'x'

                criteria.append(AcceptanceCriterion(
                    text=text,
                    checked=checked,
                    line_number=line_offset + i + 1
                ))

        return criteria
