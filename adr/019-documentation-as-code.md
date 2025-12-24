---
adr_id: "019"
title: "Documentation as Code - Validierbare Referenzen"
status: Proposed
date: 2024-12-24

project_type: helix_internal
component_type: ENHANCEMENT
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - src/helix/docs/__init__.py
    - src/helix/docs/reference_resolver.py
    - src/helix/docs/symbol_extractor.py
    - src/helix/docs/diagram_validator.py
    - src/helix/docs/schema.py
    - src/helix/quality_gates/docs_refs_valid.py
    - docs/schemas/helix-docs-v1.schema.json
    - tests/docs/test_reference_resolver.py
    - tests/docs/test_symbol_extractor.py
  modify:
    - src/helix/tools/docs_compiler.py
    - docs/sources/*.yaml (migrate to new schema)
    - .git/hooks/pre-commit
  docs:
    - docs/DOCUMENTATION-AS-CODE.md
    - skills/helix/SKILL.md

depends_on:
  - "014"  # Documentation Architecture
  - "018"  # LSP Integration

related_to:
  - "013"  # Debug & Observability
---

# ADR-019: Documentation as Code - Validierbare Referenzen

## Status

Proposed

---

## Kontext

### Das Problem

Dokumentation in HELIX v4 kann veralten ohne dass es bemerkt wird:

```yaml
# docs/sources/debug.yaml (AKTUELL - fragil)
modules:
  - name: StreamParser
    module: "helix.debug.stream_parser"    # ← String, nicht validiert
    description: "Parses NDJSON events"    # ← Manuell, kann veralten
    methods:
      - "parse_line(line: str) -> Event"   # ← String, Methode könnte umbenannt sein
```

**Konkrete Probleme:**
1. **Verwaiste Referenzen**: Modul wird gelöscht, Doku bleibt
2. **Veraltete Signaturen**: Methode wird umbenannt, Doku zeigt alten Namen
3. **Inkonsistente Beschreibungen**: Docstring ≠ YAML description
4. **Diagramme mit gelöschten Komponenten**: ASCII-Art zeigt nicht-existente Klassen

### Proof of Concept Ergebnis

Ein einfacher Validator fand **17 veraltete Referenzen** in nur 2 YAML-Dateien:

```
❌ debug.yaml:        5 methods not found
❌ orchestrator.yaml: 12 methods not found
```

### Die Idee: "Documentation as Code"

Behandle Dokumentation wie Code:
- **Typisierte Referenzen** statt Strings
- **Compile-Time Validierung** statt Runtime-Überraschungen
- **Refactoring-Safe** durch tracked dependencies

---

## Entscheidung

### Wir implementieren ein Drei-Schichten Dokumentationssystem:

```
┌─────────────────────────────────────────────────────────────┐
│ SCHICHT 1: CODE (Ground Truth)                              │
│                                                             │
│ src/helix/debug/stream_parser.py                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ class StreamParser:                                     │ │
│ │     """Parses NDJSON events from Claude CLI."""         │ │
│ │                                                         │ │
│ │     def parse_line(self, line: str) -> Event:           │ │
│ │         """Parse a single NDJSON line."""               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ → Quelle der Wahrheit für Namen, Signaturen, Docstrings     │
└─────────────────────────────────────────────────────────────┘
                        ↓ extrahiert via AST/LSP
┌─────────────────────────────────────────────────────────────┐
│ SCHICHT 2: DOKU-CODE (Validierbare Referenzen + Semantik)   │
│                                                             │
│ docs/sources/debug.yaml                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ _meta:                                                  │ │
│ │   schema: helix-docs/v1                                 │ │
│ │                                                         │ │
│ │ modules:                                                │ │
│ │   - $ref: helix.debug.stream_parser.StreamParser        │ │
│ │     # AUTO: name, docstring, methods, file, line        │ │
│ │                                                         │ │
│ │     # MANUELL: Semantik die Code nicht hat              │ │
│ │     when_to_use: "Real-time CLI output processing"      │ │
│ │     pitfalls:                                           │ │
│ │       - "Handle partial lines at stream end"            │ │
│ │     examples:                                           │ │
│ │       - title: "Basic usage"                            │ │
│ │         code: |                                         │ │
│ │           parser = StreamParser()                       │ │
│ │           for event in parser.parse_stream(stdin):      │ │
│ │               print(event)                              │ │
│ │                                                         │ │
│ │ diagrams:                                               │ │
│ │   - $file: docs/diagrams/debug-flow.txt                 │ │
│ │     $refs:                                              │ │
│ │       - helix.debug.stream_parser.StreamParser          │ │
│ │       - helix.debug.tool_tracker.ToolTracker            │ │
│ │     # ↑ Wenn $ref entfernt → Diagramm muss aktualisiert │ │
│ │                                                         │ │
│ │ workflows:                                              │ │
│ │   - id: start_debug                                     │ │
│ │     steps:                                              │ │
│ │       - action: "Parse events"                          │ │
│ │         $uses: helix.debug.StreamParser.parse_stream    │ │
│ │         # ↑ Validierbar!                                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ → Mix aus Auto-Extracted + Manuell, alles validierbar       │
└─────────────────────────────────────────────────────────────┘
                        ↓ kompiliert via docs_compiler
┌─────────────────────────────────────────────────────────────┐
│ SCHICHT 3: GENERIERTE DOCS (für Claude Agents)              │
│                                                             │
│ skills/helix/SKILL.md, CLAUDE.md                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ## StreamParser                                         │ │
│ │                                                         │ │
│ │ *Location: src/helix/debug/stream_parser.py:45*         │ │
│ │                                                         │ │
│ │ Parses NDJSON events from Claude CLI.                   │ │
│ │                                                         │ │
│ │ **When to use:** Real-time CLI output processing        │ │
│ │                                                         │ │
│ │ **Methods:**                                            │ │
│ │ - `parse_line(line: str) -> Event`                      │ │
│ │ - `parse_stream(stream) -> Iterator[Event]`             │ │
│ │                                                         │ │
│ │ **Example:**                                            │ │
│ │ ```python                                               │ │
│ │ parser = StreamParser()                                 │ │
│ │ for event in parser.parse_stream(stdin):                │ │
│ │     print(event)                                        │ │
│ │ ```                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ → Fertige Doku, garantiert konsistent mit Code              │
└─────────────────────────────────────────────────────────────┘
```

---

## Spezifikation

### 1. YAML Schema: helix-docs/v1

#### 1.1 Referenz-Syntax

```yaml
# Modul/Klassen-Referenz (vollständig)
$ref: helix.debug.stream_parser.StreamParser

# Methoden-Referenz
$uses: helix.debug.StreamParser.parse_line

# Datei-Referenz
$file: docs/diagrams/debug-flow.txt

# Script-Referenz
$calls: scripts/claude-wrapper.sh

# Optionale Referenz (Warning statt Error wenn nicht gefunden)
$ref?: helix.debug.optional_module.OptionalClass
```

#### 1.2 Auto-Extracted Fields

Bei `$ref` werden automatisch extrahiert:

```yaml
modules:
  - $ref: helix.debug.stream_parser.StreamParser
    # ↓ AUTO-GENERATED (nicht manuell editieren) ↓
    _auto:
      name: "StreamParser"
      module: "helix.debug.stream_parser"
      file: "src/helix/debug/stream_parser.py"
      line: 45
      docstring: "Parses NDJSON events from Claude CLI stdout."
      docstring_short: "Parses NDJSON events from Claude CLI."
      methods:
        - name: "__init__"
          signature: "(self) -> None"
          line: 50
        - name: "parse_line"
          signature: "(self, line: str) -> Event"
          docstring: "Parse a single NDJSON line."
          line: 67
        - name: "parse_stream"
          signature: "(self, stream: IO) -> Iterator[Event]"
          docstring: "Parse a stream of NDJSON lines."
          line: 89
      class_attributes:
        - name: "EVENT_TYPES"
          type: "list[str]"
    # ↑ AUTO-GENERATED ↑
    
    # ↓ MANUELL (editierbar) ↓
    when_to_use: "Real-time CLI output processing"
    pitfalls:
      - "Handle partial lines"
    best_practices:
      - "Use parse_stream for continuous processing"
```

#### 1.3 Diagram Referenzen

```yaml
diagrams:
  - id: debug_data_flow
    title: "Debug System Data Flow"
    $file: docs/diagrams/debug-flow.txt
    
    # Symbole die im Diagramm vorkommen MÜSSEN
    $refs:
      - helix.debug.stream_parser.StreamParser
      - helix.debug.tool_tracker.ToolTracker
      - helix.debug.cost_calculator.CostCalculator
    
    # Optional: Beschreibung der Verbindungen
    connections:
      - from: StreamParser
        to: ToolTracker
        label: "parsed events"
      - from: ToolTracker
        to: CostCalculator
        label: "tool usage"
```

#### 1.4 Workflow Referenzen

```yaml
workflows:
  - id: start_debug_session
    title: "Debug Session starten"
    description: "Vollständiger Workflow für Debug-Session"
    
    steps:
      - id: 1
        action: "Start wrapper script"
        $calls: scripts/claude-wrapper.sh
        args: ["--debug", "--output-format", "ndjson"]
        
      - id: 2
        action: "Initialize parser"
        $uses: helix.debug.StreamParser.__init__
        
      - id: 3
        action: "Parse event stream"
        $uses: helix.debug.StreamParser.parse_stream
        input: "stdout from step 1"
        output: "Iterator[Event]"
        
      - id: 4
        action: "Track tool calls"
        $uses: helix.debug.ToolTracker.track
        input: "events from step 3"
        
      - id: 5
        action: "Display dashboard"
        $uses: helix.debug.LiveDashboard.render
        condition: "if --live flag set"
```

### 2. Reference Resolver

```python
# src/helix/docs/reference_resolver.py

@dataclass
class ResolvedReference:
    """A resolved symbol reference."""
    ref: str                      # Original reference string
    exists: bool                  # Whether symbol exists
    kind: str                     # "module", "class", "method", "function", "file"
    file: Path | None             # Source file path
    line: int | None              # Line number in source
    docstring: str | None         # Extracted docstring
    signature: str | None         # For methods/functions
    children: list[str] | None    # For classes: method names
    error: str | None             # Error message if not found

class ReferenceResolver:
    """Resolves $ref references to actual code symbols."""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.extractor = SymbolExtractor(project_root)
        self._cache: dict[str, ResolvedReference] = {}
    
    def resolve(self, ref: str) -> ResolvedReference:
        """Resolve a reference like 'helix.debug.StreamParser.parse_line'."""
        if ref in self._cache:
            return self._cache[ref]
        
        # Parse reference
        parts = ref.split(".")
        
        # Try as module.class.method
        if len(parts) >= 3:
            module = ".".join(parts[:-2])
            class_name = parts[-2]
            member = parts[-1]
            result = self._resolve_member(module, class_name, member)
        elif len(parts) >= 2:
            # Could be module.class or module.function
            module = ".".join(parts[:-1])
            symbol = parts[-1]
            result = self._resolve_symbol(module, symbol)
        else:
            # Just a module
            result = self._resolve_module(ref)
        
        self._cache[ref] = result
        return result
    
    def resolve_file(self, path: str) -> ResolvedReference:
        """Resolve a $file reference."""
        full_path = self.root / path
        return ResolvedReference(
            ref=path,
            exists=full_path.exists(),
            kind="file",
            file=full_path if full_path.exists() else None,
            line=None,
            docstring=None,
            signature=None,
            children=None,
            error=None if full_path.exists() else f"File not found: {path}"
        )
    
    def validate_all(self, yaml_data: dict) -> list[ValidationIssue]:
        """Validate all references in a YAML document."""
        issues = []
        
        for ref in self._find_refs(yaml_data):
            resolved = self.resolve(ref.value)
            if not resolved.exists:
                issues.append(ValidationIssue(
                    severity="error" if not ref.optional else "warning",
                    path=ref.yaml_path,
                    ref=ref.value,
                    message=resolved.error or f"Symbol not found: {ref.value}"
                ))
        
        return issues
```

### 3. Symbol Extractor

```python
# src/helix/docs/symbol_extractor.py

@dataclass
class ExtractedSymbol:
    """Information extracted from a code symbol."""
    name: str
    kind: str  # "class", "function", "method", "module"
    file: Path
    line: int
    docstring: str | None
    signature: str | None
    children: list["ExtractedSymbol"]
    decorators: list[str]
    bases: list[str]  # For classes: base class names

class SymbolExtractor:
    """Extracts symbol information from Python source files."""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.src_root = project_root / "src"
    
    def extract_module(self, module_path: str) -> ExtractedSymbol | None:
        """Extract all symbols from a module."""
        file_path = self._module_to_path(module_path)
        if not file_path or not file_path.exists():
            return None
        
        with open(file_path) as f:
            tree = ast.parse(f.read())
        
        return self._extract_from_ast(tree, file_path, module_path)
    
    def extract_class(self, module: str, class_name: str) -> ExtractedSymbol | None:
        """Extract a specific class from a module."""
        module_info = self.extract_module(module)
        if not module_info:
            return None
        
        for child in module_info.children:
            if child.name == class_name and child.kind == "class":
                return child
        return None
    
    def extract_method(self, module: str, class_name: str, method: str) -> ExtractedSymbol | None:
        """Extract a specific method from a class."""
        class_info = self.extract_class(module, class_name)
        if not class_info:
            return None
        
        for child in class_info.children:
            if child.name == method:
                return child
        return None
    
    def _extract_from_ast(self, tree: ast.AST, file: Path, module: str) -> ExtractedSymbol:
        """Extract symbols from AST."""
        children = []
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                children.append(self._extract_class(node, file))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                children.append(self._extract_function(node, file))
        
        return ExtractedSymbol(
            name=module.split(".")[-1],
            kind="module",
            file=file,
            line=1,
            docstring=ast.get_docstring(tree),
            signature=None,
            children=children,
            decorators=[],
            bases=[]
        )
    
    def _extract_class(self, node: ast.ClassDef, file: Path) -> ExtractedSymbol:
        """Extract class information."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                methods.append(self._extract_function(item, file))
        
        return ExtractedSymbol(
            name=node.name,
            kind="class",
            file=file,
            line=node.lineno,
            docstring=ast.get_docstring(node),
            signature=None,
            children=methods,
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            bases=[self._base_name(b) for b in node.bases]
        )
    
    def _extract_function(self, node: ast.FunctionDef, file: Path) -> ExtractedSymbol:
        """Extract function/method information."""
        return ExtractedSymbol(
            name=node.name,
            kind="method" if self._is_method(node) else "function",
            file=file,
            line=node.lineno,
            docstring=ast.get_docstring(node),
            signature=self._get_signature(node),
            children=[],
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            bases=[]
        )
    
    def _get_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        sig = f"({', '.join(args)})"
        if node.returns:
            sig += f" -> {ast.unparse(node.returns)}"
        return sig
```

### 4. Diagram Validator

```python
# src/helix/docs/diagram_validator.py

@dataclass
class DiagramValidation:
    """Result of validating a diagram."""
    diagram_id: str
    file: Path
    valid: bool
    referenced_symbols: list[str]
    missing_symbols: list[str]
    extra_symbols: list[str]  # In diagram but not in $refs
    warnings: list[str]

class DiagramValidator:
    """Validates diagrams against their $refs declarations."""
    
    def __init__(self, resolver: ReferenceResolver):
        self.resolver = resolver
    
    def validate(self, diagram_config: dict) -> DiagramValidation:
        """Validate a diagram configuration."""
        diagram_id = diagram_config.get("id", "unknown")
        file_ref = diagram_config.get("$file")
        declared_refs = diagram_config.get("$refs", [])
        
        # Check file exists
        file_resolved = self.resolver.resolve_file(file_ref)
        if not file_resolved.exists:
            return DiagramValidation(
                diagram_id=diagram_id,
                file=Path(file_ref),
                valid=False,
                referenced_symbols=declared_refs,
                missing_symbols=[],
                extra_symbols=[],
                warnings=[f"Diagram file not found: {file_ref}"]
            )
        
        # Check all declared refs exist
        missing = []
        for ref in declared_refs:
            resolved = self.resolver.resolve(ref)
            if not resolved.exists:
                missing.append(ref)
        
        # Optionally: Parse diagram to find symbols mentioned
        # (This would require diagram-specific parsing)
        
        return DiagramValidation(
            diagram_id=diagram_id,
            file=file_resolved.file,
            valid=len(missing) == 0,
            referenced_symbols=declared_refs,
            missing_symbols=missing,
            extra_symbols=[],
            warnings=[]
        )
```

### 5. Quality Gate: docs_refs_valid

```python
# src/helix/quality_gates/docs_refs_valid.py

class DocsRefsValidGate:
    """Quality gate that validates all documentation references."""
    
    name = "docs_refs_valid"
    description = "Validates that all $ref in docs/sources/*.yaml point to existing symbols"
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.resolver = ReferenceResolver(project_root)
        self.diagram_validator = DiagramValidator(self.resolver)
    
    async def check(self, strict: bool = False) -> GateResult:
        """Run the validation."""
        sources_dir = self.root / "docs" / "sources"
        all_issues: list[ValidationIssue] = []
        
        for yaml_file in sources_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            
            # Validate references
            issues = self.resolver.validate_all(data)
            for issue in issues:
                issue.file = yaml_file
            all_issues.extend(issues)
            
            # Validate diagrams
            for diagram in data.get("diagrams", []):
                result = self.diagram_validator.validate(diagram)
                if not result.valid:
                    for symbol in result.missing_symbols:
                        all_issues.append(ValidationIssue(
                            severity="error",
                            file=yaml_file,
                            path=f"diagrams.{result.diagram_id}.$refs",
                            ref=symbol,
                            message=f"Diagram references non-existent symbol: {symbol}"
                        ))
        
        errors = [i for i in all_issues if i.severity == "error"]
        warnings = [i for i in all_issues if i.severity == "warning"]
        
        if errors:
            return GateResult(
                passed=False,
                message=f"Found {len(errors)} broken references",
                details={
                    "errors": [asdict(e) for e in errors],
                    "warnings": [asdict(w) for w in warnings]
                }
            )
        
        if warnings and strict:
            return GateResult(
                passed=False,
                message=f"Found {len(warnings)} warnings (strict mode)",
                details={"warnings": [asdict(w) for w in warnings]}
            )
        
        return GateResult(
            passed=True,
            message=f"All references valid ({len(warnings)} warnings)",
            details={"warnings": [asdict(w) for w in warnings]} if warnings else {}
        )
```

### 6. Enhanced Docs Compiler

```python
# Updates to src/helix/tools/docs_compiler.py

class DocsCompiler:
    """Enhanced compiler with reference resolution."""
    
    def compile(self, validate: bool = True, strict: bool = False) -> CompileResult:
        """Compile documentation from sources."""
        
        if validate:
            # Phase 1: Validate all references
            gate = DocsRefsValidGate(self.root)
            result = gate.check(strict=strict)
            if not result.passed:
                return CompileResult(
                    success=False,
                    message="Reference validation failed",
                    errors=result.details.get("errors", [])
                )
        
        # Phase 2: Resolve and enrich references
        for yaml_file in self.sources_dir.glob("*.yaml"):
            data = self._load_and_resolve(yaml_file)
            self._resolved_sources[yaml_file.stem] = data
        
        # Phase 3: Generate outputs
        outputs = self._generate_outputs()
        
        return CompileResult(
            success=True,
            message=f"Generated {len(outputs)} files",
            files=outputs
        )
    
    def _load_and_resolve(self, yaml_file: Path) -> dict:
        """Load YAML and resolve all $ref to actual data."""
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        
        return self._resolve_refs_recursive(data)
    
    def _resolve_refs_recursive(self, obj: Any) -> Any:
        """Recursively resolve $ref in data structure."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                # Resolve and merge
                resolved = self.resolver.resolve(obj["$ref"])
                auto_data = {
                    "_auto": {
                        "name": resolved.name,
                        "module": resolved.module,
                        "file": str(resolved.file),
                        "line": resolved.line,
                        "docstring": resolved.docstring,
                        "docstring_short": self._first_line(resolved.docstring),
                        "methods": [
                            {
                                "name": m.name,
                                "signature": m.signature,
                                "docstring": m.docstring,
                                "line": m.line
                            }
                            for m in resolved.children
                            if m.kind == "method"
                        ]
                    }
                }
                # Merge auto with manual fields
                return {**auto_data, **{k: v for k, v in obj.items() if k != "$ref"}}
            else:
                return {k: self._resolve_refs_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_refs_recursive(item) for item in obj]
        else:
            return obj
```

### 7. Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit (extended)

# ... existing checks ...

# Documentation Reference Validation
echo "[docs] Validating documentation references..."

# Check if any docs/sources/*.yaml changed
YAML_CHANGED=$(git diff --cached --name-only | grep "^docs/sources/.*\.yaml$")

# Check if any src/helix/**/*.py changed
CODE_CHANGED=$(git diff --cached --name-only | grep "^src/helix/.*\.py$")

if [ -n "$CODE_CHANGED" ]; then
    echo "[docs] Code changed - validating documentation references..."
    
    # Run reference validator
    PYTHONPATH=src python3 -c "
from helix.quality_gates.docs_refs_valid import DocsRefsValidGate
from pathlib import Path
import asyncio

gate = DocsRefsValidGate(Path('.'))
result = asyncio.run(gate.check(strict=False))

if not result.passed:
    print()
    print('❌ BROKEN DOCUMENTATION REFERENCES:')
    print()
    for error in result.details.get('errors', []):
        print(f\"  {error['file']}:{error['path']}\")
        print(f\"    → {error['message']}\")
        print()
    print('Please update docs/sources/*.yaml to match code changes.')
    exit(1)

warnings = result.details.get('warnings', [])
if warnings:
    print()
    print(f'⚠️  {len(warnings)} documentation warnings (non-blocking):')
    for w in warnings[:5]:
        print(f\"  {w['file']}: {w['message']}\")
    if len(warnings) > 5:
        print(f'  ... and {len(warnings) - 5} more')
    print()

print('✅ Documentation references valid')
"
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "⛔ Commit blocked: Fix documentation references first"
        echo "   Run: python -m helix.tools.docs_compiler validate"
        exit 1
    fi
fi

# ... continue with other checks ...
```

---

## CLI Interface

```bash
# Validate all references
python -m helix.tools.docs_compiler validate
python -m helix.tools.docs_compiler validate --strict  # Warnings = errors

# Compile with validation
python -m helix.tools.docs_compiler compile
python -m helix.tools.docs_compiler compile --skip-validation

# Extract symbols from module (for creating new YAML)
python -m helix.tools.docs_compiler extract helix.debug.stream_parser
# Output:
# modules:
#   - $ref: helix.debug.stream_parser.StreamParser
#     # TODO: Add manual fields (when_to_use, pitfalls, examples)

# Show what would change
python -m helix.tools.docs_compiler diff

# Migrate old YAML to new schema
python -m helix.tools.docs_compiler migrate docs/sources/debug.yaml
```

---

## Migration Strategy

### Phase 1: Add Schema Support (Backward Compatible)

1. Implement ReferenceResolver and SymbolExtractor
2. Add `_meta.schema: helix-docs/v1` detection
3. Old YAML files continue to work
4. New files can use `$ref` syntax

### Phase 2: Add Validation Gate

1. Implement DocsRefsValidGate
2. Add as optional gate in config
3. Run in CI but don't block

### Phase 3: Migrate Existing YAML

1. Run `docs_compiler migrate` on each file
2. Review and add manual fields
3. Enable blocking validation

### Phase 4: Full Enforcement

1. Pre-commit hook blocks on errors
2. CI fails on broken refs
3. Documentation phase requires valid refs

---

## Akzeptanzkriterien

### Must Have
- [ ] `$ref` syntax resolves to actual code symbols
- [ ] Validation detects non-existent modules/classes/methods
- [ ] `$file` validates file existence
- [ ] `$uses` in workflows validates method existence
- [ ] Auto-extraction of docstrings and signatures
- [ ] Quality Gate: docs_refs_valid
- [ ] Pre-commit hook warns on broken refs
- [ ] CLI: validate, compile, extract commands

### Should Have
- [ ] `$diagram_refs` validates symbols in diagrams
- [ ] Workflow step validation
- [ ] Migration tool for existing YAML
- [ ] Diff command to show what would change
- [ ] Caching for performance

### Nice to Have
- [ ] LSP integration for better resolution
- [ ] IDE support (VS Code extension)
- [ ] Auto-fix suggestions
- [ ] Diagram content parsing (detect symbols in ASCII art)

---

## Konsequenzen

### Vorteile

1. **Keine veraltete Dokumentation**: Referenzen werden validiert
2. **Refactoring-Safe**: Umbenennung bricht Docs → wird erkannt
3. **Single Source of Truth**: Docstrings sind die Wahrheit
4. **Weniger manuelle Arbeit**: Auto-Extraction von Signaturen
5. **Bessere Docs**: Kombination aus Auto + Manual

### Nachteile

1. **Komplexität**: Neues System zu lernen
2. **Migration**: Bestehende YAML müssen angepasst werden
3. **Build-Zeit**: Validation braucht Zeit

### Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| False Positives | Mittel | `$ref?` für optionale Refs |
| Performance | Niedrig | Caching, inkrementelle Validierung |
| Adoption | Mittel | Gute Doku, Migration-Tools |

---

## Referenzen

- ADR-014: Documentation Architecture
- ADR-018: LSP Integration
- [TypeScript Type System](https://www.typescriptlang.org/) - Inspiration für typisierte Referenzen
- [Sphinx autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html) - Auto-extraction Konzept
- [OpenAPI $ref](https://swagger.io/docs/specification/using-ref/) - Reference-Syntax Inspiration

---

## Changelog

- 2024-12-24: Initial MaxVP specification
