# Phase 2: Workflow-Definitionen (ADR-023)

Du bist ein Claude Code Entwickler der Workflow-Templates für HELIX v4 erstellt.

---

## 🎯 Ziel

Erstelle Workflow-Definitionen für alle 4 Projekt-Typen:

| Projekt-Typ | Datei | Beschreibung |
|-------------|-------|--------------|
| Intern + Leicht | `intern-simple.yaml` | ADR → Dev → Verify → Docs → Deploy-Test → E2E → Deploy-Prod |
| Intern + Komplex | `intern-complex.yaml` | Planning-Agent → Dynamische Phasen → Deploy |
| Extern + Leicht | `extern-simple.yaml` | Planning → Dev → Verify → Docs |
| Extern + Komplex | `extern-complex.yaml` | Planning-Agent → Dynamische Phasen |

---

## 📚 Zuerst lesen

1. `docs/ARCHITECTURE-ORCHESTRATOR.md` - Projekt-Typen Konzept
2. `docs/ROADMAP-CONSULTANT-WORKFLOWS.md` - Entscheidungen
3. `templates/project-types/feature.yaml` - Bestehendes Template
4. `skills/helix/evolution/SKILL.md` - Evolution Workflow

---

## 📋 Aufgaben

### 1. ADR-023 erstellen

Erstelle `output/adr/023-workflow-definitions.md`:

```yaml
---
adr_id: "023"
title: "Workflow-Definitionen für Projekt-Typen"
status: Proposed
project_type: helix_internal
component_type: CONFIG
classification: NEW
change_scope: minor

files:
  create:
    - templates/workflows/intern-simple.yaml
    - templates/workflows/intern-complex.yaml
    - templates/workflows/extern-simple.yaml
    - templates/workflows/extern-complex.yaml
  docs:
    - docs/WORKFLOW-DEFINITIONS.md
---
```

### 2. Workflow Templates erstellen

#### `templates/workflows/intern-simple.yaml`

```yaml
name: intern-simple
description: Leichtes internes HELIX-Projekt
project_type: helix_internal
complexity: simple

phases:
  - id: planning
    type: consultant
    template: consultant/planning.md
    output: [ADR-*.md]
    gate: adr_valid
    
  - id: development
    type: development
    template: developer/python.md
    gate: syntax_check
    sub_agent_verify: true
    max_retries: 3
    
  - id: verify
    type: verification
    gate: tests_pass
    
  - id: documentation
    type: documentation
    template: documentation/technical.md
    gate: files_exist
    
  - id: deploy-test
    type: deploy
    target: test
    script: scripts/deploy-test.sh
    gate: deploy_success
    
  - id: e2e
    type: test
    script: scripts/run-e2e.sh
    gate: e2e_pass
    
  - id: deploy-prod
    type: deploy
    target: production
    script: scripts/deploy-prod.sh
    gate: integration_pass

on_phase_fail:
  max_retries: 3
  escalate_to: consultant
  final_action: abort

phase_reset:
  enabled: true
  allowed_by: [user, consultant, orchestrator]
```

#### Ähnlich für die anderen 3 Workflows

### 3. Dokumentation

Erstelle `output/docs/WORKFLOW-DEFINITIONS.md`:
- Übersicht aller Workflows
- Wann welchen nutzen
- Phase-Beschreibungen

---

## 📁 Output

| Datei | Beschreibung |
|-------|--------------|
| `output/adr/023-workflow-definitions.md` | ADR |
| `output/templates/workflows/intern-simple.yaml` | Intern + Leicht |
| `output/templates/workflows/intern-complex.yaml` | Intern + Komplex |
| `output/templates/workflows/extern-simple.yaml` | Extern + Leicht |
| `output/templates/workflows/extern-complex.yaml` | Extern + Komplex |
| `output/docs/WORKFLOW-DEFINITIONS.md` | Dokumentation |

---

## ✅ Quality Gate

- [ ] ADR-023 valide (YAML + Sections)
- [ ] Alle 4 Workflow-Templates existieren
- [ ] YAML Syntax valide
- [ ] Alle Phasen definiert laut Entscheidungen:
  - intern-simple: 7 Phasen (planning → deploy-prod)
  - intern-complex: planning-agent + max 5 dynamische + deploy
  - extern-simple: 4 Phasen (planning → documentation)
  - extern-complex: planning-agent + max 5 dynamische

---

## 🔗 Referenzen

- Entscheidungen: `docs/ROADMAP-CONSULTANT-WORKFLOWS.md`
- Phase-Reset: enabled für user, consultant, orchestrator
- Sub-Agent Verify: 3 Retries, dann Eskalation
