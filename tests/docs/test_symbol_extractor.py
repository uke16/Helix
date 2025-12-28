"""
Tests for SymbolExtractor.

ADR-019: Tests for the symbol extraction functionality that parses
Python source files to extract symbol information.
"""

from pathlib import Path

import pytest

from helix.docs.schema import SymbolKind
from helix.docs.symbol_extractor import SymbolExtractor


@pytest.fixture
def project_with_code(tmp_path: Path) -> Path:
    """Create a temporary project with sample Python code."""
    # Create src directory structure
    src_dir = tmp_path / "src" / "testpkg"
    src_dir.mkdir(parents=True)

    # Create __init__.py
    (src_dir / "__init__.py").write_text('"""TestPkg package."""\n')

    # Create a comprehensive test module
    sample_module = src_dir / "classes.py"
    sample_module.write_text('''"""Module with various class types for testing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


class SimpleClass:
    """A simple class with basic methods."""

    def __init__(self, name: str):
        """Initialize with a name.

        Args:
            name: The name to use.
        """
        self.name = name

    def greet(self) -> str:
        """Return a greeting.

        Returns:
            A greeting string.
        """
        return f"Hello, {self.name}!"


class ClassWithClassMethod:
    """Class with class methods and static methods."""

    count: int = 0

    @classmethod
    def get_count(cls) -> int:
        """Get the current count."""
        return cls.count

    @staticmethod
    def static_helper(x: int) -> int:
        """A static helper method."""
        return x * 2

    @property
    def computed(self) -> str:
        """A computed property."""
        return "computed"


class ChildClass(SimpleClass):
    """A class that inherits from SimpleClass."""

    def __init__(self, name: str, age: int):
        """Initialize with name and age."""
        super().__init__(name)
        self.age = age

    def greet(self) -> str:
        """Override the parent greeting."""
        return f"Hello, {self.name} ({self.age})!"


class MultipleInheritance(SimpleClass, ABC):
    """Class with multiple inheritance."""

    @abstractmethod
    def abstract_method(self) -> None:
        """An abstract method."""
        pass


class GenericClass(Generic[T]):
    """A generic class."""

    def __init__(self, value: T):
        """Initialize with a value."""
        self.value = value

    def get(self) -> T:
        """Get the value."""
        return self.value


@dataclass
class DataClass:
    """A dataclass for testing decorator extraction."""

    name: str
    value: int = 0
''')

    # Create a module with functions
    functions_module = src_dir / "functions.py"
    functions_module.write_text('''"""Module with various function types for testing."""

from typing import Optional, List, Callable


def simple_function(x: int, y: int) -> int:
    """Add two numbers.

    Args:
        x: First number.
        y: Second number.

    Returns:
        The sum.
    """
    return x + y


def function_with_defaults(
    name: str,
    greeting: str = "Hello",
    punctuation: str = "!"
) -> str:
    """Greet someone.

    Args:
        name: Person's name.
        greeting: The greeting to use.
        punctuation: Ending punctuation.

    Returns:
        The greeting string.
    """
    return f"{greeting}, {name}{punctuation}"


def function_with_args(*args: int, **kwargs: str) -> dict:
    """Function with variable arguments.

    Args:
        *args: Variable positional arguments.
        **kwargs: Variable keyword arguments.

    Returns:
        A dictionary with the args.
    """
    return {"args": args, "kwargs": kwargs}


def function_with_complex_types(
    items: List[str],
    callback: Optional[Callable[[str], int]] = None
) -> List[int]:
    """Function with complex type hints.

    Args:
        items: List of items.
        callback: Optional callback function.

    Returns:
        List of results.
    """
    if callback:
        return [callback(item) for item in items]
    return [len(item) for item in items]


async def async_function(data: str) -> str:
    """An async function.

    Args:
        data: Input data.

    Returns:
        Processed data.
    """
    return data.upper()


def function_without_types(a, b):
    """Function without type annotations."""
    return a + b


def _private_function(x: int) -> int:
    """A private function."""
    return x * 2


def decorated_function() -> str:
    """A plain function that could be decorated."""
    return "result"
''')

    # Create a module with syntax error (for error handling tests)
    invalid_module = src_dir / "invalid.py"
    invalid_module.write_text('''"""Invalid module with syntax error."""

def broken_function(
    # Missing closing parenthesis
''')

    # Create a subpackage
    subpkg_dir = src_dir / "subpkg"
    subpkg_dir.mkdir()
    (subpkg_dir / "__init__.py").write_text('"""Subpackage."""\n')
    (subpkg_dir / "nested.py").write_text('''"""Nested module."""


class NestedClass:
    """A nested class."""

    def nested_method(self) -> None:
        """A nested method."""
        pass
''')

    return tmp_path


class TestSymbolExtractorModule:
    """Test module extraction."""

    def test_extract_module_basic(self, project_with_code: Path):
        """Test extracting a basic module."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.classes")

        assert result is not None
        assert result.kind == SymbolKind.MODULE
        assert result.name == "classes"
        assert result.file.name == "classes.py"
        assert result.line == 1
        assert "Module with various class types" in (result.docstring or "")

    def test_extract_module_not_found(self, project_with_code: Path):
        """Test extracting a non-existent module."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.nonexistent")

        assert result is None

    def test_extract_module_with_syntax_error(self, project_with_code: Path):
        """Test extracting a module with syntax error."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.invalid")

        assert result is None

    def test_extract_module_children(self, project_with_code: Path):
        """Test that module contains expected children."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.classes")

        assert result is not None
        child_names = [c.name for c in result.children]
        assert "SimpleClass" in child_names
        assert "ChildClass" in child_names
        assert "GenericClass" in child_names
        assert "DataClass" in child_names

    def test_extract_nested_module(self, project_with_code: Path):
        """Test extracting a nested module."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.subpkg.nested")

        assert result is not None
        assert result.name == "nested"


class TestSymbolExtractorClass:
    """Test class extraction."""

    def test_extract_class_basic(self, project_with_code: Path):
        """Test extracting a basic class."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "SimpleClass")

        assert result is not None
        assert result.kind == SymbolKind.CLASS
        assert result.name == "SimpleClass"
        assert result.line > 1
        assert "simple class with basic methods" in (result.docstring or "").lower()

    def test_extract_class_methods(self, project_with_code: Path):
        """Test that class contains expected methods."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "SimpleClass")

        assert result is not None
        method_names = [m.name for m in result.children]
        assert "__init__" in method_names
        assert "greet" in method_names

    def test_extract_class_with_decorators(self, project_with_code: Path):
        """Test extracting a class with decorators."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "DataClass")

        assert result is not None
        assert "dataclass" in result.decorators

    def test_extract_class_with_inheritance(self, project_with_code: Path):
        """Test extracting a class with inheritance."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "ChildClass")

        assert result is not None
        assert "SimpleClass" in result.bases

    def test_extract_class_with_multiple_inheritance(self, project_with_code: Path):
        """Test extracting a class with multiple inheritance."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "MultipleInheritance")

        assert result is not None
        assert len(result.bases) == 2
        assert "SimpleClass" in result.bases
        assert "ABC" in result.bases

    def test_extract_class_generic(self, project_with_code: Path):
        """Test extracting a generic class."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "GenericClass")

        assert result is not None
        # Generic[T] should be in bases
        assert any("Generic" in base for base in result.bases)

    def test_extract_class_not_found(self, project_with_code: Path):
        """Test extracting a non-existent class."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "NonExistentClass")

        assert result is None


class TestSymbolExtractorFunction:
    """Test function extraction."""

    def test_extract_function_basic(self, project_with_code: Path):
        """Test extracting a basic function."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "simple_function")

        assert result is not None
        assert result.kind == SymbolKind.FUNCTION
        assert result.name == "simple_function"
        assert result.signature is not None
        assert "x: int" in result.signature
        assert "y: int" in result.signature
        assert "-> int" in result.signature

    def test_extract_function_with_defaults(self, project_with_code: Path):
        """Test extracting a function with default values."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "function_with_defaults")

        assert result is not None
        assert result.signature is not None
        # Should include default values
        assert "greeting" in result.signature
        assert "Hello" in result.signature

    def test_extract_function_with_args_kwargs(self, project_with_code: Path):
        """Test extracting a function with *args and **kwargs."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "function_with_args")

        assert result is not None
        assert result.signature is not None
        assert "*args" in result.signature
        assert "**kwargs" in result.signature

    def test_extract_async_function(self, project_with_code: Path):
        """Test extracting an async function."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "async_function")

        assert result is not None
        assert result.kind == SymbolKind.FUNCTION
        assert "data: str" in result.signature
        assert "-> str" in result.signature

    def test_extract_function_without_types(self, project_with_code: Path):
        """Test extracting a function without type annotations."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "function_without_types")

        assert result is not None
        assert result.signature is not None
        # Should have args but no type annotations
        assert "a" in result.signature
        assert "b" in result.signature

    def test_extract_private_function(self, project_with_code: Path):
        """Test extracting a private function."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "_private_function")

        assert result is not None
        assert result.name == "_private_function"

    def test_extract_function_not_found(self, project_with_code: Path):
        """Test extracting a non-existent function."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_function("testpkg.functions", "nonexistent_function")

        assert result is None


class TestSymbolExtractorMethod:
    """Test method extraction."""

    def test_extract_method_basic(self, project_with_code: Path):
        """Test extracting a basic method."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method("testpkg.classes", "SimpleClass", "greet")

        assert result is not None
        assert result.kind == SymbolKind.METHOD
        assert result.name == "greet"
        assert result.signature is not None
        assert "self" in result.signature
        assert "-> str" in result.signature

    def test_extract_method_init(self, project_with_code: Path):
        """Test extracting __init__ method."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method("testpkg.classes", "SimpleClass", "__init__")

        assert result is not None
        assert result.name == "__init__"
        assert "name: str" in result.signature

    def test_extract_classmethod(self, project_with_code: Path):
        """Test extracting a classmethod."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "ClassWithClassMethod", "get_count"
        )

        assert result is not None
        assert "classmethod" in result.decorators

    def test_extract_staticmethod(self, project_with_code: Path):
        """Test extracting a staticmethod."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "ClassWithClassMethod", "static_helper"
        )

        assert result is not None
        assert "staticmethod" in result.decorators

    def test_extract_property(self, project_with_code: Path):
        """Test extracting a property."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "ClassWithClassMethod", "computed"
        )

        assert result is not None
        assert "property" in result.decorators

    def test_extract_abstract_method(self, project_with_code: Path):
        """Test extracting an abstract method."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "MultipleInheritance", "abstract_method"
        )

        assert result is not None
        assert "abstractmethod" in result.decorators

    def test_extract_method_not_found(self, project_with_code: Path):
        """Test extracting a non-existent method."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "SimpleClass", "nonexistent_method"
        )

        assert result is None

    def test_extract_method_from_nonexistent_class(self, project_with_code: Path):
        """Test extracting a method from a non-existent class."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_method(
            "testpkg.classes", "NonExistentClass", "method"
        )

        assert result is None


class TestExtractedSymbolProperties:
    """Test ExtractedSymbol computed properties."""

    def test_docstring_short(self, project_with_code: Path):
        """Test the docstring_short property."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "SimpleClass")

        assert result is not None
        assert result.docstring_short is not None
        assert "\n" not in result.docstring_short
        assert "simple class" in result.docstring_short.lower()

    def test_to_dict(self, project_with_code: Path):
        """Test the to_dict method."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "SimpleClass")

        assert result is not None
        d = result.to_dict()
        assert "name" in d
        assert "kind" in d
        assert "file" in d
        assert "line" in d
        assert d["name"] == "SimpleClass"
        assert d["kind"] == "class"

    def test_to_dict_with_children(self, project_with_code: Path):
        """Test to_dict includes children."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "SimpleClass")

        assert result is not None
        d = result.to_dict()
        assert "children" in d
        assert len(d["children"]) > 0

    def test_to_dict_with_decorators(self, project_with_code: Path):
        """Test to_dict includes decorators."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_class("testpkg.classes", "DataClass")

        assert result is not None
        d = result.to_dict()
        assert "decorators" in d
        assert "dataclass" in d["decorators"]


class TestModuleToPath:
    """Test module path resolution."""

    def test_module_in_src(self, project_with_code: Path):
        """Test finding a module in src directory."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.classes")

        assert result is not None
        assert "src" in str(result.file)

    def test_package_init(self, project_with_code: Path):
        """Test finding a package's __init__.py."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg")

        assert result is not None
        assert result.file.name == "__init__.py"

    def test_nested_package(self, project_with_code: Path):
        """Test finding a nested package."""
        extractor = SymbolExtractor(project_with_code)

        result = extractor.extract_module("testpkg.subpkg")

        assert result is not None
        assert result.file.name == "__init__.py"
        assert "subpkg" in str(result.file)
