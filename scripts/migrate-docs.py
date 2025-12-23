#!/usr/bin/env python3
"""
Migration Script for HELIX Documentation System.

This script migrates from manually maintained documentation to the
generated documentation system (ADR-014).

Features:
- Backup current CLAUDE.md and skills/helix/SKILL.md
- Generate new versions from templates
- Show diff between old and new
- Optionally replace old files with generated versions

Usage:
    python migrate-docs.py --backup           # Create backups only
    python migrate-docs.py --diff             # Show what would change
    python migrate-docs.py --dry-run          # Simulate migration
    python migrate-docs.py --migrate          # Perform actual migration

Example:
    cd helix-v4
    python projects/external/impl-phase5/output/scripts/migrate-docs.py --diff
    python projects/external/impl-phase5/output/scripts/migrate-docs.py --migrate
"""

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def find_repo_root() -> Path:
    """Find the HELIX repository root.

    Returns:
        Path to repository root.

    Raises:
        RuntimeError: If root cannot be found.
    """
    current = Path.cwd()
    while current != current.parent:
        if (current / "CLAUDE.md").exists() and (current / "src" / "helix").exists():
            return current
        current = current.parent
    raise RuntimeError("Cannot find HELIX repository root")


def load_yaml_sources(sources_dir: Path) -> dict[str, Any]:
    """Load all YAML source files.

    Args:
        sources_dir: Path to docs/sources directory.

    Returns:
        Dictionary with parsed YAML data.
    """
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)

    context: dict[str, Any] = {}

    if not sources_dir.exists():
        print(f"ERROR: Sources directory not found: {sources_dir}")
        sys.exit(1)

    for yaml_file in sorted(sources_dir.glob("*.yaml")):
        key = yaml_file.stem.replace("-", "_")
        with open(yaml_file, encoding="utf-8") as f:
            context[key] = yaml.safe_load(f)

    return context


def render_template(templates_dir: Path, template_name: str, context: dict) -> str:
    """Render a Jinja2 template.

    Args:
        templates_dir: Path to templates directory.
        template_name: Name of template file.
        context: Context dictionary for rendering.

    Returns:
        Rendered template content.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: pip install jinja2")
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_name)
    return template.render(**context)


def create_backup(file_path: Path, backup_dir: Path) -> Path | None:
    """Create a backup of a file.

    Args:
        file_path: File to backup.
        backup_dir: Directory for backups.

    Returns:
        Path to backup file, or None if file doesn't exist.
    """
    if not file_path.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(file_path, backup_path)
    return backup_path


def generate_header(template_name: str) -> str:
    """Generate the auto-generation header.

    Args:
        template_name: Name of source template.

    Returns:
        Header string.
    """
    return (
        f"<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
        f"<!-- Template: docs/templates/{template_name} -->\n"
        f"<!-- Regenerate: python -m helix.tools.docs_compiler compile -->\n\n"
    )


def show_diff(old_content: str, new_content: str, file_name: str) -> bool:
    """Show diff between old and new content.

    Args:
        old_content: Original file content.
        new_content: New generated content.
        file_name: Name of file for display.

    Returns:
        True if there are differences, False otherwise.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_name}",
        tofile=f"b/{file_name}",
    ))

    if diff:
        print(f"\n{'=' * 60}")
        print(f"Diff for: {file_name}")
        print("=" * 60)
        for line in diff[:100]:  # Limit output
            if line.startswith("+") and not line.startswith("+++"):
                print(f"\033[32m{line}\033[0m", end="")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"\033[31m{line}\033[0m", end="")
            else:
                print(line, end="")

        if len(diff) > 100:
            print(f"\n... ({len(diff) - 100} more lines)")
        return True
    else:
        print(f"\n{file_name}: No changes")
        return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate HELIX documentation to generated system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python migrate-docs.py --backup     # Create backups only
    python migrate-docs.py --diff       # Show what would change
    python migrate-docs.py --dry-run    # Simulate migration
    python migrate-docs.py --migrate    # Perform actual migration
        """,
    )

    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backups of current files",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff between current and generated",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Perform actual migration",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration without confirmation",
    )

    args = parser.parse_args()

    if not any([args.backup, args.diff, args.dry_run, args.migrate]):
        parser.print_help()
        sys.exit(1)

    # Find repository root
    try:
        root = find_repo_root()
        print(f"Repository root: {root}")
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Configuration
    sources_dir = root / "docs" / "sources"
    templates_dir = root / "docs" / "templates"
    backup_dir = root / ".backups" / "docs"

    # Files to migrate
    migrations = [
        {
            "template": "CLAUDE.md.j2",
            "output": root / "CLAUDE.md",
            "name": "CLAUDE.md",
        },
        {
            "template": "SKILL.md.j2",
            "output": root / "skills" / "helix" / "SKILL.md",
            "name": "skills/helix/SKILL.md",
        },
    ]

    # Check directories exist
    if not sources_dir.exists():
        print(f"ERROR: Sources directory not found: {sources_dir}")
        print("Have you set up docs/sources/*.yaml files?")
        sys.exit(1)

    if not templates_dir.exists():
        print(f"ERROR: Templates directory not found: {templates_dir}")
        print("Have you set up docs/templates/*.j2 files?")
        sys.exit(1)

    # Load sources
    print("\nLoading YAML sources...")
    context = load_yaml_sources(sources_dir)
    print(f"  Loaded {len(context)} source files")

    # Process each file
    changes_detected = False

    for migration in migrations:
        template_name = migration["template"]
        output_path = migration["output"]
        display_name = migration["name"]

        print(f"\nProcessing: {display_name}")

        # Generate new content
        try:
            new_content = generate_header(template_name) + render_template(
                templates_dir, template_name, context
            )
            print(f"  Generated {len(new_content)} characters")
        except Exception as e:
            print(f"  ERROR: Failed to render template: {e}")
            continue

        # Get old content
        if output_path.exists():
            old_content = output_path.read_text(encoding="utf-8")
        else:
            old_content = ""
            print(f"  (File does not exist, will be created)")

        # Backup
        if args.backup or args.migrate:
            if output_path.exists():
                backup_path = create_backup(output_path, backup_dir)
                if backup_path:
                    print(f"  Backup: {backup_path}")

        # Diff
        if args.diff or args.dry_run:
            if show_diff(old_content, new_content, display_name):
                changes_detected = True

        # Migrate
        if args.migrate:
            if old_content == new_content:
                print(f"  No changes needed for {display_name}")
            else:
                if not args.force:
                    confirm = input(f"  Replace {display_name}? [y/N] ").strip().lower()
                    if confirm != "y":
                        print(f"  Skipped {display_name}")
                        continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(new_content, encoding="utf-8")
                print(f"  MIGRATED: {display_name}")
                changes_detected = True

    # Summary
    print("\n" + "=" * 60)
    if args.backup:
        print(f"Backups created in: {backup_dir}")

    if args.diff or args.dry_run:
        if changes_detected:
            print("Changes detected. Run with --migrate to apply.")
        else:
            print("No changes detected. Documentation is up to date.")

    if args.migrate:
        if changes_detected:
            print("Migration complete!")
            print("\nNext steps:")
            print("  1. Review the changes: git diff")
            print("  2. Run tests: pytest")
            print("  3. Commit: git add . && git commit -m 'Migrate to generated docs'")
        else:
            print("No migration needed. Documentation is up to date.")

    print("=" * 60)


if __name__ == "__main__":
    main()
