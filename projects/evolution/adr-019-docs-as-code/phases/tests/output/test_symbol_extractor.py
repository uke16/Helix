"""
Tests for Symbol Extractor.

ADR-019: Tests for extracting symbol information from Python source files
using AST parsing for documentation validation.
"""

import tempfile
from pathlib import Path

import pytest

from helix.docs.symbol_extractor import SymbolExtractor
from helix.docs.schema import SymbolKind


@pytest.fixture
def temp_project():
    """Create a temporary project with sample Python files."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Create src directory structure
        src_dir = root / "src" / "testpkg"
        src_dir.mkdir(parents=True)

        # Create __init__.py
        init_content = '''"""Test package for symbol extraction."""

__version__ = "1.0.0"
'''
        (src_dir / "__init__.py").write_text(init_content)

        # Create a comprehensive module
        module_content = '''"""
A comprehensive test module.

This module contains various Python constructs to test symbol extraction.
"""

from typing import List, Optional, Union
from dataclasses import dataclass


def simple_function():
    """A simple function without arguments."""
    pass


def function_with_args(a: int, b: str, c: float = 3.14) -> str:
    """A function with typed arguments.

    Args:
        a: An integer.
        b: A string.
        c: A float with default value.

    Returns:
        A formatted string.
    """
    return f"{a} {b} {c}"


def function_with_varargs(*args, **kwargs) -> None:
    """A function with variable arguments."""
    pass


def function_with_complex_sig(
    pos_only: int,
    /,
    regular: str,
    *args: tuple,
    kw_only: bool = True,
    **kwargs: dict,
) -> Optional[str]:
    """A function with complex signature including positional-only."""
    return None


async def async_function(data: bytes) -> str:
    """An async function."""
    return data.decode()


class SimpleClass:
    """A simple class."""
    pass


class ClassWithMethods:
    """A class with various methods.

    This class demonstrates different method types.
    """

    class_attribute: str = "default"

    def __init__(self, value: int):
        """Initialize with a value.

        Args:
            value: The initial value.
        """
        self.value = value

    def instance_method(self) -> int:
        """Return the value."""
        return self.value

    @classmethod
    def class_method(cls, x: int) -> "ClassWithMethods":
        """Create from x."""
        return cls(x)

    @staticmethod
    def static_method(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @property
    def prop(self) -> int:
        """A property."""
        return self.value * 2

    async def async_method(self) -> None:
        """An async method."""
        pass


class DerivedClass(ClassWithMethods):
    """A class that inherits from ClassWithMethods."""

    def additional_method(self) -> str:
        """An additional method."""
        return "extra"


@dataclass
class DataClass:
    """A dataclass."""
    name: str
    value: int = 0


class GenericClass(List[str]):
    """A class with generic base."""
    pass


class MultiInheritance(ClassWithMethods, SimpleClass):
    """A class with multiple inheritance."""
    pass
'''
        (src_dir / "comprehensive.py").write_text(module_content)

        # Create a nested module structure
        nested = src_dir / "nested"
        nested.mkdir()
        (nested / "__init__.py").write_text('"""Nested package."""\n')

        inner_module = '''"""Inner module."""


class InnerClass:
    """A class in nested module."""

    def inner_method(self) -> str:
        """Inner method."""
        return "inner"
'''
        (nested / "inner.py").write_text(inner_module)

        # Create a module with syntax error (to test error handling)
        (src_dir / "broken.py").write_text("def broken(\n")

        yield root


class TestSymbolExtractor:
    """Tests for the SymbolExtractor class."""

    def test_extract_module(self, temp_project):
        """Test extracting a module."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg.comprehensive")

        assert result is not None
        assert result.kind == SymbolKind.MODULE
        assert result.name == "comprehensive"
        assert result.docstring is not None
        assert "comprehensive test module" in result.docstring.lower()

    def test_extract_module_children(self, temp_project):
        """Test that module extraction includes children."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg.comprehensive")

        assert result is not None
        assert len(result.children) > 0

        child_names = [c.name for c in result.children]
        assert "simple_function" in child_names
        assert "SimpleClass" in child_names
        assert "ClassWithMethods" in child_names

    def test_extract_nonexistent_module(self, temp_project):
        """Test extracting a non-existent module."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("nonexistent.module")

        assert result is None

    def test_extract_broken_module(self, temp_project):
        """Test extracting a module with syntax errors."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg.broken")

        assert result is None


class TestFunctionExtraction:
    """Tests for function extraction."""

    def test_extract_simple_function(self, temp_project):
        """Test extracting a simple function."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "simple_function")

        assert result is not None
        assert result.kind == SymbolKind.FUNCTION
        assert result.name == "simple_function"
        assert result.docstring == "A simple function without arguments."

    def test_extract_function_with_args(self, temp_project):
        """Test extracting a function with arguments."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "function_with_args")

        assert result is not None
        assert result.signature is not None
        assert "a: int" in result.signature
        assert "b: str" in result.signature
        assert "c: float" in result.signature
        assert "-> str" in result.signature

    def test_extract_function_default_args(self, temp_project):
        """Test that default arguments are captured."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "function_with_args")

        assert result is not None
        assert "3.14" in result.signature

    def test_extract_function_varargs(self, temp_project):
        """Test extracting a function with *args and **kwargs."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "function_with_varargs")

        assert result is not None
        assert "*args" in result.signature
        assert "**kwargs" in result.signature

    def test_extract_async_function(self, temp_project):
        """Test extracting an async function."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "async_function")

        assert result is not None
        assert result.kind == SymbolKind.FUNCTION
        assert "-> str" in result.signature

    def test_extract_nonexistent_function(self, temp_project):
        """Test extracting a non-existent function."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "nonexistent")

        assert result is None


class TestClassExtraction:
    """Tests for class extraction."""

    def test_extract_simple_class(self, temp_project):
        """Test extracting a simple class."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "SimpleClass")

        assert result is not None
        assert result.kind == SymbolKind.CLASS
        assert result.name == "SimpleClass"
        assert result.docstring == "A simple class."

    def test_extract_class_with_methods(self, temp_project):
        """Test extracting a class with methods."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "ClassWithMethods")

        assert result is not None
        assert len(result.children) > 0

        method_names = [c.name for c in result.children]
        assert "__init__" in method_names
        assert "instance_method" in method_names
        assert "class_method" in method_names
        assert "static_method" in method_names

    def test_class_method_kind(self, temp_project):
        """Test that class children have METHOD kind."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "ClassWithMethods")

        assert result is not None
        for child in result.children:
            assert child.kind == SymbolKind.METHOD

    def test_class_with_decorators(self, temp_project):
        """Test extracting decorator information."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "DataClass")

        assert result is not None
        assert "dataclass" in result.decorators

    def test_class_with_bases(self, temp_project):
        """Test extracting base class information."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "DerivedClass")

        assert result is not None
        assert "ClassWithMethods" in result.bases

    def test_class_with_generic_base(self, temp_project):
        """Test extracting class with generic base type."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "GenericClass")

        assert result is not None
        assert len(result.bases) > 0

    def test_class_multiple_inheritance(self, temp_project):
        """Test extracting class with multiple inheritance."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "MultiInheritance")

        assert result is not None
        assert len(result.bases) == 2
        assert "ClassWithMethods" in result.bases
        assert "SimpleClass" in result.bases

    def test_extract_nonexistent_class(self, temp_project):
        """Test extracting a non-existent class."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "NonexistentClass")

        assert result is None


class TestMethodExtraction:
    """Tests for method extraction."""

    def test_extract_method(self, temp_project):
        """Test extracting a method from a class."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "instance_method"
        )

        assert result is not None
        assert result.kind == SymbolKind.METHOD
        assert result.name == "instance_method"
        assert "-> int" in result.signature

    def test_extract_init_method(self, temp_project):
        """Test extracting __init__ method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "__init__"
        )

        assert result is not None
        assert "value: int" in result.signature

    def test_extract_decorated_method(self, temp_project):
        """Test extracting a decorated method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "class_method"
        )

        assert result is not None
        assert "classmethod" in result.decorators

    def test_extract_static_method(self, temp_project):
        """Test extracting a static method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "static_method"
        )

        assert result is not None
        assert "staticmethod" in result.decorators

    def test_extract_property_method(self, temp_project):
        """Test extracting a property."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "prop"
        )

        assert result is not None
        assert "property" in result.decorators

    def test_extract_async_method(self, temp_project):
        """Test extracting an async method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "async_method"
        )

        assert result is not None
        assert result.kind == SymbolKind.METHOD

    def test_extract_nonexistent_method(self, temp_project):
        """Test extracting a non-existent method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "ClassWithMethods", "nonexistent"
        )

        assert result is None

    def test_extract_method_from_nonexistent_class(self, temp_project):
        """Test extracting a method from a non-existent class."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.comprehensive", "NonexistentClass", "method"
        )

        assert result is None


class TestNestedModules:
    """Tests for nested module extraction."""

    def test_extract_nested_module(self, temp_project):
        """Test extracting a nested module."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg.nested.inner")

        assert result is not None
        assert result.kind == SymbolKind.MODULE

    def test_extract_class_from_nested_module(self, temp_project):
        """Test extracting a class from a nested module."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.nested.inner", "InnerClass")

        assert result is not None
        assert result.kind == SymbolKind.CLASS
        assert result.name == "InnerClass"

    def test_extract_method_from_nested_module(self, temp_project):
        """Test extracting a method from a class in a nested module."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_method(
            "testpkg.nested.inner", "InnerClass", "inner_method"
        )

        assert result is not None
        assert result.kind == SymbolKind.METHOD

    def test_extract_package_init(self, temp_project):
        """Test extracting a package __init__.py."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg")

        assert result is not None
        assert result.kind == SymbolKind.MODULE
        assert result.docstring is not None


class TestExtractedSymbolMethods:
    """Tests for ExtractedSymbol dataclass methods."""

    def test_docstring_short(self, temp_project):
        """Test the docstring_short property."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "ClassWithMethods")

        assert result is not None
        assert result.docstring_short is not None
        assert result.docstring_short == "A class with various methods."

    def test_to_dict(self, temp_project):
        """Test the to_dict method."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "ClassWithMethods")

        assert result is not None

        d = result.to_dict()

        assert d["name"] == "ClassWithMethods"
        assert d["kind"] == "class"
        assert "file" in d
        assert "line" in d
        assert "docstring" in d
        assert "children" in d

    def test_to_dict_includes_signature(self, temp_project):
        """Test that to_dict includes signature for functions."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "function_with_args")

        assert result is not None

        d = result.to_dict()

        assert "signature" in d
        assert "a: int" in d["signature"]


class TestEdgeCases:
    """Tests for edge cases."""

    def test_module_to_path_fallback(self, temp_project):
        """Test _module_to_path with various module paths."""
        extractor = SymbolExtractor(temp_project)

        # Test nested module
        result = extractor.extract_module("testpkg.nested.inner")
        assert result is not None

    def test_complex_signature(self, temp_project):
        """Test extracting complex function signature."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_function("testpkg.comprehensive", "function_with_complex_sig")

        assert result is not None
        assert result.signature is not None
        # Should contain various parts of the complex signature
        assert "pos_only: int" in result.signature

    def test_line_numbers(self, temp_project):
        """Test that line numbers are captured."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_class("testpkg.comprehensive", "SimpleClass")

        assert result is not None
        assert result.line > 0

    def test_file_path(self, temp_project):
        """Test that file paths are captured."""
        extractor = SymbolExtractor(temp_project)

        result = extractor.extract_module("testpkg.comprehensive")

        assert result is not None
        assert result.file is not None
        assert result.file.exists()
        assert result.file.name == "comprehensive.py"
