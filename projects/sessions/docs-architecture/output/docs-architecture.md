# HELIX Dokumentations-Architektur: Konzept für Redundanzfreiheit

> **Meta-Consultant Analyse**
>
> Erstellt: 2025-12-23

---

## Executive Summary

Dieses Konzept beschreibt eine **generierungsbasierte Dokumentationsarchitektur** für HELIX v4.
Die Kernidee: **Eine Quelle, viele Ausgaben**.

| Problem | Lösung |
|---------|--------|
| Quality Gates in 137 Dateien dokumentiert | Eine Source-Datei, Rest generiert |
| 14+ Stellen manuell synchronisieren | Automatische Kompilierung |
| Inkonsistenz bei Updates garantiert | Single Source of Truth |

---

## 1. Architektur-Entscheidung

### Bewertung der Optionen

| Option | Vorteile | Nachteile | Bewertung |
|--------|----------|-----------|-----------|
| **A: Sync-Tool** | Erhält bestehende Struktur | Merge-Konflikte, Komplexität, fehleranfällig | ⭐⭐ |
| **B: Generierung** | Garantierte Konsistenz, einmalige Pflege | Initialer Migrationsaufwand, Build-Step nötig | ⭐⭐⭐⭐ |
| **C: Hybrid** | Flexibel, schrittweise Migration möglich | Zwei Systeme zu verstehen, verwirrend | ⭐⭐⭐ |

### Entscheidung: **Option B - Generierungsbasiert**

**Begründung:**

1. **Deterministisch**: Gleiche Quelle → Gleiche Ausgabe
2. **Atomic Updates**: Eine Änderung = Alle Stellen konsistent
3. **Validierbar**: Build-Fehler zeigen Inkonsistenzen sofort
4. **HELIX-Native**: Passt zum Phasen-Konzept (Quality Gate: `docs_compiled`)

---

## 2. Source of Truth Definition

### 2.1 Zwei-Quellen-Modell

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PRIMARY SOURCES (manuell gepflegt)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. DOCSTRINGS im Code                                                   │
│     → API-Referenz, Parameter, Beispiele                                │
│     → src/helix/**/*.py                                                 │
│                                                                          │
│  2. DEFINITIONS in YAML                                                  │
│     → Feature-Definitionen, Konfigurationsschema                        │
│     → docs/sources/*.yaml                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ docs compile
┌─────────────────────────────────────────────────────────────────────────┐
│  GENERATED OUTPUTS (automatisch erstellt)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  - CLAUDE.md (Root)           ← Aggregiert aus Sources                  │
│  - skills/*/SKILL.md          ← Generiert aus Definitions + Docstrings  │
│  - docs/ARCHITECTURE-*.md     ← Generiert aus Code + Definitions        │
│  - adr/INDEX.md               ← Generiert aus adr/*.md Header           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Warum dieses Modell?

| Alternative | Problem |
|-------------|---------|
| **a) Nur Docstrings** | Strukturierte Metadaten fehlen (Gate-Typen, Konfiguration) |
| **b) Nur YAML-Files** | Code-Beispiele veralten, Typen unsynchron |
| **c) ADRs als Source** | ADRs sind historisch, nicht operativ |
| **d) Skills als Source** | Skills sind zu hoch-level, keine Schema-Validierung |

**Zwei Quellen sind optimal:**
- **Docstrings** = nahe am Code, validiert durch Python-Typsystem
- **YAML-Definitions** = strukturiert, validierbar, schema-basiert

---

## 3. Source-Datei-Struktur

### 3.1 Verzeichnisstruktur

```
docs/
├── sources/                          # PRIMARY SOURCES
│   ├── quality-gates.yaml            # Quality Gate Definitionen
│   ├── phase-types.yaml              # Phasen-Typen
│   ├── escalation.yaml               # Escalation-System
│   ├── evolution.yaml                # Self-Evolution
│   └── domains.yaml                  # Domain-Experten
│
├── templates/                        # Jinja2 Templates
│   ├── CLAUDE.md.j2                  # → CLAUDE.md
│   ├── SKILL.md.j2                   # → skills/*/SKILL.md
│   ├── ARCHITECTURE-MODULES.md.j2    # → docs/ARCHITECTURE-MODULES.md
│   └── partials/
│       ├── quality-gates-table.md.j2
│       ├── quality-gates-detail.md.j2
│       └── code-example.md.j2
│
└── generated/                        # Marker-Verzeichnis
    └── .gitkeep                      # (generierte Files leben woanders)
```

### 3.2 Source-Datei Format

**Beispiel: `docs/sources/quality-gates.yaml`**

```yaml
# docs/sources/quality-gates.yaml
# PRIMARY SOURCE für alle Quality Gate Dokumentation

_meta:
  version: "1.0"
  description: "Quality Gate Definitions für HELIX v4"
  generated_outputs:
    - CLAUDE.md
    - skills/helix/SKILL.md
    - docs/ARCHITECTURE-MODULES.md

gates:
  - id: files_exist
    name: "Files Exist"
    description: "Prüft ob alle erwarteten Output-Dateien existiert"
    category: deterministic
    phase_usage: [development, documentation]

    params:
      - name: required_files
        type: list[str]
        required: true
        description: "Liste der erwarteten Dateipfade"

    example:
      yaml: |
        quality_gate:
          type: files_exist
          required_files:
            - output/result.md
            - output/schema.py

      explanation: "Prüft dass beide Dateien nach der Phase existieren"

    implementation:
      module: helix.quality_gates
      class: QualityGateRunner
      method: check_files_exist

  - id: syntax_check
    name: "Syntax Check"
    description: "Validiert Python/TypeScript Syntax"
    category: deterministic
    phase_usage: [development]

    params:
      - name: file_patterns
        type: list[str]
        required: false
        default: ["**/*.py"]
        description: "Glob-Patterns für zu prüfende Dateien"

    example:
      yaml: |
        quality_gate:
          type: syntax_check
          file_patterns:
            - "src/**/*.py"
            - "tests/**/*.py"

    implementation:
      module: helix.quality_gates
      class: QualityGateRunner
      method: check_syntax

  - id: tests_pass
    name: "Tests Pass"
    description: "Führt pytest/jest aus und prüft Erfolg"
    category: deterministic
    phase_usage: [testing]

    params:
      - name: test_command
        type: str
        required: false
        default: "pytest"
        description: "Auszuführender Test-Befehl"
      - name: working_dir
        type: str
        required: false
        description: "Arbeitsverzeichnis für Tests"

    example:
      yaml: |
        quality_gate:
          type: tests_pass
          test_command: "pytest -v"

    implementation:
      module: helix.quality_gates
      class: QualityGateRunner
      method: check_tests_pass

  - id: review_approved
    name: "Review Approved"
    description: "LLM-Review des Outputs"
    category: llm_based
    phase_usage: [review]

    params:
      - name: review_type
        type: str
        required: true
        enum: [code, architecture, documentation]
        description: "Art des Reviews"
      - name: criteria
        type: list[str]
        required: false
        description: "Zusätzliche Review-Kriterien"

    example:
      yaml: |
        quality_gate:
          type: review_approved
          review_type: code
          criteria:
            - "Keine hardcodierten Credentials"
            - "Type Hints vorhanden"

    implementation:
      module: helix.quality_gates
      class: QualityGateRunner
      method: check_review_approved

  - id: adr_valid
    name: "ADR Valid"
    description: "Validiert ADR-Dokumente gegen Template"
    category: deterministic
    phase_usage: [consultant, review]

    params:
      - name: file
        type: str
        required: true
        description: "Pfad zur ADR-Datei"

    example:
      yaml: |
        quality_gate:
          type: adr_valid
          file: output/feature-adr.md

    validation_checks:
      errors:
        - "YAML Frontmatter vorhanden"
        - "Pflichtfelder: adr_id, title, status"
        - "Pflicht-Sections: Kontext, Entscheidung, Implementation, etc."
        - "Mindestens ein Akzeptanzkriterium"
      warnings:
        - "Empfohlene Felder: component_type, classification"
        - "Weniger als 3 Akzeptanzkriterien"

    implementation:
      module: helix.adr.gate
      class: ADRQualityGate
      method: check

    see_also:
      - docs/ADR-TEMPLATE.md
      - skills/helix/adr/SKILL.md
```

---

## 4. Kompilier-Prozess

### 4.1 Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│  COMPILE PIPELINE                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. COLLECT SOURCES                                                      │
│     ├── docs/sources/*.yaml         → Load YAML definitions              │
│     ├── src/helix/**/*.py           → Extract docstrings (AST)          │
│     └── adr/*.md                    → Parse ADR headers                  │
│                                                                          │
│  2. BUILD CONTEXT                                                        │
│     └── Merge all sources into unified context dict                     │
│                                                                          │
│  3. RENDER TEMPLATES                                                     │
│     ├── CLAUDE.md.j2                → CLAUDE.md                          │
│     ├── SKILL.md.j2                 → skills/helix/SKILL.md             │
│     └── ARCHITECTURE-MODULES.md.j2  → docs/ARCHITECTURE-MODULES.md      │
│                                                                          │
│  4. VALIDATE                                                             │
│     ├── Markdown link validation                                         │
│     ├── Token budget check                                               │
│     └── Cross-reference consistency                                      │
│                                                                          │
│  5. WRITE                                                                │
│     └── Only if validation passes                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Template-Beispiele

**`docs/templates/partials/quality-gates-table.md.j2`**

```jinja2
## Quality Gates

| Gate | Beschreibung | Kategorie | Verwendung |
|------|--------------|-----------|------------|
{% for gate in quality_gates.gates %}
| `{{ gate.id }}` | {{ gate.description }} | {{ gate.category }} | {{ gate.phase_usage | join(", ") }} |
{% endfor %}

→ Details: `skills/helix/SKILL.md`
```

**`docs/templates/partials/quality-gates-detail.md.j2`**

```jinja2
## Quality Gates

{% for gate in quality_gates.gates %}
### {{ gate.name }} (`{{ gate.id }}`)

{{ gate.description }}

**Parameter:**

| Name | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
{% for param in gate.params %}
| `{{ param.name }}` | `{{ param.type }}` | {{ "Ja" if param.required else "Nein" }} | {{ param.description }} |
{% endfor %}

**Beispiel:**

```yaml
{{ gate.example.yaml }}
```

{{ gate.example.explanation if gate.example.explanation else "" }}

{% if gate.see_also %}
**Siehe auch:**
{% for ref in gate.see_also %}
- [{{ ref }}]({{ ref }})
{% endfor %}
{% endif %}

---

{% endfor %}
```

**`docs/templates/CLAUDE.md.j2`**

```jinja2
# HELIX v4 - Claude Code Instruktionen

> Du arbeitest im HELIX v4 Projekt - einem AI Development Orchestration System.

<!-- AUTO-GENERATED: Nicht manuell editieren! -->
<!-- Source: docs/sources/*.yaml -->
<!-- Regenerate: python -m helix.tools.docs compile -->

## Deine Rolle

1. **Consultant** - Meeting mit User → spec.yaml, phases.yaml
2. **Developer** - Implementierung nach Spezifikation
3. **Reviewer** - Code-Review
4. **Documentation** - Technische Dokumentation

## Domain-Wissen laden

| Wenn du... | Lies: |
|------------|-------|
{% for domain in domains.items %}
| {{ domain.trigger }} | `{{ domain.skill_path }}` |
{% endfor %}

## Quality Gates (Übersicht)

{% include 'partials/quality-gates-table.md.j2' %}

## Projekt-Struktur

```
helix-v4/
├── src/helix/        # Python Orchestrator
├── skills/           # Domain-Wissen
├── adr/              # Architektur-Entscheidungen
├── projects/
│   ├── sessions/     # Consultant Sessions
│   └── external/     # Ausführbare Projekte
└── docs/             # Referenz-Dokumentation
```

## Wichtigste Regeln

### DO:
- Lies relevante Skills vor der Arbeit
- Schreibe nach output/
- Dokumentiere was du getan hast

### DON'T:
- Ändere keine Dateien außerhalb deines Verzeichnisses
- Lösche keine existierenden Dateien
- Mache keine Netzwerk-Requests ohne Grund

## Hilfe

- HELIX Konzept: `ONBOARDING.md`
- Architektur: `docs/ARCHITECTURE-MODULES.md`
- ADR Template: `docs/ADR-TEMPLATE.md`
```

### 4.3 Generierte Ausgaben (Beispiele)

**Aus Source → CLAUDE.md (Auszug):**

```markdown
## Quality Gates (Übersicht)

| Gate | Beschreibung | Kategorie | Verwendung |
|------|--------------|-----------|------------|
| `files_exist` | Prüft ob alle erwarteten Output-Dateien existiert | deterministic | development, documentation |
| `syntax_check` | Validiert Python/TypeScript Syntax | deterministic | development |
| `tests_pass` | Führt pytest/jest aus und prüft Erfolg | deterministic | testing |
| `review_approved` | LLM-Review des Outputs | llm_based | review |
| `adr_valid` | Validiert ADR-Dokumente gegen Template | deterministic | consultant, review |

→ Details: `skills/helix/SKILL.md`
```

**Aus Source → skills/helix/SKILL.md (Auszug):**

```markdown
## Quality Gates

### Files Exist (`files_exist`)

Prüft ob alle erwarteten Output-Dateien existiert

**Parameter:**

| Name | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `required_files` | `list[str]` | Ja | Liste der erwarteten Dateipfade |

**Beispiel:**

```yaml
quality_gate:
  type: files_exist
  required_files:
    - output/result.md
    - output/schema.py
```

Prüft dass beide Dateien nach der Phase existieren

---

### ADR Valid (`adr_valid`)

Validiert ADR-Dokumente gegen Template

[... weitere Details aus Source ...]

**Siehe auch:**
- [docs/ADR-TEMPLATE.md](docs/ADR-TEMPLATE.md)
- [skills/helix/adr/SKILL.md](skills/helix/adr/SKILL.md)
```

---

## 5. Tooling-Konzept

### 5.1 CLI-Befehle

```bash
# Dokumentation kompilieren
python -m helix.tools.docs compile

# Nur validieren (ohne zu schreiben)
python -m helix.tools.docs validate

# Sources anzeigen
python -m helix.tools.docs sources

# Diff anzeigen (was würde sich ändern?)
python -m helix.tools.docs diff

# Einzelne Datei kompilieren
python -m helix.tools.docs compile --target CLAUDE.md
```

### 5.2 Tool-Implementation

**`src/helix/tools/docs_compiler.py`**

```python
"""
HELIX Documentation Compiler

Compiles documentation from YAML sources and code docstrings.

Usage:
    python -m helix.tools.docs compile
    python -m helix.tools.docs validate
    python -m helix.tools.docs sources
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Any
import yaml
import ast
from jinja2 import Environment, FileSystemLoader

@dataclass
class CompileResult:
    """Result of a compilation run."""
    success: bool
    files_written: list[Path]
    errors: list[str]
    warnings: list[str]

class DocCompiler:
    """Compiles documentation from sources."""

    def __init__(self, root: Path = None):
        self.root = root or Path(".")
        self.sources_dir = self.root / "docs" / "sources"
        self.templates_dir = self.root / "docs" / "templates"
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def collect_sources(self) -> dict[str, Any]:
        """Collect all source data."""
        context = {}

        # Load YAML sources
        for yaml_file in self.sources_dir.glob("*.yaml"):
            key = yaml_file.stem.replace("-", "_")
            with open(yaml_file) as f:
                context[key] = yaml.safe_load(f)

        # Extract docstrings from code
        context["modules"] = self._extract_docstrings()

        # Parse ADR headers
        context["adrs"] = self._parse_adr_headers()

        return context

    def _extract_docstrings(self) -> list[dict]:
        """Extract module/class/function docstrings from Python code."""
        modules = []
        src_dir = self.root / "src" / "helix"

        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            try:
                tree = ast.parse(py_file.read_text())
                module_doc = ast.get_docstring(tree)

                classes = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                            "methods": [
                                {
                                    "name": m.name,
                                    "docstring": ast.get_docstring(m)
                                }
                                for m in node.body
                                if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
                            ]
                        })

                modules.append({
                    "path": str(py_file.relative_to(self.root)),
                    "docstring": module_doc,
                    "classes": classes
                })
            except SyntaxError:
                pass

        return modules

    def _parse_adr_headers(self) -> list[dict]:
        """Parse ADR YAML headers."""
        from helix.adr import ADRParser

        adrs = []
        adr_dir = self.root / "adr"
        parser = ADRParser()

        for adr_file in adr_dir.glob("*.md"):
            if adr_file.name == "INDEX.md":
                continue
            try:
                adr = parser.parse_file(adr_file)
                adrs.append({
                    "id": adr.metadata.adr_id,
                    "title": adr.metadata.title,
                    "status": adr.metadata.status.value,
                    "path": str(adr_file.relative_to(self.root))
                })
            except Exception:
                pass

        return sorted(adrs, key=lambda x: x["id"])

    def compile(self, targets: list[str] = None) -> CompileResult:
        """Compile documentation from sources."""
        context = self.collect_sources()
        errors = []
        warnings = []
        files_written = []

        # Define output mappings
        outputs = {
            "CLAUDE.md": self.root / "CLAUDE.md",
            "skills/helix/SKILL.md": self.root / "skills" / "helix" / "SKILL.md",
            "docs/ARCHITECTURE-MODULES.md": self.root / "docs" / "ARCHITECTURE-MODULES.md",
        }

        if targets:
            outputs = {k: v for k, v in outputs.items() if k in targets}

        for template_name, output_path in outputs.items():
            template_file = template_name.replace("/", "_") + ".j2"

            try:
                template = self.env.get_template(template_file)
                content = template.render(**context)

                # Add generation header
                header = f"<!-- AUTO-GENERATED from docs/sources/*.yaml -->\n"
                header += f"<!-- Regenerate: python -m helix.tools.docs compile -->\n\n"

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(header + content)
                files_written.append(output_path)

            except Exception as e:
                errors.append(f"Failed to compile {template_name}: {e}")

        return CompileResult(
            success=len(errors) == 0,
            files_written=files_written,
            errors=errors,
            warnings=warnings
        )

    def validate(self) -> CompileResult:
        """Validate without writing."""
        context = self.collect_sources()
        errors = []
        warnings = []

        # Check all templates render
        for template_file in self.templates_dir.glob("*.j2"):
            if template_file.name.startswith("_"):
                continue
            try:
                template = self.env.get_template(template_file.name)
                template.render(**context)
            except Exception as e:
                errors.append(f"Template {template_file.name} failed: {e}")

        # Check token budgets
        claude_md = self.root / "CLAUDE.md"
        if claude_md.exists():
            lines = len(claude_md.read_text().splitlines())
            if lines > 300:
                warnings.append(f"CLAUDE.md has {lines} lines (budget: 300)")

        for skill in self.root.glob("skills/**/SKILL.md"):
            lines = len(skill.read_text().splitlines())
            if lines > 600:
                warnings.append(f"{skill} has {lines} lines (budget: 600)")

        return CompileResult(
            success=len(errors) == 0,
            files_written=[],
            errors=errors,
            warnings=warnings
        )

    def show_sources(self) -> list[Path]:
        """List all source files."""
        sources = list(self.sources_dir.glob("*.yaml"))
        return sources


def main():
    import sys

    compiler = DocCompiler()
    command = sys.argv[1] if len(sys.argv) > 1 else "compile"

    if command == "compile":
        result = compiler.compile()
        for f in result.files_written:
            print(f"Written: {f}")
        for e in result.errors:
            print(f"ERROR: {e}")
        for w in result.warnings:
            print(f"WARNING: {w}")
        sys.exit(0 if result.success else 1)

    elif command == "validate":
        result = compiler.validate()
        for e in result.errors:
            print(f"ERROR: {e}")
        for w in result.warnings:
            print(f"WARNING: {w}")
        print("Validation passed" if result.success else "Validation failed")
        sys.exit(0 if result.success else 1)

    elif command == "sources":
        for source in compiler.show_sources():
            print(source)

    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m helix.tools.docs [compile|validate|sources]")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 5.3 Docstring-Extraktion

```python
"""
Docstring Extractor für automatische API-Dokumentation.

Extrahiert strukturierte Informationen aus Python Docstrings
im Google-Style Format.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FunctionDoc:
    name: str
    docstring: str
    params: list[dict]
    returns: str | None
    raises: list[str]
    examples: list[str]

def parse_google_docstring(docstring: str) -> dict:
    """Parse Google-style docstring into structured data."""
    if not docstring:
        return {}

    result = {
        "summary": "",
        "description": "",
        "params": [],
        "returns": None,
        "raises": [],
        "examples": []
    }

    # First line is summary
    lines = docstring.strip().split("\n")
    result["summary"] = lines[0].strip()

    # Parse sections
    current_section = "description"
    section_content = []

    for line in lines[1:]:
        stripped = line.strip()

        if stripped in ("Args:", "Arguments:", "Parameters:"):
            current_section = "params"
            continue
        elif stripped in ("Returns:", "Return:"):
            current_section = "returns"
            continue
        elif stripped in ("Raises:", "Raise:"):
            current_section = "raises"
            continue
        elif stripped in ("Example:", "Examples:"):
            current_section = "examples"
            continue

        if current_section == "params" and stripped:
            # Parse "name: description" or "name (type): description"
            match = re.match(r"(\w+)(?:\s*\(([^)]+)\))?:\s*(.+)", stripped)
            if match:
                result["params"].append({
                    "name": match.group(1),
                    "type": match.group(2),
                    "description": match.group(3)
                })

        elif current_section == "returns" and stripped:
            result["returns"] = stripped

        elif current_section == "examples":
            section_content.append(line)

    if section_content and current_section == "examples":
        result["examples"] = ["".join(section_content)]

    return result
```

---

## 6. HELIX Integration

### 6.1 Quality Gate: `docs_compiled`

```yaml
# config/quality-gates.yaml

gates:
  docs_compiled:
    description: "Prüft ob generierte Docs aktuell sind"
    implementation: helix.quality_gates.check_docs_compiled
    when: [after_documentation, pre_commit]
```

**Implementation:**

```python
# src/helix/quality_gates.py

def check_docs_compiled(phase_dir: Path, config: dict) -> GateResult:
    """Check if generated docs match sources."""
    from helix.tools.docs_compiler import DocCompiler

    compiler = DocCompiler()
    context = compiler.collect_sources()

    # Check each generated file
    outputs = {
        "CLAUDE.md": Path("CLAUDE.md"),
        "skills/helix/SKILL.md": Path("skills/helix/SKILL.md"),
    }

    mismatches = []

    for template_name, output_path in outputs.items():
        if not output_path.exists():
            mismatches.append(f"{output_path} does not exist")
            continue

        # Render template
        template = compiler.env.get_template(template_name.replace("/", "_") + ".j2")
        expected = template.render(**context)
        actual = output_path.read_text()

        # Skip header comparison
        actual_body = "\n".join(actual.split("\n")[3:])  # Skip header

        if expected.strip() != actual_body.strip():
            mismatches.append(f"{output_path} is out of date")

    if mismatches:
        return GateResult(
            passed=False,
            message="Generated docs are out of date",
            details={"mismatches": mismatches}
        )

    return GateResult(passed=True, message="Docs are up to date")
```

### 6.2 Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check if docs sources changed
if git diff --cached --name-only | grep -q "docs/sources/"; then
    echo "Docs sources changed, validating..."

    if ! python -m helix.tools.docs validate; then
        echo "ERROR: Docs validation failed"
        exit 1
    fi

    # Auto-regenerate
    python -m helix.tools.docs compile

    # Stage regenerated files
    git add CLAUDE.md skills/*/SKILL.md docs/ARCHITECTURE-*.md
fi
```

### 6.3 phases.yaml Integration

```yaml
# Beispiel phases.yaml mit Documentation-Phase

phases:
  - id: "5"
    name: Documentation Update
    type: documentation
    description: |
      Update documentation sources and regenerate.

      1. Update docs/sources/*.yaml if feature definitions changed
      2. Ensure docstrings are complete
      3. Run: python -m helix.tools.docs compile

    quality_gate:
      type: docs_compiled

  - id: "6"
    name: Final Review
    type: review
    depends_on: ["5"]
```

### 6.4 CI/CD Integration

```yaml
# .github/workflows/docs.yaml

name: Documentation

on:
  push:
    paths:
      - 'docs/sources/**'
      - 'src/helix/**/*.py'
  pull_request:
    paths:
      - 'docs/sources/**'
      - 'src/helix/**/*.py'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Validate docs
        run: python -m helix.tools.docs validate

      - name: Check docs are current
        run: |
          python -m helix.tools.docs compile
          if ! git diff --exit-code; then
            echo "ERROR: Generated docs are out of date!"
            echo "Run: python -m helix.tools.docs compile"
            exit 1
          fi
```

---

## 7. Migration-Plan

### Phase 1: Infrastruktur (Tag 1-2)

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 1.1 | Erstelle `docs/sources/` Verzeichnis | Basis-Struktur |
| 1.2 | Erstelle `docs/templates/` Verzeichnis | Template-Ordner |
| 1.3 | Implementiere `docs_compiler.py` | Tool funktionsfähig |
| 1.4 | Füge CLI-Entry-Point hinzu | `python -m helix.tools.docs` |

### Phase 2: Quality Gates Migration (Tag 3-4)

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 2.1 | Extrahiere Quality Gates aus CLAUDE.md → `docs/sources/quality-gates.yaml` | Source erstellt |
| 2.2 | Erstelle `quality-gates-table.md.j2` Partial | Tabellen-Template |
| 2.3 | Erstelle `quality-gates-detail.md.j2` Partial | Detail-Template |
| 2.4 | Teste Kompilierung mit Quality Gates | Erste Generierung |

### Phase 3: Weitere Sources (Tag 5-7)

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 3.1 | Erstelle `docs/sources/phase-types.yaml` | Phasen definiert |
| 3.2 | Erstelle `docs/sources/domains.yaml` | Domains definiert |
| 3.3 | Erstelle `docs/sources/escalation.yaml` | Escalation definiert |
| 3.4 | Vervollständige alle Templates | Alle Outputs generierbar |

### Phase 4: Integration (Tag 8-10)

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 4.1 | Implementiere `docs_compiled` Quality Gate | Gate funktioniert |
| 4.2 | Füge Pre-Commit Hook hinzu | Automatische Validierung |
| 4.3 | Füge CI/CD Workflow hinzu | Pipeline-Integration |
| 4.4 | Dokumentiere Migration in ADR | ADR-014 erstellt |

### Phase 5: Cleanup (Tag 11-14)

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 5.1 | Entferne manuell gepflegte Duplikate | Redundanzen weg |
| 5.2 | Aktualisiere CLAUDE.md auf generierte Version | Root-Datei aktuell |
| 5.3 | Aktualisiere alle Skills | Skills aktuell |
| 5.4 | Validiere mit `docs validate` | Alles konsistent |

---

## 8. Beispiel-Implementation: Quality Gates

### 8.1 Vollständige Source-Datei

Die vollständige `docs/sources/quality-gates.yaml` wurde in Kapitel 3.2 gezeigt.

### 8.2 Generierte Ausgaben

**CLAUDE.md (Auszug) - Layer 1:**

```markdown
## Quality Gates (Übersicht)

| Gate | Beschreibung | Verwendung |
|------|--------------|------------|
| `files_exist` | Prüft ob Output-Dateien existieren | development, documentation |
| `syntax_check` | Validiert Python/TypeScript Syntax | development |
| `tests_pass` | Führt pytest/jest aus | testing |
| `review_approved` | LLM-Review des Outputs | review |
| `adr_valid` | Validiert ADR-Dokumente | consultant, review |

→ Details: skills/helix/SKILL.md
```

**skills/helix/SKILL.md (Auszug) - Layer 2:**

```markdown
## Quality Gates

### Files Exist (`files_exist`)

Prüft ob alle erwarteten Output-Dateien existiert.

**Parameter:**

| Name | Typ | Pflicht | Default | Beschreibung |
|------|-----|---------|---------|--------------|
| `required_files` | `list[str]` | Ja | - | Liste der erwarteten Dateipfade |

**Beispiel:**

```yaml
quality_gate:
  type: files_exist
  required_files:
    - output/result.md
    - output/schema.py
```

**Implementation:** `helix.quality_gates.QualityGateRunner.check_files_exist`

---

### ADR Valid (`adr_valid`)

Validiert ADR-Dokumente gegen das Template.

**Parameter:**

| Name | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `file` | `str` | Ja | Pfad zur ADR-Datei |

**Validierungsprüfungen:**

*Fehler (Gate schlägt fehl):*
- YAML Frontmatter vorhanden
- Pflichtfelder: adr_id, title, status
- Pflicht-Sections: Kontext, Entscheidung, Implementation, etc.
- Mindestens ein Akzeptanzkriterium

*Warnungen (Gate besteht):*
- Empfohlene Felder: component_type, classification
- Weniger als 3 Akzeptanzkriterien

**Beispiel:**

```yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

**Siehe auch:**
- [docs/ADR-TEMPLATE.md](../../../docs/ADR-TEMPLATE.md)
- [skills/helix/adr/SKILL.md](adr/SKILL.md)
```

**docs/ARCHITECTURE-MODULES.md (Auszug) - Layer 3:**

```markdown
## Quality Gate System

### Verfügbare Gates

| Gate | Kategorie | Implementation |
|------|-----------|----------------|
| `files_exist` | deterministic | `QualityGateRunner.check_files_exist` |
| `syntax_check` | deterministic | `QualityGateRunner.check_syntax` |
| `tests_pass` | deterministic | `QualityGateRunner.check_tests_pass` |
| `review_approved` | llm_based | `QualityGateRunner.check_review_approved` |
| `adr_valid` | deterministic | `ADRQualityGate.check` |

### Gate Runner

```python
from helix.quality_gates import QualityGateRunner

runner = QualityGateRunner()
result = runner.check(phase_dir, gate_config)

if not result.passed:
    print(result.message)
    print(result.details)
```

### Konfiguration in phases.yaml

```yaml
phases:
  - id: "2"
    name: Implementation
    quality_gate:
      type: files_exist
      required_files:
        - output/main.py
```

Source: `docs/sources/quality-gates.yaml`
```

---

## 9. Zusammenfassung

### Das Problem

- Quality Gates in **137 Dateien** dokumentiert
- **14+ Stellen** manuell zu synchronisieren
- Inkonsistenz bei Updates **garantiert**

### Die Lösung

1. **Generierungsbasierte Architektur** statt Sync-Tool
2. **Zwei Primary Sources**: Docstrings + YAML-Definitionen
3. **Automatische Kompilierung** in alle Ziel-Formate
4. **Quality Gate `docs_compiled`** sichert Konsistenz
5. **Pre-Commit Hook** verhindert veraltete Docs

### Der Gewinn

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Quality Gates dokumentiert in | 137 Dateien | 1 Source + Generierung |
| Update-Aufwand | 14+ Stellen manuell | 1 Stelle, Rest automatisch |
| Konsistenz-Garantie | Keine | 100% (deterministisch) |
| Validierung | Manuell | Automatisch (CI/CD) |

### Nächste Schritte

1. `docs/sources/quality-gates.yaml` erstellen
2. `docs_compiler.py` implementieren
3. Templates erstellen
4. Migration durchführen
5. Pre-Commit Hook aktivieren

---

## 10. Enforcement-Konzept

Das bisherige Konzept beschreibt **was** generiert wird. Dieser Abschnitt definiert **wann** und **wie** Dokumentation enforced wird.

### 10.1 Workflow-Entscheidung: Hybrid-Ansatz

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DOCUMENTATION WORKFLOW (Hybrid)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DEVELOPMENT-PHASE (inline, Pflicht)                                    │
│  ├── Code schreiben                                                      │
│  ├── Docstrings hinzufügen (Google-Style)                               │
│  ├── Type Hints pflegen                                                  │
│  └── Quality Gate: docstrings_complete                                  │
│                                                                          │
│  DOCUMENTATION-PHASE (optional, für neue Features)                      │
│  ├── YAML-Sources erweitern (docs/sources/*.yaml)                       │
│  ├── Templates anpassen falls nötig                                      │
│  ├── Docs kompilieren: python -m helix.tools.docs compile               │
│  └── Quality Gate: docs_compiled                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Begründung für Hybrid:**

| Ansatz | Docstrings | YAML-Sources |
|--------|------------|--------------|
| **Inline (Pflicht)** | ✅ Im gleichen Commit | ❌ Zu detailliert |
| **Separate Phase** | ❌ Veraltet schnell | ✅ Strukturiert |
| **Hybrid** | ✅ Inline | ✅ Separate Phase |

- **Docstrings** sind code-nah → müssen im gleichen Commit sein
- **YAML-Sources** sind Feature-Definitionen → brauchen Überblick

### 10.2 Vollständigkeits-Prüfung

#### Quality Gate: `docstrings_complete`

Prüft dass alle public API-Elemente dokumentiert sind:

```python
# src/helix/quality_gates/docstrings.py

import ast
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CoverageResult:
    """Documentation coverage result."""
    total: int
    documented: int
    missing: list[str]

    @property
    def percentage(self) -> float:
        return (self.documented / self.total * 100) if self.total > 0 else 100.0

def check_docstrings_complete(phase_dir: Path, config: dict) -> GateResult:
    """Check that all public functions/classes have docstrings."""

    patterns = config.get("file_patterns", ["output/**/*.py"])
    min_coverage = config.get("min_coverage", 100)  # Default: 100%

    missing = []
    total = 0
    documented = 0

    for pattern in patterns:
        for py_file in phase_dir.glob(pattern):
            tree = ast.parse(py_file.read_text())

            for node in ast.walk(tree):
                # Check classes
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    total += 1
                    if ast.get_docstring(node):
                        documented += 1
                    else:
                        missing.append(f"{py_file}:{node.lineno} class {node.name}")

                # Check functions
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    total += 1
                    if ast.get_docstring(node):
                        documented += 1
                    else:
                        missing.append(f"{py_file}:{node.lineno} def {node.name}")

    coverage = (documented / total * 100) if total > 0 else 100.0

    if coverage < min_coverage:
        return GateResult(
            passed=False,
            message=f"Docstring coverage {coverage:.1f}% < {min_coverage}%",
            details={
                "coverage": coverage,
                "missing": missing[:10],  # First 10
                "total_missing": len(missing)
            }
        )

    return GateResult(
        passed=True,
        message=f"Docstring coverage: {coverage:.1f}%"
    )
```

**Verwendung in phases.yaml:**

```yaml
phases:
  - id: "2"
    name: Implementation
    type: development
    quality_gate:
      type: docstrings_complete
      file_patterns:
        - "output/**/*.py"
      min_coverage: 100
```

#### Cross-Reference Validierung

Prüft Konsistenz zwischen Code und YAML-Sources:

```python
# src/helix/tools/docs_coverage.py

"""
Documentation Coverage Tool

Prüft:
1. Jede public class/function hat docstring
2. Jede exportierte Funktion ist in YAML dokumentiert
3. Jedes YAML-Feature hat Code-Referenz (nicht verwaist)
4. Keine stale Einträge
"""

from pathlib import Path
import ast
import yaml

def check_cross_references(root: Path) -> list[str]:
    """Check that YAML sources reference existing code."""
    issues = []

    # Load all YAML sources
    sources_dir = root / "docs" / "sources"
    yaml_refs = set()

    for yaml_file in sources_dir.glob("*.yaml"):
        data = yaml.safe_load(yaml_file.read_text())

        # Extract implementation references
        for item in data.get("gates", []) + data.get("features", []):
            impl = item.get("implementation", {})
            if impl.get("module") and impl.get("class"):
                yaml_refs.add(f"{impl['module']}.{impl['class']}")

    # Check each reference exists in code
    for ref in yaml_refs:
        module_path = ref.replace(".", "/").rsplit("/", 1)[0]
        class_name = ref.rsplit(".", 1)[1]

        py_file = root / "src" / f"{module_path}.py"
        if not py_file.exists():
            issues.append(f"YAML references non-existent module: {ref}")
            continue

        tree = ast.parse(py_file.read_text())
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        if class_name not in class_names:
            issues.append(f"YAML references non-existent class: {ref}")

    return issues

def check_undocumented_exports(root: Path) -> list[str]:
    """Find public exports not documented in YAML."""
    issues = []

    # Collect all documented items from YAML
    documented = set()
    sources_dir = root / "docs" / "sources"

    for yaml_file in sources_dir.glob("*.yaml"):
        data = yaml.safe_load(yaml_file.read_text())
        for item in data.get("gates", []) + data.get("features", []):
            if impl := item.get("implementation"):
                documented.add(f"{impl.get('module')}.{impl.get('class')}")

    # Check __init__.py exports
    init_file = root / "src" / "helix" / "__init__.py"
    if init_file.exists():
        tree = ast.parse(init_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant):
                                    export_name = f"helix.{elt.value}"
                                    if export_name not in documented:
                                        issues.append(f"Export not documented: {export_name}")

    return issues
```

### 10.3 Lifecycle-Hooks

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DOCUMENTATION ENFORCEMENT POINTS                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. PRE-COMMIT HOOK (lokal)                                             │
│     └── Prüft: docstrings_complete für geänderte .py Dateien           │
│                                                                          │
│  2. QUALITY GATE IN PHASE (HELIX-gesteuert)                             │
│     ├── Development: docstrings_complete                                │
│     └── Documentation: docs_compiled                                    │
│                                                                          │
│  3. CI/CD PIPELINE (GitHub Actions)                                     │
│     ├── Validate: python -m helix.tools.docs validate                   │
│     ├── Coverage: python -m helix.tools.docs_coverage                   │
│     └── Block Merge: wenn Coverage < 100% oder Docs stale              │
│                                                                          │
│  4. PERIODIC AUDIT (wöchentlich)                                        │
│     ├── Vollständigkeits-Report                                         │
│     ├── Cross-Reference Check                                           │
│     └── Stale Documentation Detection                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

# 1. Check docstrings for changed Python files
CHANGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -n "$CHANGED_PY" ]; then
    echo "Checking docstrings..."

    for file in $CHANGED_PY; do
        # Quick AST check for missing docstrings
        python -c "
import ast
import sys

with open('$file') as f:
    tree = ast.parse(f.read())

missing = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        if not node.name.startswith('_') and not ast.get_docstring(node):
            missing.append(f'{node.lineno}: {node.name}')

if missing:
    print(f'Missing docstrings in $file:')
    for m in missing:
        print(f'  - {m}')
    sys.exit(1)
"
    done
fi

# 2. Check if docs sources changed
if git diff --cached --name-only | grep -q "docs/sources/\|src/helix/"; then
    echo "Checking docs are up to date..."

    python -m helix.tools.docs validate || {
        echo "ERROR: Docs validation failed"
        exit 1
    }

    # Regenerate and check for changes
    python -m helix.tools.docs compile

    if ! git diff --exit-code CLAUDE.md skills/*/SKILL.md docs/ARCHITECTURE-*.md > /dev/null 2>&1; then
        echo "Generated docs are out of date. Adding to commit..."
        git add CLAUDE.md skills/*/SKILL.md docs/ARCHITECTURE-*.md
    fi
fi

echo "Pre-commit checks passed."
```

### 10.4 Tool: docs_coverage.py

```python
#!/usr/bin/env python3
"""
HELIX Documentation Coverage Tool

Analysiert und reported Dokumentations-Vollständigkeit.

Usage:
    python -m helix.tools.docs_coverage           # Full report
    python -m helix.tools.docs_coverage --check   # Exit 1 if incomplete
    python -m helix.tools.docs_coverage --json    # JSON output
"""

import ast
import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Literal

@dataclass
class CoverageItem:
    """A single coverage item."""
    path: str
    line: int
    type: Literal["class", "function", "module"]
    name: str
    has_docstring: bool
    in_yaml: bool

@dataclass
class CoverageReport:
    """Full coverage report."""
    docstring_coverage: float
    yaml_coverage: float
    total_items: int
    documented_items: int
    yaml_documented: int
    missing_docstrings: list[CoverageItem]
    missing_yaml: list[CoverageItem]
    stale_yaml: list[str]  # YAML refs to non-existent code

    @property
    def is_complete(self) -> bool:
        return (
            self.docstring_coverage >= 100 and
            len(self.stale_yaml) == 0
        )

class DocsCoverageChecker:
    """Check documentation coverage."""

    def __init__(self, root: Path = None):
        self.root = root or Path(".")
        self.sources_dir = self.root / "docs" / "sources"
        self.src_dir = self.root / "src" / "helix"

    def collect_yaml_refs(self) -> set[str]:
        """Collect all implementation references from YAML."""
        refs = set()

        if not self.sources_dir.exists():
            return refs

        for yaml_file in self.sources_dir.glob("*.yaml"):
            import yaml
            data = yaml.safe_load(yaml_file.read_text())

            # Recursively find implementation refs
            self._extract_refs(data, refs)

        return refs

    def _extract_refs(self, data, refs: set):
        """Recursively extract implementation references."""
        if isinstance(data, dict):
            if "implementation" in data:
                impl = data["implementation"]
                if isinstance(impl, dict) and impl.get("module"):
                    refs.add(f"{impl['module']}.{impl.get('class', '')}")
            for v in data.values():
                self._extract_refs(v, refs)
        elif isinstance(data, list):
            for item in data:
                self._extract_refs(item, refs)

    def analyze(self) -> CoverageReport:
        """Analyze documentation coverage."""
        yaml_refs = self.collect_yaml_refs()

        items: list[CoverageItem] = []
        stale_yaml: list[str] = []

        # Check all Python files
        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            try:
                tree = ast.parse(py_file.read_text())
                rel_path = str(py_file.relative_to(self.root))
                module_path = str(py_file.relative_to(self.src_dir.parent)).replace("/", ".").replace(".py", "")

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                        full_ref = f"{module_path}.{node.name}"
                        items.append(CoverageItem(
                            path=rel_path,
                            line=node.lineno,
                            type="class",
                            name=node.name,
                            has_docstring=ast.get_docstring(node) is not None,
                            in_yaml=full_ref in yaml_refs
                        ))

                    elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                        items.append(CoverageItem(
                            path=rel_path,
                            line=node.lineno,
                            type="function",
                            name=node.name,
                            has_docstring=ast.get_docstring(node) is not None,
                            in_yaml=False  # Functions usually not in YAML
                        ))
            except SyntaxError:
                pass

        # Check for stale YAML refs
        for ref in yaml_refs:
            parts = ref.rsplit(".", 1)
            if len(parts) == 2:
                module_path, class_name = parts
                py_file = self.root / "src" / module_path.replace(".", "/") + ".py"

                if not py_file.exists():
                    stale_yaml.append(ref)
                else:
                    try:
                        tree = ast.parse(py_file.read_text())
                        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                        if class_name and class_name not in class_names:
                            stale_yaml.append(ref)
                    except SyntaxError:
                        pass

        # Calculate metrics
        total = len(items)
        with_docstrings = sum(1 for i in items if i.has_docstring)
        in_yaml = sum(1 for i in items if i.in_yaml)

        return CoverageReport(
            docstring_coverage=(with_docstrings / total * 100) if total > 0 else 100.0,
            yaml_coverage=(in_yaml / total * 100) if total > 0 else 100.0,
            total_items=total,
            documented_items=with_docstrings,
            yaml_documented=in_yaml,
            missing_docstrings=[i for i in items if not i.has_docstring],
            missing_yaml=[i for i in items if not i.in_yaml and i.type == "class"],
            stale_yaml=stale_yaml
        )

    def print_report(self, report: CoverageReport):
        """Print human-readable report."""
        print("=" * 60)
        print("HELIX Documentation Coverage Report")
        print("=" * 60)
        print()
        print(f"Docstring Coverage:  {report.docstring_coverage:.1f}% ({report.documented_items}/{report.total_items})")
        print(f"YAML Coverage:       {report.yaml_coverage:.1f}% ({report.yaml_documented}/{report.total_items})")
        print()

        if report.missing_docstrings:
            print("Missing Docstrings:")
            for item in report.missing_docstrings[:20]:
                print(f"  - {item.path}:{item.line} {item.type} {item.name}")
            if len(report.missing_docstrings) > 20:
                print(f"  ... and {len(report.missing_docstrings) - 20} more")
            print()

        if report.stale_yaml:
            print("Stale YAML References (code removed but YAML entry remains):")
            for ref in report.stale_yaml:
                print(f"  - {ref}")
            print()

        if report.is_complete:
            print("✓ Documentation is complete!")
        else:
            print("✗ Documentation is incomplete")

        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="HELIX Documentation Coverage")
    parser.add_argument("--check", action="store_true", help="Exit 1 if incomplete")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    checker = DocsCoverageChecker()
    report = checker.analyze()

    if args.json:
        # Convert to JSON-serializable format
        data = {
            "docstring_coverage": report.docstring_coverage,
            "yaml_coverage": report.yaml_coverage,
            "total_items": report.total_items,
            "documented_items": report.documented_items,
            "is_complete": report.is_complete,
            "missing_docstrings": [asdict(i) for i in report.missing_docstrings],
            "stale_yaml": report.stale_yaml
        }
        print(json.dumps(data, indent=2))
    else:
        checker.print_report(report)

    if args.check and not report.is_complete:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 10.5 Integration in HELIX Phasen

```yaml
# Beispiel: Evolution Project mit Enforcement

phases:
  - id: "1"
    name: Consultant
    type: consultant
    description: ADR erstellen
    quality_gate:
      type: adr_valid
      file: output/feature-adr.md

  - id: "2"
    name: Implementation
    type: development
    description: |
      Code implementieren mit vollständigen Docstrings.

      Jede public class/function MUSS einen Docstring haben:
      - Summary (erste Zeile)
      - Args: Parameter beschreiben
      - Returns: Rückgabewert beschreiben
      - Raises: Exceptions dokumentieren

    quality_gate:
      type: composite
      gates:
        - type: files_exist
          required_files:
            - output/feature.py
        - type: syntax_check
          file_patterns:
            - "output/**/*.py"
        - type: docstrings_complete
          file_patterns:
            - "output/**/*.py"
          min_coverage: 100

  - id: "3"
    name: Testing
    type: testing
    depends_on: ["2"]
    quality_gate:
      type: tests_pass
      test_command: "pytest output/tests/"

  - id: "4"
    name: Documentation
    type: documentation
    depends_on: ["2"]
    description: |
      YAML-Sources aktualisieren und Docs kompilieren.

      1. Neues Feature in docs/sources/*.yaml eintragen
      2. Templates anpassen falls nötig
      3. Kompilieren: python -m helix.tools.docs compile

    quality_gate:
      type: docs_compiled

  - id: "5"
    name: Review
    type: review
    depends_on: ["3", "4"]
    quality_gate:
      type: review_approved
      review_type: code
      criteria:
        - "Docstrings sind aussagekräftig"
        - "YAML-Einträge sind vollständig"
        - "Keine stale Dokumentation"
```

### 10.6 Beispiel: Neues Feature End-to-End

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FEATURE: Neues Quality Gate "schema_valid"                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SCHRITT 1: ADR erstellen (Consultant-Phase)                            │
│  ├── User beschreibt Feature                                            │
│  ├── Consultant erstellt ADR-014                                        │
│  ├── ADR enthält "Dokumentation" Section:                               │
│  │   - docs/sources/quality-gates.yaml erweitern                        │
│  │   - skills/helix/SKILL.md regenerieren                               │
│  └── Quality Gate: adr_valid ✓                                          │
│                                                                          │
│  SCHRITT 2: Implementation (Development-Phase)                          │
│  ├── Developer implementiert SchemaValidator                            │
│  ├── Docstrings hinzufügen:                                             │
│  │   ```python                                                          │
│  │   class SchemaValidator:                                             │
│  │       """Validates data against JSON Schema.                         │
│  │                                                                       │
│  │       Args:                                                           │
│  │           schema_path: Path to JSON Schema file                      │
│  │                                                                       │
│  │       Example:                                                        │
│  │           validator = SchemaValidator("schema.json")                 │
│  │           result = validator.validate(data)                          │
│  │       """                                                             │
│  │   ```                                                                 │
│  └── Quality Gate: docstrings_complete ✓                                │
│                                                                          │
│  SCHRITT 3: Tests (Testing-Phase)                                       │
│  ├── Tests implementieren                                               │
│  └── Quality Gate: tests_pass ✓                                         │
│                                                                          │
│  SCHRITT 4: Documentation (Documentation-Phase)                         │
│  ├── docs/sources/quality-gates.yaml erweitern:                         │
│  │   ```yaml                                                            │
│  │   - id: schema_valid                                                 │
│  │     name: "Schema Valid"                                             │
│  │     description: "Validiert gegen JSON Schema"                       │
│  │     params:                                                          │
│  │       - name: schema_file                                            │
│  │         type: str                                                    │
│  │         required: true                                               │
│  │     implementation:                                                  │
│  │       module: helix.quality_gates.schema                             │
│  │       class: SchemaValidator                                         │
│  │   ```                                                                 │
│  ├── Kompilieren: python -m helix.tools.docs compile                    │
│  │   → CLAUDE.md aktualisiert                                           │
│  │   → skills/helix/SKILL.md aktualisiert                               │
│  │   → docs/ARCHITECTURE-MODULES.md aktualisiert                        │
│  └── Quality Gate: docs_compiled ✓                                      │
│                                                                          │
│  SCHRITT 5: Review                                                      │
│  ├── LLM prüft Docstring-Qualität                                       │
│  ├── LLM prüft YAML-Vollständigkeit                                     │
│  └── Quality Gate: review_approved ✓                                    │
│                                                                          │
│  SCHRITT 6: Integration                                                 │
│  ├── Pre-Commit Hook validiert                                          │
│  ├── CI/CD prüft docs_coverage                                          │
│  └── Merge in main                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.7 Metriken und Reporting

| Metrik | Zielwert | Messung |
|--------|----------|---------|
| Docstring Coverage | 100% | `docs_coverage --check` |
| YAML Coverage (public classes) | 100% | `docs_coverage --check` |
| Stale References | 0 | `docs_coverage --check` |
| Generated Docs Current | Yes | `docs validate` |

**Wöchentlicher Report:**

```bash
#!/bin/bash
# scripts/weekly-docs-audit.sh

echo "=== HELIX Documentation Audit ==="
echo "Date: $(date)"
echo

# Coverage check
python -m helix.tools.docs_coverage

# Freshness check
python -m helix.tools.docs validate

# Token budget check
echo "Token Budgets:"
wc -l CLAUDE.md skills/*/SKILL.md | tail -1
```

---

## 11. Zusammenfassung (erweitert)

### Das vollständige System

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HELIX DOCUMENTATION ARCHITECTURE                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SOURCES (manuell gepflegt)                                             │
│  ├── Docstrings im Code (inline, Pflicht)                               │
│  └── YAML-Definitionen (docs/sources/*.yaml)                           │
│                                                                          │
│  GENERATION                                                              │
│  ├── docs_compiler.py (Jinja2 Templates)                                │
│  └── Outputs: CLAUDE.md, Skills, Architecture Docs                      │
│                                                                          │
│  ENFORCEMENT                                                             │
│  ├── Pre-Commit Hook (lokal)                                            │
│  ├── Quality Gates (HELIX Phasen)                                       │
│  ├── CI/CD Pipeline (GitHub Actions)                                    │
│  └── Weekly Audit (Vollprüfung)                                         │
│                                                                          │
│  METRICS                                                                 │
│  ├── Docstring Coverage: 100%                                           │
│  ├── YAML Coverage: 100%                                                │
│  ├── Stale References: 0                                                │
│  └── Generated Docs: Current                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Enforcement-Garantien

| Situation | Erkennung | Konsequenz |
|-----------|-----------|------------|
| Neue Funktion ohne Docstring | Pre-Commit Hook | Commit blockiert |
| Neues Feature ohne YAML-Eintrag | docs_coverage in Review | Phase schlägt fehl |
| Feature entfernt, YAML bleibt | Cross-Reference Check | Stale Warning |
| Parameter geändert, Beispiel alt | Compile-Validierung | Docs regeneriert |
| Docs out of date | CI/CD Pipeline | Merge blockiert |

### Nächste Schritte (erweitert)

1. `docs/sources/quality-gates.yaml` erstellen
2. `docs_compiler.py` implementieren
3. `docs_coverage.py` implementieren
4. Templates erstellen
5. Pre-Commit Hook einrichten
6. CI/CD Workflow hinzufügen
7. Migration durchführen
8. Weekly Audit aktivieren

---

*Erstellt vom HELIX Meta-Consultant, 2025-12-23*
