"""
ADR Structure Validator.

Validates that ADRs in LLM responses contain required sections
and proper YAML frontmatter.

ADR-038: Deterministic LLM Response Enforcement
"""

import re
from typing import Optional

import yaml

from .base import ResponseValidator, ValidationIssue


class ADRStructureValidator(ResponseValidator):
    """
    Validates ADR structure when response contains an ADR.

    Only activates when the response contains ADR-formatted content
    (identified by YAML frontmatter with adr_id field).

    Checks:
        - YAML frontmatter with required fields (adr_id, title, status)
        - Required sections (Kontext, Entscheidung, Akzeptanzkriterien)
        - Minimum acceptance criteria (warning if < 3)

    Example:
        validator = ADRStructureValidator()
        issues = validator.validate(adr_response, {})
    """

    # Required fields in YAML frontmatter
    REQUIRED_YAML_FIELDS = ["adr_id", "title", "status"]

    # Required markdown sections
    REQUIRED_SECTIONS = ["Kontext", "Entscheidung", "Akzeptanzkriterien"]

    # Minimum recommended acceptance criteria
    MIN_CRITERIA = 3

    @property
    def name(self) -> str:
        """Unique validator name."""
        return "adr_structure"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """
        Validate ADR structure if response contains an ADR.

        Only validates if the response appears to be an ADR
        (contains YAML frontmatter with adr_id).

        Args:
            response: The LLM response text
            context: Validation context (unused)

        Returns:
            List of validation issues (empty if valid or not an ADR)
        """
        # Only validate if this is an ADR
        if not self._is_adr(response):
            return []

        issues: list[ValidationIssue] = []

        # Validate YAML header
        issues.extend(self._validate_yaml_header(response))

        # Validate required sections
        issues.extend(self._validate_sections(response))

        # Validate acceptance criteria
        issues.extend(self._validate_criteria(response))

        return issues

    def _is_adr(self, response: str) -> bool:
        """
        Check if response contains an ADR.

        Args:
            response: Response text to check

        Returns:
            True if response appears to be an ADR
        """
        # Look for YAML frontmatter with adr_id
        return "---\nadr_id:" in response or "---\n adr_id:" in response

    def _validate_yaml_header(self, response: str) -> list[ValidationIssue]:
        """
        Validate YAML frontmatter.

        Args:
            response: ADR response text

        Returns:
            List of issues found in YAML header
        """
        issues: list[ValidationIssue] = []

        # Extract YAML frontmatter
        yaml_match = re.search(
            r"^---\n(.*?)\n---", response, re.DOTALL | re.MULTILINE
        )

        if not yaml_match:
            return [
                ValidationIssue(
                    code="MISSING_YAML_HEADER",
                    message="ADR fehlt YAML-Header",
                    fix_hint="Füge YAML-Header mit --- Delimitern hinzu",
                )
            ]

        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            if not isinstance(metadata, dict):
                return [
                    ValidationIssue(
                        code="INVALID_YAML",
                        message="ADR YAML-Header ist kein gültiges Dictionary",
                        fix_hint="Prüfe YAML-Syntax im Header",
                    )
                ]

            # Check required fields
            for field in self.REQUIRED_YAML_FIELDS:
                if field not in metadata:
                    issues.append(
                        ValidationIssue(
                            code="MISSING_ADR_FIELD",
                            message=f"ADR fehlt Pflichtfeld im Header: {field}",
                            fix_hint=f"Füge '{field}' zum YAML-Header hinzu",
                        )
                    )

        except yaml.YAMLError as e:
            issues.append(
                ValidationIssue(
                    code="INVALID_YAML",
                    message=f"ADR hat ungültigen YAML-Header: {str(e)[:100]}",
                    fix_hint="Prüfe YAML-Syntax im Header",
                )
            )

        return issues

    def _validate_sections(self, response: str) -> list[ValidationIssue]:
        """
        Validate required markdown sections.

        Args:
            response: ADR response text

        Returns:
            List of issues for missing sections
        """
        issues: list[ValidationIssue] = []

        for section in self.REQUIRED_SECTIONS:
            # Check for ## Section heading
            if f"## {section}" not in response:
                issues.append(
                    ValidationIssue(
                        code="MISSING_ADR_SECTION",
                        message=f"ADR fehlt Section: ## {section}",
                        fix_hint=f"Füge Section '## {section}' mit Inhalt hinzu",
                    )
                )

        return issues

    def _validate_criteria(self, response: str) -> list[ValidationIssue]:
        """
        Validate acceptance criteria.

        Args:
            response: ADR response text

        Returns:
            Warning if too few criteria
        """
        issues: list[ValidationIssue] = []

        if "## Akzeptanzkriterien" not in response:
            # Already reported as missing section
            return issues

        # Extract criteria section
        criteria_start = response.find("## Akzeptanzkriterien")
        criteria_section = response[criteria_start:]

        # Stop at next section
        next_section = re.search(r"\n## ", criteria_section[3:])
        if next_section:
            criteria_section = criteria_section[: next_section.start() + 3]

        # Count checkboxes
        checkbox_count = len(re.findall(r"- \[ \]", criteria_section))

        if checkbox_count < self.MIN_CRITERIA:
            issues.append(
                ValidationIssue(
                    code="INSUFFICIENT_CRITERIA",
                    message=f"ADR hat nur {checkbox_count} Akzeptanzkriterien "
                    f"(mindestens {self.MIN_CRITERIA} empfohlen)",
                    fix_hint="Füge mehr konkrete, testbare Akzeptanzkriterien hinzu",
                    severity="warning",
                )
            )

        return issues

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """
        No automatic fallback for ADR structure issues.

        ADR structure issues require manual correction as they
        involve content that cannot be automatically generated.

        Args:
            response: The invalid response
            context: Validation context

        Returns:
            None (no fallback available)
        """
        return None
