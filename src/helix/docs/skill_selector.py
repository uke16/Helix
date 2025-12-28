"""
Smart Skill Selector for HELIX v4.

ADR-020: Selects relevant skills based on user request keywords.
Matches request terms against skill keywords, aliases, and triggers
to recommend the most relevant skills for a task.

Usage:
    from helix.docs.skill_selector import SkillSelector

    selector = SkillSelector()
    matches = selector.select("BOM Export für SAP", top_n=3)

    for match in matches:
        print(f"{match.path}: {match.score} ({match.matched_keywords})")
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillMatch:
    """A matched skill with relevance score."""

    path: str
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    name: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "name": self.name,
            "description": self.description,
        }


@dataclass
class SkillEntry:
    """A skill entry from the index."""

    path: str
    name: str
    description: str
    auto_keywords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)


class SkillSelector:
    """Selects relevant skills based on request keywords.

    Scoring algorithm:
    - Exact keyword match: 10 points
    - Substring match: 3 points
    - Trigger phrase match: 15 points
    - Alias match: 10 points

    Fallback behavior:
    - If no skills match, returns all skills
    - If score < 5, skill is not recommended
    - Always includes helix skill for HELIX-related tasks

    Example:
        selector = SkillSelector()
        matches = selector.select("BOM Export für SAP")

        # Returns:
        # [SkillMatch(path="skills/pdm/SKILL.md", score=25, matched=["BOM", "SAP"])]
    """

    # Scoring weights
    EXACT_MATCH_SCORE = 10
    SUBSTRING_MATCH_SCORE = 3
    TRIGGER_MATCH_SCORE = 15
    ALIAS_MATCH_SCORE = 10

    # Minimum score to recommend a skill
    MIN_RECOMMEND_SCORE = 5

    # Default number of top skills to return
    DEFAULT_TOP_N = 3

    # Skills to always include (if they exist)
    ALWAYS_INCLUDE = {"skills/helix/SKILL.md"}

    def __init__(self, index_path: Path | None = None, project_root: Path | None = None):
        """Initialize the selector.

        Args:
            index_path: Path to skills/INDEX.yaml. Defaults to "skills/INDEX.yaml".
            project_root: Project root directory. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.index_path = index_path or self.project_root / "skills" / "INDEX.yaml"
        self._index: dict[str, Any] | None = None
        self._skills: list[SkillEntry] | None = None

    def _load_index(self) -> dict[str, Any]:
        """Load the skill index from YAML.

        Returns:
            Parsed index dictionary

        Raises:
            FileNotFoundError: If INDEX.yaml doesn't exist
        """
        if self._index is None:
            if not self.index_path.exists():
                raise FileNotFoundError(
                    f"Skill index not found: {self.index_path}. "
                    "Run 'python -m helix.docs.skill_index' to generate it."
                )
            with open(self.index_path, encoding="utf-8") as f:
                self._index = yaml.safe_load(f)
        return self._index

    def _get_skills(self) -> list[SkillEntry]:
        """Get all skills from the index.

        Returns:
            List of SkillEntry objects
        """
        if self._skills is None:
            index = self._load_index()
            self._skills = []
            for skill_data in index.get("skills", []):
                entry = SkillEntry(
                    path=skill_data.get("path", ""),
                    name=skill_data.get("name", ""),
                    description=skill_data.get("description", ""),
                    auto_keywords=skill_data.get("auto_keywords", []),
                    aliases=skill_data.get("aliases", []),
                    triggers=skill_data.get("triggers", []),
                )
                self._skills.append(entry)
        return self._skills

    def all_skills(self) -> list[SkillEntry]:
        """Get all available skills.

        Returns:
            List of all skill entries
        """
        return self._get_skills()

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into lowercase words.

        Args:
            text: Input text

        Returns:
            Set of lowercase words
        """
        words = re.findall(r"[a-zA-ZäöüÄÖÜß][a-zA-Z0-9äöüÄÖÜß_-]*", text.lower())
        return set(words)

    def _matches_trigger(self, request: str, trigger: str) -> bool:
        """Check if a request matches a trigger phrase.

        Triggers are patterns like:
        - "wenn BOM oder Stückliste erwähnt"
        - "wenn SAP-Integration benötigt"

        Args:
            request: User request text
            trigger: Trigger phrase from skill

        Returns:
            True if request matches trigger
        """
        request_lower = request.lower()
        trigger_lower = trigger.lower()

        # Extract key terms from trigger (after "wenn")
        trigger_match = re.search(r"wenn\s+(.+)", trigger_lower)
        if trigger_match:
            trigger_content = trigger_match.group(1)
            # Split by "oder" for OR conditions
            conditions = trigger_content.split(" oder ")
            for condition in conditions:
                # Remove common filler words
                condition = re.sub(
                    r"\b(erwähnt|benötigt|verwendet|gebraucht)\b", "", condition
                )
                # Check if any remaining significant word is in request
                words = self._tokenize(condition)
                if any(w in request_lower for w in words if len(w) > 2):
                    return True
        else:
            # Simple substring match for non-wenn triggers
            words = self._tokenize(trigger_lower)
            return any(w in request_lower for w in words if len(w) > 2)

        return False

    def select(self, request: str, top_n: int | None = None) -> list[SkillMatch]:
        """Select relevant skills for a request.

        Matches request text against skill keywords, aliases, and triggers.
        Returns the top N skills sorted by relevance score.

        Args:
            request: User request text
            top_n: Maximum number of skills to return. Defaults to 3.

        Returns:
            List of SkillMatch objects sorted by score (highest first)
        """
        if top_n is None:
            top_n = self.DEFAULT_TOP_N

        skills = self._get_skills()
        request_words = self._tokenize(request)
        request_lower = request.lower()

        scored: list[SkillMatch] = []

        for skill in skills:
            score = 0
            matched_keywords: list[str] = []

            # Combine all keywords for matching
            all_keywords = set(skill.auto_keywords)

            # Exact keyword matches (case-insensitive)
            for kw in all_keywords:
                kw_lower = kw.lower()
                if kw_lower in request_words:
                    score += self.EXACT_MATCH_SCORE
                    matched_keywords.append(kw)
                elif any(kw_lower in w or w in kw_lower for w in request_words):
                    # Substring match
                    score += self.SUBSTRING_MATCH_SCORE
                    if kw not in matched_keywords:
                        matched_keywords.append(kw)

            # Alias matches (treated like exact matches)
            for alias in skill.aliases:
                alias_lower = alias.lower()
                if alias_lower in request_lower or any(
                    alias_lower in w for w in request_words
                ):
                    score += self.ALIAS_MATCH_SCORE
                    matched_keywords.append(f"~{alias}")

            # Trigger matches
            for trigger in skill.triggers:
                if self._matches_trigger(request, trigger):
                    score += self.TRIGGER_MATCH_SCORE
                    matched_keywords.append(f"[{trigger[:20]}...]")

            if score > 0:
                scored.append(
                    SkillMatch(
                        path=skill.path,
                        score=score,
                        matched_keywords=matched_keywords,
                        name=skill.name,
                        description=skill.description,
                    )
                )

        # Sort by score (highest first), then by path for stability
        scored.sort(key=lambda x: (-x.score, x.path))

        # If no matches, return fallback
        if not scored:
            return self._fallback_all()

        # Filter by minimum score
        scored = [s for s in scored if s.score >= self.MIN_RECOMMEND_SCORE]

        # Return top N
        return scored[:top_n]

    def _fallback_all(self) -> list[SkillMatch]:
        """Return all skills as fallback when no matches found.

        Returns:
            List of all skills with score 0
        """
        skills = self._get_skills()
        return [
            SkillMatch(
                path=skill.path,
                score=0,
                matched_keywords=[],
                name=skill.name,
                description=skill.description,
            )
            for skill in skills
        ]

    def format_recommendations(self, matches: list[SkillMatch]) -> str:
        """Format skill recommendations as a markdown table.

        Used for injection into phase CLAUDE.md templates.

        Args:
            matches: List of skill matches

        Returns:
            Markdown formatted table
        """
        if not matches:
            return "No skill recommendations available."

        lines = [
            "| Skill | Score | Matched Keywords |",
            "|-------|-------|------------------|",
        ]

        for match in matches:
            keywords = ", ".join(match.matched_keywords[:5])  # Limit to 5
            if len(match.matched_keywords) > 5:
                keywords += f" (+{len(match.matched_keywords) - 5} more)"
            lines.append(f"| {match.path} | {match.score} | {keywords} |")

        return "\n".join(lines)


def main():
    """CLI entry point for skill selection."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Select relevant skills for a request"
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Request text to match against skills",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of top skills to return (default: 3)",
    )
    parser.add_argument(
        "--index",
        type=Path,
        help="Path to INDEX.yaml (default: skills/INDEX.yaml)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="List all skills",
    )

    args = parser.parse_args()

    selector = SkillSelector(index_path=args.index)

    if args.all:
        skills = selector.all_skills()
        print(f"Found {len(skills)} skills:")
        for skill in skills:
            print(f"  - {skill.path}: {skill.name}")
    elif args.request:
        matches = selector.select(args.request, top_n=args.top_n)
        print(selector.format_recommendations(matches))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
