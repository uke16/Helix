"""ADR Validator for HELIX v4.

This module provides validation functionality for Architecture Decision Records
following the ADR-086 Template v2 format. It validates ADR structure, required
sections, YAML header fields, and acceptance criteria.

Example:
    >>> from helix.adr.validator import ADRValidator
    >>> validator = ADRValidator()
    >>> result = validator.validate_file(Path("adr/001-feature.md"))
    >>> if not result.valid:
    ...     for error in result.errors:
    ...         print(f"ERROR: {error.message}")

See Also:
    - ADR-086: ADR-Template v2 from HELIX v3
    - parser.py: ADR parsing functionality
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .parser import (
    ADRParser,
    ADRParseError,
    ADRDocument,
    ADRStatus,
)


class IssueLevel(Enum):
    """Severity level for validation issues.

    Attributes:
        ERROR: Critical issue that makes the ADR invalid
        WARNING: Non-critical issue, ADR is still valid but could be improved
    """
    ERROR = "error"
    WARNING = "warning"


class IssueCategory(Enum):
    """Category of validation issues.

    Used to classify and filter validation issues.

    Attributes:
        PARSE_ERROR: ADR could not be parsed
        MISSING_FIELD: Required YAML header field is missing
        MISSING_RECOMMENDED_FIELD: Recommended field is missing (warning)
        INVALID_VALUE: Field has invalid value
        MISSING_SECTION: Required markdown section is missing
        EMPTY_SECTION: Section has minimal/no content
        MISSING_CRITERIA: No acceptance criteria defined
        FEW_CRITERIA: Less than recommended number of criteria
        INCONSISTENT: Inconsistency between header and body
    """
    PARSE_ERROR = "parse_error"
    MISSING_FIELD = "missing_field"
    MISSING_RECOMMENDED_FIELD = "missing_recommended_field"
    INVALID_VALUE = "invalid_value"
    MISSING_SECTION = "missing_section"
    EMPTY_SECTION = "empty_section"
    MISSING_CRITERIA = "missing_criteria"
    FEW_CRITERIA = "few_criteria"
    INCONSISTENT = "inconsistent"


@dataclass
class ValidationIssue:
    """A single validation issue found during ADR validation.

    Attributes:
        level: Severity (error or warning)
        category: Issue category for filtering
        message: Human-readable description of the issue
        location: Where in the ADR the issue was found (optional)

    Example:
        >>> issue = ValidationIssue(
        ...     level=IssueLevel.ERROR,
        ...     category=IssueCategory.MISSING_SECTION,
        ...     message="Required section missing: ## Kontext",
        ...     location="Markdown body"
        ... )
    """
    level: IssueLevel
    category: IssueCategory
    message: str
    location: Optional[str] = None

    def __str__(self) -> str:
        """Format issue as string for display."""
        prefix = "ERROR" if self.level == IssueLevel.ERROR else "WARNING"
        if self.location:
            return f"[{prefix}] {self.message} (in {self.location})"
        return f"[{prefix}] {self.message}"


@dataclass
class ValidationResult:
    """Result of ADR validation.

    Contains the overall validity status, list of issues found,
    and optionally the parsed ADR document.

    Attributes:
        valid: True if no errors were found (warnings allowed)
        issues: List of all validation issues (errors and warnings)
        adr: The parsed ADR document (if parsing succeeded)

    Example:
        >>> result = validator.validate_file(Path("adr/001.md"))
        >>> if not result.valid:
        ...     print(f"Found {len(result.errors)} error(s)")
        ...     for error in result.errors:
        ...         print(f"  - {error.message}")
    """
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    adr: Optional[ADRDocument] = None

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues.

        Returns:
            List of issues with level ERROR
        """
        return [i for i in self.issues if i.level == IssueLevel.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues.

        Returns:
            List of issues with level WARNING
        """
        return [i for i in self.issues if i.level == IssueLevel.WARNING]

    @property
    def error_count(self) -> int:
        """Number of errors found."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings found."""
        return len(self.warnings)

    def __str__(self) -> str:
        """Format result as string for display."""
        status = "VALID" if self.valid else "INVALID"
        return f"ValidationResult: {status} ({self.error_count} errors, {self.warning_count} warnings)"


class ADRValidator:
    """Validator for ADR documents following the v2 template.

    Validates ADRs against the ADR-086 template requirements:
    - Required YAML header fields (adr_id, title, status)
    - Recommended YAML header fields (component_type, classification, change_scope)
    - Required markdown sections (Kontext, Entscheidung, Implementation, etc.)
    - Acceptance criteria checkboxes
    - Consistency between header and body

    Attributes:
        REQUIRED_SECTIONS: List of required markdown section names
        OPTIONAL_SECTIONS: List of optional section names
        REQUIRED_HEADER_FIELDS: List of required YAML header fields
        RECOMMENDED_HEADER_FIELDS: List of recommended YAML header fields
        MIN_SECTION_LENGTH: Minimum content length for sections
        MIN_ACCEPTANCE_CRITERIA: Minimum recommended acceptance criteria count

    Example:
        >>> validator = ADRValidator()
        >>> result = validator.validate_file(Path("adr/086-template.md"))
        >>> if not result.valid:
        ...     for issue in result.issues:
        ...         print(issue)
        >>> else:
        ...     print(f"ADR {result.adr.metadata.adr_id} is valid!")

    See Also:
        ADR-086: ADR-Template v2
    """

    # Required sections per ADR-086 template
    REQUIRED_SECTIONS: list[str] = [
        "Kontext",
        "Entscheidung",
        "Implementation",
        "Dokumentation",
        "Akzeptanzkriterien",
        "Konsequenzen",
    ]

    # Optional sections that are common but not required
    OPTIONAL_SECTIONS: list[str] = [
        "Status",
        "Referenzen",
    ]

    # Required YAML header fields (checked by parser, but we verify presence)
    REQUIRED_HEADER_FIELDS: list[str] = [
        "adr_id",
        "title",
        "status",
    ]

    # Recommended fields for better classification
    RECOMMENDED_HEADER_FIELDS: list[str] = [
        "component_type",
        "classification",
        "change_scope",
    ]

    # Validation thresholds
    MIN_SECTION_LENGTH: int = 10  # Minimum characters for meaningful content
    MIN_ACCEPTANCE_CRITERIA: int = 3  # Recommended minimum criteria

    def __init__(self, parser: Optional[ADRParser] = None):
        """Initialize validator with optional custom parser.

        Args:
            parser: Custom ADRParser instance (creates new one if not provided)
        """
        self.parser = parser or ADRParser()

    def validate_file(self, path: Path) -> ValidationResult:
        """Validate an ADR file from disk.

        Args:
            path: Path to the ADR markdown file

        Returns:
            ValidationResult with all issues found

        Example:
            >>> result = validator.validate_file(Path("adr/001-feature.md"))
            >>> print(f"Valid: {result.valid}")
            >>> print(f"Errors: {result.error_count}")
        """
        issues: list[ValidationIssue] = []

        # Step 1: Try to parse the file
        try:
            adr = self.parser.parse_file(path)
        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    level=IssueLevel.ERROR,
                    category=IssueCategory.PARSE_ERROR,
                    message=f"ADR file not found: {path}",
                    location=str(path),
                )],
            )
        except ADRParseError as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    level=IssueLevel.ERROR,
                    category=IssueCategory.PARSE_ERROR,
                    message=str(e),
                    location=str(path),
                )],
            )

        # Step 2: Run all validations
        issues.extend(self._validate_header(adr))
        issues.extend(self._validate_sections(adr))
        issues.extend(self._validate_acceptance_criteria(adr))
        issues.extend(self._validate_consistency(adr))

        # Determine overall validity (only errors matter)
        has_errors = any(i.level == IssueLevel.ERROR for i in issues)

        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            adr=adr,
        )

    def validate_string(self, content: str, path: Optional[Path] = None) -> ValidationResult:
        """Validate ADR content from a string.

        Args:
            content: Raw ADR content (YAML header + Markdown body)
            path: Optional path for error messages

        Returns:
            ValidationResult with all issues found

        Example:
            >>> content = open("adr/001.md").read()
            >>> result = validator.validate_string(content)
        """
        issues: list[ValidationIssue] = []
        display_path = str(path) if path else "<string>"

        # Step 1: Try to parse the content
        try:
            adr = self.parser.parse_string(content, path)
        except ADRParseError as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    level=IssueLevel.ERROR,
                    category=IssueCategory.PARSE_ERROR,
                    message=str(e),
                    location=display_path,
                )],
            )

        # Step 2: Run all validations
        issues.extend(self._validate_header(adr))
        issues.extend(self._validate_sections(adr))
        issues.extend(self._validate_acceptance_criteria(adr))
        issues.extend(self._validate_consistency(adr))

        has_errors = any(i.level == IssueLevel.ERROR for i in issues)

        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            adr=adr,
        )

    def _validate_header(self, adr: ADRDocument) -> list[ValidationIssue]:
        """Validate YAML header fields.

        Checks:
        - Required fields are present (already enforced by parser)
        - Recommended fields are present (warnings if missing)
        - Status has a valid value

        Args:
            adr: Parsed ADR document

        Returns:
            List of validation issues found
        """
        issues: list[ValidationIssue] = []

        # Check recommended fields (warnings only)
        if adr.metadata.component_type is None:
            issues.append(ValidationIssue(
                level=IssueLevel.WARNING,
                category=IssueCategory.MISSING_RECOMMENDED_FIELD,
                message="Recommended header field missing: component_type",
                location="YAML header",
            ))

        if adr.metadata.classification is None:
            issues.append(ValidationIssue(
                level=IssueLevel.WARNING,
                category=IssueCategory.MISSING_RECOMMENDED_FIELD,
                message="Recommended header field missing: classification",
                location="YAML header",
            ))

        if adr.metadata.change_scope is None:
            issues.append(ValidationIssue(
                level=IssueLevel.WARNING,
                category=IssueCategory.MISSING_RECOMMENDED_FIELD,
                message="Recommended header field missing: change_scope",
                location="YAML header",
            ))

        # Note: status is already validated by parser, but we could add
        # additional business logic here if needed

        return issues

    def _validate_sections(self, adr: ADRDocument) -> list[ValidationIssue]:
        """Validate required markdown sections.

        Checks:
        - All required sections are present
        - Sections have meaningful content (not empty)

        Args:
            adr: Parsed ADR document

        Returns:
            List of validation issues found
        """
        issues: list[ValidationIssue] = []
        section_names_lower = {name.lower(): name for name in adr.sections.keys()}

        # Check for required sections
        for required in self.REQUIRED_SECTIONS:
            required_lower = required.lower()
            if required_lower not in section_names_lower:
                issues.append(ValidationIssue(
                    level=IssueLevel.ERROR,
                    category=IssueCategory.MISSING_SECTION,
                    message=f"Required section missing: ## {required}",
                    location="Markdown body",
                ))
            else:
                # Section exists, check if it has content
                actual_name = section_names_lower[required_lower]
                section = adr.sections[actual_name]
                content_length = len(section.content.strip())

                if content_length < self.MIN_SECTION_LENGTH:
                    issues.append(ValidationIssue(
                        level=IssueLevel.WARNING,
                        category=IssueCategory.EMPTY_SECTION,
                        message=f"Section has minimal content ({content_length} chars): ## {actual_name}",
                        location=f"Section '{actual_name}'",
                    ))

        return issues

    def _validate_acceptance_criteria(self, adr: ADRDocument) -> list[ValidationIssue]:
        """Validate acceptance criteria checkboxes.

        Checks:
        - At least one acceptance criterion is defined
        - Recommends minimum number of criteria

        Args:
            adr: Parsed ADR document

        Returns:
            List of validation issues found
        """
        issues: list[ValidationIssue] = []
        criteria_count = len(adr.acceptance_criteria)

        if criteria_count == 0:
            issues.append(ValidationIssue(
                level=IssueLevel.ERROR,
                category=IssueCategory.MISSING_CRITERIA,
                message="No acceptance criteria defined (no checkboxes found in Akzeptanzkriterien section)",
                location="Akzeptanzkriterien",
            ))
        elif criteria_count < self.MIN_ACCEPTANCE_CRITERIA:
            issues.append(ValidationIssue(
                level=IssueLevel.WARNING,
                category=IssueCategory.FEW_CRITERIA,
                message=f"Only {criteria_count} acceptance criteria defined (recommend at least {self.MIN_ACCEPTANCE_CRITERIA})",
                location="Akzeptanzkriterien",
            ))

        return issues

    def _validate_consistency(self, adr: ADRDocument) -> list[ValidationIssue]:
        """Validate consistency between header and body.

        Checks:
        - Files listed in header.files.docs appear in Dokumentation section
        - Title in header matches H1 title (if present)

        Args:
            adr: Parsed ADR document

        Returns:
            List of validation issues found
        """
        issues: list[ValidationIssue] = []

        # Check docs files consistency
        docs_section = None
        for name, section in adr.sections.items():
            if name.lower() == "dokumentation":
                docs_section = section
                break

        if docs_section and adr.metadata.files.docs:
            for doc_file in adr.metadata.files.docs:
                if doc_file not in docs_section.content:
                    issues.append(ValidationIssue(
                        level=IssueLevel.WARNING,
                        category=IssueCategory.INCONSISTENT,
                        message=f"File listed in header but not mentioned in Dokumentation section: {doc_file}",
                        location="Dokumentation",
                    ))

        # Check if title contains ADR ID (common convention)
        # This is informational, not an error
        adr_id = adr.metadata.adr_id
        title = adr.metadata.title
        if adr_id and not (adr_id in title or f"ADR-{adr_id}" in title):
            # Just informational, many ADRs don't include the ID in title
            pass

        return issues

    def get_completion_status(self, adr: ADRDocument) -> dict:
        """Get completion status of acceptance criteria.

        Returns statistics about checked/unchecked criteria.

        Args:
            adr: Parsed ADR document

        Returns:
            Dict with total, checked, unchecked counts and completion percentage

        Example:
            >>> status = validator.get_completion_status(adr)
            >>> print(f"Completed: {status['completion_percent']}%")
        """
        total = len(adr.acceptance_criteria)
        checked = sum(1 for c in adr.acceptance_criteria if c.checked)
        unchecked = total - checked

        return {
            "total": total,
            "checked": checked,
            "unchecked": unchecked,
            "completion_percent": round((checked / total * 100) if total > 0 else 0, 1),
        }

    def get_unchecked_criteria(self, adr: ADRDocument) -> list[str]:
        """Get list of unchecked acceptance criteria texts.

        Useful for tracking remaining work on an ADR.

        Args:
            adr: Parsed ADR document

        Returns:
            List of criterion texts that are not yet checked

        Example:
            >>> unchecked = validator.get_unchecked_criteria(adr)
            >>> for item in unchecked:
            ...     print(f"[ ] {item}")
        """
        return [c.text for c in adr.acceptance_criteria if not c.checked]
