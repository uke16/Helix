"""
Tests for Reference Resolver.

ADR-019: Tests for validating that $ref references in documentation
resolve correctly to actual code symbols.
"""

import tempfile
from pathlib import Path

import pytest

from helix.docs.reference_resolver import ReferenceResolver
from helix.docs.schema import RefType, SymbolKind, ValidationIssue


@pytest.fixture
def temp_project():
    """Create a temporary project with sample Python files."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Create src directory structure
        src_dir = root / "src" / "myproject"
        src_dir.mkdir(parents=True)

        # Create __init__.py
        (src_dir / "__init__.py").write_text('"""My Project package."""\n')

        # Create a sample module with classes and functions
        sample_module = '''"""
Sample module for testing reference resolution.

This module contains classes and functions to test symbol extraction.
"""


def standalone_function(x: int, y: int) -> int:
    """Add two numbers together.

    Args:
        x: First number.
        y: Second number.

    Returns:
        Sum of x and y.
    """
    return x + y


class SampleClass:
    """A sample class for testing.

    This class demonstrates class extraction with methods.
    """

    def __init__(self, name: str):
        """Initialize with a name.

        Args:
            name: The name for this instance.
        """
        self.name = name

    def greet(self) -> str:
        """Return a greeting.

        Returns:
            A greeting string.
        """
        return f"Hello, {self.name}!"

    async def async_method(self) -> None:
        """An async method for testing."""
        pass


class AnotherClass:
    """Another class without methods."""
    pass
'''
        (src_dir / "sample.py").write_text(sample_module)

        # Create a nested module
        nested_dir = src_dir / "utils"
        nested_dir.mkdir()
        (nested_dir / "__init__.py").write_text('"""Utils package."""\n')

        helper_module = '''"""Helper utilities."""


def helper_func(value: str) -> str:
    """A helper function."""
    return value.upper()


class HelperClass:
    """A helper class."""

    def help(self) -> str:
        """Provide help."""
        return "help"
'''
        (nested_dir / "helpers.py").write_text(helper_module)

        # Create a script file
        scripts_dir = root / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.sh").write_text("#!/bin/bash\necho 'Hello'\n")

        # Create a data file
        (root / "data.txt").write_text("Some data\n")

        yield root


class TestReferenceResolver:
    """Tests for the ReferenceResolver class."""

    def test_resolve_module(self, temp_project):
        """Test resolving a module reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample")

        assert result.exists is True
        assert result.kind == SymbolKind.MODULE
        assert result.file is not None
        assert "sample.py" in str(result.file)
        assert result.docstring is not None
        assert "Sample module" in result.docstring

    def test_resolve_class(self, temp_project):
        """Test resolving a class reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.SampleClass")

        assert result.exists is True
        assert result.kind == SymbolKind.CLASS
        assert result.docstring is not None
        assert "sample class" in result.docstring.lower()

    def test_resolve_function(self, temp_project):
        """Test resolving a function reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.standalone_function")

        assert result.exists is True
        assert result.kind == SymbolKind.FUNCTION
        assert result.signature is not None
        assert "x: int" in result.signature
        assert "-> int" in result.signature

    def test_resolve_method(self, temp_project):
        """Test resolving a method reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.SampleClass.greet")

        assert result.exists is True
        assert result.kind == SymbolKind.METHOD
        assert result.signature is not None
        assert "-> str" in result.signature

    def test_resolve_async_method(self, temp_project):
        """Test resolving an async method reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.SampleClass.async_method")

        assert result.exists is True
        assert result.kind == SymbolKind.METHOD

    def test_resolve_nested_module(self, temp_project):
        """Test resolving a nested module reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.utils.helpers")

        assert result.exists is True
        assert result.kind == SymbolKind.MODULE

    def test_resolve_nested_class(self, temp_project):
        """Test resolving a class in a nested module."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.utils.helpers.HelperClass")

        assert result.exists is True
        assert result.kind == SymbolKind.CLASS

    def test_resolve_nested_method(self, temp_project):
        """Test resolving a method in a nested module."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.utils.helpers.HelperClass.help")

        assert result.exists is True
        assert result.kind == SymbolKind.METHOD

    def test_resolve_nonexistent_module(self, temp_project):
        """Test resolving a non-existent module."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("nonexistent.module")

        assert result.exists is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_nonexistent_class(self, temp_project):
        """Test resolving a non-existent class."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.NonExistentClass")

        assert result.exists is False
        assert result.error is not None

    def test_resolve_nonexistent_method(self, temp_project):
        """Test resolving a non-existent method falls back to class."""
        resolver = ReferenceResolver(temp_project)

        # When a method doesn't exist, the resolver falls back to
        # less specific interpretations (class, then module)
        result = resolver.resolve("myproject.sample.SampleClass.nonexistent")

        # The resolver finds the class as a fallback
        assert result.exists is True
        assert result.kind == SymbolKind.CLASS

    def test_resolve_truly_nonexistent_symbol(self, temp_project):
        """Test resolving a completely non-existent symbol path."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.NonExistent.method")

        assert result.exists is False
        assert result.error is not None

    def test_caching(self, temp_project):
        """Test that resolved references are cached."""
        resolver = ReferenceResolver(temp_project)

        # Resolve twice
        result1 = resolver.resolve("myproject.sample.SampleClass")
        result2 = resolver.resolve("myproject.sample.SampleClass")

        # Should be the same cached object
        assert result1 is result2

    def test_clear_cache(self, temp_project):
        """Test clearing the cache."""
        resolver = ReferenceResolver(temp_project)

        result1 = resolver.resolve("myproject.sample.SampleClass")
        resolver.clear_cache()
        result2 = resolver.resolve("myproject.sample.SampleClass")

        # Should be different objects after cache clear
        assert result1 is not result2
        # But should have same content
        assert result1.exists == result2.exists
        assert result1.kind == result2.kind


class TestFileResolution:
    """Tests for file reference resolution."""

    def test_resolve_file_exists(self, temp_project):
        """Test resolving an existing file reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_file("data.txt")

        assert result.exists is True
        assert result.kind == SymbolKind.FILE
        assert result.file is not None

    def test_resolve_file_not_exists(self, temp_project):
        """Test resolving a non-existent file reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_file("nonexistent.txt")

        assert result.exists is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_nested_file(self, temp_project):
        """Test resolving a file in a subdirectory."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_file("scripts/run.sh")

        assert result.exists is True
        assert result.kind == SymbolKind.FILE


class TestScriptResolution:
    """Tests for script reference resolution."""

    def test_resolve_script_exists(self, temp_project):
        """Test resolving an existing script reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_script("scripts/run.sh")

        assert result.exists is True
        assert result.kind == SymbolKind.SCRIPT

    def test_resolve_script_not_exists(self, temp_project):
        """Test resolving a non-existent script reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_script("scripts/nonexistent.sh")

        assert result.exists is False
        assert result.error is not None

    def test_resolve_script_is_directory(self, temp_project):
        """Test resolving a directory as script fails."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve_script("scripts")

        assert result.exists is False
        assert result.error is not None
        assert "Not a file" in result.error


class TestYamlValidation:
    """Tests for YAML document validation."""

    def test_validate_all_valid_refs(self, temp_project):
        """Test validation with all valid references."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "modules": [
                {"$ref": "myproject.sample"},
                {"$ref": "myproject.sample.SampleClass"},
            ],
            "files": [
                {"$file": "data.txt"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_all_with_invalid_refs(self, temp_project):
        """Test validation with invalid references."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "modules": [
                {"$ref": "myproject.sample"},
                {"$ref": "nonexistent.module"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "nonexistent" in issues[0].ref

    def test_validate_optional_refs(self, temp_project):
        """Test validation with optional references produces warnings."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "modules": [
                {"$ref?": "nonexistent.module"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_validate_nested_refs(self, temp_project):
        """Test validation with nested references."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "components": {
                "core": {
                    "$ref": "myproject.sample.SampleClass",
                    "methods": [
                        {"$uses": "myproject.sample.SampleClass.greet"},
                    ],
                },
            },
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_refs_list(self, temp_project):
        """Test validation with $refs list for diagrams."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "diagram": {
                "$refs": [
                    "myproject.sample.SampleClass",
                    "myproject.sample.AnotherClass",
                ],
            },
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_calls_ref(self, temp_project):
        """Test validation with $calls reference."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "scripts": [
                {"$calls": "scripts/run.sh"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_file_ref(self, temp_project):
        """Test validation with $file reference."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "data": {
                "$file": "data.txt",
            },
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_invalid_file_ref(self, temp_project):
        """Test validation with invalid $file reference."""
        resolver = ReferenceResolver(temp_project)

        yaml_data = {
            "data": {
                "$file": "nonexistent.txt",
            },
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "error"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_ref(self, temp_project):
        """Test handling of empty reference."""
        resolver = ReferenceResolver(temp_project)

        # Single-part reference treated as module
        result = resolver.resolve("")

        assert result.exists is False

    def test_single_part_ref(self, temp_project):
        """Test handling of single-part reference."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject")

        # Should try to resolve as module
        assert result.exists is True
        assert result.kind == SymbolKind.MODULE

    def test_class_with_children(self, temp_project):
        """Test that resolved class includes method children."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject.sample.SampleClass")

        assert result.exists is True
        assert result.children is not None
        assert len(result.children) > 0

        method_names = [c.name for c in result.children]
        assert "__init__" in method_names
        assert "greet" in method_names

    def test_resolve_init_package(self, temp_project):
        """Test resolving a package with __init__.py."""
        resolver = ReferenceResolver(temp_project)

        result = resolver.resolve("myproject")

        assert result.exists is True
        assert result.kind == SymbolKind.MODULE
        assert "__init__.py" in str(result.file)
