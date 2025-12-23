"""Contextual completeness validation for ADRs.

Layer 2 of the ADR validation system. Applies context-dependent
rules based on ADR metadata (change_scope, classification, etc.).

This module loads rules from config/adr-completeness-rules.yaml and
evaluates them against parsed ADR documents.

Example:
    >>> from helix.adr.completeness import CompletenessValidator
    >>> from helix.adr import ADRParser
    >>>
    >>> parser = ADRParser()
    >>> adr = parser.parse_file(Path("output/ADR-feature.md"))
    >>>
    >>> validator = CompletenessValidator()
    >>> result = validator.check(adr)
    >>> if not result.passed:
    ...     for issue in result.issues:
    ...         print(issue)

See Also:
    - ADR-015: Approval & Validation System
    - config/adr-completeness-rules.yaml: Rule definitions
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import re

import yaml

# Import from sibling modules (these exist in the helix.adr package)
# When integrated, change to: from .parser import ADRDocument
# For now, we use a forward reference approach
try:
    from helix.adr.parser import ADRDocument
    from helix.adr.validator import ValidationIssue, IssueLevel, IssueCategory
except ImportError:
    # Fallback for standalone testing
    ADRDocument = Any  # type: ignore

    class IssueLevel:
        """Severity level for validation issues."""
        ERROR = "error"
        WARNING = "warning"

    class IssueCategory:
        """Category of validation issues."""
        MISSING_SECTION = "missing_section"
        EMPTY_SECTION = "empty_section"
        MISSING_CRITERIA = "missing_criteria"

    @dataclass
    class ValidationIssue:
        """A single validation issue."""
        level: str
        category: str
        message: str
        location: Optional[str] = None


@dataclass
class CompletenessRule:
    """A contextual completeness rule.

    Represents a single rule loaded from the YAML configuration.
    Rules have conditions (when) and requirements (require).

    Attributes:
        id: Unique identifier for the rule (e.g., "major-needs-migration")
        name: Human-readable name
        when: Dict of conditions that must match for rule to apply
        require: Dict of requirements to check when rule applies
        severity: Either "error" or "warning"
        message: Message to show when rule fails
    """
    id: str
    name: str
    when: dict
    require: dict
    severity: str  # "error" | "warning"
    message: str


@dataclass
class CompletenessResult:
    """Result of completeness validation.

    Contains the overall pass/fail status and all issues found.

    Attributes:
        passed: True if no errors (warnings allowed)
        issues: List of all ValidationIssue objects
        rules_checked: Total number of rules in config
        rules_triggered: Number of rules whose conditions matched
        rules_passed: Number of triggered rules that passed
    """
    passed: bool
    issues: list = field(default_factory=list)
    rules_checked: int = 0
    rules_triggered: int = 0
    rules_passed: int = 0


class CompletenessValidator:
    """Validates ADRs against contextual rules.

    Loads rules from YAML configuration and evaluates them against
    ADR documents. Rules are only checked if their `when` conditions
    match the ADR's metadata.

    Attributes:
        rules_path: Path to the YAML rules file
        rules: List of loaded CompletenessRule objects
        base_rules: Dict of base rules (always active)

    Example:
        >>> validator = CompletenessValidator()
        >>> result = validator.check(adr_document)
        >>> if not result.passed:
        ...     for issue in result.issues:
        ...         print(issue)
    """

    # Default path relative to HELIX root
    DEFAULT_RULES_PATH = Path("config/adr-completeness-rules.yaml")

    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize with rule file.

        Args:
            rules_path: Path to YAML rules file.
                        Default: config/adr-completeness-rules.yaml
        """
        self.rules_path = rules_path or self.DEFAULT_RULES_PATH
        self.rules: list[CompletenessRule] = []
        self.base_rules: dict = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from YAML file.

        Parses the YAML configuration and creates CompletenessRule
        objects for each contextual rule defined.
        """
        if not self.rules_path.exists():
            # No rules file - use empty rules
            return

        try:
            with open(self.rules_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            # Log error but continue with empty rules
            print(f"Warning: Failed to parse rules file: {e}")
            return

        if not config:
            return

        # Load base rules
        self.base_rules = config.get("base_rules", {})

        # Load contextual rules
        self.rules = []
        for rule_def in config.get("contextual_rules", []):
            try:
                rule = CompletenessRule(
                    id=rule_def["id"],
                    name=rule_def["name"],
                    when=rule_def.get("when", {}),
                    require=rule_def.get("require", {}),
                    severity=rule_def.get("severity", "warning"),
                    message=rule_def.get("message", f"Rule {rule_def['id']} failed"),
                )
                self.rules.append(rule)
            except KeyError as e:
                print(f"Warning: Invalid rule definition (missing {e}): {rule_def}")
                continue

    def check(self, adr: "ADRDocument") -> CompletenessResult:
        """Check ADR against all applicable rules.

        Evaluates each rule's conditions against the ADR metadata.
        If conditions match, checks the rule's requirements.

        Args:
            adr: The ADR document to check

        Returns:
            CompletenessResult with found issues
        """
        issues: list[ValidationIssue] = []
        rules_triggered = 0
        rules_passed = 0

        for rule in self.rules:
            if self._matches_condition(rule.when, adr):
                rules_triggered += 1
                rule_issues = self._check_requirements(rule, adr)

                if not rule_issues:
                    rules_passed += 1
                else:
                    issues.extend(rule_issues)

        # Check if any issues are errors
        has_errors = any(
            getattr(i, 'level', i.level) == IssueLevel.ERROR
            if hasattr(IssueLevel, 'ERROR') and isinstance(IssueLevel.ERROR, str) is False
            else getattr(i, 'level', None) == "error"
            for i in issues
        )

        return CompletenessResult(
            passed=not has_errors,
            issues=issues,
            rules_checked=len(self.rules),
            rules_triggered=rules_triggered,
            rules_passed=rules_passed,
        )

    def _matches_condition(self, when: dict, adr: "ADRDocument") -> bool:
        """Check if a rule applies to the ADR.

        Evaluates all conditions in the `when` dict against the ADR.
        All conditions must match for the rule to apply.

        Args:
            when: Dict of conditions to check
            adr: The ADR document

        Returns:
            True if all conditions match
        """
        # Empty when = always match (but typically we use all: [] for this)
        if not when:
            return True

        metadata = adr.metadata

        for key, expected in when.items():
            # Handle special condition operators

            # any: At least one sub-condition must match
            if key == "any":
                if not isinstance(expected, list):
                    expected = [expected]
                if not any(self._matches_condition(cond, adr) for cond in expected):
                    return False
                continue

            # all: All sub-conditions must match
            if key == "all":
                if not isinstance(expected, list):
                    expected = [expected]
                # Empty list means "always true"
                if expected and not all(self._matches_condition(cond, adr) for cond in expected):
                    return False
                continue

            # content_contains: Check if content contains text
            if key == "content_contains":
                if expected.lower() not in adr.raw_content.lower():
                    return False
                continue

            # section_exists: Check if section exists
            if key == "section_exists":
                if not self._find_section(adr, expected):
                    return False
                continue

            # field_not_empty: Check if field has value
            if key.endswith("_not_empty"):
                field = key.replace("_not_empty", "")
                value = self._get_field(metadata, field)
                if not value:
                    return False
                continue

            # Simple field comparison
            actual = self._get_field(metadata, key)

            # Handle enum comparison
            if hasattr(actual, 'value'):
                actual = actual.value

            if actual != expected:
                return False

        return True

    def _get_field(self, metadata: Any, field: str) -> Any:
        """Get field value from metadata.

        Supports special field names for nested access:
        - files_create: metadata.files.create
        - depends_on: metadata.depends_on

        Args:
            metadata: ADRMetadata object
            field: Field name to access

        Returns:
            Field value or None
        """
        # Handle special nested fields
        if field == "files_create":
            files = getattr(metadata, 'files', None)
            return getattr(files, 'create', None) if files else None

        if field == "files_modify":
            files = getattr(metadata, 'files', None)
            return getattr(files, 'modify', None) if files else None

        if field == "depends_on":
            return getattr(metadata, 'depends_on', None)

        # Get attribute, handling enums
        value = getattr(metadata, field, None)
        if hasattr(value, 'value'):
            return value.value
        return value

    def _check_requirements(
        self,
        rule: CompletenessRule,
        adr: "ADRDocument"
    ) -> list[ValidationIssue]:
        """Check the requirements of a triggered rule.

        Evaluates all requirements defined in the rule's `require` dict.

        Args:
            rule: The rule to check
            adr: The ADR document

        Returns:
            List of ValidationIssue objects for failed requirements
        """
        issues: list[ValidationIssue] = []
        require = rule.require

        # Determine issue level based on severity
        if hasattr(IssueLevel, 'ERROR') and not isinstance(IssueLevel.ERROR, str):
            level = IssueLevel.ERROR if rule.severity == "error" else IssueLevel.WARNING
        else:
            level = "error" if rule.severity == "error" else "warning"

        # Check required sections
        if "sections" in require:
            for sec_req in require["sections"]:
                section_name = sec_req["name"]
                section = self._find_section(adr, section_name)

                if not section:
                    issues.append(self._create_issue(
                        level=level,
                        category="missing_section",
                        message=f"{rule.message} - Section fehlt: {section_name}",
                        location=f"Rule: {rule.id}",
                    ))
                else:
                    # Check min_length
                    min_len = sec_req.get("min_length", 0)
                    if len(section.content) < min_len:
                        issues.append(self._create_issue(
                            level=level,
                            category="empty_section",
                            message=f"{rule.message} - Section zu kurz: {section_name} ({len(section.content)} < {min_len} Zeichen)",
                            location=f"Rule: {rule.id}",
                        ))

                    # Check required elements
                    for element in sec_req.get("required_elements", []):
                        if not re.search(element, section.content, re.IGNORECASE):
                            issues.append(self._create_issue(
                                level=level,
                                category="missing_criteria",
                                message=f"{rule.message} - Element fehlt in Section: {element}",
                                location=f"Section: {section_name}",
                            ))

        # Check content patterns
        if "content_patterns" in require:
            for pattern_req in require["content_patterns"]:
                pattern = pattern_req["pattern"]
                min_matches = pattern_req.get("min_matches", 1)
                location = pattern_req.get("location", "any")

                search_text = self._get_search_text(adr, location)
                matches = len(re.findall(pattern, search_text, re.IGNORECASE))

                if matches < min_matches:
                    issues.append(self._create_issue(
                        level=level,
                        category="missing_criteria",
                        message=f"{rule.message} - Pattern nicht gefunden: {pattern}",
                        location=f"Rule: {rule.id}",
                    ))

        # Check acceptance criteria keywords
        if "acceptance_criteria_keywords" in require:
            keywords = require["acceptance_criteria_keywords"]
            criteria_text = ""
            akz_section = self._find_section(adr, "Akzeptanzkriterien")
            if akz_section:
                criteria_text = akz_section.content.lower()

            for keyword in keywords:
                if keyword.lower() not in criteria_text:
                    issues.append(self._create_issue(
                        level=level,
                        category="missing_criteria",
                        message=f"{rule.message} - Akzeptanzkriterium fehlt: {keyword}",
                        location="Akzeptanzkriterien",
                    ))

        return issues

    def _create_issue(
        self,
        level: Any,
        category: str,
        message: str,
        location: Optional[str] = None
    ) -> ValidationIssue:
        """Create a ValidationIssue with proper types.

        Handles both enum and string-based IssueLevel/IssueCategory.

        Args:
            level: Issue level (error/warning)
            category: Issue category
            message: Issue message
            location: Optional location string

        Returns:
            ValidationIssue object
        """
        # Handle category conversion
        if hasattr(IssueCategory, 'MISSING_SECTION') and not isinstance(IssueCategory.MISSING_SECTION, str):
            category_map = {
                "missing_section": IssueCategory.MISSING_SECTION,
                "empty_section": IssueCategory.EMPTY_SECTION,
                "missing_criteria": IssueCategory.MISSING_CRITERIA,
            }
            cat = category_map.get(category, IssueCategory.MISSING_CRITERIA)
        else:
            cat = category

        return ValidationIssue(
            level=level,
            category=cat,
            message=message,
            location=location,
        )

    def _find_section(self, adr: "ADRDocument", name: str) -> Optional[Any]:
        """Find section by name (case-insensitive).

        Args:
            adr: The ADR document
            name: Section name to find

        Returns:
            ADRSection object or None
        """
        name_lower = name.lower()
        for sec_name, section in adr.sections.items():
            if sec_name.lower() == name_lower:
                return section
        return None

    def _get_search_text(self, adr: "ADRDocument", location: str) -> str:
        """Get text to search based on location.

        Args:
            adr: The ADR document
            location: Where to search ("any", "header", "content", or section name)

        Returns:
            Text to search in
        """
        if location == "any":
            return adr.raw_content
        if location == "header":
            return str(adr.metadata)
        if location == "content":
            return adr.raw_content

        # Location is a section name
        section = self._find_section(adr, location)
        return section.content if section else ""


def validate_completeness(
    adr_path: Path,
    rules_path: Optional[Path] = None
) -> CompletenessResult:
    """Convenience function to validate an ADR file.

    Parses the ADR and runs completeness validation.

    Args:
        adr_path: Path to the ADR file
        rules_path: Optional path to rules file

    Returns:
        CompletenessResult

    Raises:
        FileNotFoundError: If ADR file doesn't exist
        ADRParseError: If ADR can't be parsed
    """
    from helix.adr import ADRParser

    parser = ADRParser()
    adr = parser.parse_file(adr_path)

    validator = CompletenessValidator(rules_path)
    return validator.check(adr)
