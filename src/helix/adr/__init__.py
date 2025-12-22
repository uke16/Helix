"""ADR (Architecture Decision Records) System for HELIX v4.

This package provides tools for parsing and validating Architecture Decision Records
following the ADR-086 Template v2 format.

Modules:
    parser: Parse ADR documents from files or strings
    validator: Validate ADRs against template requirements (Phase 3)

Example:
    >>> from helix.adr import ADRParser, ADRDocument
    >>> parser = ADRParser()
    >>> adr = parser.parse_file(Path("adr/001-feature.md"))
    >>> print(adr.metadata.title)
    >>> print(adr.sections["Kontext"].content)

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

__all__ = [
    # Main classes
    "ADRParser",
    "ADRParseError",
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
