# Aufgabe: ADR-014 erstellen

Du bist der HELIX Meta-Consultant. Erstelle ADR-014 basierend auf dem Konzept in output/docs-architecture.md.

## Kontext

Das Konzept beschreibt:
1. Generierungsbasierte Dokumentation (Single Source of Truth)
2. Zwei-Quellen-Modell (Docstrings + YAML)
3. Drei-Schichten-Hierarchie (Kern, Domain, Referenz)
4. Enforcement via Quality Gates, Pre-Commit, CI/CD
5. Tooling (docs_compiler, docs_coverage)

## ADR erstellen

Lies zuerst:
- output/docs-architecture.md (das vollständige Konzept)
- ../../adr/INDEX.md (nächste Nummer = 014)
- ../../skills/helix/adr/SKILL.md (ADR-Format)

Erstelle dann: output/ADR-014-documentation-architecture.md

### YAML Header

```yaml
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
```

### Inhalt

Das ADR soll enthalten:

1. **Kontext**
   - Das Problem: 14+ Stellen für Quality Gates
   - Redundanz = Inkonsistenz
   - Kein Lifecycle Management

2. **Entscheidung**
   - Generierungsbasierte Architektur
   - Zwei-Quellen-Modell (Docstrings + YAML)
   - Drei-Schichten-Hierarchie mit Token-Budgets
   - ASCII-Diagramm der Architektur

3. **Implementation**
   - Source-Datei Format (YAML Beispiel)
   - Template-Struktur
   - Compiler-Konzept
   - Coverage-Tool

4. **Enforcement**
   - Hybrid-Workflow (wann wird dokumentiert)
   - Quality Gates: docstrings_complete, docs_compiled
   - Pre-Commit Hook
   - CI/CD Integration
   - Weekly Audit

5. **Dokumentation**
   - DOC-INDEX.md erstellen
   - DOCUMENTATION-GUIDE.md erstellen

6. **Akzeptanzkriterien** (als Checkboxen)
   - Sources: YAML-Dateien erstellt
   - Compiler: docs_compiler.py funktioniert
   - Coverage: docs_coverage.py funktioniert
   - Enforcement: Quality Gates implementiert
   - Migration: Bestehende Docs migriert

7. **Konsequenzen**
   - Positiv: Konsistenz, Automatisierung
   - Negativ: Initialer Migrationsaufwand
   - Neutral: Build-Step nötig

## Wichtig

- Das ADR soll UMFASSEND sein (es ist das Doku-Konzept)
- Aber nicht das gesamte Konzept kopieren - referenziere es
- Konkrete Code-Beispiele für kritische Teile
- Klare Akzeptanzkriterien für Implementation
