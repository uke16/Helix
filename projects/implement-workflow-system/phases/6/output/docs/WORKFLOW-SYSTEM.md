# HELIX Workflow System

> **Workflow-basierte Projekt-Orchestrierung statt Tool-Aufrufe**

---

## Übersicht

Das Workflow-System ermöglicht dem Consultant, vollständige Entwicklungs-Workflows zu starten statt einzelne Tools aufzurufen. Jeder Workflow definiert eine Sequenz von Phasen mit automatischer Verifikation.

### Kernkonzepte

```
User → Consultant → Workflow → [Phase 1 → Verify] → [Phase 2 → Verify] → ... → Done
                                      ↓
                                  Sub-Agent prüft
                                      ↓
                              Feedback bei Fail (3x)
                                      ↓
                              Eskalation bei final Fail
```

---

## Projekt-Typen

Das System unterscheidet Projekte nach zwei Dimensionen:

### Projekt-Matrix

|  | **Simple** | **Complex** |
|---|---|---|
| **Intern** (`helix_internal`) | `intern-simple` | `intern-complex` |
| **Extern** (`external`) | `extern-simple` | `extern-complex` |

### Wann welcher Typ?

| Typ | Wann verwenden | Beispiele |
|-----|----------------|-----------|
| **Intern + Simple** | HELIX Feature, klarer Scope, <5 Dateien | Neues Tool, Bug Fix, Config-Änderung |
| **Intern + Complex** | HELIX Feature, unklarer Scope, groß | Modul-Refactoring, neues System |
| **Extern + Simple** | Externes Tool, klarer Scope | CLI Tool, Script, Helper |
| **Extern + Complex** | Externes Projekt, groß | Vollständige Anwendung |

---

## Workflows im Detail

### `intern-simple` (7 Phasen)

```
Planning → Development → Verify → Documentation → Deploy-Test → E2E → Deploy-Prod
```

- Für klare, gut definierte HELIX Features
- Vollständiger Deploy-Zyklus
- Sub-Agent Verifikation nach jeder Phase

### `intern-complex` (Dynamisch + 5 Standard-Phasen)

```
[Feasibility] → Planning-Agent → [1-5 dynamische Phasen] → Verify → Docs → Deploy-Test → E2E → Deploy-Prod
```

- Planning-Agent analysiert Scope
- Generiert 1-5 Entwicklungsphasen dynamisch
- Optional: Feasibility-Studie bei unklarem Scope

### `extern-simple` (4 Phasen)

```
Planning → Development → Verify → Documentation
```

- Kein HELIX Deploy-Zyklus
- Für eigenständige Tools/Projekte

### `extern-complex` (Dynamisch + 2 Standard-Phasen)

```
[Feasibility] → Planning-Agent → [1-5 dynamische Phasen] → Verify → Documentation
```

- Dynamische Phasen wie `intern-complex`
- Ohne Deploy-Zyklus

---

## Sub-Agent Verifikation (ADR-025)

Jede Phase mit `verify_agent: true` wird nach Abschluss geprüft.

### Ablauf

```
Phase abgeschlossen
       ↓
Sub-Agent (Haiku) prüft Output
       ↓
   ┌───┴───┐
   ↓       ↓
Success   Fail
   ↓       ↓
Weiter   Feedback → Retry (max 3x)
                        ↓
                   Final Fail
                        ↓
                   Eskalation → Abbruch
```

### Konfiguration

```yaml
# In workflow template
phases:
  - id: development
    verify_agent: true  # Aktiviert Sub-Agent Verifikation

# Projekt-Level
max_retries: 3  # Anzahl Retries pro Phase
```

### Feedback-Mechanismus

Bei Fail schreibt der Sub-Agent eine `feedback.md`:

```markdown
# Verification Feedback

**Attempt**: 2/3

## Issues Found
- Missing file: tests/test_module.py
- Syntax error in src/module.py line 42

## Required Actions
Please fix the issues and update your output.
```

---

## Dynamische Phasen (ADR-026)

Komplexe Projekte starten mit einem Planning-Agent.

### Ablauf

```
Projekt-Beschreibung
        ↓
   PlanningAgent
        ↓
   Scope-Analyse
        ↓
  ┌─────┴─────┐
  ↓           ↓
Klar      Unklar
  ↓           ↓
1-5 Phasen  Feasibility + 1-5 Phasen
```

### Phase-Generierung

Der Planning-Agent erstellt:
1. `phases.yaml` mit dynamischen Phasen
2. `CLAUDE.md` pro Phase
3. `decomposed-phases.yaml` mit Details

### Beispiel Output

```yaml
# decomposed-phases.yaml
feasibility_needed: false
reasoning: "Clear requirements, 3 components"
phases:
  - id: dev-1
    name: "Data Layer"
    type: development
    estimated_sessions: 1
  - id: dev-2
    name: "API Layer"
    type: development
    estimated_sessions: 2
    dependencies: [dev-1]
  - id: dev-3
    name: "Frontend Integration"
    type: development
    estimated_sessions: 1
    dependencies: [dev-2]
```

---

## API Reference

### Workflow starten

```bash
POST /helix/execute
Content-Type: application/json

{
  "project_path": "projects/internal/my-feature/",
  "phase_filter": null
}

# Response
{
  "job_id": "abc123",
  "status": "running"
}
```

### Job Status

```bash
GET /helix/jobs/{job_id}

# Response
{
  "job_id": "abc123",
  "status": "running",
  "current_phase": "development",
  "progress": 0.5
}
```

### Alle Jobs

```bash
GET /helix/jobs?limit=20
```

### Job abbrechen

```bash
DELETE /helix/jobs/{job_id}
```

### Live Stream (SSE)

```bash
GET /helix/stream/{job_id}

# Event Stream
event: phase_start
data: {"phase": "development"}

event: output
data: {"line": "Creating src/module.py..."}

event: phase_complete
data: {"phase": "development", "success": true}
```

### Phase Reset

```bash
POST /helix/execute
Content-Type: application/json

{
  "project_path": "projects/internal/my-feature/",
  "phase_filter": "2",
  "reset": true
}
```

---

## Consultant Workflow-Auswahl

Der Consultant wählt den Workflow basierend auf:

### 1. Intern vs Extern

**Frage an User wenn unklar:**
> "Betrifft dieses Feature HELIX selbst, oder ist es ein separates Projekt?"

- **Intern**: Ändert `src/helix/`, `adr/`, `skills/`
- **Extern**: Lebt in `projects/external/`

### 2. Simple vs Complex

- **Simple**: Scope klar, <5 Files, 1-2 Sessions
- **Complex**: Scope unklar, braucht Planning

### Workflow starten

```bash
# 1. Projekt-Verzeichnis
mkdir -p projects/internal/my-feature/phases

# 2. Template kopieren
cp templates/workflows/intern-simple.yaml projects/internal/my-feature/phases.yaml

# 3. Via API starten
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/internal/my-feature/"}'

# 4. Status
curl http://localhost:8001/helix/jobs
```

---

## Troubleshooting

### Phase schlägt wiederholt fehl

1. Prüfe `feedback.md` im Phase-Verzeichnis
2. Behebe die genannten Issues manuell
3. Reset und neu starten:

```bash
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "...", "phase_filter": "N", "reset": true}'
```

### Eskalation aufgetreten

1. Prüfe `escalation.md` im Projekt-Root
2. Review der Phase-Outputs
3. Entscheide: Fix oder Skip

### Planning-Agent generiert zu viele/wenige Phasen

Passe `max_phases` in der Workflow-Konfiguration an:

```yaml
# templates/workflows/intern-complex.yaml
max_dynamic_phases: 3  # Reduziert auf max 3
```

---

## ADRs

| ADR | Titel | Status |
|-----|-------|--------|
| ADR-023 | Workflow-Definitionen | Proposed |
| ADR-024 | Consultant Workflow-Wissen | Proposed |
| ADR-025 | Sub-Agent Verifikation | Proposed |
| ADR-026 | Dynamische Phasen | Proposed |

---

## Quick Reference

```bash
# Intern Simple (HELIX Feature, klar)
cp templates/workflows/intern-simple.yaml projects/internal/X/phases.yaml
curl -X POST localhost:8001/helix/execute -d '{"project_path": "projects/internal/X/"}'

# Intern Complex (HELIX Feature, unklar)
cp templates/workflows/intern-complex.yaml projects/internal/X/phases.yaml
curl -X POST localhost:8001/helix/execute -d '{"project_path": "projects/internal/X/"}'

# Extern Simple (Tool, klar)
cp templates/workflows/extern-simple.yaml projects/external/X/phases.yaml
curl -X POST localhost:8001/helix/execute -d '{"project_path": "projects/external/X/"}'

# Status
curl localhost:8001/helix/jobs

# Reset Phase N
curl -X POST localhost:8001/helix/execute -d '{"project_path": "...", "phase_filter": "N", "reset": true}'
```

---

*Erstellt: 2025-12-26*
*Basierend auf: ADR-023, ADR-024, ADR-025, ADR-026*
