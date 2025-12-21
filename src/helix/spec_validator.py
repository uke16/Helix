"""Spec validation for HELIX v4.

Validates spec.yaml files against the schema definition.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ValidationError:
    """A validation error or warning.

    Attributes:
        path: JSON path to the invalid field (e.g., "meta.id").
        message: Description of the validation error.
        value: The invalid value, if applicable.
    """
    path: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validating a spec.yaml file.

    Attributes:
        valid: Whether the spec is valid (no errors).
        errors: List of validation errors.
        warnings: List of validation warnings.
    """
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)


class SpecValidator:
    """Validates spec.yaml files against the HELIX v4 schema.

    The SpecValidator ensures that spec.yaml files contain all required
    fields and that field values are valid.

    Required fields:
        - meta.id: Unique identifier for the spec
        - meta.domain: Domain category (e.g., "cli-tool", "web-app")
        - implementation.summary: Brief description of what to implement

    Example:
        validator = SpecValidator()
        result = validator.validate(Path("/project/spec.yaml"))
        if not result.valid:
            for error in result.errors:
                print(f"Error at {error.path}: {error.message}")
    """

    REQUIRED_FIELDS = [
        ("meta.id", str),
        ("meta.domain", str),
        ("implementation.summary", str),
    ]

    OPTIONAL_FIELDS = [
        ("meta.name", str),
        ("meta.version", str),
        ("meta.language", str),
        ("implementation.requirements", list),
        ("implementation.constraints", list),
        ("implementation.acceptance_criteria", list),
        ("context.skills", list),
        ("context.templates", list),
        ("output.files", list),
    ]

    VALID_DOMAINS = {
        "cli-tool",
        "web-app",
        "api-service",
        "library",
        "data-pipeline",
        "infrastructure",
        "documentation",
        "testing",
    }

    VALID_LANGUAGES = {
        "python",
        "typescript",
        "javascript",
        "go",
        "rust",
        "java",
        "kotlin",
    }

    def validate(self, spec_path: Path) -> ValidationResult:
        """Validate a spec.yaml file.

        Args:
            spec_path: Path to the spec.yaml file.

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        if not spec_path.exists():
            errors.append(ValidationError(
                path="",
                message=f"Spec file not found: {spec_path}",
            ))
            return ValidationResult(valid=False, errors=errors)

        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(ValidationError(
                path="",
                message=f"Invalid YAML: {e}",
            ))
            return ValidationResult(valid=False, errors=errors)

        if not spec:
            errors.append(ValidationError(
                path="",
                message="Spec file is empty",
            ))
            return ValidationResult(valid=False, errors=errors)

        for field_path, expected_type in self.REQUIRED_FIELDS:
            value = self._get_nested(spec, field_path)
            if value is None:
                errors.append(ValidationError(
                    path=field_path,
                    message=f"Required field '{field_path}' is missing",
                ))
            elif not isinstance(value, expected_type):
                errors.append(ValidationError(
                    path=field_path,
                    message=f"Field '{field_path}' must be {expected_type.__name__}",
                    value=value,
                ))

        for field_path, expected_type in self.OPTIONAL_FIELDS:
            value = self._get_nested(spec, field_path)
            if value is not None and not isinstance(value, expected_type):
                warnings.append(ValidationError(
                    path=field_path,
                    message=f"Field '{field_path}' should be {expected_type.__name__}",
                    value=value,
                ))

        domain = self._get_nested(spec, "meta.domain")
        if domain and domain not in self.VALID_DOMAINS:
            warnings.append(ValidationError(
                path="meta.domain",
                message=f"Unknown domain '{domain}'. Valid domains: {self.VALID_DOMAINS}",
                value=domain,
            ))

        language = self._get_nested(spec, "meta.language")
        if language and language not in self.VALID_LANGUAGES:
            warnings.append(ValidationError(
                path="meta.language",
                message=f"Unknown language '{language}'. Valid languages: {self.VALID_LANGUAGES}",
                value=language,
            ))

        meta_id = self._get_nested(spec, "meta.id")
        if meta_id and not self._is_valid_id(meta_id):
            errors.append(ValidationError(
                path="meta.id",
                message="ID must be lowercase alphanumeric with hyphens only",
                value=meta_id,
            ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_dict(self, spec: dict[str, Any]) -> ValidationResult:
        """Validate a spec dictionary directly.

        Args:
            spec: The spec dictionary to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        if not spec:
            errors.append(ValidationError(
                path="",
                message="Spec is empty",
            ))
            return ValidationResult(valid=False, errors=errors)

        for field_path, expected_type in self.REQUIRED_FIELDS:
            value = self._get_nested(spec, field_path)
            if value is None:
                errors.append(ValidationError(
                    path=field_path,
                    message=f"Required field '{field_path}' is missing",
                ))
            elif not isinstance(value, expected_type):
                errors.append(ValidationError(
                    path=field_path,
                    message=f"Field '{field_path}' must be {expected_type.__name__}",
                    value=value,
                ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _get_nested(self, data: dict[str, Any], path: str) -> Any:
        """Get a nested value from a dictionary using dot notation.

        Args:
            data: The dictionary to search.
            path: Dot-separated path (e.g., "meta.id").

        Returns:
            The value at the path, or None if not found.
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None

        return current

    def _is_valid_id(self, id_value: str) -> bool:
        """Check if an ID is valid.

        Valid IDs are lowercase alphanumeric with hyphens.

        Args:
            id_value: The ID to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not id_value:
            return False

        import re
        return bool(re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", id_value))
