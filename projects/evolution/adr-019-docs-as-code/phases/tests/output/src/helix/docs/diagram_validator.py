"""
Diagram Validator for Documentation as Code.

ADR-019: Validates diagrams against their $refs declarations, ensuring
that all referenced symbols exist and are properly documented.
"""

import re
from pathlib import Path
from typing import Any

from helix.docs.schema import DiagramValidation, ValidationIssue
from helix.docs.reference_resolver import ReferenceResolver


class DiagramValidator:
    """Validates diagrams against their $refs declarations."""

    def __init__(self, resolver: ReferenceResolver):
        """Initialize the validator.

        Args:
            resolver: ReferenceResolver for validating symbol references.
        """
        self.resolver = resolver

    def validate(self, diagram_config: dict) -> DiagramValidation:
        """Validate a diagram configuration.

        Args:
            diagram_config: Diagram configuration from YAML.

        Returns:
            DiagramValidation result.
        """
        diagram_id = diagram_config.get("id", "unknown")
        file_ref = diagram_config.get("$file")
        declared_refs = diagram_config.get("$refs", [])
        warnings = []

        # Check file exists
        if not file_ref:
            return DiagramValidation(
                diagram_id=diagram_id,
                file=None,
                valid=False,
                referenced_symbols=declared_refs,
                missing_symbols=[],
                extra_symbols=[],
                warnings=["No $file specified for diagram"],
            )

        file_resolved = self.resolver.resolve_file(file_ref)
        if not file_resolved.exists:
            return DiagramValidation(
                diagram_id=diagram_id,
                file=Path(file_ref),
                valid=False,
                referenced_symbols=declared_refs,
                missing_symbols=[],
                extra_symbols=[],
                warnings=[f"Diagram file not found: {file_ref}"],
            )

        # Check all declared refs exist
        missing = []
        for ref in declared_refs:
            resolved = self.resolver.resolve(ref)
            if not resolved.exists:
                missing.append(ref)

        # Optionally: Parse diagram to find symbols mentioned
        extra_symbols = []
        if file_resolved.file:
            try:
                found_in_diagram = self._extract_symbols_from_diagram(
                    file_resolved.file
                )
                # Check for symbols in diagram that are not in $refs
                declared_names = {ref.split(".")[-1] for ref in declared_refs}
                for symbol in found_in_diagram:
                    if symbol not in declared_names:
                        extra_symbols.append(symbol)
                        warnings.append(
                            f"Symbol '{symbol}' found in diagram but not in $refs"
                        )
            except Exception as e:
                warnings.append(f"Could not parse diagram content: {e}")

        return DiagramValidation(
            diagram_id=diagram_id,
            file=file_resolved.file,
            valid=len(missing) == 0,
            referenced_symbols=declared_refs,
            missing_symbols=missing,
            extra_symbols=extra_symbols,
            warnings=warnings,
        )

    def validate_all(
        self, diagrams: list[dict], yaml_file: Path | None = None
    ) -> list[ValidationIssue]:
        """Validate all diagrams and return validation issues.

        Args:
            diagrams: List of diagram configurations.
            yaml_file: Source YAML file for error reporting.

        Returns:
            List of validation issues.
        """
        issues = []

        for diagram in diagrams:
            result = self.validate(diagram)

            if not result.valid:
                for symbol in result.missing_symbols:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            file=yaml_file,
                            path=f"diagrams.{result.diagram_id}.$refs",
                            ref=symbol,
                            message=f"Diagram references non-existent symbol: {symbol}",
                        )
                    )

            # Add warnings for extra symbols
            for warning in result.warnings:
                if "found in diagram but not in $refs" in warning:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            file=yaml_file,
                            path=f"diagrams.{result.diagram_id}",
                            ref="",
                            message=warning,
                        )
                    )

        return issues

    def _extract_symbols_from_diagram(self, file_path: Path) -> set[str]:
        """Extract potential symbol names from a diagram file.

        This is a heuristic approach that looks for:
        - CamelCase words (class names)
        - Words in boxes (ASCII art)
        - Quoted identifiers

        Args:
            file_path: Path to the diagram file.

        Returns:
            Set of potential symbol names found.
        """
        symbols = set()

        try:
            content = file_path.read_text()
        except Exception:
            return symbols

        # Find CamelCase words (potential class names)
        camel_case = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", content)
        symbols.update(camel_case)

        # Find words in ASCII boxes: │ SomeClass │ or | SomeClass |
        boxed = re.findall(r"[│|]\s*(\w+)\s*[│|]", content)
        symbols.update(boxed)

        # Find words in square brackets: [SomeClass]
        bracketed = re.findall(r"\[(\w+)\]", content)
        symbols.update(bracketed)

        # Find words after arrows: -> SomeClass or --> SomeClass
        after_arrow = re.findall(r"[-=]+>\s*(\w+)", content)
        symbols.update(after_arrow)

        # Filter out common non-symbol words
        common_words = {
            "the", "and", "or", "if", "else", "for", "while", "return",
            "class", "def", "import", "from", "as", "with", "try", "except",
            "True", "False", "None", "Input", "Output", "Data", "Event",
            "Step", "Action", "Result", "Start", "End", "Process", "Flow",
        }
        symbols -= common_words

        return symbols

    def suggest_refs(self, diagram_file: Path) -> list[str]:
        """Suggest $refs based on symbols found in a diagram.

        Args:
            diagram_file: Path to the diagram file.

        Returns:
            List of suggested reference patterns.
        """
        symbols = self._extract_symbols_from_diagram(diagram_file)
        suggestions = []

        for symbol in sorted(symbols):
            # Try to find a matching class/function
            # This is a placeholder - in a real implementation,
            # we would search the codebase
            suggestions.append(f"# TODO: Resolve '{symbol}' to full path")

        return suggestions
