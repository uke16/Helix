"""Context Manager for HELIX v4.

Manages skills and context preparation for phases.
"""

import os
from pathlib import Path
from typing import Any

import yaml


class ContextManager:
    """Manages skills and prepares context for phase execution.

    The ContextManager handles:
    - Loading skill definitions from the skills directory
    - Creating symlinks to skills in phase directories
    - Mapping domains and languages to relevant skills

    Skills are stored in /home/aiuser01/helix-v4/skills/ and contain
    reusable knowledge and patterns for specific domains.

    Example:
        manager = ContextManager()
        manager.prepare_phase_context(
            phase_dir=Path("/project/phases/01-foundation"),
            spec={"meta": {"domain": "cli-tool", "language": "python"}}
        )
    """

    DEFAULT_SKILLS_DIR = Path("/home/aiuser01/helix-v4/skills")

    DOMAIN_SKILL_MAP: dict[str, list[str]] = {
        "cli-tool": ["cli-development", "argument-parsing", "user-interaction"],
        "web-app": ["web-development", "frontend", "api-design"],
        "api-service": ["api-design", "rest-patterns", "authentication"],
        "library": ["api-design", "documentation", "versioning"],
        "data-pipeline": ["data-processing", "etl-patterns", "scheduling"],
        "infrastructure": ["devops", "cloud-patterns", "security"],
        "documentation": ["technical-writing", "markdown", "diagrams"],
        "testing": ["testing-patterns", "mocking", "coverage"],
    }

    LANGUAGE_SKILL_MAP: dict[str, list[str]] = {
        "python": ["python-best-practices", "python-testing", "python-packaging"],
        "typescript": ["typescript-patterns", "node-ecosystem", "type-safety"],
        "javascript": ["javascript-patterns", "node-ecosystem", "async-patterns"],
        "go": ["go-patterns", "go-testing", "go-modules"],
        "rust": ["rust-patterns", "cargo-ecosystem", "memory-safety"],
        "java": ["java-patterns", "maven-gradle", "jvm-ecosystem"],
        "kotlin": ["kotlin-patterns", "kotlin-coroutines", "jvm-ecosystem"],
    }

    def __init__(self, skills_dir: Path | None = None) -> None:
        """Initialize the ContextManager.

        Args:
            skills_dir: Directory containing skill definitions.
                       Defaults to /home/aiuser01/helix-v4/skills/.
        """
        self.skills_dir = skills_dir or self.DEFAULT_SKILLS_DIR
        self._skill_cache: dict[str, dict[str, Any]] | None = None

    def prepare_phase_context(self, phase_dir: Path, spec: dict[str, Any]) -> None:
        """Prepare the context for a phase execution.

        Creates symlinks to relevant skills and prepares any other
        context needed for the phase.

        Args:
            phase_dir: Path to the phase directory.
            spec: The spec dictionary from spec.yaml.
        """
        skills_to_link = self._get_skills_from_spec(spec)

        skills_link_dir = phase_dir / ".skills"
        skills_link_dir.mkdir(parents=True, exist_ok=True)

        for skill_name in skills_to_link:
            skill_path = self.skills_dir / skill_name
            if skill_path.exists():
                link_path = skills_link_dir / skill_name
                self._create_symlink(skill_path, link_path)

    def _get_skills_from_spec(self, spec: dict[str, Any]) -> list[str]:
        """Get list of skills needed based on spec.

        Args:
            spec: The spec dictionary.

        Returns:
            List of skill names to include.
        """
        skills: set[str] = set()

        explicit_skills = spec.get("context", {}).get("skills", [])
        skills.update(explicit_skills)

        meta = spec.get("meta", {})
        domain = meta.get("domain")
        if domain:
            domain_skills = self.get_skills_for_domain(domain)
            skills.update(s.name for s in domain_skills)

        language = meta.get("language")
        if language:
            language_skills = self.get_skills_for_language(language)
            skills.update(s.name for s in language_skills)

        return list(skills)

    def get_skills_for_domain(self, domain: str) -> list[Path]:
        """Get skill paths for a specific domain.

        Args:
            domain: The domain name (e.g., "cli-tool").

        Returns:
            List of paths to relevant skill directories.
        """
        skill_names = self.DOMAIN_SKILL_MAP.get(domain, [])
        return self._resolve_skill_paths(skill_names)

    def get_skills_for_language(self, language: str) -> list[Path]:
        """Get skill paths for a specific programming language.

        Args:
            language: The language name (e.g., "python").

        Returns:
            List of paths to relevant skill directories.
        """
        skill_names = self.LANGUAGE_SKILL_MAP.get(language.lower(), [])
        return self._resolve_skill_paths(skill_names)

    def _resolve_skill_paths(self, skill_names: list[str]) -> list[Path]:
        """Resolve skill names to paths.

        Args:
            skill_names: List of skill names.

        Returns:
            List of existing skill paths.
        """
        paths = []
        for name in skill_names:
            skill_path = self.skills_dir / name
            if skill_path.exists():
                paths.append(skill_path)
        return paths

    def _create_symlink(self, source: Path, target: Path) -> None:
        """Create a symlink from target to source.

        Args:
            source: The source path (what the link points to).
            target: The target path (where the link is created).
        """
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            else:
                return

        try:
            target.symlink_to(source)
        except OSError:
            pass

    def list_available_skills(self) -> list[str]:
        """List all available skills.

        Returns:
            List of skill names.
        """
        if not self.skills_dir.exists():
            return []

        return [
            p.name for p in self.skills_dir.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]

    def get_skill_info(self, skill_name: str) -> dict[str, Any] | None:
        """Get information about a specific skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Skill info dictionary or None if not found.
        """
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            return None

        info_file = skill_path / "skill.yaml"
        if info_file.exists():
            with open(info_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        readme = skill_path / "README.md"
        if readme.exists():
            with open(readme, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.split("\n")
            title = lines[0].lstrip("# ") if lines else skill_name
            description = lines[2] if len(lines) > 2 else ""
            return {
                "name": skill_name,
                "title": title,
                "description": description,
            }

        return {
            "name": skill_name,
            "title": skill_name,
            "description": "",
        }

    def cleanup_phase_context(self, phase_dir: Path) -> None:
        """Clean up context from a phase directory.

        Removes symlinks created by prepare_phase_context.

        Args:
            phase_dir: Path to the phase directory.
        """
        skills_link_dir = phase_dir / ".skills"
        if skills_link_dir.exists():
            for link in skills_link_dir.iterdir():
                if link.is_symlink():
                    link.unlink()
            try:
                skills_link_dir.rmdir()
            except OSError:
                pass
