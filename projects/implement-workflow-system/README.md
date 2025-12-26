# Projekt: Workflow System Implementation

> Implementiert ADR-018 (LSP) + ADR-023 bis ADR-026 (Workflow System)

---

## Übersicht

Dieses Projekt implementiert das vollständige Consultant Workflow System:

| Phase | ADR | Was wird implementiert |
|-------|-----|------------------------|
| 1 | ADR-018 | LSP Integration für bessere Code-Intelligence |
| 2 | ADR-023 | Workflow-Definitionen (4 Projekt-Typen) |
| 3 | ADR-024 | Consultant Workflow-Wissen |
| 4 | ADR-025 | Sub-Agent Verifikation mit Retry-Loop |
| 5 | ADR-026 | Dynamische Phasen für komplexe Projekte |
| 6 | - | Integration & E2E Tests |

---

## Starten

### Option A: Via API

```bash
# Phase 1 starten
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/implement-workflow-system", "phase": 1}'

# Status prüfen
curl http://localhost:8001/helix/jobs
```

### Option B: Via CLI

```bash
cd /home/aiuser01/helix-v4
helix run projects/implement-workflow-system --phase 1
```

### Option C: Direkt mit Claude Code

```bash
cd /home/aiuser01/helix-v4/projects/implement-workflow-system/phases/1
claude --dangerously-skip-permissions
# Dann: "Lies CLAUDE.md und führe die Aufgaben aus"
```

---

## Entscheidungen

Basierend auf Diskussion vom 2025-12-26:

| Frage | Entscheidung |
|-------|--------------|
| Phasen intern-simple | 7: Planning → Dev → Verify → Docs → Deploy-Test → E2E → Deploy-Prod |
| Phasen extern-simple | 4: Planning → Dev → Verify → Docs |
| Externe Projekte | `projects/external/{name}/` |
| Intern vs Extern | Consultant fragt wenn unklar |
| Leicht vs Komplex | User sagt oder Consultant schätzt |
| Max Retries | 3 pro Phase |
| Bei finalem Fail | Eskalation → Consultant → Abbruch |
| Feedback | In gleicher Session via Sub-Agent |
| Dynamische Phasen | Planning-Agent generiert 1-5 |
| Phase Reset | Möglich durch User, Consultant, Orchestrator |

---

## Struktur

```
projects/implement-workflow-system/
├── README.md           # Diese Datei
├── phases.yaml         # Projekt-Definition
└── phases/
    ├── 1/              # LSP Integration
    │   ├── CLAUDE.md
    │   ├── input/
    │   └── output/
    ├── 2/              # Workflow-Definitionen
    │   └── ...
    ├── 3/              # Consultant Workflow-Wissen
    │   └── ...
    ├── 4/              # Sub-Agent Verifikation
    │   └── ...
    ├── 5/              # Dynamische Phasen
    │   └── ...
    └── 6/              # Integration & E2E
        └── ...
```

---

## Nach Abschluss

Wenn alle Phasen erfolgreich:

1. **4 neue ADRs** in `adr/`:
   - ADR-023: Workflow-Definitionen
   - ADR-024: Consultant Workflow-Wissen
   - ADR-025: Sub-Agent Verifikation
   - ADR-026: Dynamische Phasen

2. **Neue Module** in `src/helix/`:
   - `verification/sub_agent.py`
   - `verification/feedback.py`
   - `planning/agent.py`
   - `planning/phase_generator.py`

3. **Neue Templates** in `templates/`:
   - `workflows/intern-simple.yaml`
   - `workflows/intern-complex.yaml`
   - `workflows/extern-simple.yaml`
   - `workflows/extern-complex.yaml`

4. **Erweitertes Consultant Template**

5. **E2E Tests** in `tests/integration/`

---

*Erstellt: 2025-12-26*
