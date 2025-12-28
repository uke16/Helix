"""Tests for Symbol Extractor.

ADR-019: Tests cover extracting symbols from Python source files using AST parsing.

Tests cover:
- Module extraction
- Class extraction with methods
- Function extraction
- Method extraction from classes
- Signature extraction
- Decorator extraction
- Base class extraction
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from textwrap import dedent

from helix.docs.symbol_extractor import SymbolExtractor
from helix.docs.schema import SymbolKind, ExtractedSymbol


# --- Test Fixtures ---

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project structure."""
    # Create src directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


@pytest.fixture
def extractor(project_root: Path) -> SymbolExtractor:
    """Create a SymbolExtractor instance."""
    return SymbolExtractor(project_root)


@pytest.fixture
def sample_module(project_root: Path) -> str:
    """Create a sample Python module and return its module path."""
    module_dir = project_root / "src" / "mypackage"
    module_dir.mkdir(parents=True)

    # Create __init__.py
    (module_dir / "__init__.py").write_text('"""MyPackage module."""\n')

    # Create sample module
    module_file = module_dir / "sample.py"
    module_file.write_text(dedent('''
        """Sample module for testing.

        This module contains sample classes and functions.
        """

        from typing import Optional, List


        def standalone_function(name: str, count: int = 1) -> str:
            """A standalone function.

            Args:
                name: The name to use.
                count: Number of times to repeat.

            Returns:
                The formatted string.
            """
            return name * count


        async def async_function(data: List[str]) -> None:
            """An async function for testing."""
            pass


        class SampleClass:
            """A sample class for testing.

            This class demonstrates various method types.
            """

            def __init__(self, value: int):
                """Initialize the class."""
                self.value = value

            def get_value(self) -> int:
                """Get the current value."""
                return self.value

            def set_value(self, value: int) -> None:
                """Set a new value."""
                self.value = value

            @property
            def doubled(self) -> int:
                """Get doubled value."""
                return self.value * 2

            @staticmethod
            def static_method(x: int) -> int:
                """A static method."""
                return x + 1

            @classmethod
            def class_method(cls, value: int) -> "SampleClass":
                """A class method."""
                return cls(value)


        class DerivedClass(SampleClass):
            """A derived class."""

            def extra_method(self) -> str:
                """An extra method in derived class."""
                return "extra"
    ''').strip())

    return "mypackage.sample"


@pytest.fixture
def module_with_generics(project_root: Path) -> str:
    """Create a module with generic types."""
    module_dir = project_root / "src" / "generics"
    module_dir.mkdir(parents=True)

    module_file = module_dir / "types.py"
    module_file.write_text(dedent('''
        """Module with generic types."""

        from typing import Generic, TypeVar, List, Dict

        T = TypeVar("T")
        K = TypeVar("K")
        V = TypeVar("V")


        class Container(Generic[T]):
            """A generic container."""

            def __init__(self, item: T) -> None:
                self.item = item

            def get(self) -> T:
                """Get the item."""
                return self.item


        class Mapper(Generic[K, V]):
            """A generic mapper with two type params."""

            def map(self, key: K) -> V:
                """Map a key to value."""
                raise NotImplementedError
    ''').strip())

    return "generics.types"


# --- Tests for extract_module ---

class TestExtractModule:
    """Tests for SymbolExtractor.extract_module()"""

    def test_extract_existing_module(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting an existing module."""
        result = extractor.extract_module(sample_module)

        assert result is not None
        assert result.kind == SymbolKind.MODULE
        assert result.name == "sample"
        assert result.docstring is not None
        assert "Sample module" in result.docstring

    def test_extract_nonexistent_module(self, extractor: SymbolExtractor):
        """Test extracting a module that doesn't exist."""
        result = extractor.extract_module("nonexistent.module")

        assert result is None

    def test_module_children(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that module children are extracted."""
        result = extractor.extract_module(sample_module)

        assert result is not None
        assert len(result.children) > 0

        # Should have functions and classes
        names = [c.name for c in result.children]
        assert "standalone_function" in names
        assert "async_function" in names
        assert "SampleClass" in names
        assert "DerivedClass" in names

    def test_module_with_init(self, extractor: SymbolExtractor, project_root: Path):
        """Test extracting a package with __init__.py."""
        # Create package
        pkg_dir = project_root / "src" / "testpkg"
        pkg_dir.mkdir(parents=True)

        init_file = pkg_dir / "__init__.py"
        init_file.write_text(dedent('''
            """Test package."""

            def package_function():
                """A function in the package __init__."""
                pass
        '''))

        result = extractor.extract_module("testpkg")

        assert result is not None
        assert result.kind == SymbolKind.MODULE
        assert "Test package" in result.docstring


# --- Tests for extract_class ---

class TestExtractClass:
    """Tests for SymbolExtractor.extract_class()"""

    def test_extract_existing_class(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting an existing class."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        assert result.kind == SymbolKind.CLASS
        assert result.name == "SampleClass"
        assert result.docstring is not None
        assert "sample class" in result.docstring.lower()

    def test_extract_nonexistent_class(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a class that doesn't exist."""
        result = extractor.extract_class(sample_module, "NonexistentClass")

        assert result is None

    def test_class_methods(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that class methods are extracted."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        method_names = [m.name for m in result.children]

        assert "__init__" in method_names
        assert "get_value" in method_names
        assert "set_value" in method_names
        assert "doubled" in method_names
        assert "static_method" in method_names
        assert "class_method" in method_names

    def test_class_bases(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that class bases are extracted."""
        result = extractor.extract_class(sample_module, "DerivedClass")

        assert result is not None
        assert "SampleClass" in result.bases

    def test_class_with_generics(
        self, extractor: SymbolExtractor, module_with_generics: str
    ):
        """Test extracting a class with generic types."""
        result = extractor.extract_class(module_with_generics, "Container")

        assert result is not None
        assert result.name == "Container"
        # Generic[T] should be in bases
        assert any("Generic" in base for base in result.bases)

    def test_class_line_number(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that class line number is correct."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        assert result.line > 0


# --- Tests for extract_function ---

class TestExtractFunction:
    """Tests for SymbolExtractor.extract_function()"""

    def test_extract_existing_function(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting an existing function."""
        result = extractor.extract_function(sample_module, "standalone_function")

        assert result is not None
        assert result.kind == SymbolKind.FUNCTION
        assert result.name == "standalone_function"
        assert result.docstring is not None

    def test_extract_async_function(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting an async function."""
        result = extractor.extract_function(sample_module, "async_function")

        assert result is not None
        assert result.name == "async_function"
        assert result.docstring is not None

    def test_extract_nonexistent_function(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a function that doesn't exist."""
        result = extractor.extract_function(sample_module, "nonexistent_function")

        assert result is None

    def test_function_signature(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that function signature is extracted."""
        result = extractor.extract_function(sample_module, "standalone_function")

        assert result is not None
        assert result.signature is not None
        assert "name" in result.signature
        assert "str" in result.signature
        assert "count" in result.signature


# --- Tests for extract_method ---

class TestExtractMethod:
    """Tests for SymbolExtractor.extract_method()"""

    def test_extract_existing_method(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting an existing method."""
        result = extractor.extract_method(sample_module, "SampleClass", "get_value")

        assert result is not None
        assert result.name == "get_value"
        assert result.docstring is not None

    def test_extract_init_method(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting __init__ method."""
        result = extractor.extract_method(sample_module, "SampleClass", "__init__")

        assert result is not None
        assert result.name == "__init__"

    def test_extract_nonexistent_method(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a method that doesn't exist."""
        result = extractor.extract_method(sample_module, "SampleClass", "nonexistent")

        assert result is None

    def test_extract_method_from_nonexistent_class(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a method from a nonexistent class."""
        result = extractor.extract_method(sample_module, "NonexistentClass", "method")

        assert result is None

    def test_method_with_decorators(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test that method decorators are extracted."""
        result = extractor.extract_method(sample_module, "SampleClass", "static_method")

        assert result is not None
        assert "staticmethod" in result.decorators

    def test_property_decorator(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a property."""
        result = extractor.extract_method(sample_module, "SampleClass", "doubled")

        assert result is not None
        assert "property" in result.decorators

    def test_classmethod_decorator(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test extracting a classmethod."""
        result = extractor.extract_method(sample_module, "SampleClass", "class_method")

        assert result is not None
        assert "classmethod" in result.decorators


# --- Tests for Signature Extraction ---

class TestSignatureExtraction:
    """Tests for function/method signature extraction."""

    def test_simple_signature(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test simple function signature."""
        result = extractor.extract_function(sample_module, "standalone_function")

        assert result is not None
        assert result.signature is not None
        # Should contain parameter types
        assert "str" in result.signature
        assert "int" in result.signature

    def test_signature_with_defaults(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test signature with default values."""
        result = extractor.extract_function(sample_module, "standalone_function")

        assert result is not None
        # count has default value of 1
        assert "= 1" in result.signature or "=1" in result.signature

    def test_signature_with_return_type(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test signature includes return type."""
        result = extractor.extract_function(sample_module, "standalone_function")

        assert result is not None
        assert "->" in result.signature
        assert "str" in result.signature

    def test_signature_with_complex_types(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test signature with complex type annotations."""
        result = extractor.extract_function(sample_module, "async_function")

        assert result is not None
        assert "List" in result.signature


# --- Tests for Edge Cases ---

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_module(self, extractor: SymbolExtractor, project_root: Path):
        """Test extracting an empty module."""
        module_dir = project_root / "src" / "empty"
        module_dir.mkdir(parents=True)

        (module_dir / "mod.py").write_text("")

        result = extractor.extract_module("empty.mod")

        assert result is not None
        assert result.children == []
        assert result.docstring is None

    def test_module_with_syntax_error(
        self, extractor: SymbolExtractor, project_root: Path
    ):
        """Test module with syntax error returns None."""
        module_dir = project_root / "src" / "broken"
        module_dir.mkdir(parents=True)

        (module_dir / "mod.py").write_text("def broken(:\n    pass")

        result = extractor.extract_module("broken.mod")

        assert result is None

    def test_nested_class(self, extractor: SymbolExtractor, project_root: Path):
        """Test extracting top-level class (nested classes not extracted)."""
        module_dir = project_root / "src" / "nested"
        module_dir.mkdir(parents=True)

        (module_dir / "mod.py").write_text(dedent('''
            """Module with nested class."""

            class Outer:
                """Outer class."""

                class Inner:
                    """Inner class."""
                    pass
        '''))

        result = extractor.extract_class("nested.mod", "Outer")

        assert result is not None
        assert result.name == "Outer"
        # Inner class should not be in children (only methods)
        inner_in_children = any(c.name == "Inner" for c in result.children)
        assert not inner_in_children

    def test_module_path_conversion(
        self, extractor: SymbolExtractor, project_root: Path
    ):
        """Test various module path formats."""
        # Create nested module
        nested_dir = project_root / "src" / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)

        (nested_dir / "mod.py").write_text('"""Deeply nested."""')

        result = extractor.extract_module("a.b.c.mod")

        assert result is not None
        assert "Deeply nested" in result.docstring


# --- Tests for ExtractedSymbol ---

class TestExtractedSymbol:
    """Tests for ExtractedSymbol data class."""

    def test_docstring_short(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test docstring_short property."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        assert result.docstring_short is not None
        assert "sample class" in result.docstring_short.lower()
        # Should only be first line
        assert "\n" not in result.docstring_short

    def test_to_dict(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test to_dict() serialization."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        data = result.to_dict()

        assert data["name"] == "SampleClass"
        assert data["kind"] == "class"
        assert "file" in data
        assert "line" in data
        assert "docstring" in data
        assert "children" in data

    def test_to_dict_with_methods(
        self, extractor: SymbolExtractor, sample_module: str
    ):
        """Test to_dict includes methods."""
        result = extractor.extract_class(sample_module, "SampleClass")

        assert result is not None
        data = result.to_dict()

        assert "children" in data
        assert len(data["children"]) > 0

        # Methods should have their info
        method_names = [m["name"] for m in data["children"]]
        assert "get_value" in method_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
