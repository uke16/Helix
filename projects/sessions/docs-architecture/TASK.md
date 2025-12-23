# Aufgabe: Dokumentations-Architektur ohne Redundanz

Du bist der HELIX Meta-Consultant. Entwickle ein Konzept für redundanzfreie Dokumentation.

## Das Problem

Aktuell: Quality Gates an **14 Stellen** dokumentiert!
- CLAUDE.md
- docs/ARCHITECTURE-MODULES.md (31 Referenzen!)
- docs/CONCEPT.md
- skills/helix/SKILL.md
- ... und 10 weitere

Bei Änderung: 14 Stellen manuell updaten → Inkonsistenz garantiert

## Die Idee des Users

**Option A: Sync-Tool**
- Tool das Redundanzen erkennt
- Automatisch alle Stellen synchronisiert
- Problem: Komplexität, Merge-Konflikte

**Option B: Generierte Dokumentation**
- Nur EINE Stelle pflegen (Source of Truth)
- Höhere Schichten werden GENERIERT
- Wie Code-Generierung, aber für Docs

## Deine Aufgabe

Entwickle ein Konzept das folgende Fragen beantwortet:

### 1. Architektur-Entscheidung

Welcher Ansatz ist besser?
- Option A: Sync-Tool (wie git, aber für Doku-Fragmente)
- Option B: Generierung (wie Jinja Templates für Docs)
- Option C: Hybrid (manche Docs generiert, manche manuell)

### 2. Source of Truth Definition

Wo liegt die "unterste Schicht"?

Möglichkeiten:
```
a) Code-Docstrings
   → Python docstrings sind Source of Truth
   → Alles andere wird daraus generiert
   
b) Dedizierte Source-Files
   → docs/sources/*.yaml oder *.md
   → Strukturierte Daten die in verschiedene Formate kompiliert werden
   
c) ADRs als Source
   → ADRs definieren Features
   → Skills/CLAUDE.md werden aus ADRs generiert
   
d) Skill-First
   → Skills sind Source of Truth
   → CLAUDE.md wird aus Skills aggregiert
```

### 3. Kompilier-Prozess

Wie würde die Generierung funktionieren?

```
Beispiel für Quality Gates:

SOURCE (skills/helix/quality-gates.yaml):
  - name: files_exist
    description: Prüft ob Output-Dateien existieren
    params: [required_files]
    example: |
      quality_gate:
        type: files_exist
        required_files: [output/result.md]

GENERIERT → CLAUDE.md:
  "Quality Gates: files_exist, syntax_check, adr_valid
   → Details: skills/helix/SKILL.md"

GENERIERT → skills/helix/SKILL.md:
  ## Quality Gates
  ### files_exist
  Prüft ob Output-Dateien existieren.
  ```yaml
  quality_gate:
    type: files_exist
  ```

GENERIERT → docs/ARCHITECTURE-MODULES.md:
  ### Quality Gate System
  Available gates: files_exist, syntax_check, adr_valid
  See: skills/helix/quality-gates.yaml for definitions
```

### 4. Tooling

Welche Tools brauchen wir?

- `docs compile` - Generiert alle Docs aus Sources
- `docs validate` - Prüft ob generierte Docs aktuell sind
- `docs sources` - Zeigt alle Source-Dateien

### 5. Integration mit HELIX

Wie passt das in den HELIX Workflow?

- Quality Gate: `docs_compiled` - Sind generierte Docs aktuell?
- Pre-Commit Hook: Docs automatisch regenerieren?
- CI/CD: Docs bei jedem Push validieren?

## Constraints

1. Muss mit Claude Code funktionieren (kein externer Build-Server)
2. Muss inkrementell sein (nicht alles neu generieren)
3. Muss menschenlesbar bleiben (kein Binary-Format)
4. Muss einfach erweiterbar sein

## Output

Schreibe in output/docs-architecture.md:

1. Architektur-Entscheidung mit Begründung
2. Source of Truth Definition
3. Kompilier-Prozess mit Beispielen
4. Tooling-Konzept
5. HELIX Integration
6. Migration-Plan (wie kommen wir dahin?)
7. Beispiel-Implementation für Quality Gates

Sei konkret und pragmatisch!
