# HELIX v4 Workflow System

> **Workflow-basierte Projekt-Orchestrierung**
>
> Basierend auf: ADR-023, ADR-024, ADR-025, ADR-026

---

## Workflow-Matrix

|  | **Simple** | **Complex** |
|---|---|---|
| **Intern** (`helix_internal`) | `intern-simple` | `intern-complex` |
| **Extern** (`external`) | `extern-simple` | `extern-complex` |

---

## Workflow-Templates

Templates in `/templates/workflows/`:

### `intern-simple` (7 Phasen)

```
Planning → Development → Verify → Documentation → Deploy-Test → E2E → Deploy-Prod
```

- Für klare, gut definierte HELIX Features
- Vollständiger Deploy-Zyklus mit Test-System
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

---

## Wann welcher Workflow?

### Intern vs Extern

**Intern (`helix_internal`)**:
- Ändert `src/helix/`, `adr/`, `skills/`
- Braucht Deploy-to-Test → E2E → Deploy-to-Prod

**Extern (`external`)**:
- Lebt in `projects/external/`
- Kein HELIX-Integration nötig

### Simple vs Complex

**Simple**:
- Scope ist klar definiert
- < 5 Dateien betroffen
- 1-2 Claude Code Sessions

**Complex**:
- Scope unklar oder groß
- Braucht Zerlegung in Teilaufgaben
- Feasibility-Prüfung sinnvoll

---

## Sub-Agent Verifikation (ADR-025)

Jede Phase mit `verify_agent: true` wird nach Abschluss geprüft.

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
                   Eskalation
```

### Konfiguration

```yaml
# In workflow template
max_retries: 3

phases:
  - id: development
    verify_agent: true  # Aktiviert Verifikation
```

---

## Dynamische Phasen (ADR-026)

Der PlanningAgent analysiert den Scope und generiert dynamisch 1-5 Phasen.

### Ablauf

```
Projekt-Beschreibung
        ↓
   PlanningAgent (Sonnet)
        ↓
   Scope-Analyse
        ↓
  ┌─────┴─────┐
  ↓           ↓
Klar      Unklar
  ↓           ↓
1-5 Phasen  Feasibility + 1-5 Phasen
```

### Output

- `phases.yaml` - Generierte Phasen
- `CLAUDE.md` pro Phase - Spezifische Anweisungen
- `decomposed-phases.yaml` - Details

---

## Workflow starten

```bash
# 1. Projekt-Verzeichnis erstellen
mkdir -p projects/internal/my-feature/phases

# 2. Template kopieren
cp templates/workflows/intern-simple.yaml projects/internal/my-feature/phases.yaml

# 3. Via API starten
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/internal/my-feature/"}'

# 4. Status prüfen
curl http://localhost:8001/helix/jobs
```

---

## Dokumentation

- [docs/WORKFLOW-SYSTEM.md](../../docs/WORKFLOW-SYSTEM.md) - Vollständige Dokumentation
- [templates/consultant/workflow-guide.md](../../templates/consultant/workflow-guide.md) - Consultant Guide
- [adr/023-workflow-definitions.md](../../adr/023-workflow-definitions.md) - ADR-023
- [adr/025-sub-agent-verification.md](../../adr/025-sub-agent-verification.md) - ADR-025
- [adr/026-dynamic-phase-generation.md](../../adr/026-dynamic-phase-generation.md) - ADR-026
