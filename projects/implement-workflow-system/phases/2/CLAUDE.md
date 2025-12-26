# Phase 2: Workflow-Definitionen (ADR-023)

> Erstelle 4 Workflow-Templates für die Projekt-Matrix

---

## 🎯 Aufgabe

Erstelle Workflow-Templates für alle 4 Kombinationen:

| Projekt-Typ | Komplexität | Template |
|-------------|-------------|----------|
| helix_internal | simple | `templates/workflows/intern-simple.yaml` |
| helix_internal | complex | `templates/workflows/intern-complex.yaml` |
| external | simple | `templates/workflows/extern-simple.yaml` |
| external | complex | `templates/workflows/extern-complex.yaml` |

---

## 📋 Workflow-Phasen

### Intern Simple
```
Planning → Development → Verify → Documentation → Deploy-Test → E2E → Deploy-Prod
```

### Intern Complex
```
Planning-Agent → Feasibility (optional) → [1-5 dynamische Phasen] → Verify → Docs → Deploy-Test → E2E → Deploy-Prod
```

### Extern Simple
```
Planning → Development → Verify → Documentation
```

### Extern Complex
```
Planning-Agent → Feasibility (optional) → [1-5 dynamische Phasen] → Verify → Documentation
```

---

## 🔧 Template-Format

```yaml
name: intern-simple
description: Leichtes internes HELIX-Projekt
project_type: helix_internal
complexity: simple
max_retries: 3  # Pro Phase mit Sub-Agent Verifikation

phases:
  - id: planning
    type: consultant
    description: "ADR erstellen"
    template: consultant/planning.md
    verify_agent: true  # Sub-Agent prüft
    
  - id: development
    type: development
    description: "Code implementieren"
    template: developer/python.md
    verify_agent: true
    
  # ... weitere Phasen
```

---

## 📁 Output

Erstelle in `output/`:
1. `templates/workflows/intern-simple.yaml`
2. `templates/workflows/intern-complex.yaml`
3. `templates/workflows/extern-simple.yaml`
4. `templates/workflows/extern-complex.yaml`

Dann:
1. Kopiere nach `../../templates/workflows/`
2. Erstelle ADR-023 in `output/adr/`
3. Validiere: `python -m helix.tools.adr_tool validate output/adr/023-workflow-definitions.md`

---

## ✅ Akzeptanzkriterien

- [ ] 4 Workflow-Templates existieren
- [ ] Jedes Template hat: name, project_type, complexity, phases
- [ ] Phasen haben: id, type, description, verify_agent
- [ ] max_retries: 3 konfiguriert
- [ ] ADR-023 validiert erfolgreich

---

## 📚 Referenzen

- `docs/ROADMAP-CONSULTANT-WORKFLOWS.md` - Gap-Analyse
- `docs/ARCHITECTURE-ORCHESTRATOR.md` - Simple/Complex Konzept
- `skills/helix/evolution/SKILL.md` - Deploy → Validate → Integrate
- `templates/project-types/feature.yaml` - Bestehendes Template
