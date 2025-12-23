"""Template rendering tests for HELIX documentation compiler.

Tests that:
1. All YAML sources are loadable and valid
2. All templates render without errors
3. Generated output is valid Markdown
4. Output is written to generated/ directory

Usage:
    pytest output/tests/test_templates.py -v

    # Or run directly:
    python output/tests/test_templates.py
"""

import sys
from pathlib import Path
from typing import Any

import pytest


# Adjust path to find sources and templates
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
SOURCES_DIR = INPUT_DIR / "sources"
TEMPLATES_DIR = INPUT_DIR / "templates"
GENERATED_DIR = OUTPUT_DIR / "generated"


def load_yaml_sources() -> dict[str, Any]:
    """Load all YAML source files into a context dictionary.

    Returns:
        Dictionary with source file stems as keys and parsed YAML as values.

    Raises:
        ImportError: If PyYAML is not installed.
        yaml.YAMLError: If a YAML file is malformed.
    """
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    context: dict[str, Any] = {}

    if not SOURCES_DIR.exists():
        pytest.skip(f"Sources directory not found: {SOURCES_DIR}")

    for yaml_file in sorted(SOURCES_DIR.glob("*.yaml")):
        key = yaml_file.stem.replace("-", "_")
        with open(yaml_file, encoding="utf-8") as f:
            context[key] = yaml.safe_load(f)

    return context


def get_jinja2_env():
    """Create a Jinja2 environment for template rendering.

    Returns:
        Configured Jinja2 Environment.

    Raises:
        ImportError: If Jinja2 is not installed.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        pytest.skip("Jinja2 not installed")

    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class TestYAMLSources:
    """Test suite for YAML source file validation."""

    def test_sources_directory_exists(self):
        """Verify the sources directory exists."""
        assert SOURCES_DIR.exists(), f"Sources directory not found: {SOURCES_DIR}"

    def test_quality_gates_yaml_exists(self):
        """Verify quality-gates.yaml exists."""
        assert (SOURCES_DIR / "quality-gates.yaml").exists()

    def test_phase_types_yaml_exists(self):
        """Verify phase-types.yaml exists."""
        assert (SOURCES_DIR / "phase-types.yaml").exists()

    def test_domains_yaml_exists(self):
        """Verify domains.yaml exists."""
        assert (SOURCES_DIR / "domains.yaml").exists()

    def test_escalation_yaml_exists(self):
        """Verify escalation.yaml exists."""
        assert (SOURCES_DIR / "escalation.yaml").exists()

    def test_all_yamls_loadable(self):
        """Verify all YAML files can be parsed without errors."""
        context = load_yaml_sources()
        assert len(context) >= 4, f"Expected at least 4 sources, got {len(context)}"

    def test_quality_gates_structure(self):
        """Verify quality-gates.yaml has correct structure."""
        context = load_yaml_sources()
        assert "quality_gates" in context
        assert "gates" in context["quality_gates"]
        assert len(context["quality_gates"]["gates"]) >= 5

    def test_phase_types_structure(self):
        """Verify phase-types.yaml has correct structure."""
        context = load_yaml_sources()
        assert "phase_types" in context
        assert "phase_types" in context["phase_types"]
        assert len(context["phase_types"]["phase_types"]) >= 5

    def test_domains_structure(self):
        """Verify domains.yaml has correct structure."""
        context = load_yaml_sources()
        assert "domains" in context
        assert "domains" in context["domains"]
        assert len(context["domains"]["domains"]) >= 4

    def test_escalation_structure(self):
        """Verify escalation.yaml has correct structure."""
        context = load_yaml_sources()
        assert "escalation" in context
        assert "escalation" in context["escalation"]
        assert "levels" in context["escalation"]["escalation"]


class TestTemplateRendering:
    """Test suite for Jinja2 template rendering."""

    def test_templates_directory_exists(self):
        """Verify the templates directory exists."""
        assert TEMPLATES_DIR.exists(), f"Templates directory not found: {TEMPLATES_DIR}"

    def test_claude_md_template_exists(self):
        """Verify CLAUDE.md.j2 exists."""
        assert (TEMPLATES_DIR / "CLAUDE.md.j2").exists()

    def test_skill_md_template_exists(self):
        """Verify SKILL.md.j2 exists."""
        assert (TEMPLATES_DIR / "SKILL.md.j2").exists()

    def test_partials_exist(self):
        """Verify all required partials exist."""
        partials_dir = TEMPLATES_DIR / "partials"
        assert partials_dir.exists()

        required_partials = [
            "quality-gates-table.md.j2",
            "quality-gates-detail.md.j2",
        ]
        for partial in required_partials:
            assert (partials_dir / partial).exists(), f"Missing partial: {partial}"

    def test_render_claude_md(self):
        """Test CLAUDE.md.j2 renders without errors."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("CLAUDE.md.j2")
        output = template.render(**context)

        assert len(output) > 0
        assert "# HELIX" in output
        assert "Quality Gates" in output

    def test_render_skill_md(self):
        """Test SKILL.md.j2 renders without errors."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("SKILL.md.j2")
        output = template.render(**context)

        assert len(output) > 0
        assert "HELIX" in output

    def test_render_quality_gates_table(self):
        """Test quality-gates-table.md.j2 renders without errors."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("partials/quality-gates-table.md.j2")
        output = template.render(**context)

        assert len(output) > 0
        assert "files_exist" in output
        assert "adr_valid" in output

    def test_render_quality_gates_detail(self):
        """Test quality-gates-detail.md.j2 renders without errors."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("partials/quality-gates-detail.md.j2")
        output = template.render(**context)

        assert len(output) > 0
        assert "Files Exist" in output


class TestOutputGeneration:
    """Test suite for output file generation."""

    def test_generate_claude_md(self):
        """Generate CLAUDE.md to generated/ directory."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("CLAUDE.md.j2")
        output = template.render(**context)

        # Add generation header
        header = (
            "<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
            "<!-- Template: docs/templates/CLAUDE.md.j2 -->\n"
            "<!-- Regenerate: python -m helix.tools.docs_compiler compile -->\n\n"
        )

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = GENERATED_DIR / "CLAUDE.md"
        output_path.write_text(header + output, encoding="utf-8")

        assert output_path.exists()
        lines = len(output_path.read_text().splitlines())
        print(f"Generated CLAUDE.md with {lines} lines")

    def test_generate_skill_md(self):
        """Generate SKILL.md to generated/ directory."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("SKILL.md.j2")
        output = template.render(**context)

        # Add generation header
        header = (
            "<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
            "<!-- Template: docs/templates/SKILL.md.j2 -->\n"
            "<!-- Regenerate: python -m helix.tools.docs_compiler compile -->\n\n"
        )

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = GENERATED_DIR / "SKILL.md"
        output_path.write_text(header + output, encoding="utf-8")

        assert output_path.exists()
        lines = len(output_path.read_text().splitlines())
        print(f"Generated SKILL.md with {lines} lines")


class TestMarkdownValidity:
    """Test suite for validating generated Markdown."""

    def test_claude_md_has_headers(self):
        """Verify generated CLAUDE.md has proper header structure."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("CLAUDE.md.j2")
        output = template.render(**context)

        # Check for essential sections
        assert "# HELIX" in output, "Missing main title"
        assert "## " in output, "Missing section headers"
        assert "---" in output, "Missing section separators"

    def test_skill_md_has_headers(self):
        """Verify generated SKILL.md has proper header structure."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        template = env.get_template("SKILL.md.j2")
        output = template.render(**context)

        # Check for essential sections
        assert "# HELIX" in output, "Missing main title"
        assert "## " in output, "Missing section headers"

    def test_no_template_syntax_in_output(self):
        """Verify no Jinja2 syntax leaks into output."""
        context = load_yaml_sources()
        env = get_jinja2_env()

        for template_name in ["CLAUDE.md.j2", "SKILL.md.j2"]:
            template = env.get_template(template_name)
            output = template.render(**context)

            assert "{{" not in output, f"Unrendered variable in {template_name}"
            assert "{%" not in output, f"Unrendered block in {template_name}"
            assert "{#" not in output, f"Unrendered comment in {template_name}"


def run_tests():
    """Run all tests and generate output files."""
    print("=" * 60)
    print("HELIX Documentation Template Tests")
    print("=" * 60)

    # Check dependencies
    try:
        import yaml  # noqa: F401
        print("[OK] PyYAML installed")
    except ImportError:
        print("[FAIL] PyYAML not installed - run: pip install pyyaml")
        return False

    try:
        from jinja2 import Environment  # noqa: F401
        print("[OK] Jinja2 installed")
    except ImportError:
        print("[FAIL] Jinja2 not installed - run: pip install jinja2")
        return False

    print()

    # Load sources
    print("Loading YAML sources...")
    try:
        context = load_yaml_sources()
        print(f"  Loaded {len(context)} source files")
        for key in context:
            print(f"    - {key}")
    except Exception as e:
        print(f"[FAIL] Failed to load sources: {e}")
        return False

    print()

    # Render templates
    print("Rendering templates...")
    env = get_jinja2_env()

    templates_to_render = {
        "CLAUDE.md.j2": "CLAUDE.md",
        "SKILL.md.j2": "SKILL.md",
    }

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    for template_name, output_name in templates_to_render.items():
        try:
            template = env.get_template(template_name)
            output = template.render(**context)

            # Add generation header
            header = (
                "<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
                f"<!-- Template: docs/templates/{template_name} -->\n"
                "<!-- Regenerate: python -m helix.tools.docs_compiler compile -->\n\n"
            )

            output_path = GENERATED_DIR / output_name
            output_path.write_text(header + output, encoding="utf-8")

            lines = len(output_path.read_text().splitlines())
            print(f"  [OK] {template_name} -> {output_name} ({lines} lines)")

        except Exception as e:
            print(f"  [FAIL] {template_name}: {e}")
            return False

    print()
    print("=" * 60)
    print("All tests passed!")
    print(f"Generated files written to: {GENERATED_DIR}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
