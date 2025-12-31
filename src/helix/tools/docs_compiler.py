"""
HELIX Documentation Compiler

Compiles documentation from YAML sources and code docstrings into
generated output files (CLAUDE.md, skills/*/SKILL.md, etc.).

This module implements the core documentation generation pipeline
as specified in ADR-014.

Usage:
    python -m helix.tools.docs_compiler compile    # Generate all docs
    python -m helix.tools.docs_compiler validate   # Validate without writing
    python -m helix.tools.docs_compiler sources    # List source files
    python -m helix.tools.docs_compiler diff       # Show what would change

Example:
    >>> from helix.tools.docs_compiler import DocCompiler
    >>> compiler = DocCompiler()
    >>> result = compiler.compile()
    >>> if result.success:
    ...     print(f"Generated {len(result.files_written)} files")
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, cast, TYPE_CHECKING
import ast
import argparse
import sys

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
except ImportError:
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore
    TemplateNotFound = Exception  # type: ignore


@dataclass
class CompileResult:
    """Result of a documentation compilation run.

    Attributes:
        success: Whether the compilation completed without errors.
        files_written: List of file paths that were written.
        errors: List of error messages encountered during compilation.
        warnings: List of warning messages (non-fatal issues).
    """

    success: bool
    files_written: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SourceInfo:
    """Information about a documentation source file.

    Attributes:
        path: Path to the source file.
        key: Key used in the context dictionary.
        description: Description from the _meta section.
        generated_outputs: List of files this source generates.
    """

    path: Path
    key: str
    description: str = ""
    generated_outputs: list[str] = field(default_factory=list)


class DocCompiler:
    """Compiles documentation from YAML sources and code docstrings.

    The DocCompiler implements a pipeline that:
    1. Collects data from YAML source files (docs/sources/*.yaml)
    2. Extracts docstrings from Python code (src/helix/**/*.py)
    3. Parses ADR headers (adr/*.md)
    4. Renders Jinja2 templates to generate output files
    5. Validates the generated content

    Args:
        root: Root directory of the HELIX project. Defaults to current directory.

    Example:
        >>> compiler = DocCompiler(Path("/path/to/helix"))
        >>> result = compiler.compile()
        >>> if not result.success:
        ...     for error in result.errors:
        ...         print(f"ERROR: {error}")
    """

    # Token budget limits (in lines, as proxy for tokens)
    TOKEN_BUDGETS = {
        "CLAUDE.md": 300,
        "SKILL.md": 600,
    }

    # Template to output file mapping
    OUTPUT_MAPPINGS = {
        "CLAUDE.md.j2": "CLAUDE.md",
        "SKILL.md.j2": "skills/helix/SKILL.md",
        "ARCHITECTURE-MODULES.md.j2": "docs/ARCHITECTURE-MODULES.md",
    }

    def __init__(self, root: Path | None = None):
        """Initialize the DocCompiler.

        Args:
            root: Root directory of the HELIX project. Defaults to current directory.
        """
        self.root = root or Path(".")
        self.sources_dir = self.root / "docs" / "sources"
        self.templates_dir = self.root / "docs" / "templates"
        self._env: Any = None

    @property
    def env(self) -> Any:
        """Get the Jinja2 environment, creating it lazily.

        Returns:
            Configured Jinja2 Environment.

        Raises:
            RuntimeError: If Jinja2 is not installed.
        """
        if self._env is None:
            if Environment is None:  # pragma: no cover
                raise RuntimeError("Jinja2 is not installed. Run: pip install jinja2")

            if Environment is None:  # pragma: no cover
                raise RuntimeError("Jinja2 is not installed. Run: pip install jinja2")
            # Environment is guaranteed not None here
            _Env = cast(type, Environment)
            self._env = _Env(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        return self._env

    def collect_sources(self) -> dict[str, Any]:
        """Collect all source data from YAML files and code.

        Gathers data from:
        - YAML definition files in docs/sources/
        - Python docstrings from src/helix/
        - ADR headers from adr/

        Returns:
            Dictionary containing all collected context data.

        Raises:
            RuntimeError: If PyYAML is not installed.
        """
        if yaml is None:
            raise RuntimeError("PyYAML is not installed. Run: pip install pyyaml")

        context: dict[str, Any] = {}

        # Load YAML sources
        if self.sources_dir.exists():
            for yaml_file in sorted(self.sources_dir.glob("*.yaml")):
                key = yaml_file.stem.replace("-", "_")
                with open(yaml_file, encoding="utf-8") as f:
                    context[key] = yaml.safe_load(f)

        # Extract docstrings from code
        context["modules"] = self._extract_docstrings()

        # Parse ADR headers
        context["adrs"] = self._parse_adr_headers()

        return context

    def _extract_docstrings(self) -> list[dict[str, Any]]:
        """Extract module/class/function docstrings from Python code.

        Parses all Python files in src/helix/ and extracts docstrings
        for modules, classes, and public methods.

        Returns:
            List of module information dictionaries containing:
            - path: Relative path to the Python file
            - docstring: Module-level docstring
            - classes: List of class information with methods
        """
        modules: list[dict[str, Any]] = []
        src_dir = self.root / "src" / "helix"

        if not src_dir.exists():
            return modules

        for py_file in sorted(src_dir.rglob("*.py")):
            # Skip private modules except __init__.py
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                module_doc = ast.get_docstring(tree)

                classes: list[dict[str, Any]] = []
                functions: list[dict[str, Any]] = []

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = []
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                if not item.name.startswith("_") or item.name == "__init__":
                                    methods.append({
                                        "name": item.name,
                                        "docstring": ast.get_docstring(item),
                                        "lineno": item.lineno,
                                    })

                        classes.append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                            "lineno": node.lineno,
                            "methods": methods,
                        })

                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith("_"):
                            functions.append({
                                "name": node.name,
                                "docstring": ast.get_docstring(node),
                                "lineno": node.lineno,
                            })

                modules.append({
                    "path": str(py_file.relative_to(self.root)),
                    "docstring": module_doc,
                    "classes": classes,
                    "functions": functions,
                })

            except SyntaxError:
                # Skip files with syntax errors
                pass

        return modules

    def _parse_adr_headers(self) -> list[dict[str, Any]]:
        """Parse ADR YAML headers from markdown files.

        Reads all ADR files in adr/ directory and extracts the
        YAML frontmatter metadata.

        Returns:
            List of ADR information dictionaries sorted by ID.
        """
        if yaml is None:
            return []

        adrs: list[dict[str, Any]] = []
        adr_dir = self.root / "adr"

        if not adr_dir.exists():
            return adrs

        for adr_file in sorted(adr_dir.glob("*.md")):
            if adr_file.name == "INDEX.md":
                continue

            try:
                content = adr_file.read_text(encoding="utf-8")

                # Extract YAML frontmatter between --- markers
                if content.startswith("---"):
                    end_marker = content.find("---", 3)
                    if end_marker != -1:
                        yaml_content = content[3:end_marker].strip()
                        metadata = yaml.safe_load(yaml_content)

                        if metadata:
                            adrs.append({
                                "id": metadata.get("adr_id", ""),
                                "title": metadata.get("title", ""),
                                "status": metadata.get("status", ""),
                                "path": str(adr_file.relative_to(self.root)),
                            })

            except Exception:  # yaml.YAMLError or OSError
                # Skip files with parsing errors
                pass

        return sorted(adrs, key=lambda x: x.get("id", ""))

    def compile(self, targets: list[str] | None = None) -> CompileResult:
        """Compile documentation from sources.

        Generates output files by rendering Jinja2 templates with
        collected source data.

        Args:
            targets: Optional list of specific output files to generate.
                    If None, all configured outputs are generated.

        Returns:
            CompileResult with success status, files written, and any errors.
        """
        errors: list[str] = []
        warnings: list[str] = []
        files_written: list[Path] = []

        # Collect all source data
        try:
            context = self.collect_sources()
        except RuntimeError as e:
            return CompileResult(success=False, errors=[str(e)])

        # Determine which outputs to generate
        outputs = dict(self.OUTPUT_MAPPINGS)
        if targets:
            outputs = {k: v for k, v in outputs.items() if v in targets}

        # Render each template
        for template_name, output_path_str in outputs.items():
            output_path = self.root / output_path_str

            try:
                template = self.env.get_template(template_name)
                content = template.render(**context)

                # Add generation header
                header = self._generate_header(template_name)

                # Ensure parent directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the file
                output_path.write_text(header + content, encoding="utf-8")
                files_written.append(output_path)

            except TemplateNotFound:
                # Template doesn't exist yet - this is expected during initial setup
                warnings.append(f"Template not found: {template_name}")

            except Exception as e:
                errors.append(f"Failed to compile {template_name}: {e}")

        # Check token budgets
        budget_warnings = self._check_token_budgets()
        warnings.extend(budget_warnings)

        return CompileResult(
            success=len(errors) == 0,
            files_written=files_written,
            errors=errors,
            warnings=warnings,
        )

    def _generate_header(self, template_name: str) -> str:
        """Generate the auto-generation header for output files.

        Args:
            template_name: Name of the source template.

        Returns:
            Header string to prepend to generated files.
        """
        return (
            f"<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
            f"<!-- Template: docs/templates/{template_name} -->\n"
            f"<!-- Regenerate: python -m helix.tools.docs_compiler compile -->\n\n"
        )

    def _check_token_budgets(self) -> list[str]:
        """Check that generated files stay within token budgets.

        Returns:
            List of warning messages for files exceeding their budgets.
        """
        warnings: list[str] = []

        for filename, budget in self.TOKEN_BUDGETS.items():
            # Find matching files
            if filename == "CLAUDE.md":
                file_path = self.root / filename
            elif filename == "SKILL.md":
                # Check all SKILL.md files
                for skill_file in self.root.glob("skills/**/SKILL.md"):
                    if skill_file.exists():
                        lines = len(skill_file.read_text(encoding="utf-8").splitlines())
                        if lines > budget:
                            warnings.append(
                                f"{skill_file.relative_to(self.root)} has {lines} lines "
                                f"(budget: {budget})"
                            )
                continue
            else:
                file_path = self.root / filename

            if file_path.exists():
                lines = len(file_path.read_text(encoding="utf-8").splitlines())
                if lines > budget:
                    warnings.append(f"{filename} has {lines} lines (budget: {budget})")

        return warnings

    def validate(self) -> CompileResult:
        """Validate sources and templates without writing files.

        Checks that:
        - All YAML sources are valid
        - All templates render without errors
        - Token budgets are not exceeded

        Returns:
            CompileResult with validation status and any errors/warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Collect sources (validates YAML)
        try:
            context = self.collect_sources()
        except RuntimeError as e:
            return CompileResult(success=False, errors=[str(e)])

        # Validate all templates render
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.j2"):
                if template_file.name.startswith("_"):
                    continue

                try:
                    template = self.env.get_template(template_file.name)
                    template.render(**context)
                except Exception as e:
                    errors.append(f"Template {template_file.name} failed: {e}")

            # Also validate partials
            partials_dir = self.templates_dir / "partials"
            if partials_dir.exists():
                for partial_file in partials_dir.glob("*.j2"):
                    try:
                        template = self.env.get_template(f"partials/{partial_file.name}")
                        template.render(**context)
                    except Exception as e:
                        errors.append(f"Partial {partial_file.name} failed: {e}")

        # Check token budgets
        warnings.extend(self._check_token_budgets())

        return CompileResult(
            success=len(errors) == 0,
            files_written=[],
            errors=errors,
            warnings=warnings,
        )

    def show_sources(self) -> list[SourceInfo]:
        """List all documentation source files with metadata.

        Returns:
            List of SourceInfo objects describing each source file.
        """
        sources: list[SourceInfo] = []

        if not self.sources_dir.exists():
            return sources

        for yaml_file in sorted(self.sources_dir.glob("*.yaml")):
            key = yaml_file.stem.replace("-", "_")
            description = ""
            generated_outputs: list[str] = []

            try:
                if yaml is not None:
                    with open(yaml_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data and "_meta" in data:
                            meta = data["_meta"]
                            description = meta.get("description", "")
                            generated_outputs = meta.get("generated_outputs", [])
            except Exception:  # yaml.YAMLError or OSError
                pass

            sources.append(SourceInfo(
                path=yaml_file,
                key=key,
                description=description,
                generated_outputs=generated_outputs,
            ))

        return sources

    def diff(self) -> dict[str, str]:
        """Show what would change if compile was run.

        Compares current file contents with what would be generated.

        Returns:
            Dictionary mapping output paths to diff strings.
        """
        import difflib

        diffs: dict[str, str] = {}

        try:
            context = self.collect_sources()
        except RuntimeError:
            return diffs

        for template_name, output_path_str in self.OUTPUT_MAPPINGS.items():
            output_path = self.root / output_path_str

            try:
                template = self.env.get_template(template_name)
                new_content = self._generate_header(template_name) + template.render(**context)

                if output_path.exists():
                    old_content = output_path.read_text(encoding="utf-8")

                    if old_content != new_content:
                        diff = difflib.unified_diff(
                            old_content.splitlines(keepends=True),
                            new_content.splitlines(keepends=True),
                            fromfile=f"a/{output_path_str}",
                            tofile=f"b/{output_path_str}",
                        )
                        diffs[output_path_str] = "".join(diff)
                else:
                    diffs[output_path_str] = f"[NEW FILE: {output_path_str}]"

            except TemplateNotFound:
                pass
            except Exception as e:
                diffs[output_path_str] = f"[ERROR: {e}]"

        return diffs


def main() -> None:
    """CLI entry point for the documentation compiler.

    Provides subcommands for compile, validate, sources, and diff operations.
    """
    parser = argparse.ArgumentParser(
        description="HELIX Documentation Compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m helix.tools.docs_compiler compile     # Generate all docs
    python -m helix.tools.docs_compiler validate    # Check without writing
    python -m helix.tools.docs_compiler sources     # List source files
    python -m helix.tools.docs_compiler diff        # Show pending changes
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compile command
    compile_parser = subparsers.add_parser("compile", help="Compile documentation")
    compile_parser.add_argument(
        "--target",
        "-t",
        action="append",
        dest="targets",
        help="Specific output file to generate (can be repeated)",
    )

    # validate command
    subparsers.add_parser("validate", help="Validate sources and templates")

    # sources command
    subparsers.add_parser("sources", help="List source files")

    # diff command
    subparsers.add_parser("diff", help="Show what would change")

    args = parser.parse_args()

    # Default to compile if no command specified
    if args.command is None:
        args.command = "compile"
        args.targets = None

    compiler = DocCompiler()

    if args.command == "compile":
        targets = getattr(args, "targets", None)
        result = compiler.compile(targets=targets)

        for f in result.files_written:
            print(f"Written: {f}")

        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)

        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

        if result.success:
            print(f"\nCompilation successful: {len(result.files_written)} files written")
        else:
            print("\nCompilation failed", file=sys.stderr)

        sys.exit(0 if result.success else 1)

    elif args.command == "validate":
        result = compiler.validate()

        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)

        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

        if result.success:
            print("Validation passed")
        else:
            print("Validation failed", file=sys.stderr)

        sys.exit(0 if result.success else 1)

    elif args.command == "sources":
        sources = compiler.show_sources()

        if not sources:
            print("No source files found in docs/sources/")
        else:
            print("Documentation Sources:")
            print("-" * 60)
            for source in sources:
                print(f"\n{source.path}")
                print(f"  Key: {source.key}")
                if source.description:
                    print(f"  Description: {source.description}")
                if source.generated_outputs:
                    print(f"  Generates: {', '.join(source.generated_outputs)}")

    elif args.command == "diff":
        diffs = compiler.diff()

        if not diffs:
            print("No changes detected")
        else:
            for path, diff_content in diffs.items():
                print(f"\n{'=' * 60}")
                print(f"File: {path}")
                print("=" * 60)
                print(diff_content)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
