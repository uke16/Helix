"""Tests for Reference Resolver.

ADR-019: Tests cover resolving $ref references in documentation YAML files
to actual code symbols.

Tests cover:
- Resolving module references
- Resolving class references
- Resolving method references
- Resolving function references
- Resolving file references
- Resolving script references
- Validation of YAML documents
- Caching behavior
- Error handling
"""

import pytest
from pathlib import Path
from textwrap import dedent

from helix.docs.reference_resolver import ReferenceResolver
from helix.docs.schema import SymbolKind, RefType, ValidationIssue


# --- Test Fixtures ---

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project structure."""
    # Create src directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


@pytest.fixture
def resolver(project_root: Path) -> ReferenceResolver:
    """Create a ReferenceResolver instance."""
    return ReferenceResolver(project_root)


@pytest.fixture
def sample_codebase(project_root: Path) -> None:
    """Create a sample codebase for testing resolution."""
    # Create helix.debug package
    debug_dir = project_root / "src" / "helix" / "debug"
    debug_dir.mkdir(parents=True)

    (debug_dir.parent / "__init__.py").write_text('"""HELIX package."""')
    (debug_dir / "__init__.py").write_text('"""Debug module."""')

    # Create stream_parser module
    stream_parser = debug_dir / "stream_parser.py"
    stream_parser.write_text(dedent('''
        """Stream Parser for debugging.

        This module provides streaming parsing capabilities.
        """

        from typing import Optional


        class StreamParser:
            """Parses streaming debug output.

            This class handles line-by-line parsing of debug streams.
            """

            def __init__(self, buffer_size: int = 1024):
                """Initialize the parser.

                Args:
                    buffer_size: Size of the internal buffer.
                """
                self.buffer_size = buffer_size

            def parse_line(self, line: str) -> Optional[dict]:
                """Parse a single line.

                Args:
                    line: The line to parse.

                Returns:
                    Parsed data or None if not parseable.
                """
                return {"line": line}

            def reset(self) -> None:
                """Reset the parser state."""
                pass


        def create_parser(buffer_size: int = 1024) -> StreamParser:
            """Factory function to create a parser.

            Args:
                buffer_size: Buffer size for the parser.

            Returns:
                A new StreamParser instance.
            """
            return StreamParser(buffer_size)
    ''').strip())

    # Create another module
    utils_dir = project_root / "src" / "helix" / "utils"
    utils_dir.mkdir(parents=True)
    (utils_dir / "__init__.py").write_text('"""Utils module."""')

    helpers = utils_dir / "helpers.py"
    helpers.write_text(dedent('''
        """Helper utilities."""


        def format_output(data: dict) -> str:
            """Format data for output."""
            return str(data)
    ''').strip())

    # Create some files and scripts
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir()

    (scripts_dir / "run_tests.sh").write_text("#!/bin/bash\npytest tests/")
    (scripts_dir / "setup.py").write_text("# Setup script")

    docs_dir = project_root / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Documentation")


# --- Tests for resolve() ---

class TestResolve:
    """Tests for ReferenceResolver.resolve()"""

    def test_resolve_module(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a module reference."""
        result = resolver.resolve("helix.debug.stream_parser")

        assert result.exists
        assert result.kind == SymbolKind.MODULE
        assert result.ref == "helix.debug.stream_parser"
        assert result.docstring is not None

    def test_resolve_class(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a class reference."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        assert result.exists
        assert result.kind == SymbolKind.CLASS
        assert result.ref == "helix.debug.stream_parser.StreamParser"
        assert "streaming" in result.docstring.lower()

    def test_resolve_method(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a method reference."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser.parse_line")

        assert result.exists
        assert result.kind == SymbolKind.METHOD
        assert "parse_line" in result.ref
        assert result.signature is not None

    def test_resolve_function(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a function reference."""
        result = resolver.resolve("helix.debug.stream_parser.create_parser")

        assert result.exists
        assert result.kind == SymbolKind.FUNCTION
        assert result.signature is not None

    def test_resolve_nonexistent(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a nonexistent reference."""
        result = resolver.resolve("helix.nonexistent.module")

        assert not result.exists
        assert result.kind is None
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_nonexistent_class(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a nonexistent class."""
        result = resolver.resolve("helix.debug.stream_parser.NonexistentClass")

        assert not result.exists
        assert result.error is not None

    def test_resolve_nonexistent_method(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a nonexistent method falls back to class."""
        # The resolver falls back to the class when method isn't found
        result = resolver.resolve("helix.debug.stream_parser.StreamParser.nonexistent")

        # When method isn't found, resolver returns the class
        # (ref is preserved as original, but kind is CLASS)
        assert result.exists
        assert result.kind == SymbolKind.CLASS
        # The children should include class methods
        assert result.children is not None
        method_names = [m.name for m in result.children]
        assert "parse_line" in method_names

    def test_resolve_init_method(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving __init__ method."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser.__init__")

        assert result.exists
        assert result.kind == SymbolKind.METHOD


# --- Tests for resolve_file() ---

class TestResolveFile:
    """Tests for ReferenceResolver.resolve_file()"""

    def test_resolve_existing_file(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving an existing file."""
        result = resolver.resolve_file("docs/README.md")

        assert result.exists
        assert result.kind == SymbolKind.FILE
        assert result.file is not None
        assert result.file.name == "README.md"

    def test_resolve_nonexistent_file(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a nonexistent file."""
        result = resolver.resolve_file("docs/nonexistent.md")

        assert not result.exists
        assert result.kind is None
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_source_file(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a source file."""
        result = resolver.resolve_file("src/helix/debug/stream_parser.py")

        assert result.exists
        assert result.kind == SymbolKind.FILE


# --- Tests for resolve_script() ---

class TestResolveScript:
    """Tests for ReferenceResolver.resolve_script()"""

    def test_resolve_existing_script(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving an existing script."""
        result = resolver.resolve_script("scripts/run_tests.sh")

        assert result.exists
        assert result.kind == SymbolKind.SCRIPT
        assert result.file is not None

    def test_resolve_nonexistent_script(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a nonexistent script."""
        result = resolver.resolve_script("scripts/nonexistent.sh")

        assert not result.exists
        assert result.kind is None
        assert result.error is not None

    def test_resolve_script_as_directory_fails(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test that resolving a directory as script fails."""
        result = resolver.resolve_script("scripts")

        assert not result.exists
        assert result.error is not None


# --- Tests for validate_all() ---

class TestValidateAll:
    """Tests for ReferenceResolver.validate_all()"""

    def test_validate_valid_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating a document with valid references."""
        yaml_data = {
            "modules": [
                {"$ref": "helix.debug.stream_parser"},
                {"$ref": "helix.debug.stream_parser.StreamParser"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_invalid_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating a document with invalid references."""
        yaml_data = {
            "modules": [
                {"$ref": "helix.nonexistent.module"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "nonexistent" in issues[0].ref

    def test_validate_optional_ref(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test that $ref? produces warning instead of error."""
        yaml_data = {
            "modules": [
                {"$ref?": "helix.optional.module"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_validate_file_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating $file references."""
        yaml_data = {
            "files": [
                {"$file": "docs/README.md"},
                {"$file": "docs/nonexistent.md"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert "nonexistent.md" in issues[0].ref

    def test_validate_calls_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating $calls references."""
        yaml_data = {
            "scripts": [
                {"$calls": "scripts/run_tests.sh"},
                {"$calls": "scripts/missing.sh"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert "missing.sh" in issues[0].ref

    def test_validate_uses_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating $uses references."""
        yaml_data = {
            "usage": [
                {"$uses": "helix.debug.stream_parser.StreamParser.parse_line"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_refs_list(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating $refs list (for diagrams)."""
        yaml_data = {
            "diagram": {
                "$refs": [
                    "helix.debug.stream_parser.StreamParser",
                    "helix.nonexistent.Class",
                ]
            }
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert "nonexistent" in issues[0].ref

    def test_validate_nested_structure(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating deeply nested structures."""
        yaml_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "$ref": "helix.debug.stream_parser.StreamParser"
                    }
                }
            }
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_list_items(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating references in list items."""
        yaml_data = {
            "items": [
                {"name": "item1", "$ref": "helix.debug.stream_parser"},
                {"name": "item2", "$ref": "helix.nonexistent"},
            ]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1


# --- Tests for Caching ---

class TestCaching:
    """Tests for resolution caching."""

    def test_caching_same_reference(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test that same reference uses cache."""
        ref = "helix.debug.stream_parser.StreamParser"

        result1 = resolver.resolve(ref)
        result2 = resolver.resolve(ref)

        # Should be the same object from cache
        assert result1 is result2

    def test_clear_cache(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test clearing the cache."""
        ref = "helix.debug.stream_parser.StreamParser"

        result1 = resolver.resolve(ref)
        resolver.clear_cache()
        result2 = resolver.resolve(ref)

        # Should be different objects after cache clear
        assert result1 is not result2
        # But same content
        assert result1.ref == result2.ref
        assert result1.exists == result2.exists


# --- Tests for ResolvedReference Properties ---

class TestResolvedReferenceProperties:
    """Tests for ResolvedReference data class properties."""

    def test_name_property(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test the name property."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        assert result.name == "StreamParser"

    def test_module_property_for_class(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test the module property for a class."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        assert result.module == "helix.debug.stream_parser"

    def test_module_property_for_method(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test the module property for a method."""
        result = resolver.resolve(
            "helix.debug.stream_parser.StreamParser.parse_line"
        )

        # For methods, module should be up to the class
        assert result.module == "helix.debug.stream_parser"

    def test_docstring_short(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test docstring_short property."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        assert result.docstring_short is not None
        assert "\n" not in result.docstring_short

    def test_to_auto_dict(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test to_auto_dict() serialization."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        data = result.to_auto_dict()

        assert data["name"] == "StreamParser"
        assert "module" in data
        assert "file" in data
        assert "line" in data
        assert "docstring" in data

    def test_to_auto_dict_with_methods(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test to_auto_dict() includes methods for classes."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        data = result.to_auto_dict()

        assert "methods" in data
        method_names = [m["name"] for m in data["methods"]]
        assert "parse_line" in method_names


# --- Tests for Edge Cases ---

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_single_part_reference(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving a single-part reference (just module name)."""
        # Single part should try to resolve as module
        result = resolver.resolve("helix")

        # helix exists as a package
        assert result.exists
        assert result.kind == SymbolKind.MODULE

    def test_deep_nesting(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test resolving deeply nested references."""
        result = resolver.resolve(
            "helix.debug.stream_parser.StreamParser.parse_line"
        )

        assert result.exists
        assert result.kind == SymbolKind.METHOD

    def test_resolution_with_children(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test that class resolution includes children (methods)."""
        result = resolver.resolve("helix.debug.stream_parser.StreamParser")

        assert result.exists
        assert result.children is not None
        assert len(result.children) > 0

        method_names = [m.name for m in result.children]
        assert "parse_line" in method_names

    def test_empty_yaml_data(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating empty YAML data."""
        issues = resolver.validate_all({})

        assert len(issues) == 0

    def test_yaml_with_no_refs(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test validating YAML with no references."""
        yaml_data = {
            "name": "Test",
            "description": "A test document",
            "items": ["one", "two", "three"],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0


# --- Tests for ValidationIssue ---

class TestValidationIssue:
    """Tests for ValidationIssue data class."""

    def test_issue_attributes(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test ValidationIssue attributes."""
        yaml_data = {
            "modules": [{"$ref": "nonexistent.module"}]
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        issue = issues[0]

        assert issue.severity == "error"
        assert issue.ref == "nonexistent.module"
        assert issue.path == "modules[0].$ref"
        assert issue.message is not None

    def test_issue_to_dict(
        self, resolver: ReferenceResolver, sample_codebase: None
    ):
        """Test ValidationIssue.to_dict()."""
        yaml_data = {
            "test": {"$ref": "missing.ref"}
        }

        issues = resolver.validate_all(yaml_data)
        issue_dict = issues[0].to_dict()

        assert "severity" in issue_dict
        assert "path" in issue_dict
        assert "ref" in issue_dict
        assert "message" in issue_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
