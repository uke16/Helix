"""ADR (Architecture Decision Records) System for HELIX v4.

This package provides tools for parsing and validating Architecture Decision Records
following the ADR-086 Template v2 format.

Modules:
    parser: Parse ADR documents from files or strings
    validator: Validate ADRs against template requirements

Example:
    >>> from helix.adr import ADRParser, ADRValidator, ADRDocument
    >>> parser = ADRParser()
    >>> adr = parser.parse_file(Path("adr/001-feature.md"))
    >>> print(adr.metadata.title)
    >>> print(adr.sections["Kontext"].content)
    >>>
    >>> # Validate ADR
    >>> validator = ADRValidator()
    >>> result = validator.validate_file(Path("adr/001-feature.md"))
    >>> if not result.valid:
    ...     for error in result.errors:
    ...         print(f"ERROR: {error.message}")

See Also:
    - ADR-086: ADR-Template v2 (defines the template format)
    - docs/ADR-TEMPLATE.md: Template for new ADRs
"""

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

from helix.adr.validator import (
    ADRValidator,
    ValidationResult,
    ValidationIssue,
    IssueLevel,
    IssueCategory,
)

__all__ = [
    # Parser classes
    "ADRParser",
    "ADRParseError",
    # Validator classes
    "ADRValidator",
    "ValidationResult",
    "ValidationIssue",
    "IssueLevel",
    "IssueCategory",
    # Data classes
    "ADRDocument",
    "ADRMetadata",
    "ADRSection",
    "ADRFiles",
    "AcceptanceCriterion",
    # Enums
    "ADRStatus",
    "ComponentType",
    "Classification",
    "ChangeScope",
]
