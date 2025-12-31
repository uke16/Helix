"""
File Existence Validator.

Validates that files referenced in ADR files.modify sections
actually exist in the filesystem.

ADR-038: Deterministic LLM Response Enforcement
"""

import re
from pathlib import Path
from typing import Optional

import yaml

from .base import ResponseValidator, ValidationIssue


class FileExistenceValidator(ResponseValidator):
    """
    Validates that files.modify references point to existing files.

    Only activates when the response contains an ADR with files.modify.
    Non-existent files in files.modify are errors - they should be
    in files.create instead.

    Provides a fallback that moves non-existent files from files.modify
    to files.create.

    Example:
        validator = FileExistenceValidator(helix_root=Path("/path/to/helix"))
        issues = validator.validate(adr_response, {})
    """

    def __init__(self, helix_root: Path):
        """
        Initialize the validator.

        Args:
            helix_root: Root directory of the HELIX project
        """
        self.helix_root = Path(helix_root)

    @property
    def name(self) -> str:
        """Unique validator name."""
        return "file_existence"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """
        Validate that files.modify entries exist.

        Args:
            response: The LLM response text
            context: Validation context (unused)

        Returns:
            List of issues for non-existent files
        """
        # Extract files.modify from YAML
        modify_files = self._extract_modify_files(response)

        if not modify_files:
            return []

        issues: list[ValidationIssue] = []

        for file_path in modify_files:
            full_path = self.helix_root / file_path
            if not full_path.exists():
                issues.append(
                    ValidationIssue(
                        code="FILE_NOT_FOUND",
                        message=f"files.modify referenziert nicht existierende Datei: {file_path}",
                        fix_hint=f"Entferne '{file_path}' aus files.modify oder "
                        "verschiebe nach files.create",
                    )
                )

        return issues

    def _extract_modify_files(self, response: str) -> list[str]:
        """
        Extract files.modify list from ADR YAML header.

        Args:
            response: ADR response text

        Returns:
            List of file paths from files.modify
        """
        # Extract YAML frontmatter
        yaml_match = re.search(
            r"^---\n(.*?)\n---", response, re.DOTALL | re.MULTILINE
        )

        if not yaml_match:
            return []

        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            if not isinstance(metadata, dict):
                return []

            files = metadata.get("files", {})
            if not isinstance(files, dict):
                return []

            modify = files.get("modify", [])
            if not isinstance(modify, list):
                return []

            return [str(f) for f in modify]

        except (yaml.YAMLError, AttributeError):
            return []

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """
        Move non-existent files from files.modify to files.create.

        Args:
            response: The ADR response with invalid file references
            context: Validation context

        Returns:
            Corrected response, or None if cannot fix
        """
        # Extract YAML frontmatter
        yaml_match = re.search(
            r"^---\n(.*?)\n---", response, re.DOTALL | re.MULTILINE
        )

        if not yaml_match:
            return None

        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            if not isinstance(metadata, dict):
                return None

            files = metadata.get("files", {})
            if not isinstance(files, dict):
                return None

            modify_files = files.get("modify", [])
            create_files = files.get("create", [])

            if not isinstance(modify_files, list):
                modify_files = []
            if not isinstance(create_files, list):
                create_files = []

        except (yaml.YAMLError, AttributeError):
            return None

        # Find non-existent files and move them
        moved: list[str] = []
        new_modify: list[str] = []

        for file_path in modify_files:
            full_path = self.helix_root / file_path
            if full_path.exists():
                new_modify.append(file_path)
            else:
                if file_path not in create_files:
                    create_files.append(file_path)
                moved.append(file_path)

        if not moved:
            return None  # Nothing to fix

        # Update metadata
        if "files" not in metadata:
            metadata["files"] = {}

        metadata["files"]["modify"] = new_modify
        metadata["files"]["create"] = create_files

        # Rebuild YAML header
        new_yaml = yaml.dump(
            metadata, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

        # Reconstruct response
        return f"---\n{new_yaml}---{response[yaml_match.end():]}"
