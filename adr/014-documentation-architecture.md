---
adr_id: "014"
title: "Documentation Architecture - Generated Docs with Enforcement"
status: Proposed

component_type: PROCESS
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - docs/sources/quality-gates.yaml
    - docs/sources/phase-types.yaml
    - docs/sources/domains.yaml
    - docs/templates/CLAUDE.md.j2
    - docs/templates/SKILL.md.j2
    - docs/templates/partials/quality-gates-table.md.j2
    - src/helix/tools/docs_compiler.py
    - src/helix/tools/docs_coverage.py
    - scripts/weekly-docs-audit.sh
  modify:
    - CLAUDE.md
    - skills/helix/SKILL.md
    - .git/hooks/pre-commit
  docs:
    - docs/DOC-INDEX.md
    - docs/DOCUMENTATION-GUIDE.md

depends_on: ["002", "003"]
---

# ADR-014: Documentation Architecture - Generated Docs with Enforcement

## Kontext

### Das Problem: Dokumentations-Redundanz

HELIX v4 dokumentiert Quality Gates aktuell an **14+ Stellen**:

| Ort | Verwendung |
|-----|------------|
| `CLAUDE.md` | Übersicht für Claude Code |
| `skills/helix/SKILL.md` | Details für Developer |
| `docs/ARCHITECTURE-MODULES.md` | Technische Referenz |
| `phases.yaml` (jedes Projekt) | Konfiguration |
| ADRs (002, 011, etc.) | Historische Entscheidungen |
| Docstrings im Code | API-Dokumentation |

**Konsequenzen der Redundanz:**

1. **Inkonsistenz garantiert**: Bei Updates wird mindestens eine Stelle vergessen
2. **Hoher Pflegeaufwand**: 14+ Stellen manuell synchronisieren
3. **Vertrauen sinkt**: Nutzer wissen nicht welche Quelle aktuell ist
4. **Kein Lifecycle**: Keine automatische Erkennung veralteter Dokumentation

### Beispiel: Quality Gate `adr_valid`

Wenn `adr_valid` einen neuen Parameter bekommt, müssen aktualisiert werden:
- Root CLAUDE.md (Tabelle)
- skills/helix/SKILL.md (Detailbeschreibung)
- skills/helix/adr/SKILL.md (Verwendungsbeispiel)
- docs/ARCHITECTURE-MODULES.md (API-Referenz)
- docs/ADR-TEMPLATE.md (Hinweis)
- Docstrings in `helix/adr/gate.py`

**Wahrscheinlichkeit dass alle 6 Stellen aktualisiert werden: ~20%**

## Entscheidung

### Generierungsbasierte Dokumentationsarchitektur

Wir implementieren **Option B: Generierung** statt manueller Synchronisation.

**Kernprinzip: Eine Quelle, viele Ausgaben**

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

### Zwei-Quellen-Modell

| Quelle | Enthält | Warum |
|--------|---------|-------|
| **Docstrings** | API-Signatur, Parameter, Beispiele | Nahe am Code, validiert durch Python-Typsystem |
| **YAML-Definitionen** | Feature-Metadaten, Konfigurationsschema | Strukturiert, schema-validierbar |

### Drei-Schichten-Hierarchie mit Token-Budgets

| Schicht | Ziel-Audience | Token-Budget | Inhalt |
|---------|---------------|--------------|--------|
| **Layer 1: CLAUDE.md** | Alle Claude Code Instanzen | ~300 Zeilen | Übersicht, Links zu Details |
| **Layer 2: Skills** | Domain-spezifische Instanzen | ~600 Zeilen | Vollständige Feature-Docs |
| **Layer 3: Architecture Docs** | Deep-Dive, Debugging | Unbegrenzt | Technische Referenz, Beispiele |

## Implementation

### 1. Source-Datei Format

**`docs/sources/quality-gates.yaml`** (Auszug):

```yaml
_meta:
  version: "1.0"
  description: "Quality Gate Definitions für HELIX v4"
  generated_outputs:
    - CLAUDE.md
    - skills/helix/SKILL.md

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

    implementation:
      module: helix.quality_gates
      class: QualityGateRunner
      method: check_files_exist
```

### 2. Compiler-Architektur

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

### 3. CLI-Befehle

```bash
# Dokumentation kompilieren
python -m helix.tools.docs compile

# Nur validieren (ohne zu schreiben)
python -m helix.tools.docs validate

# Sources anzeigen
python -m helix.tools.docs sources

# Diff anzeigen (was würde sich ändern?)
python -m helix.tools.docs diff
```

### 4. DocCompiler Kern-Klasse

```python
# src/helix/tools/docs_compiler.py

from pathlib import Path
from dataclasses import dataclass
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
    """Compiles documentation from sources.

    Usage:
        compiler = DocCompiler()
        result = compiler.compile()

        if not result.success:
            for error in result.errors:
                print(f"ERROR: {error}")
    """

    def __init__(self, root: Path = None):
        self.root = root or Path(".")
        self.sources_dir = self.root / "docs" / "sources"
        self.templates_dir = self.root / "docs" / "templates"
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def collect_sources(self) -> dict:
        """Collect all source data from YAML and docstrings."""
        context = {}

        # Load YAML sources
        for yaml_file in self.sources_dir.glob("*.yaml"):
            key = yaml_file.stem.replace("-", "_")
            with open(yaml_file) as f:
                context[key] = yaml.safe_load(f)

        # Extract docstrings
        context["modules"] = self._extract_docstrings()

        return context

    def compile(self, targets: list[str] = None) -> CompileResult:
        """Compile documentation from sources."""
        # ... implementation
```

### 5. Coverage-Tool

```python
# src/helix/tools/docs_coverage.py

@dataclass
class CoverageReport:
    """Full coverage report."""
    docstring_coverage: float
    yaml_coverage: float
    total_items: int
    documented_items: int
    missing_docstrings: list[CoverageItem]
    stale_yaml: list[str]

    @property
    def is_complete(self) -> bool:
        return (
            self.docstring_coverage >= 100 and
            len(self.stale_yaml) == 0
        )
```

## Enforcement

### Hybrid-Workflow

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

### Quality Gates

**1. `docstrings_complete`** - Prüft dass alle public API-Elemente dokumentiert sind:

```yaml
# phases.yaml
quality_gate:
  type: docstrings_complete
  file_patterns:
    - "output/**/*.py"
  min_coverage: 100
```

**2. `docs_compiled`** - Prüft dass generierte Docs aktuell sind:

```yaml
quality_gate:
  type: docs_compiled
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check docstrings for changed Python files
CHANGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -n "$CHANGED_PY" ]; then
    echo "Checking docstrings..."
    # Quick AST check for missing docstrings
fi

# Check if docs sources changed
if git diff --cached --name-only | grep -q "docs/sources/"; then
    echo "Docs sources changed, validating..."
    python -m helix.tools.docs validate || exit 1
    python -m helix.tools.docs compile
    git add CLAUDE.md skills/*/SKILL.md docs/ARCHITECTURE-*.md
fi
```

### CI/CD Integration

```yaml
# .github/workflows/docs.yaml
name: Documentation

on:
  push:
    paths:
      - 'docs/sources/**'
      - 'src/helix/**/*.py'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate docs
        run: python -m helix.tools.docs validate

      - name: Check docs are current
        run: |
          python -m helix.tools.docs compile
          if ! git diff --exit-code; then
            echo "ERROR: Generated docs are out of date!"
            exit 1
          fi
```

### Enforcement-Garantien

| Situation | Erkennung | Konsequenz |
|-----------|-----------|------------|
| Neue Funktion ohne Docstring | Pre-Commit Hook | Commit blockiert |
| Neues Feature ohne YAML-Eintrag | docs_coverage in Review | Phase schlägt fehl |
| Feature entfernt, YAML bleibt | Cross-Reference Check | Stale Warning |
| Parameter geändert, Beispiel alt | Compile-Validierung | Docs regeneriert |
| Docs out of date | CI/CD Pipeline | Merge blockiert |

## Dokumentation

Diese Änderung erfordert neue und aktualisierte Dokumentation:

| Dokument | Aktion | Beschreibung |
|----------|--------|--------------|
| `docs/DOC-INDEX.md` | Erstellen | Index aller Documentation Sources |
| `docs/DOCUMENTATION-GUIDE.md` | Erstellen | Anleitung für Contributors |
| `CLAUDE.md` | Aktualisieren | Hinweis auf Generierung hinzufügen |
| `skills/helix/SKILL.md` | Aktualisieren | docs_compiler dokumentieren |

## Akzeptanzkriterien

### Sources

- [ ] `docs/sources/quality-gates.yaml` erstellt mit allen 5 Gates
- [ ] `docs/sources/phase-types.yaml` erstellt
- [ ] `docs/sources/domains.yaml` erstellt

### Compiler

- [ ] `src/helix/tools/docs_compiler.py` implementiert
- [ ] CLI: `python -m helix.tools.docs compile` funktioniert
- [ ] CLI: `python -m helix.tools.docs validate` funktioniert
- [ ] CLAUDE.md wird korrekt generiert
- [ ] skills/helix/SKILL.md wird korrekt generiert

### Coverage Tool

- [ ] `src/helix/tools/docs_coverage.py` implementiert
- [ ] Docstring-Coverage wird korrekt berechnet
- [ ] Cross-Reference-Check findet stale Einträge

### Enforcement

- [ ] Quality Gate `docstrings_complete` implementiert
- [ ] Quality Gate `docs_compiled` implementiert
- [ ] Pre-Commit Hook eingerichtet
- [ ] CI/CD Workflow konfiguriert

### Migration

- [ ] Bestehende CLAUDE.md in Template konvertiert
- [ ] Bestehende Skills in Templates konvertiert
- [ ] Erste vollständige Kompilierung erfolgreich
- [ ] Keine Diff zwischen alt und neu

## Konsequenzen

### Vorteile

1. **Konsistenz garantiert**: Gleiche Quelle → Gleiche Ausgabe
2. **Atomic Updates**: Eine Änderung = Alle Stellen konsistent
3. **Validierbar**: Build-Fehler zeigen Inkonsistenzen sofort
4. **HELIX-Native**: Passt zum Phasen-Konzept
5. **Auditierbar**: Wöchentlicher Coverage-Report

### Nachteile

1. **Initialer Migrationsaufwand**: Bestehende Docs in Sources konvertieren
2. **Build-Step erforderlich**: Docs müssen kompiliert werden
3. **Template-Komplexität**: Jinja2-Kenntnisse nötig für Anpassungen

### Mitigation

- Migration schrittweise durchführen (erst Quality Gates, dann weitere)
- Pre-Commit Hook macht Build-Step transparent
- Template-Beispiele und Guide bereitstellen

### Metriken nach Implementation

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Quality Gates dokumentiert in | 14+ Stellen | 1 Source + Generierung |
| Update-Aufwand | 14+ Stellen manuell | 1 Stelle, Rest automatisch |
| Konsistenz-Garantie | Keine | 100% (deterministisch) |
| Validierung | Manuell | Automatisch (CI/CD) |

---

*ADR erstellt vom HELIX Meta-Consultant*
*Vollständiges Konzept: [output/docs-architecture.md](docs-architecture.md)*

---

## Migration-Plan

### Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MIGRATION: 14 Tage in 5 Phasen                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1: Infrastruktur (Tag 1-2)                                       │
│  └── Verzeichnisse, Compiler-Grundgerüst, CLI                           │
│                                                                          │
│  Phase 2: Quality Gates (Tag 3-4)                                       │
│  └── Erste Source-Datei, erste Templates, erste Generierung             │
│                                                                          │
│  Phase 3: Weitere Sources (Tag 5-7)                                     │
│  └── phase-types, domains, escalation                                   │
│                                                                          │
│  Phase 4: Enforcement (Tag 8-10)                                        │
│  └── Quality Gates, Pre-Commit, CI/CD                                   │
│                                                                          │
│  Phase 5: Cleanup (Tag 11-14)                                           │
│  └── Redundanzen entfernen, Validierung                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Infrastruktur (Tag 1-2)

| Schritt | Aktion | Befehl/Datei | Ergebnis |
|---------|--------|--------------|----------|
| 1.1 | Verzeichnisse erstellen | `mkdir -p docs/sources docs/templates/partials` | Basis-Struktur |
| 1.2 | Compiler implementieren | `src/helix/tools/docs_compiler.py` | Tool-Grundgerüst |
| 1.3 | CLI Entry-Point | `__main__.py` hinzufügen | `python -m helix.tools.docs` |
| 1.4 | Basis-Test | `python -m helix.tools.docs --help` | CLI funktioniert |

**Validierung Phase 1:**
```bash
python -m helix.tools.docs --help
# Sollte: compile, validate, sources Befehle zeigen
```

### Phase 2: Quality Gates Migration (Tag 3-4)

| Schritt | Aktion | Details |
|---------|--------|---------|
| 2.1 | Source extrahieren | Quality Gates aus CLAUDE.md → `docs/sources/quality-gates.yaml` |
| 2.2 | Tabellen-Template | `docs/templates/partials/quality-gates-table.md.j2` |
| 2.3 | Detail-Template | `docs/templates/partials/quality-gates-detail.md.j2` |
| 2.4 | CLAUDE.md Template | `docs/templates/CLAUDE.md.j2` |
| 2.5 | Erste Kompilierung | `python -m helix.tools.docs compile` |

**Source-Datei Beispiel (`docs/sources/quality-gates.yaml`):**
```yaml
gates:
  - id: files_exist
    name: "Files Exist"
    description: "Prüft ob alle erwarteten Output-Dateien existieren"
    category: deterministic
    params:
      - name: required_files
        type: list[str]
        required: true
    example: |
      quality_gate:
        type: files_exist
        required_files:
          - output/result.md
```

**Validierung Phase 2:**
```bash
python -m helix.tools.docs compile
diff CLAUDE.md CLAUDE.md.backup  # Sollte: nur Formatierung unterschiedlich
```

### Phase 3: Weitere Sources (Tag 5-7)

| Schritt | Source-Datei | Inhalt |
|---------|--------------|--------|
| 3.1 | `docs/sources/phase-types.yaml` | consultant, development, testing, review, documentation |
| 3.2 | `docs/sources/domains.yaml` | helix, pdm, encoder, infrastructure |
| 3.3 | `docs/sources/escalation.yaml` | Escalation-Level und Strategien |
| 3.4 | SKILL.md Template | `docs/templates/SKILL.md.j2` |

**Validierung Phase 3:**
```bash
python -m helix.tools.docs compile
ls -la CLAUDE.md skills/helix/SKILL.md  # Beide generiert
```

### Phase 4: Enforcement (Tag 8-10)

| Schritt | Aktion | Implementation |
|---------|--------|----------------|
| 4.1 | Quality Gate `docstrings_complete` | `src/helix/quality_gates/docstrings.py` |
| 4.2 | Quality Gate `docs_compiled` | `src/helix/quality_gates/docs.py` |
| 4.3 | Coverage Tool | `src/helix/tools/docs_coverage.py` |
| 4.4 | Pre-Commit Hook | `.git/hooks/pre-commit` |
| 4.5 | CI/CD Workflow | `.github/workflows/docs.yml` (optional) |

**Pre-Commit Hook:**
```bash
#!/bin/bash
# Prüft Docstrings für geänderte .py Dateien
# Regeneriert Docs wenn Sources geändert

python -m helix.tools.docs validate || exit 1
```

**Validierung Phase 4:**
```bash
# Test: Commit ohne Docstring sollte fehlschlagen
echo "def test(): pass" > /tmp/test.py
git add /tmp/test.py && git commit -m "test"  # Sollte: blockiert
```

### Phase 5: Cleanup & Validierung (Tag 11-14)

| Schritt | Aktion | Prüfung |
|---------|--------|---------|
| 5.1 | Redundanzen identifizieren | `grep -r "quality.*gate" docs/ skills/` |
| 5.2 | Redundanzen entfernen | Manuelle Sections in generierten Dateien entfernen |
| 5.3 | CLAUDE.md ersetzen | `mv CLAUDE.md.generated CLAUDE.md` |
| 5.4 | Skills ersetzen | Skills auf generierte Version umstellen |
| 5.5 | Vollvalidierung | `python -m helix.tools.docs_coverage` |

**Finale Validierung:**
```bash
# Alles sollte grün sein
python -m helix.tools.docs validate
python -m helix.tools.docs_coverage
git diff  # Keine unerwarteten Änderungen
```

### Rollback-Plan

Falls Probleme auftreten:

```bash
# 1. Backup wiederherstellen
git checkout HEAD~1 -- CLAUDE.md skills/

# 2. Generierung deaktivieren
rm .git/hooks/pre-commit

# 3. Problem analysieren
python -m helix.tools.docs validate --verbose
```

### Erfolgskriterien

| Kriterium | Messung | Zielwert |
|-----------|---------|----------|
| Docstring Coverage | `docs_coverage` | 100% |
| YAML Coverage | `docs_coverage` | 100% |
| Stale References | `docs_coverage` | 0 |
| Generated Docs Current | `docs validate` | ✅ |
| Pre-Commit funktioniert | Test-Commit | ✅ |
| Redundanzen eliminiert | `grep` Analyse | 0 |

