"""Concept-to-ADR diff for validating completeness.

Layer 3 of the ADR validation system. Compares a source concept
document with the generated ADR to find missing sections.

When an ADR is created from a concept document (e.g., during a
Consultant meeting), important content might be lost in translation.
This module detects such losses by comparing the sections present
in the concept with those in the final ADR.

Example:
    >>> from helix.adr.concept_diff import ConceptDiffer
    >>> from helix.adr import ADRParser
    >>>
    >>> parser = ADRParser()
    >>> adr = parser.parse_file(Path("output/ADR-feature.md"))
    >>>
    >>> differ = ConceptDiffer()
    >>> result = differ.compare(
    ...     concept_path=Path("output/concept.md"),
    ...     adr=adr
    ... )
    >>> if result.missing_in_adr:
    ...     print(f"Missing sections: {result.missing_in_adr}")

See Also:
    - ADR-015: Approval & Validation System
    - ADR-014: Documentation Architecture (motivation)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import re


# Forward reference for type hints
try:
    from helix.adr.parser import ADRDocument
except ImportError:
    ADRDocument = Any  # type: ignore


@dataclass
class ConceptSection:
    """A section extracted from a concept document.

    Attributes:
        name: Section heading text
        level: Heading level (2 for ##, 3 for ###, etc.)
        content: Content under the heading
        line_start: Line number where section starts
    """
    name: str
    level: int
    content: str = ""
    line_start: int = 0


@dataclass
class ConceptDiffResult:
    """Result of concept-ADR comparison.

    Contains information about section coverage between the
    source concept and the generated ADR.

    Attributes:
        concept_path: Path to the concept file
        concept_sections: List of section names found in concept
        adr_sections: List of section names found in ADR
        missing_in_adr: Sections in concept but not in ADR
        extra_in_adr: Sections in ADR but not in concept
        coverage_percent: Percentage of concept sections in ADR
        warnings: List of warning messages
    """
    concept_path: Path
    concept_sections: list[str] = field(default_factory=list)
    adr_sections: list[str] = field(default_factory=list)
    missing_in_adr: list[str] = field(default_factory=list)
    extra_in_adr: list[str] = field(default_factory=list)
    coverage_percent: float = 100.0
    warnings: list[str] = field(default_factory=list)

    @property
    def has_missing_sections(self) -> bool:
        """Check if any sections are missing in the ADR."""
        return len(self.missing_in_adr) > 0

    @property
    def summary(self) -> str:
        """Generate a summary message."""
        if not self.missing_in_adr:
            return f"All {len(self.concept_sections)} concept sections covered ({self.coverage_percent}%)"
        return (
            f"{len(self.missing_in_adr)} sections missing from ADR "
            f"({self.coverage_percent}% coverage): {', '.join(self.missing_in_adr)}"
        )


class ConceptDiffer:
    """Compares concept document with generated ADR.

    Finds missing sections that were in the concept but not in the ADR.
    This helps detect information loss when converting concepts to ADRs.

    Attributes:
        IGNORED_SECTIONS: Set of section names to ignore in comparison

    Example:
        >>> differ = ConceptDiffer()
        >>> result = differ.compare(
        ...     concept_path=Path("output/concept.md"),
        ...     adr=parsed_adr
        ... )
        >>> if result.missing_in_adr:
        ...     print(f"Missing: {result.missing_in_adr}")
    """

    # Sections that are typically in concepts but don't map 1:1 to ADR sections
    IGNORED_SECTIONS: set[str] = {
        # Meta sections
        "status",
        "zusammenfassung",
        "summary",
        "referenzen",
        "references",
        "meta",
        "übersicht",
        "overview",
        # Discussion sections
        "fragen",
        "questions",
        "open questions",
        "offene fragen",
        "diskussion",
        "discussion",
        # Version/history
        "changelog",
        "history",
        "versionen",
        "versions",
        # Appendix sections often have different names
        "appendix",
        "anhang",
        "glossar",
        "glossary",
    }

    # Section name mappings (concept name -> ADR name)
    SECTION_MAPPINGS: dict[str, str] = {
        "kontext": "kontext",
        "context": "kontext",
        "hintergrund": "kontext",
        "background": "kontext",
        "problem": "kontext",
        "entscheidung": "entscheidung",
        "decision": "entscheidung",
        "lösung": "entscheidung",
        "solution": "entscheidung",
        "umsetzung": "implementation",
        "implementation": "implementation",
        "implementierung": "implementation",
        "technische umsetzung": "implementation",
        "doku": "dokumentation",
        "dokumentation": "dokumentation",
        "documentation": "dokumentation",
        "docs": "dokumentation",
        "akzeptanzkriterien": "akzeptanzkriterien",
        "acceptance criteria": "akzeptanzkriterien",
        "kriterien": "akzeptanzkriterien",
        "konsequenzen": "konsequenzen",
        "consequences": "konsequenzen",
        "auswirkungen": "konsequenzen",
        "trade-offs": "konsequenzen",
        "tradeoffs": "konsequenzen",
        "migration": "migration",
        "migrationsplan": "migration",
        "migration plan": "migration",
    }

    def compare(
        self,
        concept_path: Path,
        adr: "ADRDocument"
    ) -> ConceptDiffResult:
        """Compare concept with ADR.

        Extracts sections from both documents and identifies missing
        sections that were in the concept but not in the ADR.

        Args:
            concept_path: Path to concept markdown file
            adr: Parsed ADR document

        Returns:
            ConceptDiffResult with section comparison details
        """
        warnings: list[str] = []

        # Handle non-existent concept file
        if not concept_path.exists():
            return ConceptDiffResult(
                concept_path=concept_path,
                concept_sections=[],
                adr_sections=list(adr.sections.keys()),
                missing_in_adr=[],
                extra_in_adr=[],
                coverage_percent=100.0,
                warnings=["Concept file not found - skipping comparison"],
            )

        # Read and parse concept
        try:
            concept_content = concept_path.read_text(encoding="utf-8")
        except Exception as e:
            return ConceptDiffResult(
                concept_path=concept_path,
                concept_sections=[],
                adr_sections=list(adr.sections.keys()),
                missing_in_adr=[],
                extra_in_adr=[],
                coverage_percent=100.0,
                warnings=[f"Failed to read concept file: {e}"],
            )

        # Extract sections from both documents
        concept_sections = self._extract_sections(concept_content)
        adr_sections_lower = {name.lower(): name for name in adr.sections.keys()}

        # Filter out ignored sections from concept
        relevant_concept = [
            s for s in concept_sections
            if s.lower() not in self.IGNORED_SECTIONS
        ]

        # Normalize section names for comparison
        concept_normalized = self._normalize_sections(relevant_concept)
        adr_normalized = set(adr_sections_lower.keys())

        # Find missing sections (in concept but not in ADR)
        missing = []
        for original, normalized in zip(relevant_concept, concept_normalized):
            if normalized not in adr_normalized:
                missing.append(original)

        # Find extra sections (in ADR but not in concept)
        # This is informational only
        extra = []
        for adr_name_lower in adr_normalized:
            found = False
            for normalized in concept_normalized:
                if normalized == adr_name_lower:
                    found = True
                    break
            if not found and adr_name_lower not in self.IGNORED_SECTIONS:
                extra.append(adr_sections_lower[adr_name_lower])

        # Calculate coverage percentage
        if relevant_concept:
            covered = len(relevant_concept) - len(missing)
            coverage = covered / len(relevant_concept) * 100
        else:
            coverage = 100.0

        return ConceptDiffResult(
            concept_path=concept_path,
            concept_sections=concept_sections,
            adr_sections=list(adr.sections.keys()),
            missing_in_adr=missing,
            extra_in_adr=extra,
            coverage_percent=round(coverage, 1),
            warnings=warnings,
        )

    def _extract_sections(self, content: str) -> list[str]:
        """Extract H2 section names from markdown.

        Parses markdown content to find all ## headings and extracts
        their names (without the ## prefix).

        Args:
            content: Markdown content

        Returns:
            List of section names (original casing preserved)
        """
        sections = []

        for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
            section_name = match.group(1).strip()
            # Remove markdown formatting (bold, italic, code)
            section_name = re.sub(r"[*_`]", "", section_name)
            # Remove trailing punctuation
            section_name = section_name.rstrip(":")
            sections.append(section_name)

        return sections

    def _normalize_sections(self, sections: list[str]) -> list[str]:
        """Normalize section names for comparison.

        Applies mappings to convert various section names to their
        canonical ADR equivalents.

        Args:
            sections: List of section names

        Returns:
            List of normalized section names
        """
        normalized = []

        for section in sections:
            section_lower = section.lower()

            # Check if there's a mapping
            if section_lower in self.SECTION_MAPPINGS:
                normalized.append(self.SECTION_MAPPINGS[section_lower])
            else:
                normalized.append(section_lower)

        return normalized

    def get_detailed_diff(
        self,
        concept_path: Path,
        adr: "ADRDocument"
    ) -> dict[str, Any]:
        """Get a detailed diff with content comparison.

        Provides more detail than compare(), including content length
        comparisons for matching sections.

        Args:
            concept_path: Path to concept markdown
            adr: Parsed ADR document

        Returns:
            Dict with detailed comparison information
        """
        result = self.compare(concept_path, adr)

        # Read concept content
        concept_content = ""
        if concept_path.exists():
            concept_content = concept_path.read_text(encoding="utf-8")

        # Build section-by-section comparison
        sections_detail = []

        for section_name in result.concept_sections:
            # Find matching ADR section
            adr_match = None
            normalized = self.SECTION_MAPPINGS.get(
                section_name.lower(),
                section_name.lower()
            )
            for adr_name in adr.sections:
                if adr_name.lower() == normalized:
                    adr_match = adr.sections[adr_name]
                    break

            sections_detail.append({
                "concept_name": section_name,
                "adr_match": adr_match.name if adr_match else None,
                "in_adr": adr_match is not None,
                "adr_content_length": len(adr_match.content) if adr_match else 0,
            })

        return {
            "concept_path": str(result.concept_path),
            "coverage_percent": result.coverage_percent,
            "missing_count": len(result.missing_in_adr),
            "missing_sections": result.missing_in_adr,
            "sections_detail": sections_detail,
            "warnings": result.warnings,
        }


def check_concept_coverage(
    adr_path: Path,
    concept_path: Path
) -> ConceptDiffResult:
    """Convenience function to check concept coverage.

    Parses the ADR and compares it with the concept document.

    Args:
        adr_path: Path to the ADR file
        concept_path: Path to the concept file

    Returns:
        ConceptDiffResult

    Raises:
        FileNotFoundError: If ADR file doesn't exist
        ADRParseError: If ADR can't be parsed
    """
    from helix.adr import ADRParser

    parser = ADRParser()
    adr = parser.parse_file(adr_path)

    differ = ConceptDiffer()
    return differ.compare(concept_path, adr)
