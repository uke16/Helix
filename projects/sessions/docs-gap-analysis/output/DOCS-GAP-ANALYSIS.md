# Documentation Gap Analysis: ADR-013 & ADR-017

> Warum wurde die Dokumentation nach der Implementation nicht aktualisiert?

---

## Executive Summary

Nach der Implementation von ADR-013 (Debug & Observability) und ADR-017 (Phase Orchestrator) sind die neuen Features **nicht im Single Source of Truth System** angekommen.

### Das Kernproblem

**ADR-014 (Documentation Architecture) hat Status "Implemented" - ist aber de facto NICHT implementiert!**

| Komponente aus ADR-014 | Soll-Status | Ist-Status |
|------------------------|-------------|------------|
| `docs/sources/*.yaml` | Existiert | **Existiert NICHT** |
| `docs/templates/*.j2` | Existiert | **Existiert NICHT** |
| Pre-Commit Hook | Aktiv | **Nicht konfiguriert** |
| `docs_compiled` Gate | Implementiert | **Nicht implementiert** |
| DocsCompiler | Voll funktional | Nur Basis-Struktur |

### Konsequenz

Claude Code Instanzen die `skills/helix/SKILL.md` lesen, wissen nichts von:
- Debug & Observability Engine (ADR-013)
- Phase Orchestrator (ADR-017)

Diese Features sind für zukünftige Claude Instanzen **unsichtbar**.

---

## 1. Root Cause Analyse

### 1.1 ADR-014 wurde nicht implementiert

ADR-014 definiert das "Single Source of Truth" System:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SOLL-ARCHITEKTUR (ADR-014):                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PRIMARY SOURCES (manuell gepflegt)                                      │
│  ├── docs/sources/quality-gates.yaml                                     │
│  ├── docs/sources/phase-types.yaml                                       │
│  └── Docstrings im Code                                                  │
│                                                                          │
│                    │                                                     │
│                    ▼ python -m helix.tools.docs compile                  │
│                                                                          │
│  GENERATED OUTPUTS (automatisch)                                         │
│  ├── CLAUDE.md                                                           │
│  ├── skills/helix/SKILL.md                                               │
│  └── docs/ARCHITECTURE-*.md                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Aber: Diese Infrastruktur existiert nicht!**

```bash
# Prüfung durchgeführt:
$ ls docs/sources/*.yaml
→ No files found

$ ls docs/templates/*.j2
→ No files found

$ git log --oneline docs/sources/
→ (leer - Verzeichnis wurde nie erstellt)
```

Die YAML Sources und Jinja2 Templates aus ADR-014 wurden **nie erstellt**.

**Interessant:** `skills/helix/SKILL.md` hat den Header:
```markdown
<!-- AUTO-GENERATED from docs/sources/*.yaml -->
<!-- Template: docs/templates/SKILL.md.j2 -->
```

Der Header behauptet es sei generiert, aber die Sources existieren nicht!

### 1.2 Direkte Claude Code CLI statt Consultant-Prozess

Die Implementations von ADR-013 und ADR-017 wurden vermutlich mit direktem Claude CLI ausgeführt, nicht über den HELIX Consultant-Prozess:

```
┌─────────────────────────────────────────────────────────────────┐
│  WIE ES HÄTTE LAUFEN SOLLEN:                                    │
│                                                                  │
│  1. Consultant → Erstellt ADR mit "## Dokumentation" Section    │
│  2. phases.yaml → Enthält Documentation-Phase                   │
│  3. Documentation Phase → Aktualisiert alle 4 Ebenen            │
│  4. Quality Gate → Prüft ob docs/sources/*.yaml aktuell         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  WAS TATSÄCHLICH PASSIERT IST:                                  │
│                                                                  │
│  1. Claude CLI direkt ausgeführt                                │
│  2. Code implementiert                                          │
│  3. docs/DEBUGGING.md und docs/ORCHESTRATOR-GUIDE.md erstellt   │
│  4. FERTIG - ohne Documentation Update Phase                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Kein Enforcement-Mechanismus

ADR-014 definiert Quality Gates für Dokumentation, aber:
- `docstrings_complete` Gate existiert nicht
- `docs_compiled` Gate existiert nicht
- Pre-Commit Hook ist nicht eingerichtet
- CI/CD Workflow fehlt

**Ohne Enforcement passiert Dokumentation nicht.**

---

## 2. Prozess-Lücke

### Wo genau bricht der Prozess ab?

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ADR schreiben                                                  │
│        ↓                                                         │
│   Code implementieren                                            │
│        ↓                                                         │
│   Feature-spezifische Docs erstellen                            │
│   (docs/DEBUGGING.md, docs/ORCHESTRATOR-GUIDE.md)               │
│        ↓                                                         │
│   ╔═══════════════════════════════════════════════════════════╗ │
│   ║  LÜCKE: Hier sollte passieren:                            ║ │
│   ║                                                            ║ │
│   ║  1. docs/sources/*.yaml erweitern                         ║ │
│   ║  2. skills/helix/SKILL.md aktualisieren                   ║ │
│   ║  3. docs/ARCHITECTURE-MODULES.md erweitern                ║ │
│   ║  4. CLAUDE.md aktualisieren                               ║ │
│   ║                                                            ║ │
│   ║  → Kein automatischer Schritt!                            ║ │
│   ║  → Kein Quality Gate prüft das!                           ║ │
│   ║  → Keine Documentation Phase im Workflow!                 ║ │
│   ╚═══════════════════════════════════════════════════════════╝ │
│        ↓                                                         │
│   FERTIG (aber unvollständig)                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Konkret für ADR-013 und ADR-017:

| Dokument | Aktueller Stand | Sollte enthalten |
|----------|-----------------|------------------|
| `skills/helix/SKILL.md` | Erwähnt NICHT debug/, orchestrator/ | Debug-Module, Orchestrator-Module |
| `docs/ARCHITECTURE-MODULES.md` | Enthält alte orchestrator.py | Neues orchestrator/ Package |
| `docs/sources/*.yaml` | **Existiert nicht** | debug.yaml, orchestrator.yaml |
| `CLAUDE.md` | Kein Hinweis auf Debug/Orchestrator | Tools Section erweitern |

---

## 3. Lösungsoptionen

### Option A: Post-Implementation Hook

**Idee:** Nach jeder Implementation automatisch docs/sources/*.yaml aktualisieren.

```yaml
# phases.yaml - Jedes Projekt
phases:
  - id: documentation
    name: "Documentation Sync"
    type: documentation
    quality_gate:
      type: docs_updated
      check:
        - skills/helix/SKILL.md
        - docs/sources/*.yaml
```

**Pro:**
- Zwingt zur Dokumentation in jedem Projekt
- Kann automatisch validiert werden

**Contra:**
- Erfordert Disziplin beim Erstellen von phases.yaml
- Bypassed bei direktem Claude CLI Aufruf
- Manuelle Pflege von docs/sources/*.yaml

**Erzwingung:**
- Quality Gate `docs_updated` implementieren
- Phase schlägt fehl wenn Dateien nicht aktualisiert

---

### Option B: ADR-Template erweitern

**Idee:** ADR muss explizit docs/sources/*.yaml Änderungen definieren.

```yaml
# Im ADR Header
files:
  create:
    - src/helix/debug/__init__.py
    - docs/DEBUGGING.md
  modify:
    - skills/helix/SKILL.md           # PFLICHT!
    - docs/sources/modules.yaml       # PFLICHT!
  docs:
    - docs/ARCHITECTURE-MODULES.md
```

**Pro:**
- Dokumentation wird Teil der Planung
- ADR Validator kann prüfen ob docs/sources/*.yaml geändert wird
- Consultant sieht Doku-Anforderungen sofort

**Contra:**
- Erhöht Aufwand beim ADR-Schreiben
- Kann vergessen werden wenn Claude CLI direkt verwendet wird

**Erzwingung:**
```python
# In ADRValidator erweitern
def validate_docs_modified(self, adr: ADRDocument) -> list[ValidationIssue]:
    """Prüft ob docs/sources/*.yaml in files.modify steht."""
    modified = adr.metadata.files.modify or []
    if not any("docs/sources" in f for f in modified):
        return [ValidationIssue(
            level=IssueLevel.WARNING,
            message="ADR sollte docs/sources/*.yaml aktualisieren"
        )]
    return []
```

---

### Option C: Automatische Extraktion

**Idee:** Tool das aus Code + Docstrings automatisch YAML Sources generiert.

```bash
python -m helix.tools.docs_extractor src/helix/debug/ > docs/sources/debug.yaml
```

**Pro:**
- Keine manuelle Pflege nötig
- Immer synchron mit Code
- Docstrings = Single Source of Truth

**Contra:**
- Komplex zu implementieren
- Docstrings müssen sehr strukturiert sein
- Semantische Information (Workflow, Best Practices) fehlt

**Realistisch?**
- Für API-Referenz: **Ja, machbar**
- Für Workflow-Dokumentation: **Nein, zu komplex**
- Empfehlung: Hybrid - API automatisch, Workflow manuell

---

### Option D: Documentation Phase als Pflicht in HELIX

**Idee:** HELIX Orchestrator erzwingt Documentation Phase für jeden Projekt-Typ.

```python
# In helix/orchestrator/runner.py
DEFAULT_PHASES = {
    "simple": ["consultant", "development", "review", "documentation", "integration"],
    "complex": ["consultant", "feasibility", "planning", "development", "review", "documentation", "integration"],
}

# Documentation Phase ist nicht optional!
```

**Pro:**
- Systemisch erzwungen
- Kann nicht übersprungen werden
- Konsistent über alle Projekte

**Contra:**
- Erfordert Änderung am Orchestrator
- Was wenn direkt CLI verwendet wird?

---

### Option E: Pre-Commit Hook für docs/sources

**Idee:** Git Hook prüft ob docs/sources/*.yaml aktuell ist.

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Wenn src/helix/ geändert wurde, müssen auch docs/sources/ geändert sein
CHANGED_SRC=$(git diff --cached --name-only | grep "^src/helix/")
CHANGED_DOCS=$(git diff --cached --name-only | grep "^docs/sources/")

if [ -n "$CHANGED_SRC" ] && [ -z "$CHANGED_DOCS" ]; then
    echo "ERROR: Code geändert ohne docs/sources/ zu aktualisieren!"
    echo "Bitte docs/sources/*.yaml aktualisieren und 'python -m helix.tools.docs compile' ausführen."
    exit 1
fi
```

**Pro:**
- Blockiert Commits ohne Dokumentation
- Einfach zu implementieren
- Funktioniert auch bei direktem CLI-Aufruf

**Contra:**
- Kann mit --no-verify umgangen werden
- Nur lokal, nicht im CI/CD

---

## 4. Empfehlung

### Pragmatische Lösung für HELIX v4

**Kombiniere Option B + Option D + Option E:**

```
┌─────────────────────────────────────────────────────────────────┐
│  EMPFOHLENE ÄNDERUNGEN                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ADR-014 tatsächlich implementieren                          │
│     → docs/sources/*.yaml Struktur erstellen                    │
│     → Jinja2 Templates für CLAUDE.md, SKILL.md                  │
│     → DocsCompiler Tool fertigstellen                           │
│                                                                  │
│  2. ADR-Template erweitern (Option B)                           │
│     → "## Dokumentation" Section wird Pflicht                   │
│     → ADR Validator prüft auf docs/sources Referenzen           │
│                                                                  │
│  3. Documentation Phase erzwingen (Option D)                    │
│     → Jeder Projekt-Typ enthält Documentation Phase             │
│     → Phase hat Quality Gate: docs_compiled                     │
│                                                                  │
│  4. Pre-Commit Hook (Option E)                                  │
│     → Warnt wenn src/ geändert ohne docs/sources/               │
│     → Regeneriert CLAUDE.md und SKILL.md automatisch            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Priorisierung

| Priorität | Aktion | Aufwand | Impact |
|-----------|--------|---------|--------|
| **P1** | docs/sources/*.yaml erstellen (debug, orchestrator) | 2h | Sofort skills aktuell |
| **P1** | ADR-014 Implementation fertigstellen | 4h | Compiler funktioniert |
| **P2** | ADR Validator erweitern | 1h | Zukunft: ADRs prüfen |
| **P2** | Pre-Commit Hook einrichten | 0.5h | Sofort-Enforcement |
| **P3** | Documentation Phase als Default | 1h | Systemisch erzwungen |

### Sofort-Maßnahme für ADR-013 und ADR-017

```yaml
# docs/sources/modules.yaml - ERSTELLEN

modules:
  - name: debug
    description: "Debug & Observability Engine"
    submodules:
      - stream_parser: "Parses NDJSON from Claude CLI"
      - tool_tracker: "Tracks tool calls with timing"
      - cost_calculator: "Token and cost tracking"
      - live_dashboard: "Terminal and SSE dashboards"
      - events: "Event type definitions"
    see_also:
      - docs/DEBUGGING.md
      - ADR-013

  - name: orchestrator
    description: "Phase Orchestrator for autonomous execution"
    submodules:
      - runner: "OrchestratorRunner main class"
      - phase_executor: "Executes individual phases"
      - data_flow: "Manages input/output copying"
      - status: "Status persistence and tracking"
    see_also:
      - docs/ORCHESTRATOR-GUIDE.md
      - ADR-017
```

---

## 5. Vorgeschlagene Änderungen an ADR-014

### Ergänzung: Enforcement-Section

```markdown
## Enforcement (NEU)

### Pflicht-Checks

1. **ADR Validator**
   - Prüft ob "## Dokumentation" Section existiert
   - Prüft ob docs/sources/*.yaml in files.modify steht
   - Warning wenn nicht, kein Error (pragmatisch)

2. **Pre-Commit Hook**
   - Blockiert Commits die src/helix/ ändern ohne docs/sources/
   - Kann mit --no-verify umgangen werden (für Hotfixes)

3. **Documentation Phase**
   - Jeder Projekt-Typ enthält Documentation Phase
   - Quality Gate: docs_compiled
   - Phase schlägt fehl wenn Compiler Diff zeigt

### Umgehung dokumentieren

Wenn Documentation übersprungen wird:
- [ ] TODO Issue erstellen
- [ ] In nächstem Sprint nachholen
- [ ] Commit-Message enthält "SKIP-DOCS: [Grund]"
```

### Ergänzung: Bootstrapping-Section

```markdown
## Bootstrapping (NEU)

### Initiale docs/sources Struktur

```
docs/sources/
├── quality-gates.yaml    # Alle Quality Gate Definitionen
├── phase-types.yaml      # Phase-Typ Definitionen
├── domains.yaml          # Domain und Skill Übersicht
├── modules.yaml          # Python Module Beschreibungen
├── escalation.yaml       # Escalation Level
└── tools.yaml            # Available Tools (adr_tool, docs_compiler, etc.)
```

### Migration existierender Docs

1. Extrahiere Inhalte aus SKILL.md → yaml
2. Extrahiere Inhalte aus ARCHITECTURE-MODULES.md → yaml
3. Erstelle Jinja2 Templates
4. Erste Kompilierung
5. Verify: Diff zwischen alt und neu minimal
```

---

## 6. Fazit

### Das eigentliche Problem

**ADR-014 wurde geschrieben aber nie implementiert.**

Die "Single Source of Truth" Architektur existiert nur auf Papier. Die Konsequenz:
- Neue Features dokumentieren sich in isolierten docs/*.md Dateien
- skills/helix/SKILL.md wird manuell gepflegt (und vergessen)
- docs/sources/*.yaml existiert nicht
- Kein Compiler, kein Enforcement, kein System

### Der Ausweg

1. **Sofort:** ADR-013 und ADR-017 manuell in skills/helix/SKILL.md nachtragen
2. **Diese Woche:** docs/sources/*.yaml Struktur erstellen
3. **Nächster Sprint:** ADR-014 vollständig implementieren
4. **Danach:** Pre-Commit Hook und CI/CD Enforcement

### Lessons Learned

> **ADRs sind nur so gut wie ihre Implementation.**
>
> Ein ADR das beschreibt wie Dokumentation funktionieren soll,
> hilft nichts wenn es selbst nicht dokumentiert wird.

---

*Analyse erstellt: 2025-12-24*
*Session: docs-gap-analysis*
