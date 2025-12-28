"""
Tests for SkillSelector.

ADR-020: Tests the intelligent skill selection based on request keywords,
aliases, and triggers.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from helix.docs.skill_selector import SkillMatch, SkillSelector


@pytest.fixture
def sample_index_yaml():
    """Sample INDEX.yaml content for testing."""
    return {
        "_meta": {
            "generated_at": "2024-12-28T10:00:00+00:00",
            "generator": "helix.docs.skill_index",
        },
        "skills": [
            {
                "path": "skills/pdm/SKILL.md",
                "name": "PDM - Product Data Management",
                "description": "BOM, Artikel, Stucklisten, SAP-Integration",
                "auto_keywords": [
                    "PDM",
                    "BOM",
                    "Bill of Materials",
                    "Artikel",
                    "SAP",
                    "Stuckliste",
                ],
                "aliases": ["Bill of Materials", "Produktdaten", "Product Data"],
                "triggers": [
                    "wenn BOM oder Stuckliste erwahnt",
                    "wenn SAP-Integration benotigt",
                ],
            },
            {
                "path": "skills/encoder/SKILL.md",
                "name": "POSITAL Encoder",
                "description": "Encoder products, specifications",
                "auto_keywords": [
                    "Encoder",
                    "POSITAL",
                    "Absolute",
                    "Incremental",
                    "Resolution",
                ],
                "aliases": ["Drehgeber", "Sensor"],
                "triggers": ["wenn Encoder erwahnt"],
            },
            {
                "path": "skills/helix/SKILL.md",
                "name": "HELIX Core",
                "description": "HELIX Orchestration System",
                "auto_keywords": [
                    "HELIX",
                    "Phase",
                    "Quality Gate",
                    "Orchestrator",
                    "ADR",
                ],
                "aliases": ["Orchestration", "Workflow"],
                "triggers": ["wenn HELIX erwahnt", "wenn Phase oder Workflow erwahnt"],
            },
            {
                "path": "skills/infrastructure/SKILL.md",
                "name": "Infrastructure",
                "description": "Docker, PostgreSQL, deployment",
                "auto_keywords": [
                    "Docker",
                    "PostgreSQL",
                    "Database",
                    "Container",
                    "Deployment",
                ],
                "aliases": ["DevOps", "Datenbank"],
                "triggers": ["wenn Docker oder Container erwahnt"],
            },
        ],
    }


@pytest.fixture
def temp_index_file(sample_index_yaml, tmp_path):
    """Create a temporary INDEX.yaml file."""
    index_path = tmp_path / "skills" / "INDEX.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        yaml.dump(sample_index_yaml, f, allow_unicode=True)
    return index_path


@pytest.fixture
def selector(temp_index_file, tmp_path):
    """Create a SkillSelector with test index."""
    return SkillSelector(index_path=temp_index_file, project_root=tmp_path)


class TestSkillSelectorInit:
    """Tests for SkillSelector initialization."""

    def test_init_with_default_path(self, tmp_path):
        """Test initialization with default index path."""
        selector = SkillSelector(project_root=tmp_path)
        assert selector.index_path == tmp_path / "skills" / "INDEX.yaml"

    def test_init_with_custom_path(self, temp_index_file, tmp_path):
        """Test initialization with custom index path."""
        selector = SkillSelector(index_path=temp_index_file, project_root=tmp_path)
        assert selector.index_path == temp_index_file

    def test_load_index_file_not_found(self, tmp_path):
        """Test error when INDEX.yaml doesn't exist."""
        selector = SkillSelector(project_root=tmp_path)
        with pytest.raises(FileNotFoundError) as exc_info:
            selector.all_skills()
        assert "Skill index not found" in str(exc_info.value)


class TestSkillSelectorSelect:
    """Tests for SkillSelector.select() method."""

    def test_select_exact_keyword_match(self, selector):
        """Test selecting skills with exact keyword match."""
        matches = selector.select("BOM Export")

        assert len(matches) > 0
        # PDM skill should be first (has BOM keyword)
        assert matches[0].path == "skills/pdm/SKILL.md"
        assert matches[0].score >= SkillSelector.EXACT_MATCH_SCORE
        assert "BOM" in matches[0].matched_keywords

    def test_select_multiple_keywords(self, selector):
        """Test selecting with multiple matching keywords."""
        matches = selector.select("BOM SAP Integration")

        assert len(matches) > 0
        # PDM skill should score higher with multiple matches
        pdm_match = next((m for m in matches if m.path == "skills/pdm/SKILL.md"), None)
        assert pdm_match is not None
        assert pdm_match.score >= 2 * SkillSelector.EXACT_MATCH_SCORE

    def test_select_case_insensitive(self, selector):
        """Test that matching is case-insensitive."""
        matches_upper = selector.select("BOM")
        matches_lower = selector.select("bom")

        assert len(matches_upper) == len(matches_lower)
        assert matches_upper[0].path == matches_lower[0].path

    def test_select_alias_match(self, selector):
        """Test matching against aliases."""
        matches = selector.select("Produktdaten Management")

        assert len(matches) > 0
        pdm_match = next((m for m in matches if m.path == "skills/pdm/SKILL.md"), None)
        assert pdm_match is not None
        # Should have alias match indicator
        assert any("~" in kw for kw in pdm_match.matched_keywords)

    def test_select_trigger_match(self, selector):
        """Test matching against trigger phrases."""
        matches = selector.select("Ich brauche Stuckliste Information")

        assert len(matches) > 0
        pdm_match = next((m for m in matches if m.path == "skills/pdm/SKILL.md"), None)
        assert pdm_match is not None
        # Trigger match adds significant score
        assert pdm_match.score >= SkillSelector.TRIGGER_MATCH_SCORE

    def test_select_top_n_limit(self, selector):
        """Test limiting results to top N."""
        matches = selector.select("HELIX Docker BOM", top_n=2)

        assert len(matches) <= 2

    def test_select_default_top_n(self, selector):
        """Test default top_n is 3."""
        # Query that matches all skills
        matches = selector.select("Docker BOM Encoder HELIX")

        assert len(matches) <= SkillSelector.DEFAULT_TOP_N

    def test_select_no_match_returns_fallback(self, selector):
        """Test fallback when no keywords match."""
        matches = selector.select("xxxxxxxxxxxxxxx")

        # Should return all skills as fallback
        assert len(matches) == 4
        # All should have score 0
        assert all(m.score == 0 for m in matches)

    def test_select_minimum_score_filter(self, selector):
        """Test that skills below minimum score are filtered out."""
        # Partial match should still exceed minimum
        matches = selector.select("PDM")

        assert len(matches) > 0
        assert all(m.score >= SkillSelector.MIN_RECOMMEND_SCORE for m in matches)

    def test_select_sorted_by_score(self, selector):
        """Test results are sorted by score descending."""
        matches = selector.select("BOM Docker")

        # Verify sorted by score
        scores = [m.score for m in matches]
        assert scores == sorted(scores, reverse=True)


class TestSkillSelectorTriggers:
    """Tests for trigger phrase matching."""

    def test_trigger_with_wenn_keyword(self, selector):
        """Test trigger matching with 'wenn' prefix."""
        matches = selector.select("Encoder Configuration")

        encoder_match = next(
            (m for m in matches if m.path == "skills/encoder/SKILL.md"), None
        )
        assert encoder_match is not None

    def test_trigger_with_oder_condition(self, selector):
        """Test trigger with OR conditions."""
        # Trigger: "wenn BOM oder Stuckliste erwahnt"
        matches_bom = selector.select("BOM")
        matches_stuckliste = selector.select("Stuckliste")

        # Both should match PDM skill
        assert any(m.path == "skills/pdm/SKILL.md" for m in matches_bom)
        assert any(m.path == "skills/pdm/SKILL.md" for m in matches_stuckliste)


class TestSkillMatch:
    """Tests for SkillMatch dataclass."""

    def test_skill_match_to_dict(self):
        """Test SkillMatch serialization."""
        match = SkillMatch(
            path="skills/test/SKILL.md",
            score=25,
            matched_keywords=["BOM", "SAP"],
            name="Test Skill",
            description="Test description",
        )

        result = match.to_dict()

        assert result["path"] == "skills/test/SKILL.md"
        assert result["score"] == 25
        assert result["matched_keywords"] == ["BOM", "SAP"]
        assert result["name"] == "Test Skill"
        assert result["description"] == "Test description"


class TestAllSkills:
    """Tests for all_skills() method."""

    def test_all_skills_returns_entries(self, selector):
        """Test that all_skills returns all skill entries."""
        skills = selector.all_skills()

        assert len(skills) == 4
        paths = [s.path for s in skills]
        assert "skills/pdm/SKILL.md" in paths
        assert "skills/encoder/SKILL.md" in paths
        assert "skills/helix/SKILL.md" in paths
        assert "skills/infrastructure/SKILL.md" in paths

    def test_all_skills_contains_keywords(self, selector):
        """Test that skill entries contain keywords."""
        skills = selector.all_skills()

        pdm_skill = next(s for s in skills if s.path == "skills/pdm/SKILL.md")
        assert "BOM" in pdm_skill.auto_keywords
        assert "SAP" in pdm_skill.auto_keywords


class TestFormatRecommendations:
    """Tests for format_recommendations() method."""

    def test_format_recommendations_markdown_table(self, selector):
        """Test markdown table formatting."""
        matches = selector.select("BOM")
        result = selector.format_recommendations(matches)

        # Should be markdown table
        assert "| Skill | Score | Matched Keywords |" in result
        assert "|-------|-------|------------------|" in result
        assert "skills/pdm/SKILL.md" in result

    def test_format_empty_recommendations(self, selector):
        """Test formatting empty match list."""
        result = selector.format_recommendations([])

        assert "No skill recommendations available" in result

    def test_format_truncates_keywords(self, selector):
        """Test that keywords are limited to 5 in display."""
        # Create a match with many keywords
        match = SkillMatch(
            path="test",
            score=100,
            matched_keywords=["a", "b", "c", "d", "e", "f", "g"],
        )

        result = selector.format_recommendations([match])

        # Should show 5 + "(+2 more)"
        assert "+2 more" in result


class TestTokenization:
    """Tests for text tokenization."""

    def test_tokenize_with_umlauts(self, selector):
        """Test tokenization handles German umlauts."""
        tokens = selector._tokenize("Stuckliste Artikel")

        assert "stuckliste" in tokens
        assert "artikel" in tokens

    def test_tokenize_with_special_chars(self, selector):
        """Test tokenization handles hyphenated words."""
        tokens = selector._tokenize("SAP-Integration test-case")

        assert "sap-integration" in tokens
        assert "test-case" in tokens

    def test_tokenize_removes_numbers_only(self, selector):
        """Test that pure numbers are not tokens but alphanumeric are."""
        tokens = selector._tokenize("test123 456 abc")

        assert "test123" in tokens
        assert "abc" in tokens
        # Pure number should not be a token if filtered
