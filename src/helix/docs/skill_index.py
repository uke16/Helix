"""
Skill Index Generator for HELIX v4.

ADR-020: Generates skills/INDEX.yaml with auto-extracted keywords from SKILL.md files.
Enables intelligent skill selection by providing searchable metadata for each skill.

Usage:
    from helix.docs.skill_index import SkillIndexGenerator

    generator = SkillIndexGenerator()
    index = generator.generate_index()
    generator.save_index()  # Saves to skills/INDEX.yaml
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillInfo:
    """Information about a single skill."""

    path: str
    name: str
    description: str
    auto_keywords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML output."""
        result: dict[str, Any] = {
            "path": self.path,
            "name": self.name,
            "description": self.description,
            "auto_keywords": self.auto_keywords,
        }
        # Only include optional fields if they have values
        if self.aliases:
            result["aliases"] = self.aliases
        if self.triggers:
            result["triggers"] = self.triggers
        return result


@dataclass
class SkillIndex:
    """Complete skill index with metadata."""

    skills: list[SkillInfo] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generator: str = "helix.docs.skill_index"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML output."""
        return {
            "_meta": {
                "generated_at": self.generated_at.isoformat(),
                "generator": self.generator,
            },
            "skills": [skill.to_dict() for skill in self.skills],
        }


class SkillIndexGenerator:
    """Generates skills/INDEX.yaml from SKILL.md files.

    Extracts keywords from:
    - Markdown headers (##, ###)
    - Code terms (`backtick` content)
    - Bold terms (**bold**)
    - Key concepts and API methods

    Example:
        generator = SkillIndexGenerator(skills_dir=Path("skills"))
        index = generator.generate_index()

        # Get recommended skills for a request
        print(index.skills)
    """

    # Common words to filter out (noise)
    NOISE_WORDS = frozenset(
        {
            # English articles/prepositions
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            # German articles/prepositions
            "der",
            "die",
            "das",
            "ein",
            "eine",
            "einer",
            "und",
            "oder",
            "aber",
            "mit",
            "bei",
            "zu",
            "von",
            "für",
            "als",
            "wenn",
            "wird",
            "werden",
            "ist",
            "sind",
            "war",
            "waren",
            "sein",
            "haben",
            "hat",
            "hatte",
            "kann",
            "können",
            "muss",
            "müssen",
            "soll",
            "sollen",
            "wann",
            "wie",
            "was",
            "wo",
            # Common technical noise
            "example",
            "beispiel",
            "note",
            "see",
            "also",
            "more",
            "details",
            "overview",
            "übersicht",
            "usage",
            "use",
            "using",
            "used",
            "etc",
            "e.g",
            "i.e",
            "true",
            "false",
            "null",
            "none",
        }
    )

    # Minimum keyword length
    MIN_KEYWORD_LENGTH = 2

    # Maximum keywords per skill
    MAX_KEYWORDS = 30

    def __init__(
        self, skills_dir: Path | None = None, project_root: Path | None = None
    ):
        """Initialize the generator.

        Args:
            skills_dir: Directory containing skill folders. Defaults to "skills".
            project_root: Project root directory. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.skills_dir = skills_dir or self.project_root / "skills"

    def extract_name_and_description(self, content: str) -> tuple[str, str]:
        """Extract name and description from SKILL.md content.

        Looks for:
        - First H1 header as name
        - First paragraph or blockquote as description

        Args:
            content: Markdown content of SKILL.md

        Returns:
            Tuple of (name, description)
        """
        name = "Unknown Skill"
        description = ""

        # Extract name from first H1
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            name = h1_match.group(1).strip()

        # Extract description from first blockquote or first paragraph after H1
        blockquote_match = re.search(r"^>\s*(.+(?:\n>\s*.+)*)", content, re.MULTILINE)
        if blockquote_match:
            # Clean up blockquote markers
            desc_lines = blockquote_match.group(0).split("\n")
            description = " ".join(
                line.lstrip(">").strip() for line in desc_lines if line.strip()
            )
        else:
            # Fall back to first non-header paragraph
            paragraphs = re.findall(
                r"(?:^|\n\n)([^#\n>][^\n]+(?:\n[^#\n>][^\n]+)*)", content
            )
            if paragraphs:
                description = paragraphs[0].strip().replace("\n", " ")

        # Truncate description if too long
        if len(description) > 200:
            description = description[:197] + "..."

        return name, description

    def extract_keywords(self, skill_path: Path) -> set[str]:
        """Extract keywords from a SKILL.md file.

        Extracts from:
        - Headers (##, ###, etc.)
        - Code terms in backticks
        - Bold terms in **asterisks**
        - Function/method names
        - Technical terms

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            Set of extracted keywords
        """
        content = skill_path.read_text(encoding="utf-8")

        keywords: set[str] = set()

        # Extract headers (## Header, ### Subheader)
        headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
        for header in headers:
            # Split header into words and add significant ones
            words = self._tokenize(header)
            keywords.update(w for w in words if self._is_significant(w))

        # Extract code terms (`term`)
        code_terms = re.findall(r"`([^`]+)`", content)
        for term in code_terms:
            # Code terms are often method names or technical terms
            if self._is_significant(term):
                keywords.add(term)
            # Also add individual words from snake_case or camelCase
            words = self._split_identifier(term)
            keywords.update(w for w in words if self._is_significant(w))

        # Extract bold terms (**term**)
        bold_terms = re.findall(r"\*\*([^*]+)\*\*", content)
        for term in bold_terms:
            words = self._tokenize(term)
            keywords.update(w for w in words if self._is_significant(w))

        # Extract potential API methods (word followed by parentheses)
        methods = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
        keywords.update(m for m in methods if self._is_significant(m))

        # Filter and limit keywords
        filtered = self._filter_keywords(keywords)

        # Sort by length (longer = more specific) and limit
        sorted_keywords = sorted(filtered, key=lambda x: (-len(x), x))
        return set(sorted_keywords[: self.MAX_KEYWORDS])

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of words
        """
        # Split on non-alphanumeric characters
        return re.findall(r"[a-zA-ZäöüÄÖÜß][a-zA-Z0-9äöüÄÖÜß_-]*", text)

    def _split_identifier(self, identifier: str) -> list[str]:
        """Split camelCase or snake_case identifier into words.

        Args:
            identifier: Identifier like "getUserData" or "get_user_data"

        Returns:
            List of words ["get", "User", "Data"] or ["get", "user", "data"]
        """
        # First split on underscores
        parts = identifier.split("_")

        words = []
        for part in parts:
            # Split camelCase
            camel_words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", part)
            words.extend(camel_words)

        return words

    def _is_significant(self, word: str) -> bool:
        """Check if a word is significant enough to be a keyword.

        Args:
            word: Word to check

        Returns:
            True if word should be included as keyword
        """
        if len(word) < self.MIN_KEYWORD_LENGTH:
            return False
        if word.lower() in self.NOISE_WORDS:
            return False
        # Skip pure numbers
        if word.isdigit():
            return False
        return True

    def _filter_keywords(self, keywords: set[str]) -> set[str]:
        """Filter and clean keywords.

        Args:
            keywords: Set of raw keywords

        Returns:
            Cleaned set of keywords
        """
        filtered = set()
        for kw in keywords:
            # Skip very short keywords
            if len(kw) < self.MIN_KEYWORD_LENGTH:
                continue
            # Skip noise words
            if kw.lower() in self.NOISE_WORDS:
                continue
            # Keep original case for technical terms
            filtered.add(kw)
        return filtered

    def generate_index(self) -> SkillIndex:
        """Generate the complete skill index.

        Scans all SKILL.md files in the skills directory and extracts
        metadata and keywords from each.

        Returns:
            SkillIndex with all discovered skills
        """
        index = SkillIndex()

        # Find all SKILL.md files
        skill_files = sorted(self.skills_dir.rglob("SKILL.md"))

        for skill_file in skill_files:
            try:
                content = skill_file.read_text(encoding="utf-8")
                name, description = self.extract_name_and_description(content)
                keywords = self.extract_keywords(skill_file)

                # Create relative path from project root
                rel_path = skill_file.relative_to(self.project_root)

                skill_info = SkillInfo(
                    path=str(rel_path),
                    name=name,
                    description=description,
                    auto_keywords=sorted(keywords),
                    aliases=[],  # Manually maintained
                    triggers=[],  # Manually maintained
                )
                index.skills.append(skill_info)
            except Exception as e:
                # Log but continue with other skills
                print(f"Warning: Failed to process {skill_file}: {e}")

        return index

    def save_index(self, output_path: Path | None = None) -> Path:
        """Generate and save the skill index to YAML.

        Args:
            output_path: Output file path. Defaults to skills/INDEX.yaml

        Returns:
            Path to the generated file
        """
        index = self.generate_index()
        output = output_path or self.skills_dir / "INDEX.yaml"

        # Ensure parent directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            # Add header comment
            f.write("# Auto-generated skill index\n")
            f.write(f"# Generated: {index.generated_at.isoformat()}\n")
            f.write("# Regenerate: python -m helix.docs.skill_index\n")
            f.write("#\n")
            f.write("# Manual fields (preserved on regeneration):\n")
            f.write("#   aliases: Synonyms for skill keywords\n")
            f.write("#   triggers: Phrase patterns that activate this skill\n")
            f.write("\n")

            yaml.dump(
                index.to_dict(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output


def main():
    """CLI entry point for skill index generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate skills/INDEX.yaml from SKILL.md files"
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Directory containing skills (default: skills/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: skills/INDEX.yaml)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    generator = SkillIndexGenerator(
        skills_dir=args.skills_dir,
        project_root=args.project_root,
    )

    output_path = generator.save_index(args.output)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
