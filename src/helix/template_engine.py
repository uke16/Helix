"""Template Engine for HELIX v4.

Jinja2-based template engine for CLAUDE.md generation.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


class TemplateEngine:
    """Jinja2-based template engine for generating CLAUDE.md files.

    The TemplateEngine supports template inheritance with two levels:
    - Base templates (e.g., _base.md)
    - Language/domain specific templates (e.g., python.md)

    Templates are loaded from the configured templates directory
    and rendered with project-specific context.

    Example:
        engine = TemplateEngine()
        claude_md = engine.render_claude_md(
            template_name="python",
            context={
                "project_name": "my-cli-tool",
                "description": "A CLI tool for data processing",
                "skills": ["testing", "cli-development"],
            }
        )
    """

    DEFAULT_TEMPLATES_DIR = Path("/home/aiuser01/helix-v4/templates")

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize the TemplateEngine.

        Args:
            templates_dir: Directory containing Jinja2 templates.
                          Defaults to /home/aiuser01/helix-v4/templates/.
        """
        self.templates_dir = templates_dir or self.DEFAULT_TEMPLATES_DIR
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get the Jinja2 environment, creating it if necessary."""
        if self._env is None:
            self._env = self._create_environment()
        return self._env

    def _create_environment(self) -> Environment:
        """Create and configure the Jinja2 environment.

        Returns:
            Configured Jinja2 Environment.
        """
        loader = FileSystemLoader(str(self.templates_dir))

        env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        env.filters["indent_lines"] = self._indent_lines
        env.filters["bullet_list"] = self._bullet_list
        env.filters["numbered_list"] = self._numbered_list

        return env

    def get_template(self, name: str) -> Template:
        """Get a template by name.

        Args:
            name: Template name (without .md extension).

        Returns:
            The Jinja2 Template object.

        Raises:
            TemplateNotFound: If the template doesn't exist.
        """
        template_name = name if name.endswith(".md") else f"{name}.md"

        try:
            return self.env.get_template(template_name)
        except TemplateNotFound:
            if "/" not in name:
                try:
                    return self.env.get_template(f"claude/{template_name}")
                except TemplateNotFound:
                    pass
            raise

    def render_claude_md(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a CLAUDE.md file from a template.

        Args:
            template_name: Name of the template to use.
            context: Template context dictionary.

        Returns:
            Rendered CLAUDE.md content.
        """
        template = self.get_template(template_name)
        return template.render(**context)

    def render_from_spec(self, spec: dict[str, Any]) -> str:
        """Render CLAUDE.md from a spec dictionary.

        Automatically selects the appropriate template based on
        the spec's domain and language.

        Args:
            spec: The spec dictionary from spec.yaml.

        Returns:
            Rendered CLAUDE.md content.
        """
        meta = spec.get("meta", {})
        domain = meta.get("domain", "default")
        language = meta.get("language", "python")

        template_name = self._select_template(domain, language)

        context = self._build_context(spec)

        return self.render_claude_md(template_name, context)

    def _select_template(self, domain: str, language: str) -> str:
        """Select the best template for the given domain and language.

        Args:
            domain: Project domain (e.g., "cli-tool").
            language: Programming language (e.g., "python").

        Returns:
            Template name to use.
        """
        candidates = [
            f"{domain}-{language}",
            domain,
            language,
            "_base",
        ]

        for candidate in candidates:
            template_path = self.templates_dir / "claude" / f"{candidate}.md"
            if template_path.exists():
                return f"claude/{candidate}"

            template_path = self.templates_dir / f"{candidate}.md"
            if template_path.exists():
                return candidate

        return "_base"

    def _build_context(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Build template context from a spec dictionary.

        Args:
            spec: The spec dictionary.

        Returns:
            Context dictionary for template rendering.
        """
        meta = spec.get("meta", {})
        implementation = spec.get("implementation", {})
        context_config = spec.get("context", {})
        output_config = spec.get("output", {})

        return {
            "project_id": meta.get("id", "unknown"),
            "project_name": meta.get("name", meta.get("id", "Unknown Project")),
            "version": meta.get("version", "1.0.0"),
            "domain": meta.get("domain", "default"),
            "language": meta.get("language", "python"),
            "summary": implementation.get("summary", ""),
            "requirements": implementation.get("requirements", []),
            "constraints": implementation.get("constraints", []),
            "acceptance_criteria": implementation.get("acceptance_criteria", []),
            "skills": context_config.get("skills", []),
            "templates": context_config.get("templates", []),
            "output_files": output_config.get("files", []),
            "spec": spec,
        }

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """Render a template from a string.

        Args:
            template_string: Jinja2 template as a string.
            context: Template context dictionary.

        Returns:
            Rendered template content.
        """
        template = self.env.from_string(template_string)
        return template.render(**context)

    @staticmethod
    def _indent_lines(text: str, width: int = 2, first: bool = False) -> str:
        """Indent all lines of text.

        Args:
            text: Text to indent.
            width: Number of spaces to indent.
            first: Whether to indent the first line.

        Returns:
            Indented text.
        """
        indent = " " * width
        lines = text.split("\n")

        if first:
            return "\n".join(indent + line for line in lines)
        else:
            result = [lines[0]]
            result.extend(indent + line for line in lines[1:])
            return "\n".join(result)

    @staticmethod
    def _bullet_list(items: list[str], bullet: str = "-") -> str:
        """Convert a list to a bullet list.

        Args:
            items: List of items.
            bullet: Bullet character to use.

        Returns:
            Formatted bullet list.
        """
        return "\n".join(f"{bullet} {item}" for item in items)

    @staticmethod
    def _numbered_list(items: list[str]) -> str:
        """Convert a list to a numbered list.

        Args:
            items: List of items.

        Returns:
            Formatted numbered list.
        """
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))
