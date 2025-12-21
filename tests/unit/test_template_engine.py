import pytest
from pathlib import Path

from helix.template_engine import TemplateEngine


class TestTemplateEngine:
    """Tests for TemplateEngine."""

    def test_render_simple_template(self, temp_dir):
        """Should render template with variables."""
        # Create test template
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        (template_dir / "test.md").write_text("Hello {{ name }}!")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.md", {"name": "World"})

        assert result == "Hello World!"

    def test_render_with_missing_variable(self, temp_dir):
        """Should handle missing variables gracefully."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        (template_dir / "test.md").write_text("Hello {{ name }}!")

        engine = TemplateEngine(template_dir)
        # Should not raise, use undefined handling
        result = engine.render("test.md", {})
        assert "Hello" in result

    def test_template_inheritance(self, temp_dir):
        """Should support template inheritance."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()

        (template_dir / "_base.md").write_text("""
# Base
{% block content %}{% endblock %}
""")
        (template_dir / "child.md").write_text("""
{% extends "_base.md" %}
{% block content %}Child content{% endblock %}
""")

        engine = TemplateEngine(template_dir)
        result = engine.render("child.md", {})

        assert "Base" in result
        assert "Child content" in result
