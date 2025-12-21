import pytest
from pathlib import Path

from helix.context_manager import ContextManager


class TestContextManager:
    """Tests for ContextManager."""

    def test_get_skills_for_domain(self):
        """Should return skills for a domain."""
        manager = ContextManager()
        skills = manager.get_skills_for_domain("pdm")

        assert isinstance(skills, list)

    def test_get_skills_for_language(self):
        """Should return skills for a language."""
        manager = ContextManager()
        skills = manager.get_skills_for_language("python")

        assert isinstance(skills, list)

    def test_prepare_phase_context(self, sample_project, temp_dir):
        """Should prepare context for phase execution."""
        manager = ContextManager()
        phase_dir = temp_dir / "phase"
        phase_dir.mkdir()

        context = manager.prepare_phase_context(
            project_dir=sample_project,
            phase_dir=phase_dir,
            domain="helix",
            language="python",
        )

        assert "skills" in context
        assert "project" in context
