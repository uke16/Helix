---
adr_id: "019"
title: "Documentation as Code - Validierbare Referenzen"
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
    - src/helix/tools/ref_validator.py
    - tests/tools/test_ref_validator.py
  modify:
    - src/helix/tools/docs_compiler.py
    - docs/sources/debug.yaml
    - docs/sources/tools.yaml
  docs:
    - skills/helix/SKILL.md
    - docs/SELF-DOCUMENTATION.md

depends_on:
  - ADR-014
---

# ADR-019: Documentation as Code - Validierbare Referenzen

## Kontext

Unsere YAML-Dokumentation in `docs/sources/*.yaml` kann auf Code verweisen der nicht mehr existiert. Das aktuelle Format verwendet reine Strings für Code-Referenzen:

```yaml
# docs/sources/debug.yaml - AKTUELL
modules:
  - name: StreamParser
    module: "helix.debug.stream_parser"  # String - keine Validierung!
    methods:
      - "parse_line(line: str)"          # String - keine Validierung!
```

**Probleme:**
1. Wenn `helix.debug.stream_parser` gelöscht wird, merkt es niemand
2. Wenn `parse_line` zu `parse` umbenannt wird, bleibt die Doku falsch
3. Claude Code Instanzen lesen falsche Dokumentation und halluzinieren API-Calls
4. Der docs_compiler prüft nur YAML-Syntax, nicht ob der Code existiert

**Was passiert ohne Lösung:**
- Dokumentation driftet schleichend vom Code ab
- Fehler werden erst entdeckt wenn jemand die API nutzt und sie nicht funktioniert
- Claude Code generiert Code der auf nicht-existierenden Methoden basiert

## Entscheidung

Wir implementieren **validierbare Code-Referenzen** im YAML-Format mit einem neuen `ref_validator` Tool. Die Lösung besteht aus drei Teilen:

### 1. Neue YAML-Syntax mit `$ref`-Markern

```yaml
# docs/sources/debug.yaml - NEU
modules:
  - name: StreamParser
    module:
      $ref: helix.debug.stream_parser     # Validierbar!
    key_classes:
      - name:
          $class: helix.debug.stream_parser.StreamParser
        methods:
          - $method: helix.debug.stream_parser.StreamParser.parse_line
          - $method: helix.debug.stream_parser.StreamParser.parse_stream
```

**Warum diese Syntax?**
- `$`-Prefix ist YAML-konform und signalisiert "hier muss validiert werden"
- Bestehende String-Felder bleiben weiterhin gültig (Abwärtskompatibilität)
- Klare Unterscheidung: `$ref` (Module), `$class` (Klassen), `$method` (Methoden), `$file` (Dateipfade)

### 2. Reference Validator Tool

Ein neues Tool `helix.tools.ref_validator` das:
- YAML-Dateien nach `$ref`/`$class`/`$method`/`$file` Markern scannt
- Referenzen gegen den echten Code validiert (via `importlib` und `ast`)
- Fehlende/falsche Referenzen als Errors meldet
- Standalone CLI und Python API bietet

### 3. Integration in docs_compiler

Der bestehende `docs_compiler` wird erweitert um:
- Automatische Referenz-Validierung beim `compile` Befehl
- Optionales `--strict` Flag das bei invaliden Refs abbricht
- Neuer `validate-refs` Subcommand für CI/Pre-Commit Hooks

**Warum nicht AST-basierte automatische Extraktion?**
- Zu komplex für erste Iteration
- Manuelle Dokumentation kann Kontext hinzufügen den Code nicht hat
- `$ref`-Marker erlauben explizite Kontrolle was dokumentiert wird

## Implementation

### 1. Reference Validator Modul

`src/helix/tools/ref_validator.py`:

```python
"""
Reference Validator for HELIX Documentation.

Validates that $ref, $class, $method, and $file markers in YAML
documentation sources point to existing code and files.

Usage:
    python -m helix.tools.ref_validator validate docs/sources/
    python -m helix.tools.ref_validator check docs/sources/debug.yaml
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
import ast
import importlib
import importlib.util
import sys

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class RefError:
    """A validation error for a code reference.

    Attributes:
        file: Path to the YAML file containing the reference.
        path: JSON-path to the reference within the YAML.
        ref_type: Type of reference ($ref, $class, $method, $file).
        value: The reference value that failed validation.
        message: Human-readable error message.
    """
    file: Path
    path: str
    ref_type: str
    value: str
    message: str


@dataclass
class ValidationResult:
    """Result of reference validation.

    Attributes:
        success: True if all references are valid.
        errors: List of validation errors.
        refs_checked: Total number of references checked.
    """
    success: bool
    errors: list[RefError] = field(default_factory=list)
    refs_checked: int = 0


class RefValidator:
    """Validates code references in YAML documentation sources.

    Scans YAML files for $ref, $class, $method, and $file markers
    and validates that they point to existing code/files.

    Args:
        root: Root directory of the project for resolving paths.

    Example:
        >>> validator = RefValidator(Path("."))
        >>> result = validator.validate_file(Path("docs/sources/debug.yaml"))
        >>> if not result.success:
        ...     for error in result.errors:
        ...         print(f"{error.file}:{error.path}: {error.message}")
    """

    # Reference marker types
    REF_MARKERS = {"$ref", "$class", "$method", "$file"}

    def __init__(self, root: Path | None = None):
        self.root = root or Path(".")
        self._import_cache: dict[str, Any] = {}

    def validate_directory(self, sources_dir: Path) -> ValidationResult:
        """Validate all YAML files in a directory.

        Args:
            sources_dir: Directory containing YAML source files.

        Returns:
            Combined ValidationResult for all files.
        """
        all_errors: list[RefError] = []
        total_refs = 0

        for yaml_file in sorted(sources_dir.glob("*.yaml")):
            result = self.validate_file(yaml_file)
            all_errors.extend(result.errors)
            total_refs += result.refs_checked

        return ValidationResult(
            success=len(all_errors) == 0,
            errors=all_errors,
            refs_checked=total_refs,
        )

    def validate_file(self, yaml_path: Path) -> ValidationResult:
        """Validate all references in a single YAML file.

        Args:
            yaml_path: Path to the YAML file.

        Returns:
            ValidationResult with any errors found.
        """
        if yaml is None:
            return ValidationResult(
                success=False,
                errors=[RefError(
                    file=yaml_path,
                    path="",
                    ref_type="",
                    value="",
                    message="PyYAML not installed"
                )]
            )

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[RefError(
                    file=yaml_path,
                    path="",
                    ref_type="",
                    value="",
                    message=f"YAML parse error: {e}"
                )]
            )

        errors: list[RefError] = []
        refs_checked = 0

        # Recursively find and validate all refs
        refs_checked = self._validate_node(data, yaml_path, "", errors)

        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            refs_checked=refs_checked,
        )

    def _validate_node(
        self,
        node: Any,
        file: Path,
        path: str,
        errors: list[RefError]
    ) -> int:
        """Recursively validate references in a YAML node.

        Returns number of refs checked.
        """
        refs_checked = 0

        if isinstance(node, dict):
            for key, value in node.items():
                new_path = f"{path}.{key}" if path else key

                # Check if this is a reference marker
                if key in self.REF_MARKERS and isinstance(value, str):
                    refs_checked += 1
                    error = self._validate_ref(key, value, file, new_path)
                    if error:
                        errors.append(error)
                else:
                    refs_checked += self._validate_node(value, file, new_path, errors)

        elif isinstance(node, list):
            for i, item in enumerate(node):
                new_path = f"{path}[{i}]"
                refs_checked += self._validate_node(item, file, new_path, errors)

        return refs_checked

    def _validate_ref(
        self,
        ref_type: str,
        value: str,
        file: Path,
        path: str
    ) -> RefError | None:
        """Validate a single reference.

        Args:
            ref_type: The marker type ($ref, $class, etc.)
            value: The reference value to validate.
            file: Source YAML file.
            path: JSON-path within the YAML.

        Returns:
            RefError if validation fails, None if valid.
        """
        if ref_type == "$file":
            return self._validate_file_ref(value, file, path)
        elif ref_type == "$ref":
            return self._validate_module_ref(value, file, path)
        elif ref_type == "$class":
            return self._validate_class_ref(value, file, path)
        elif ref_type == "$method":
            return self._validate_method_ref(value, file, path)
        return None

    def _validate_file_ref(
        self, value: str, file: Path, path: str
    ) -> RefError | None:
        """Validate a file path reference."""
        target = self.root / value
        if not target.exists():
            return RefError(
                file=file,
                path=path,
                ref_type="$file",
                value=value,
                message=f"File not found: {value}"
            )
        return None

    def _validate_module_ref(
        self, value: str, file: Path, path: str
    ) -> RefError | None:
        """Validate a module reference (e.g., helix.debug.stream_parser)."""
        try:
            if value in self._import_cache:
                return None

            # Try to find the module spec without importing
            spec = importlib.util.find_spec(value)
            if spec is None:
                return RefError(
                    file=file,
                    path=path,
                    ref_type="$ref",
                    value=value,
                    message=f"Module not found: {value}"
                )

            self._import_cache[value] = True
            return None

        except ModuleNotFoundError:
            return RefError(
                file=file,
                path=path,
                ref_type="$ref",
                value=value,
                message=f"Module not found: {value}"
            )
        except Exception as e:
            return RefError(
                file=file,
                path=path,
                ref_type="$ref",
                value=value,
                message=f"Module validation error: {e}"
            )

    def _validate_class_ref(
        self, value: str, file: Path, path: str
    ) -> RefError | None:
        """Validate a class reference (e.g., helix.debug.stream_parser.StreamParser)."""
        parts = value.rsplit(".", 1)
        if len(parts) != 2:
            return RefError(
                file=file,
                path=path,
                ref_type="$class",
                value=value,
                message=f"Invalid class reference format: {value} (expected module.ClassName)"
            )

        module_path, class_name = parts

        # First validate the module
        module_error = self._validate_module_ref(module_path, file, path)
        if module_error:
            return RefError(
                file=file,
                path=path,
                ref_type="$class",
                value=value,
                message=f"Module not found for class: {module_path}"
            )

        # Then check if class exists via AST parsing (avoid import side effects)
        return self._check_symbol_in_module(module_path, class_name, "class", file, path, value)

    def _validate_method_ref(
        self, value: str, file: Path, path: str
    ) -> RefError | None:
        """Validate a method reference (e.g., module.ClassName.method_name)."""
        parts = value.rsplit(".", 2)
        if len(parts) < 3:
            return RefError(
                file=file,
                path=path,
                ref_type="$method",
                value=value,
                message=f"Invalid method reference: {value} (expected module.Class.method)"
            )

        # Try different interpretations
        # Format: module.path.ClassName.method
        *module_parts, class_name, method_name = value.rsplit(".", 2)
        module_path = ".".join(module_parts) if module_parts else ""

        # Handle case: helix.debug.stream_parser.StreamParser.parse_line
        parts = value.split(".")
        if len(parts) >= 4:
            # Assume second-to-last is class, last is method
            method_name = parts[-1]
            class_name = parts[-2]
            module_path = ".".join(parts[:-2])

        # Validate module exists
        module_error = self._validate_module_ref(module_path, file, path)
        if module_error:
            return RefError(
                file=file,
                path=path,
                ref_type="$method",
                value=value,
                message=f"Module not found: {module_path}"
            )

        # Check class and method via AST
        return self._check_method_in_class(
            module_path, class_name, method_name, file, path, value
        )

    def _check_symbol_in_module(
        self,
        module_path: str,
        symbol_name: str,
        symbol_type: str,
        file: Path,
        path: str,
        value: str,
    ) -> RefError | None:
        """Check if a symbol exists in a module using AST parsing."""
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is None or spec.origin is None:
                return RefError(
                    file=file, path=path, ref_type=f"${symbol_type}",
                    value=value, message=f"Cannot locate module: {module_path}"
                )

            source_file = Path(spec.origin)
            if not source_file.exists():
                return RefError(
                    file=file, path=path, ref_type=f"${symbol_type}",
                    value=value, message=f"Module source not found: {spec.origin}"
                )

            source = source_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef) and node.name == symbol_name:
                    return None  # Found!
                if isinstance(node, ast.FunctionDef) and node.name == symbol_name:
                    return None  # Found!

            return RefError(
                file=file, path=path, ref_type=f"${symbol_type}",
                value=value, message=f"{symbol_type.title()} not found: {symbol_name} in {module_path}"
            )

        except Exception as e:
            return RefError(
                file=file, path=path, ref_type=f"${symbol_type}",
                value=value, message=f"AST parse error: {e}"
            )

    def _check_method_in_class(
        self,
        module_path: str,
        class_name: str,
        method_name: str,
        file: Path,
        path: str,
        value: str,
    ) -> RefError | None:
        """Check if a method exists in a class using AST parsing."""
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is None or spec.origin is None:
                return RefError(
                    file=file, path=path, ref_type="$method",
                    value=value, message=f"Cannot locate module: {module_path}"
                )

            source_file = Path(spec.origin)
            source = source_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            # Find the class
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Find the method in the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return None  # Found!

                    return RefError(
                        file=file, path=path, ref_type="$method",
                        value=value,
                        message=f"Method not found: {method_name} in class {class_name}"
                    )

            return RefError(
                file=file, path=path, ref_type="$method",
                value=value, message=f"Class not found: {class_name} in {module_path}"
            )

        except Exception as e:
            return RefError(
                file=file, path=path, ref_type="$method",
                value=value, message=f"AST parse error: {e}"
            )


def validate_refs(sources_dir: Path, root: Path | None = None) -> ValidationResult:
    """Convenience function to validate all refs in a directory.

    Args:
        sources_dir: Directory containing YAML source files.
        root: Project root for resolving paths.

    Returns:
        ValidationResult with all errors found.
    """
    validator = RefValidator(root)
    return validator.validate_directory(sources_dir)


def main() -> None:
    """CLI entry point for reference validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate code references in YAML documentation"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="File or directory to validate"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory"
    )

    args = parser.parse_args()

    validator = RefValidator(args.root)

    if args.path.is_dir():
        result = validator.validate_directory(args.path)
    else:
        result = validator.validate_file(args.path)

    if result.success:
        print(f"All {result.refs_checked} references valid")
        sys.exit(0)
    else:
        print(f"Found {len(result.errors)} invalid references:")
        for error in result.errors:
            print(f"  {error.file}:{error.path}")
            print(f"    {error.ref_type}: {error.value}")
            print(f"    {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 2. Integration in docs_compiler.py

Änderungen an `src/helix/tools/docs_compiler.py`:

```python
# Am Anfang der Datei, nach den anderen Imports:
from helix.tools.ref_validator import RefValidator, ValidationResult as RefValidationResult

# In der DocCompiler Klasse, neue Methode:
def validate_refs(self) -> RefValidationResult:
    """Validate all code references in YAML sources.

    Returns:
        RefValidationResult with any invalid references found.
    """
    validator = RefValidator(self.root)
    return validator.validate_directory(self.sources_dir)

# In compile(), nach collect_sources():
def compile(self, targets: list[str] | None = None, strict: bool = False) -> CompileResult:
    # ... existing code ...

    # Validate references if strict mode
    if strict:
        ref_result = self.validate_refs()
        if not ref_result.success:
            return CompileResult(
                success=False,
                errors=[f"Invalid ref: {e.value} - {e.message}" for e in ref_result.errors]
            )

    # ... rest of existing code ...

# Neuer CLI-Subcommand in main():
# validate-refs command
validate_refs_parser = subparsers.add_parser(
    "validate-refs",
    help="Validate code references in YAML sources"
)

# In der command-Verarbeitung:
elif args.command == "validate-refs":
    result = compiler.validate_refs()

    if result.success:
        print(f"All {result.refs_checked} references valid")
    else:
        print(f"Found {len(result.errors)} invalid references:", file=sys.stderr)
        for error in result.errors:
            print(f"  {error.file}:{error.path}", file=sys.stderr)
            print(f"    {error.message}", file=sys.stderr)

    sys.exit(0 if result.success else 1)
```

### 3. Beispiel: Migration einer YAML-Datei

**Vorher (debug.yaml):**
```yaml
modules:
  - id: stream_parser
    name: "StreamParser"
    module: "helix.debug.stream_parser"  # Unvalidiert
    key_classes:
      - name: "StreamParser"
        methods:
          - "parse_line(line: str) -> Event"
```

**Nachher (debug.yaml):**
```yaml
modules:
  - id: stream_parser
    name: "StreamParser"
    module:
      $ref: helix.debug.stream_parser      # Validiert!
    key_classes:
      - name:
          $class: helix.debug.stream_parser.StreamParser
        methods:
          - $method: helix.debug.stream_parser.StreamParser.parse_line
          # Für Signaturen bleibt weiterhin ein separates Feld möglich:
        signatures:
          - "parse_line(line: str) -> Event"
```

### 4. CLI-Nutzung

```bash
# Alle Referenzen validieren
python -m helix.tools.ref_validator docs/sources/

# Einzelne Datei prüfen
python -m helix.tools.ref_validator docs/sources/debug.yaml

# Via docs_compiler
python -m helix.tools.docs_compiler validate-refs

# Compile mit strikter Validierung (bricht bei Fehlern ab)
python -m helix.tools.docs_compiler compile --strict
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `skills/helix/SKILL.md` | Neues Tool `ref_validator` dokumentieren |
| `docs/SELF-DOCUMENTATION.md` | `$ref`-Syntax und Migrations-Guide hinzufügen |
| `CLAUDE.md` | Tool-Referenz für `ref_validator` ergänzen |
| `docs/sources/*.yaml` | Schrittweise auf `$ref`-Syntax migrieren |

## Akzeptanzkriterien

### Funktionalität

- [ ] `RefValidator` erkennt `$ref`, `$class`, `$method`, `$file` Marker
- [ ] Module-Referenzen werden via `importlib.util.find_spec` validiert
- [ ] Klassen/Methoden werden via AST-Parsing validiert (keine Imports)
- [ ] Datei-Referenzen prüfen ob Pfad existiert
- [ ] Fehler enthalten Datei, JSON-Pfad, und hilfreiche Fehlermeldung

### CLI

- [ ] `python -m helix.tools.ref_validator <path>` funktioniert
- [ ] `python -m helix.tools.docs_compiler validate-refs` funktioniert
- [ ] `--strict` Flag für compile-Befehl implementiert
- [ ] Exit-Code 1 bei Fehlern für CI-Integration

### Tests

- [ ] Unit Tests für alle Validierungs-Methoden
- [ ] Test mit gültigen Referenzen (erwarte success)
- [ ] Test mit ungültigen Referenzen (erwarte Fehler)
- [ ] Test für jedes Marker-Type (`$ref`, `$class`, `$method`, `$file`)

### Dokumentation

- [ ] skills/helix/SKILL.md aktualisiert
- [ ] Mindestens eine YAML-Datei auf `$ref`-Syntax migriert als Beispiel

## Konsequenzen

### Vorteile

- **Veraltete Dokumentation wird erkannt** - Gelöschte/umbenannte APIs werden sofort gemeldet
- **CI-Integration möglich** - Pre-Commit Hook oder Pipeline-Step verhindert kaputte Refs
- **Schrittweise Migration** - Bestehende Strings bleiben gültig, Migration nach Bedarf
- **Keine externen Services** - Reine Python-Lösung mit stdlib + ast
- **Keine Import-Seiteneffekte** - Verwendet AST-Parsing statt echte Imports

### Nachteile

- **Manuelle Migration nötig** - Bestehende YAMLs müssen angepasst werden
- **Zusätzliche Syntax** - Entwickler müssen `$ref` lernen
- **AST-Parsing-Limits** - Dynamisch generierte Klassen werden nicht erkannt
- **Performance** - AST-Parsing bei vielen Dateien kann langsam sein (Cache hilft)

### Mitigation

- **Migration-Script**: Ein einmaliges Script kann `module: "x"` zu `module: {$ref: x}` konvertieren
- **Dokumentation**: Klare Beispiele in SKILL.md
- **Caching**: `_import_cache` verhindert mehrfaches Parsen
- **Optional**: `$ref` ist opt-in, bestehende Strings bleiben möglich
