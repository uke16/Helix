---
adr_id: "019"
title: "Validatable Documentation References"
status: Proposed
date: 2024-12-24

project_type: helix_internal
component_type: TOOL
classification: NEW
change_scope: major
domain: helix
language: python

skills:
  - helix

files:
  create:
    - src/helix/tools/ref_resolver.py
    - tests/test_ref_resolver.py
  modify:
    - src/helix/tools/docs_compiler.py
    - docs/sources/debug.yaml
  docs:
    - docs/sources/documentation-system.yaml
    - skills/helix/SKILL.md

depends_on:
  - "014"
---

# ADR-019: Validatable Documentation References

## Kontext

### Was ist das Problem?

Die YAML-Dokumentation in `docs/sources/*.yaml` enthält Code-Referenzen als einfache Strings:

```yaml
# docs/sources/debug.yaml
modules:
  - name: StreamParser
    module: "helix.debug.stream_parser"  # Was wenn Modul gelöscht wird?
    methods:
      - "parse_line(line: str)"          # Was wenn Methode umbenannt wird?
```

Wenn eine Klasse, Methode oder ein Modul gelöscht oder umbenannt wird, bleibt die Dokumentation falsch - ohne dass es jemand merkt.

### Warum muss es gelöst werden?

1. **Falsche Dokumentation** verwirrt Claude Code Instanzen
2. **Keine Warnung** bei Breaking Changes an dokumentierten APIs
3. **Manuelle Prüfung** ist fehleranfällig und zeitaufwändig
4. **Vertrauensverlust** - wenn eine Referenz falsch ist, was noch?

### Was passiert wenn wir nichts tun?

- Dokumentation und Code driften auseinander
- Claude Code Instanzen halluzinieren basierend auf veralteter Doku
- Mehr Debugging-Zeit weil Doku nicht stimmt
- Refactoring wird riskant (wer weiss was noch auf alten Namen verweist?)

---

## Entscheidung

### Wir entscheiden uns für:

Ein **validatable reference system** mit `$ref`-Syntax, das Code-Referenzen zur Compile-Zeit verifiziert und bei fehlenden Symbolen warnt oder fehlschlägt.

### Diese Entscheidung beinhaltet:

1. **Neue `$ref`-Syntax** in YAML-Sources für validierbare Referenzen
2. **Reference Resolver Modul** das Python-Symbole verifiziert
3. **Integration in docs_compiler** mit `--validate-refs` Flag
4. **Quality Gate `docs_refs_valid`** für Commit-Blocking

### Warum diese Lösung?

- **Minimal-invasiv**: Bestehende YAML-Dateien funktionieren weiter
- **Opt-in**: Teams können schrittweise migrieren
- **Automatisch**: Keine manuelle Prüfung nötig
- **CI-ready**: Kann in Pipeline integriert werden

### Welche Alternativen wurden betrachtet?

1. **Docstrings als einzige Quelle**: Nicht gewählt - manuelle Anreicherung (when_to_use, examples) wäre nicht möglich
2. **External Link Checker**: Nicht gewählt - versteht Python-Symbole nicht
3. **IDE Plugin**: Nicht gewählt - funktioniert nicht in CI/CD

---

## Implementation

### 1. Reference Resolver

**Neue Datei:** `src/helix/tools/ref_resolver.py`

```python
"""Reference resolver for validatable documentation.

This module validates $ref references in YAML documentation sources
against actual Python code. It verifies that referenced modules,
classes, and methods exist.

Example:
    >>> resolver = RefResolver(root=Path("."))
    >>> result = resolver.resolve("helix.debug.StreamParser")
    >>> if result.exists:
    ...     print(f"Found at {result.location}")
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Any
import ast
import importlib.util


@dataclass
class ResolveResult:
    """Result of resolving a code reference.

    Attributes:
        ref: The original reference string.
        exists: Whether the symbol was found.
        location: File path and line number if found.
        symbol_type: Type of symbol (module, class, function, method).
        docstring: Extracted docstring if available.
        signature: Function/method signature if applicable.
        error: Error message if resolution failed.
    """

    ref: str
    exists: bool
    location: str | None = None
    symbol_type: str | None = None
    docstring: str | None = None
    signature: str | None = None
    error: str | None = None


@dataclass
class ValidationResult:
    """Result of validating all references in a YAML file.

    Attributes:
        source_file: Path to the YAML file.
        total_refs: Total number of $ref found.
        valid_refs: Number of valid references.
        invalid_refs: List of ResolveResult for invalid references.
        warnings: Optional references that are missing.
    """

    source_file: Path
    total_refs: int
    valid_refs: int
    invalid_refs: list[ResolveResult]
    warnings: list[ResolveResult]

    @property
    def success(self) -> bool:
        """True if all required references are valid."""
        return len(self.invalid_refs) == 0


class RefResolver:
    """Resolves and validates code references in documentation.

    The resolver uses AST parsing to find symbols without importing
    modules, making it safe for use with arbitrary codebases.

    Args:
        root: Project root directory containing src/.

    Example:
        >>> resolver = RefResolver(Path("/path/to/helix"))
        >>> result = resolver.resolve("helix.debug.StreamParser")
        >>> print(result.exists)  # True or False
    """

    def __init__(self, root: Path):
        self.root = root
        self.src_dir = root / "src"
        self._cache: dict[str, ResolveResult] = {}

    def resolve(self, ref: str) -> ResolveResult:
        """Resolve a single code reference.

        Args:
            ref: Reference string like "helix.debug.StreamParser"
                 or "helix.debug.StreamParser.parse_line".

        Returns:
            ResolveResult with exists=True if found.
        """
        if ref in self._cache:
            return self._cache[ref]

        result = self._do_resolve(ref)
        self._cache[ref] = result
        return result

    def _do_resolve(self, ref: str) -> ResolveResult:
        """Internal resolution logic using AST parsing."""
        parts = ref.split(".")

        # Find the module file
        module_path = self._find_module_file(parts)
        if module_path is None:
            return ResolveResult(
                ref=ref,
                exists=False,
                error=f"Module not found: {'.'.join(parts[:2])}"
            )

        # Parse the module
        try:
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError as e:
            return ResolveResult(
                ref=ref,
                exists=False,
                error=f"Syntax error in module: {e}"
            )

        # Find the symbol in the AST
        return self._find_symbol_in_ast(ref, parts, tree, module_path)

    def _find_module_file(self, parts: list[str]) -> Path | None:
        """Find the Python file for a module path."""
        if len(parts) < 2 or parts[0] != "helix":
            return None

        # Build possible file paths
        # helix.debug.stream_parser -> src/helix/debug/stream_parser.py
        module_parts = []
        for i, part in enumerate(parts[1:], 1):
            module_parts.append(part)
            file_path = self.src_dir / "helix" / "/".join(module_parts[:-1]) / f"{part}.py"
            if file_path.exists():
                return file_path

            # Check __init__.py
            init_path = self.src_dir / "helix" / "/".join(module_parts) / "__init__.py"
            if init_path.exists():
                return init_path

        return None

    def _find_symbol_in_ast(
        self,
        ref: str,
        parts: list[str],
        tree: ast.Module,
        file_path: Path
    ) -> ResolveResult:
        """Find a symbol (class, function, method) in an AST."""
        # Skip module parts to find symbol name
        symbol_parts = self._get_symbol_parts(parts, file_path)

        if not symbol_parts:
            # Just the module itself
            docstring = ast.get_docstring(tree)
            return ResolveResult(
                ref=ref,
                exists=True,
                location=str(file_path.relative_to(self.root)),
                symbol_type="module",
                docstring=docstring
            )

        return self._search_ast(ref, symbol_parts, tree, file_path)

    def _get_symbol_parts(self, parts: list[str], file_path: Path) -> list[str]:
        """Extract symbol parts from reference after module path."""
        file_stem = file_path.stem
        for i, part in enumerate(parts):
            if part == file_stem:
                return parts[i + 1:]
        return parts[2:]  # Default: skip helix.xxx

    def _search_ast(
        self,
        ref: str,
        symbol_parts: list[str],
        tree: ast.Module,
        file_path: Path
    ) -> ResolveResult:
        """Search for symbol in AST nodes."""
        if not symbol_parts:
            return ResolveResult(ref=ref, exists=False, error="Empty symbol path")

        target_name = symbol_parts[0]

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == target_name:
                if len(symbol_parts) == 1:
                    return ResolveResult(
                        ref=ref,
                        exists=True,
                        location=f"{file_path.relative_to(self.root)}:{node.lineno}",
                        symbol_type="class",
                        docstring=ast.get_docstring(node)
                    )
                else:
                    # Look for method
                    method_name = symbol_parts[1]
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return ResolveResult(
                                ref=ref,
                                exists=True,
                                location=f"{file_path.relative_to(self.root)}:{item.lineno}",
                                symbol_type="method",
                                docstring=ast.get_docstring(item),
                                signature=self._get_signature(item)
                            )
                    return ResolveResult(
                        ref=ref,
                        exists=False,
                        error=f"Method not found: {method_name}"
                    )

            elif isinstance(node, ast.FunctionDef) and node.name == target_name:
                return ResolveResult(
                    ref=ref,
                    exists=True,
                    location=f"{file_path.relative_to(self.root)}:{node.lineno}",
                    symbol_type="function",
                    docstring=ast.get_docstring(node),
                    signature=self._get_signature(node)
                )

        return ResolveResult(
            ref=ref,
            exists=False,
            error=f"Symbol not found: {target_name}"
        )

    def _get_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        return f"{node.name}({', '.join(args)}){returns}"

    def validate_yaml(self, yaml_path: Path, data: dict[str, Any]) -> ValidationResult:
        """Validate all $ref in a YAML structure.

        Args:
            yaml_path: Path to the YAML file (for error reporting).
            data: Parsed YAML data structure.

        Returns:
            ValidationResult with all findings.
        """
        refs = self._collect_refs(data)
        invalid: list[ResolveResult] = []
        warnings: list[ResolveResult] = []

        for ref_str, optional in refs:
            result = self.resolve(ref_str)
            if not result.exists:
                if optional:
                    warnings.append(result)
                else:
                    invalid.append(result)

        return ValidationResult(
            source_file=yaml_path,
            total_refs=len(refs),
            valid_refs=len(refs) - len(invalid) - len(warnings),
            invalid_refs=invalid,
            warnings=warnings
        )

    def _collect_refs(
        self,
        data: Any,
        path: str = ""
    ) -> list[tuple[str, bool]]:
        """Recursively collect all $ref from a data structure.

        Returns list of (ref_string, is_optional) tuples.
        """
        refs: list[tuple[str, bool]] = []

        if isinstance(data, dict):
            for key, value in data.items():
                if key == "$ref":
                    refs.append((value, False))
                elif key == "$ref?":
                    refs.append((value, True))
                else:
                    refs.extend(self._collect_refs(value, f"{path}.{key}"))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                refs.extend(self._collect_refs(item, f"{path}[{i}]"))

        return refs
```

### 2. Integration in docs_compiler.py

**Änderungen in:** `src/helix/tools/docs_compiler.py`

```python
# Am Anfang der Datei importieren:
from helix.tools.ref_resolver import RefResolver, ValidationResult

# In der DocCompiler Klasse, neue Methode hinzufügen:

def validate_refs(self) -> CompileResult:
    """Validate all $ref in YAML sources.

    Returns:
        CompileResult with validation status.
    """
    resolver = RefResolver(self.root)
    errors: list[str] = []
    warnings: list[str] = []

    if not self.sources_dir.exists():
        return CompileResult(success=True, warnings=["No sources directory"])

    for yaml_file in sorted(self.sources_dir.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            continue

        result = resolver.validate_yaml(yaml_file, data)

        for invalid in result.invalid_refs:
            errors.append(
                f"{yaml_file.name}: Invalid reference '{invalid.ref}' - {invalid.error}"
            )

        for warn in result.warnings:
            warnings.append(
                f"{yaml_file.name}: Optional reference missing '{warn.ref}'"
            )

    return CompileResult(
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
```

**Neuer CLI Subcommand in main():**

```python
# Nach "diff" subparser:
subparsers.add_parser("validate-refs", help="Validate all $ref in YAML sources")

# In der command-Verarbeitung:
elif args.command == "validate-refs":
    result = compiler.validate_refs()

    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)

    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if result.success:
        print("All references valid")
    else:
        print(f"Found {len(result.errors)} invalid references", file=sys.stderr)

    sys.exit(0 if result.success else 1)
```

### 3. Aktualisierte YAML-Syntax

**Beispiel-Migration in `docs/sources/debug.yaml`:**

```yaml
# VORHER (unvalidiert):
modules:
  - name: StreamParser
    module: "helix.debug.stream_parser"
    methods:
      - "parse_line(line: str)"

# NACHHER (validiert):
modules:
  - $ref: helix.debug.stream_parser.StreamParser
    # AUTO-EXTRACTED: name, docstring, location, methods
    # MANUAL (bleibt in YAML):
    when_to_use: "Real-time CLI output processing"
    pitfalls:
      - "Expects NDJSON format"
    example: |
      parser = StreamParser()
      async for event in parser.parse_stream(stdout):
          handle(event)
```

### 4. Quality Gate (optional)

**Neuer Gate-Typ in Quality Gates System:**

```yaml
# In phases.yaml verwendbar:
quality_gate:
  type: docs_refs_valid
  fail_on_warning: false  # Optional: auch bei Warnings fehlschlagen
```

---

## Dokumentation

Folgende Dokumente müssen aktualisiert werden:

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/sources/documentation-system.yaml` | $ref Syntax dokumentieren, ADR-019 Status auf "Implemented" setzen |
| `skills/helix/SKILL.md` | Neues Tool `ref_resolver` und `validate-refs` Command beschreiben |
| `CLAUDE.md` | validate-refs Befehl in der Tool-Referenz hinzufügen |
| `docs/ADR-TEMPLATE.md` | Beispiel mit $ref Syntax |

### Neue Dokumentation

Das Feature dokumentiert sich selbst durch:

1. Docstrings in `ref_resolver.py` (werden via docs_compiler extrahiert)
2. Aktualisierung von `docs/sources/documentation-system.yaml`
3. Automatische Generierung der finalen Docs via docs_compiler

---

## Akzeptanzkriterien

### 1. Funktionalität

- [ ] RefResolver kann Python-Module, Klassen und Methoden verifizieren
- [ ] $ref und $ref? Syntax wird in YAML erkannt
- [ ] validate-refs CLI-Befehl funktioniert
- [ ] Fehlende Referenzen werden mit Dateipfad und Zeile gemeldet

### 2. Edge Cases

- [ ] Umgang mit Syntax-Fehlern in Python-Dateien (graceful degradation)
- [ ] Umgang mit nicht-existierenden Modulen
- [ ] Umgang mit privaten Methoden (_method)
- [ ] Umgang mit verschachtelten Klassen

### 3. Integration

- [ ] Bestehende YAML-Dateien funktionieren weiter (keine $ref = keine Validierung)
- [ ] Kann schrittweise migriert werden
- [ ] Kompilierung funktioniert auch wenn Validierung fehlschlägt

### 4. Tests

- [ ] Unit Tests für RefResolver
- [ ] Integration Tests mit echten YAML-Dateien
- [ ] Test für CLI-Befehl

### 5. Dokumentation

- [ ] documentation-system.yaml aktualisiert
- [ ] Docstrings vollständig
- [ ] Beispiel-Migration dokumentiert

---

## Konsequenzen

### Vorteile

- **Frühe Erkennung** von veralteten Dokumentations-Referenzen
- **Automatische Validierung** ohne manuelle Prüfung
- **CI-Integration** möglich (Block commits mit broken refs)
- **Schrittweise Migration** - Teams können langsam umstellen
- **Auto-Extraction** - weniger manuelle Arbeit bei Docstrings

### Nachteile / Risiken

- **Zusätzliche Komplexität** im docs_compiler
- **Lernkurve** für neue $ref Syntax
- **AST-Parsing Grenzen** - dynamische Symbole nicht erkennbar

### Mitigation

- **Opt-in**: Bestehende Strings funktionieren weiter
- **Klare Dokumentation**: Syntax wird in SKILL.md erklärt
- **$ref? für Optionales**: Warnings statt Errors für dynamische APIs

---

## Referenzen

- ADR-014: Documentation Architecture (Basis-System)
- `docs/sources/documentation-system.yaml`: Bereits vorbereitete Konzepte
- Python AST Modul: https://docs.python.org/3/library/ast.html
