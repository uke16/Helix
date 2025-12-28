"""
Reference Resolver for Documentation as Code.

ADR-019: Resolves $ref references in documentation YAML files to actual
code symbols, validating that they exist and extracting metadata.
"""

from pathlib import Path
from typing import Any

from helix.docs.schema import (
    ExtractedSymbol,
    FoundRef,
    RefType,
    ResolvedReference,
    SymbolKind,
    ValidationIssue,
)
from helix.docs.symbol_extractor import SymbolExtractor


class ReferenceResolver:
    """Resolves $ref references to actual code symbols."""

    def __init__(self, project_root: Path):
        """Initialize the resolver.

        Args:
            project_root: Root directory of the project.
        """
        self.root = project_root
        self.extractor = SymbolExtractor(project_root)
        self._cache: dict[str, ResolvedReference] = {}

    def resolve(self, ref: str) -> ResolvedReference:
        """Resolve a reference like 'helix.debug.StreamParser.parse_line'.

        Args:
            ref: Dotted reference string.

        Returns:
            ResolvedReference with symbol information.
        """
        if ref in self._cache:
            return self._cache[ref]

        result = self._do_resolve(ref)
        self._cache[ref] = result
        return result

    def _do_resolve(self, ref: str) -> ResolvedReference:
        """Internal resolve implementation.

        Args:
            ref: Dotted reference string.

        Returns:
            ResolvedReference with symbol information.
        """
        parts = ref.split(".")

        if len(parts) < 2:
            # Just a module name
            return self._resolve_module(ref)

        # Try different interpretations
        # 1. Try as module.class.method (most specific)
        if len(parts) >= 3:
            result = self._try_as_method(parts)
            if result and result.exists:
                return result

        # 2. Try as module.class or module.function
        result = self._try_as_symbol(parts)
        if result and result.exists:
            return result

        # 3. Try as module
        module_path = ".".join(parts)
        result = self._resolve_module(module_path)
        if result.exists:
            return result

        # Nothing found - return error
        return ResolvedReference(
            ref=ref,
            exists=False,
            kind=None,
            error=f"Symbol not found: {ref}",
        )

    def _try_as_method(self, parts: list[str]) -> ResolvedReference | None:
        """Try to resolve as module.class.method.

        Args:
            parts: Split reference parts.

        Returns:
            ResolvedReference if found, None otherwise.
        """
        # Try progressively shorter module paths
        for i in range(len(parts) - 2, 0, -1):
            module = ".".join(parts[:i])
            class_name = parts[i]
            method_name = parts[i + 1] if i + 1 < len(parts) else None

            if method_name and i + 2 < len(parts):
                # More parts after method - skip this interpretation
                continue

            symbol = self.extractor.extract_class(module, class_name)
            if symbol:
                if method_name:
                    # Look for method
                    method = self.extractor.extract_method(module, class_name, method_name)
                    if method:
                        return self._symbol_to_reference(
                            ".".join(parts), method, SymbolKind.METHOD
                        )
                else:
                    # Return class
                    return self._symbol_to_reference(
                        ".".join(parts), symbol, SymbolKind.CLASS
                    )

        return None

    def _try_as_symbol(self, parts: list[str]) -> ResolvedReference | None:
        """Try to resolve as module.symbol (class or function).

        Args:
            parts: Split reference parts.

        Returns:
            ResolvedReference if found, None otherwise.
        """
        # Try progressively shorter module paths
        for i in range(len(parts) - 1, 0, -1):
            module = ".".join(parts[:i])
            symbol_name = parts[i]

            # Try as class
            symbol = self.extractor.extract_class(module, symbol_name)
            if symbol:
                return self._symbol_to_reference(
                    ".".join(parts), symbol, SymbolKind.CLASS
                )

            # Try as function
            symbol = self.extractor.extract_function(module, symbol_name)
            if symbol:
                return self._symbol_to_reference(
                    ".".join(parts), symbol, SymbolKind.FUNCTION
                )

        return None

    def _resolve_module(self, module_path: str) -> ResolvedReference:
        """Resolve a module reference.

        Args:
            module_path: Dotted module path.

        Returns:
            ResolvedReference with module information.
        """
        symbol = self.extractor.extract_module(module_path)
        if symbol:
            return self._symbol_to_reference(module_path, symbol, SymbolKind.MODULE)

        return ResolvedReference(
            ref=module_path,
            exists=False,
            kind=None,
            error=f"Module not found: {module_path}",
        )

    def _symbol_to_reference(
        self, ref: str, symbol: ExtractedSymbol, kind: SymbolKind
    ) -> ResolvedReference:
        """Convert ExtractedSymbol to ResolvedReference.

        Args:
            ref: Original reference string.
            symbol: Extracted symbol data.
            kind: Symbol kind.

        Returns:
            ResolvedReference with symbol information.
        """
        return ResolvedReference(
            ref=ref,
            exists=True,
            kind=kind,
            file=symbol.file,
            line=symbol.line,
            docstring=symbol.docstring,
            signature=symbol.signature,
            children=symbol.children if symbol.children else None,
            error=None,
        )

    def resolve_file(self, path: str) -> ResolvedReference:
        """Resolve a $file reference.

        Args:
            path: Relative file path.

        Returns:
            ResolvedReference for the file.
        """
        full_path = self.root / path
        exists = full_path.exists()

        return ResolvedReference(
            ref=path,
            exists=exists,
            kind=SymbolKind.FILE if exists else None,
            file=full_path if exists else None,
            line=None,
            docstring=None,
            signature=None,
            children=None,
            error=None if exists else f"File not found: {path}",
        )

    def resolve_script(self, path: str) -> ResolvedReference:
        """Resolve a $calls reference to a script.

        Args:
            path: Relative script path.

        Returns:
            ResolvedReference for the script.
        """
        full_path = self.root / path
        exists = full_path.exists()

        if exists and not full_path.is_file():
            return ResolvedReference(
                ref=path,
                exists=False,
                kind=None,
                error=f"Not a file: {path}",
            )

        return ResolvedReference(
            ref=path,
            exists=exists,
            kind=SymbolKind.SCRIPT if exists else None,
            file=full_path if exists else None,
            line=None,
            docstring=None,
            signature=None,
            children=None,
            error=None if exists else f"Script not found: {path}",
        )

    def validate_all(self, yaml_data: dict) -> list[ValidationIssue]:
        """Validate all references in a YAML document.

        Args:
            yaml_data: Parsed YAML data.

        Returns:
            List of validation issues found.
        """
        issues = []

        for ref in self._find_refs(yaml_data):
            resolved = self._resolve_by_type(ref)
            if not resolved.exists:
                issues.append(
                    ValidationIssue(
                        severity="warning" if ref.optional else "error",
                        path=ref.yaml_path,
                        ref=ref.value,
                        message=resolved.error or f"Symbol not found: {ref.value}",
                    )
                )

        return issues

    def _resolve_by_type(self, ref: FoundRef) -> ResolvedReference:
        """Resolve a reference based on its type.

        Args:
            ref: Found reference with type information.

        Returns:
            ResolvedReference for the reference.
        """
        if ref.ref_type in (RefType.REF, RefType.REF_OPTIONAL, RefType.USES):
            return self.resolve(ref.value)
        elif ref.ref_type == RefType.FILE:
            return self.resolve_file(ref.value)
        elif ref.ref_type == RefType.CALLS:
            return self.resolve_script(ref.value)
        else:
            return ResolvedReference(
                ref=ref.value,
                exists=False,
                kind=None,
                error=f"Unknown reference type: {ref.ref_type}",
            )

    def _find_refs(
        self, obj: Any, path: str = ""
    ) -> list[FoundRef]:
        """Find all references in a data structure.

        Args:
            obj: Data structure to search.
            path: Current YAML path.

        Returns:
            List of found references.
        """
        refs = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key

                # Check for reference keys
                if key == "$ref":
                    refs.append(
                        FoundRef(
                            ref_type=RefType.REF,
                            value=value,
                            yaml_path=new_path,
                            optional=False,
                        )
                    )
                elif key == "$ref?":
                    refs.append(
                        FoundRef(
                            ref_type=RefType.REF_OPTIONAL,
                            value=value,
                            yaml_path=new_path,
                            optional=True,
                        )
                    )
                elif key == "$uses":
                    refs.append(
                        FoundRef(
                            ref_type=RefType.USES,
                            value=value,
                            yaml_path=new_path,
                            optional=False,
                        )
                    )
                elif key == "$file":
                    refs.append(
                        FoundRef(
                            ref_type=RefType.FILE,
                            value=value,
                            yaml_path=new_path,
                            optional=False,
                        )
                    )
                elif key == "$calls":
                    refs.append(
                        FoundRef(
                            ref_type=RefType.CALLS,
                            value=value,
                            yaml_path=new_path,
                            optional=False,
                        )
                    )
                elif key == "$refs":
                    # List of references (for diagrams)
                    if isinstance(value, list):
                        for i, item in enumerate(value):
                            refs.append(
                                FoundRef(
                                    ref_type=RefType.REF,
                                    value=item,
                                    yaml_path=f"{new_path}[{i}]",
                                    optional=False,
                                )
                            )
                else:
                    # Recurse into nested structures
                    refs.extend(self._find_refs(value, new_path))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                refs.extend(self._find_refs(item, f"{path}[{i}]"))

        return refs

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()
