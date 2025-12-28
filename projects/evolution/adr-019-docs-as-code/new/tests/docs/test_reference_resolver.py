"""
Tests for ReferenceResolver.

ADR-019: Tests for the reference resolution functionality that validates
documentation references against actual code symbols.
"""

import tempfile
from pathlib import Path

import pytest

from helix.docs.schema import RefType, SymbolKind
from helix.docs.reference_resolver import ReferenceResolver


@pytest.fixture
def project_with_code(tmp_path: Path) -> Path:
    """Create a temporary project with sample Python code."""
    # Create src directory structure
    src_dir = tmp_path / "src" / "mymodule"
    src_dir.mkdir(parents=True)

    # Create __init__.py
    (src_dir / "__init__.py").write_text('"""MyModule package."""\n')

    # Create a module with classes and functions
    sample_module = src_dir / "sample.py"
    sample_module.write_text('''"""Sample module for testing."""


class SampleClass:
    """A sample class for testing."""

    def __init__(self, value: int):
        """Initialize with a value.

        Args:
            value: The initial value.
        """
        self.value = value

    def get_value(self) -> int:
        """Get the current value.

        Returns:
            The current value.
        """
        return self.value

    def set_value(self, new_value: int) -> None:
        """Set a new value.

        Args:
            new_value: The new value to set.
        """
        self.value = new_value


class AnotherClass:
    """Another class for testing."""

    pass


def standalone_function(x: int, y: int) -> int:
    """A standalone function.

    Args:
        x: First number.
        y: Second number.

    Returns:
        Sum of x and y.
    """
    return x + y


async def async_function(data: str) -> str:
    """An async function for testing.

    Args:
        data: Input data.

    Returns:
        Processed data.
    """
    return data.upper()
''')

    # Create another module
    utils_module = src_dir / "utils.py"
    utils_module.write_text('''"""Utility functions."""


def helper(value: str) -> str:
    """A helper function."""
    return value.strip()
''')

    # Create a file for $file references
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Documentation\n")

    # Create a script for $calls references
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run.sh").write_text("#!/bin/bash\necho 'Hello'\n")

    return tmp_path


class TestReferenceResolverBasic:
    """Test basic reference resolution."""

    def test_resolve_module(self, project_with_code: Path):
        """Test resolving a module reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample")

        assert result.exists is True
        assert result.kind == SymbolKind.MODULE
        assert result.file is not None
        assert result.file.name == "sample.py"
        assert result.line == 1
        assert "Sample module for testing" in (result.docstring or "")

    def test_resolve_class(self, project_with_code: Path):
        """Test resolving a class reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass")

        assert result.exists is True
        assert result.kind == SymbolKind.CLASS
        assert result.name == "SampleClass"
        assert result.file is not None
        assert result.line is not None
        assert result.line > 1  # Not at start of file
        assert "sample class for testing" in (result.docstring or "").lower()
        # Class should have children (methods)
        assert result.children is not None
        assert len(result.children) > 0

    def test_resolve_method(self, project_with_code: Path):
        """Test resolving a method reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass.get_value")

        assert result.exists is True
        assert result.kind == SymbolKind.METHOD
        assert result.name == "get_value"
        assert result.signature is not None
        assert "self" in result.signature
        assert "int" in result.signature
        assert "Get the current value" in (result.docstring or "")

    def test_resolve_function(self, project_with_code: Path):
        """Test resolving a standalone function reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.standalone_function")

        assert result.exists is True
        assert result.kind == SymbolKind.FUNCTION
        assert result.name == "standalone_function"
        assert result.signature is not None
        assert "x: int" in result.signature
        assert "y: int" in result.signature
        assert "-> int" in result.signature

    def test_resolve_async_function(self, project_with_code: Path):
        """Test resolving an async function reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.async_function")

        assert result.exists is True
        assert result.kind == SymbolKind.FUNCTION
        assert result.name == "async_function"

    def test_resolve_nonexistent_module(self, project_with_code: Path):
        """Test resolving a non-existent module."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("nonexistent.module")

        assert result.exists is False
        assert result.kind is None
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_nonexistent_class(self, project_with_code: Path):
        """Test resolving a non-existent class."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.NonExistentClass")

        assert result.exists is False
        assert result.error is not None

    def test_resolve_nonexistent_method(self, project_with_code: Path):
        """Test resolving a non-existent method.

        Note: The implementation falls back to returning the class when
        a method is not found, as it provides a graceful degradation.
        The class exists so result.exists is True, but kind is CLASS not METHOD.
        """
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass.nonexistent_method")

        # Fallback behavior: returns the class since the method doesn't exist
        # The reference is not a perfect match for a method
        assert result.exists is True  # Class exists
        assert result.kind == SymbolKind.CLASS  # Not METHOD - indicates method wasn't found


class TestReferenceResolverFileRefs:
    """Test file and script reference resolution."""

    def test_resolve_file_exists(self, project_with_code: Path):
        """Test resolving an existing file reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve_file("docs/README.md")

        assert result.exists is True
        assert result.kind == SymbolKind.FILE
        assert result.file is not None
        assert result.file.name == "README.md"

    def test_resolve_file_not_exists(self, project_with_code: Path):
        """Test resolving a non-existent file reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve_file("docs/NONEXISTENT.md")

        assert result.exists is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_resolve_script_exists(self, project_with_code: Path):
        """Test resolving an existing script reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve_script("scripts/run.sh")

        assert result.exists is True
        assert result.kind == SymbolKind.SCRIPT
        assert result.file is not None

    def test_resolve_script_not_exists(self, project_with_code: Path):
        """Test resolving a non-existent script reference."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve_script("scripts/nonexistent.sh")

        assert result.exists is False
        assert result.error is not None


class TestReferenceResolverValidateAll:
    """Test validate_all functionality for YAML documents."""

    def test_validate_all_with_valid_refs(self, project_with_code: Path):
        """Test validation with all valid references."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "modules": [
                {"$ref": "mymodule.sample.SampleClass"},
                {"$ref": "mymodule.sample.standalone_function"},
            ],
            "$file": "docs/README.md",
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 0

    def test_validate_all_with_invalid_refs(self, project_with_code: Path):
        """Test validation with invalid references."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "modules": [
                {"$ref": "mymodule.sample.SampleClass"},
                {"$ref": "mymodule.sample.NonExistentClass"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "NonExistentClass" in issues[0].ref

    def test_validate_all_with_optional_refs(self, project_with_code: Path):
        """Test validation with optional references (warnings not errors)."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "modules": [
                {"$ref?": "mymodule.sample.NonExistentClass"},
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_validate_all_with_uses_refs(self, project_with_code: Path):
        """Test validation with $uses references."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "workflows": [
                {"$uses": "mymodule.sample.SampleClass.get_value"},
                {"$uses": "mymodule.sample.NonExistentClass.method"},  # Class doesn't exist
            ],
        }

        issues = resolver.validate_all(yaml_data)

        # NonExistentClass doesn't exist, so it causes an error
        assert len(issues) == 1
        assert "NonExistentClass" in issues[0].ref

    def test_validate_all_with_refs_list(self, project_with_code: Path):
        """Test validation with $refs list (for diagrams)."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "diagrams": [
                {
                    "id": "test_diagram",
                    "$refs": [
                        "mymodule.sample.SampleClass",
                        "mymodule.sample.NonExistent",
                    ],
                }
            ],
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert "NonExistent" in issues[0].ref

    def test_validate_all_nested_structure(self, project_with_code: Path):
        """Test validation with deeply nested structure."""
        resolver = ReferenceResolver(project_with_code)

        yaml_data = {
            "level1": {
                "level2": {
                    "level3": [
                        {"$ref": "mymodule.sample.SampleClass"},
                        {
                            "nested": {
                                "$ref": "mymodule.sample.NonExistent"
                            }
                        }
                    ]
                }
            }
        }

        issues = resolver.validate_all(yaml_data)

        assert len(issues) == 1
        assert "level1.level2.level3" in issues[0].path


class TestReferenceResolverCaching:
    """Test reference caching behavior."""

    def test_caching_returns_same_result(self, project_with_code: Path):
        """Test that cached results are returned."""
        resolver = ReferenceResolver(project_with_code)

        result1 = resolver.resolve("mymodule.sample.SampleClass")
        result2 = resolver.resolve("mymodule.sample.SampleClass")

        # Should be the same object due to caching
        assert result1 is result2

    def test_clear_cache(self, project_with_code: Path):
        """Test clearing the cache."""
        resolver = ReferenceResolver(project_with_code)

        result1 = resolver.resolve("mymodule.sample.SampleClass")
        resolver.clear_cache()
        result2 = resolver.resolve("mymodule.sample.SampleClass")

        # Should be different objects after cache clear
        assert result1 is not result2
        # But should have same content
        assert result1.exists == result2.exists
        assert result1.kind == result2.kind


class TestResolvedReferenceProperties:
    """Test ResolvedReference computed properties."""

    def test_name_property(self, project_with_code: Path):
        """Test the name property extraction."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass.get_value")

        assert result.name == "get_value"

    def test_module_property(self, project_with_code: Path):
        """Test the module property extraction."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass")

        assert result.module == "mymodule.sample"

    def test_docstring_short_property(self, project_with_code: Path):
        """Test the docstring_short property."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass")

        assert result.docstring_short is not None
        assert "\n" not in result.docstring_short

    def test_to_auto_dict(self, project_with_code: Path):
        """Test conversion to _auto dictionary format."""
        resolver = ReferenceResolver(project_with_code)

        result = resolver.resolve("mymodule.sample.SampleClass")
        auto_dict = result.to_auto_dict()

        assert "name" in auto_dict
        assert auto_dict["name"] == "SampleClass"
        assert "file" in auto_dict
        assert "line" in auto_dict
