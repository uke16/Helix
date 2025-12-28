"""
Schema definitions for Documentation as Code.

ADR-019: Defines the core data structures for validatable documentation
references including symbols, references, and validation results.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class RefType(str, Enum):
    """Type of reference in documentation."""

    REF = "$ref"  # Module/class reference
    REF_OPTIONAL = "$ref?"  # Optional reference (warning instead of error)
    USES = "$uses"  # Method/function usage reference
    FILE = "$file"  # File reference
    CALLS = "$calls"  # Script/executable reference


class SymbolKind(str, Enum):
    """Kind of code symbol."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    FILE = "file"
    SCRIPT = "script"


@dataclass
class ExtractedSymbol:
    """Information extracted from a code symbol."""

    name: str
    kind: SymbolKind
    file: Path
    line: int
    docstring: str | None = None
    signature: str | None = None
    children: list["ExtractedSymbol"] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)

    @property
    def docstring_short(self) -> str | None:
        """Get the first line of the docstring."""
        if not self.docstring:
            return None
        first_line = self.docstring.split("\n")[0].strip()
        return first_line if first_line else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML output."""
        result: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind.value,
            "file": str(self.file),
            "line": self.line,
        }
        if self.docstring:
            result["docstring"] = self.docstring
            if self.docstring_short:
                result["docstring_short"] = self.docstring_short
        if self.signature:
            result["signature"] = self.signature
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        if self.decorators:
            result["decorators"] = self.decorators
        if self.bases:
            result["bases"] = self.bases
        return result


@dataclass
class ResolvedReference:
    """A resolved symbol reference."""

    ref: str  # Original reference string
    exists: bool  # Whether symbol exists
    kind: SymbolKind | None  # "module", "class", "method", "function", "file"
    file: Path | None = None  # Source file path
    line: int | None = None  # Line number in source
    docstring: str | None = None  # Extracted docstring
    signature: str | None = None  # For methods/functions
    children: list[ExtractedSymbol] | None = None  # For classes: methods
    error: str | None = None  # Error message if not found

    @property
    def name(self) -> str:
        """Get the symbol name from the reference."""
        return self.ref.split(".")[-1]

    @property
    def module(self) -> str | None:
        """Get the module path from the reference."""
        parts = self.ref.split(".")
        if len(parts) > 1:
            # For class.method, return up to class
            # For module.class, return module
            if self.kind == SymbolKind.METHOD:
                return ".".join(parts[:-2]) if len(parts) > 2 else None
            return ".".join(parts[:-1])
        return None

    @property
    def docstring_short(self) -> str | None:
        """Get the first line of the docstring."""
        if not self.docstring:
            return None
        first_line = self.docstring.split("\n")[0].strip()
        return first_line if first_line else None

    def to_auto_dict(self) -> dict[str, Any]:
        """Convert to _auto dictionary format for YAML."""
        result: dict[str, Any] = {
            "name": self.name,
        }
        if self.module:
            result["module"] = self.module
        if self.file:
            result["file"] = str(self.file)
        if self.line:
            result["line"] = self.line
        if self.docstring:
            result["docstring"] = self.docstring
            if self.docstring_short:
                result["docstring_short"] = self.docstring_short
        if self.signature:
            result["signature"] = self.signature
        if self.children:
            result["methods"] = [
                {
                    "name": c.name,
                    "signature": c.signature,
                    "docstring": c.docstring,
                    "line": c.line,
                }
                for c in self.children
                if c.kind == SymbolKind.METHOD
            ]
        return result


@dataclass
class FoundRef:
    """A reference found in a YAML document."""

    ref_type: RefType
    value: str
    yaml_path: str  # Path in YAML document (e.g., "modules[0].$ref")
    optional: bool = False


@dataclass
class ValidationIssue:
    """An issue found during validation."""

    severity: str  # "error" or "warning"
    path: str  # YAML path
    ref: str  # Reference value
    message: str  # Error/warning message
    file: Path | None = None  # Source YAML file

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "severity": self.severity,
            "path": self.path,
            "ref": self.ref,
            "message": self.message,
        }
        if self.file:
            result["file"] = str(self.file)
        return result


@dataclass
class DiagramValidation:
    """Result of validating a diagram."""

    diagram_id: str
    file: Path | None
    valid: bool
    referenced_symbols: list[str]
    missing_symbols: list[str] = field(default_factory=list)
    extra_symbols: list[str] = field(default_factory=list)  # In diagram but not in $refs
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "diagram_id": self.diagram_id,
            "file": str(self.file) if self.file else None,
            "valid": self.valid,
            "referenced_symbols": self.referenced_symbols,
            "missing_symbols": self.missing_symbols,
            "extra_symbols": self.extra_symbols,
            "warnings": self.warnings,
        }


@dataclass
class GateResult:
    """Result from a quality gate check."""

    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompileResult:
    """Result from documentation compilation."""

    success: bool
    message: str
    files: list[Path] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
