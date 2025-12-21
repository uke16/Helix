import pytest
from pathlib import Path

from helix.template_engine import TemplateEngine
from helix.context_manager import ContextManager
from helix.phase_loader import PhaseLoader


class TestTemplatePipeline:
    """Integration tests for template rendering pipeline."""

    @pytest.fixture
    def helix_templates(self):
        """Return path to actual HELIX templates."""
        return Path("/home/aiuser01/helix-v4/templates")

    def test_render_python_developer_template(self, helix_templates):
        """Should render Python developer template."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")

        engine = TemplateEngine(helix_templates / "developer")

        context = {
            "project": {"description": "Test project"},
            "task": {
                "description": "Implement feature X",
                "output_files": [
                    {"path": "src/feature.py", "description": "Main implementation"}
                ]
            },
            "quality_gate": {
                "type": "syntax_check",
                "description": "Check Python syntax"
            }
        }

        result = engine.render("python.md", context)

        assert "Python" in result
        assert "feature.py" in result

    def test_render_consultant_template(self, helix_templates):
        """Should render Meta-Consultant template."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")

        engine = TemplateEngine(helix_templates / "consultant")

        context = {
            "project": {"name": "BOM Export", "domain": "pdm"},
            "user_request": "Export BOM data to SAP",
            "experts": [
                {"name": "PDM Expert", "description": "Product data management"},
                {"name": "ERP Expert", "description": "SAP integration"},
            ]
        }

        result = engine.render("meta-consultant.md", context)

        assert "Meta-Consultant" in result or "Consultant" in result
        assert "BOM Export" in result

    def test_context_manager_provides_skills(self):
        """ContextManager should provide domain skills."""
        manager = ContextManager()

        skills = manager.get_skills_for_domain("pdm")
        assert isinstance(skills, list)

        skills = manager.get_skills_for_language("python")
        assert isinstance(skills, list)

    def test_full_claude_md_generation(self, helix_templates, temp_dir):
        """Should generate complete CLAUDE.md for a phase."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")

        # Create project
        project = temp_dir / "test-project"
        project.mkdir()
        (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Project
  domain: pdm
implementation:
  language: python
  summary: Test implementation
""")

        # Setup context
        context_manager = ContextManager()
        engine = TemplateEngine(helix_templates / "developer")

        context = context_manager.prepare_phase_context(
            project_dir=project,
            phase_dir=project / "phases" / "01-dev",
            domain="pdm",
            language="python",
        )

        # Add task info
        context["task"] = {
            "description": "Implement BOM export",
            "output_files": []
        }
        context["quality_gate"] = {"type": "syntax_check", "description": "Check syntax"}
        context["project"] = {"description": "BOM export project"}

        result = engine.render("python.md", context)

        assert len(result) > 100  # Should have substantial content
