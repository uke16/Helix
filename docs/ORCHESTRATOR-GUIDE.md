# HELIX Phase Orchestrator - User Guide

> Autonome Projekt-Ausführung mit dem HELIX Orchestrator

---

## Überblick

Der Phase Orchestrator automatisiert die Ausführung von HELIX-Projekten. Er:

- Führt Phasen sequentiell aus
- Kopiert Outputs automatisch als Inputs für folgende Phasen
- Prüft Quality Gates nach jeder Phase
- Speichert Status für Resume-Fähigkeit
- Bietet CLI und API für Projekt-Management

## Schnellstart

```bash
# Projekt erstellen
helix project create my-feature --type simple

# Projekt ausführen
helix project run my-feature

# Status prüfen
helix project status my-feature
```

---

## CLI Commands

### `helix project create`

Erstellt ein neues Projekt mit Standard-Phasenstruktur.

```bash
helix project create <name> [--type simple|complex|exploratory]
```

**Optionen:**
- `--type`: Projekt-Typ (Standard: `simple`)
  - `simple`: Consultant → Development → Review → Integration
  - `complex`: Consultant → Feasibility → Planning → Development → Review → Integration
  - `exploratory`: Consultant → Research → Decision
- `--base-dir`: Basis-Verzeichnis (Standard: `projects/external`)

**Beispiele:**
```bash
helix project create feature-x --type simple
helix project create big-refactor --type complex
helix project create new-idea --type exploratory
```

### `helix project run`

Führt alle Phasen eines Projekts aus.

```bash
helix project run <name> [--resume] [--dry-run] [--timeout 600]
```

**Optionen:**
- `--resume`: Setzt bei letzter abgeschlossener Phase fort
- `--dry-run`: Simuliert Ausführung ohne Claude CLI
- `--timeout`: Timeout pro Phase in Sekunden (Standard: 600)

**Beispiele:**
```bash
# Normaler Lauf
helix project run my-feature

# Nach Fehler fortsetzen
helix project run my-feature --resume

# Testen ohne Ausführung
helix project run my-feature --dry-run
```

### `helix project status`

Zeigt den aktuellen Status eines Projekts.

```bash
helix project status <name>
```

**Ausgabe:**
```
Project: my-feature
Status: running
Progress: 2/4 phases
Started: 2025-12-23 10:00:00

Phases:
  [OK] consultant: completed
  [OK] development: completed
  [...] review: running
  [   ] integration: pending
```

### `helix project list`

Listet alle Projekte mit Status.

```bash
helix project list
```

### `helix project reset`

Setzt den Projekt-Status zurück.

```bash
helix project reset <name> [--force]
```

### `helix project delete`

Löscht ein Projekt vollständig.

```bash
helix project delete <name> [--force]
```

---

## Projekt-Struktur

Nach `helix project create my-feature`:

```
projects/external/my-feature/
├── phases.yaml          # Phase-Definitionen
├── status.yaml          # Orchestrator-Status (automatisch)
│
└── phases/
    ├── consultant/
    │   ├── CLAUDE.md    # Instruktionen für Claude
    │   ├── input/       # Inputs (vom Orchestrator befüllt)
    │   └── output/      # Outputs (von Claude erstellt)
    │
    ├── development/
    │   ├── CLAUDE.md
    │   ├── input/       # ← Enthält consultant/output/*
    │   └── output/
    │
    └── review/
        ├── CLAUDE.md
        ├── input/       # ← Enthält development/output/*
        └── output/
```

---

## phases.yaml Konfiguration

```yaml
project:
  name: my-feature
  type: simple

phases:
  - id: consultant
    type: consultant
    quality_gate:
      type: adr_valid

  - id: development
    type: development
    input_from: [consultant]
    quality_gate:
      type: syntax_check
      language: python

  - id: review
    type: review
    input_from: [consultant, development]
    quality_gate:
      type: review_approved

  - id: integration
    type: integration
    input_from: [development, review]
    quality_gate:
      type: tests_pass
      command: pytest
```

### Phase-Optionen

| Option | Beschreibung |
|--------|--------------|
| `id` | Eindeutige ID der Phase |
| `type` | Phase-Typ (siehe unten) |
| `input_from` | Liste von Phase-IDs für Input |
| `quality_gate` | Gate-Konfiguration |
| `config.model` | LLM-Modell (opus, sonnet) |
| `config.timeout` | Phase-spezifisches Timeout |

### Phase-Typen

| Typ | Beschreibung | Standard-Gates |
|-----|--------------|----------------|
| `consultant` | ADR erstellen | `adr_valid` |
| `development` | Code implementieren | `syntax_check`, `tests_pass` |
| `review` | Code reviewen | `review_approved` |
| `testing` | Tests ausführen | `tests_pass` |
| `integration` | Integrieren | `tests_pass` |
| `feasibility` | POC erstellen | `files_exist` |
| `planning` | Phasen planen | `files_exist` |

---

## Datenfluss

Der Orchestrator kopiert automatisch Outputs zu Inputs:

```
Phase 1 (consultant)
  └── output/
      ├── ADR-feature.md
      └── spec.yaml
           │
           ▼ (automatisch kopiert)
Phase 2 (development)
  └── input/
      ├── ADR-feature.md    ← von consultant
      ├── spec.yaml         ← von consultant
      └── phases.yaml       ← Projekt-Datei
```

### Input-Patterns

```yaml
# Alle Outputs übernehmen
input_from: [phase1]

# Nur bestimmte Dateien
input_from:
  phase1:
    - "*.yaml"
    - "src/**/*.py"

# Von mehreren Phasen
input_from: [phase1, phase2]
```

---

## Quality Gates

Gates werden nach jeder Phase geprüft:

```yaml
quality_gate:
  type: syntax_check
  language: python
```

### Verfügbare Gates

| Gate | Beschreibung | Parameter |
|------|--------------|-----------|
| `files_exist` | Prüft ob Dateien existieren | `files: [...]` |
| `syntax_check` | Prüft Code-Syntax | `language: python` |
| `tests_pass` | Führt Tests aus | `command: pytest` |
| `review_approved` | Prüft Review-Status | `file: review.json` |
| `adr_valid` | Validiert ADR-Format | `file: ADR-*.md` |

### Retry-Logik

Bei Gate-Failure:
1. Phase wird erneut ausgeführt (max 3x)
2. Nach 3 Fehlversuchen: Projekt-Abbruch
3. Mit `--resume` kann nach Fix fortgesetzt werden

---

## Status-Tracking

Der Status wird in `status.yaml` gespeichert:

```yaml
project_id: my-feature
status: running          # pending, running, completed, failed
total_phases: 4
completed_phases: 2
started_at: 2025-12-23T10:00:00
phases:
  consultant:
    status: completed
    started_at: 2025-12-23T10:00:00
    completed_at: 2025-12-23T10:05:00
  development:
    status: completed
    retries: 1
```

### Resume nach Fehler

```bash
# Fehler tritt auf
helix project run my-feature
# → failed at phase: review

# Problem beheben, dann:
helix project run my-feature --resume
# → Springt zu review, überspringt abgeschlossene Phasen
```

---

## API Endpoints

Der Orchestrator bietet REST API:

### POST /project/{name}/run

```bash
curl -X POST "http://localhost:8001/project/my-feature/run" \
  -H "Content-Type: application/json" \
  -d '{"resume": false, "dry_run": false}'
```

### GET /project/{name}/status

```bash
curl "http://localhost:8001/project/my-feature/status"
```

### GET /projects

```bash
curl "http://localhost:8001/projects"
```

### POST /project

```bash
curl -X POST "http://localhost:8001/project" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-feature", "project_type": "simple"}'
```

---

## Konfiguration

### config/phase-types.yaml

Definiert Standard-Gates pro Phase-Typ:

```yaml
phase_types:
  development:
    default_gates:
      - type: syntax_check
        language: python
      - type: tests_pass
        command: pytest
    timeout: 1200

project_types:
  simple:
    default_phases:
      - consultant
      - development
      - review
      - integration
```

---

## Best Practices

### 1. Projekt-Typen richtig wählen

- `simple` für Standard-Features
- `complex` wenn unklar ob machbar
- `exploratory` für Forschung

### 2. CLAUDE.md gut schreiben

```markdown
# Phase: Development

## Kontext
Lies die Dateien in `input/`:
- `ADR-feature.md` - Was gebaut werden soll
- `spec.yaml` - Technische Details

## Aufgabe
Implementiere das Feature gemäß ADR.

## Output
Schreibe nach `output/`:
- `src/` - Python Code
- `tests/` - Pytest Tests

## Quality Gate
- Syntax muss korrekt sein
- Tests müssen durchlaufen
```

### 3. Dry-Run vor echtem Lauf

```bash
helix project run my-feature --dry-run
```

### 4. Status regelmäßig prüfen

```bash
helix project status my-feature
```

### 5. Bei Fehler analysieren und fixen

```bash
# Status zeigt Fehler
helix project status my-feature
# → Error: tests_pass failed

# Log prüfen, Problem beheben
vim phases/development/output/src/main.py

# Fortsetzen
helix project run my-feature --resume
```

---

## Troubleshooting

### "Project not found"

```bash
# Prüfen ob Projekt existiert
ls projects/external/
```

### "Phase timed out"

```bash
# Timeout erhöhen
helix project run my-feature --timeout 1200
```

### "Gate failed after 3 retries"

```bash
# Status prüfen
helix project status my-feature

# Phase manuell prüfen
cat projects/external/my-feature/phases/development/output/...

# Nach Fix: Resume
helix project run my-feature --resume
```

### "Status stuck at running"

```bash
# Reset und neu starten
helix project reset my-feature
helix project run my-feature
```

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    OrchestratorRunner                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │PhaseExecutor│  │DataFlowMgr  │  │StatusTracker│          │
│  │             │  │             │  │             │          │
│  │ Spawnt CLI  │  │ Kopiert I/O │  │ status.yaml │          │
│  │ Wartet      │  │ Glob        │  │ Resume      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
│  Für jede Phase:                                             │
│  1. Data Flow: outputs → inputs                              │
│  2. Execute: Claude CLI in phase_dir                         │
│  3. Check Gates: Validiere Output                            │
│  4. Update Status: Persistiere in YAML                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Weitere Ressourcen

- [ADR-017: Phase Orchestrator](../adr/017-phase-orchestrator.md) - Spezifikation
- [ARCHITECTURE-ORCHESTRATOR.md](ARCHITECTURE-ORCHESTRATOR.md) - Design
- [config/phase-types.yaml](../config/phase-types.yaml) - Konfiguration
