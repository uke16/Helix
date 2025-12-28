"""
HELIX Documentation as Code - Validatable References.

ADR-019: This module implements validatable documentation references
that ensure documentation stays in sync with code.

Core components:
- SymbolExtractor: Extracts symbol information from Python source files
- ReferenceResolver: Resolves $ref references to actual code symbols
- DiagramValidator: Validates diagrams against their $refs declarations

Usage:
    from helix.docs import ReferenceResolver, SymbolExtractor

    resolver = ReferenceResolver(project_root)
    result = resolver.resolve("helix.debug.StreamParser.parse_line")

    if result.exists:
        print(f"Found at {result.file}:{result.line}")
        print(f"Signature: {result.signature}")
"""

from helix.docs.schema import (
    ExtractedSymbol,
    ResolvedReference,
    ValidationIssue,
    RefType,
    DiagramValidation,
)
from helix.docs.symbol_extractor import SymbolExtractor
from helix.docs.reference_resolver import ReferenceResolver
from helix.docs.diagram_validator import DiagramValidator

__all__ = [
    "ExtractedSymbol",
    "ResolvedReference",
    "ValidationIssue",
    "RefType",
    "DiagramValidation",
    "SymbolExtractor",
    "ReferenceResolver",
    "DiagramValidator",
]
