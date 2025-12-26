# Roadmap: Consultant Workflow System

> **Ziel:** Consultant startet Workflows (nicht Tools) mit Sub-Agent Verifikation

---

## Deine Vision (verstanden)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW-BASIERT (nicht Tool-basiert)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User: "Erstelle ADR für Feature X"                                     │
│         ↓                                                               │
│  Consultant: lädt "adr-intern-workflow"                                 │
│         ↓                                                               │
│  Phase 1: Skill lesen → ADR schreiben                                   │
│         ↓                                                               │
│  Phase 2: Sub-Agent verifiziert (Sections? Format? Valid?)              │
│         ↓                                                               │
│  Fail? → Zurück zu Phase 1 (Korrektur im laufenden Prozess)             │
│         ↓                                                               │
│  Success → ADR nach /adr/ kopieren                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Projekt-Typ Matrix

```
                    │  LEICHT (simple)       │  KOMPLEX (complex)
────────────────────┼────────────────────────┼────────────────────────────
                    │                        │
  INTERN            │  Planning              │  Feasibility
  (helix_internal)  │  → Programmieren       │  → Planning (1-5 Steps)
                    │  → Verifizieren        │  → [dynamische Phasen]
                    │  → Dokumentieren       │  → Verifizieren
                    │  → Deploy to Test      │  → Dokumentieren
                    │  → E2E Tests           │  → Deploy to Test
                    │  → Deploy to Prod      │  → E2E Tests
                    │                        │  → Deploy to Prod
────────────────────┼────────────────────────┼────────────────────────────
                    │                        │
  EXTERN            │  Planning              │  Feasibility
  (external)        │  → Programmieren       │  → Planning (1-5 Steps)
                    │  → Verifizieren        │  → [dynamische Phasen]
                    │  → Dokumentieren       │  → Verifizieren
                    │  → (Tests optional)    │  → Dokumentieren
                    │                        │
────────────────────┴────────────────────────┴────────────────────────────
```

---

## Was bereits existiert ✅

### Dokumentation

| Dokument | Was es beschreibt | Status |
|----------|-------------------|--------|
| `docs/ARCHITECTURE-ORCHESTRATOR.md` | Simple/Complex/Exploratory Typen | ✅ Vorhanden |
| `docs/ADR-TEMPLATE.md` | `project_type: helix_internal \| external` | ✅ Vorhanden |
| `skills/helix/evolution/SKILL.md` | Deploy → Validate → Integrate | ✅ Vorhanden |
| `skills/helix/workflows.md` | Feature/Bugfix/Research Workflows | ✅ Vorhanden |
| `templates/project-types/` | feature.yaml, bugfix.yaml, research.yaml | ✅ Vorhanden |

### ADRs (relevant)

| ADR | Titel | Status | Relevant für |
|-----|-------|--------|--------------|
| ADR-011 | Post-Phase Verification | ✅ Implemented | Sub-Agent Verifikation |
| ADR-012 | ADR als Single Source of Truth | ✅ Implemented | ADR-basierte Workflows |
| ADR-017 | Phase Orchestrator | ✅ Implemented | Workflow-Ausführung |
| ADR-022 | Unified API Architecture | ✅ Implemented | API für Workflows |

### Code

| Modul | Funktion | Status |
|-------|----------|--------|
| `src/helix/api/orchestrator.py` | UnifiedOrchestrator | ✅ Funktioniert |
| `src/helix/evolution/` | Deploy, Validate, Integrate | ✅ Vorhanden |
| `src/helix/tools/verify_phase.py` | Phase-Verifikation | ✅ Vorhanden |
| `src/helix/tools/adr_tool.py` | ADR Validation | ✅ Vorhanden |

---

## Was FEHLT ❌ (Gap)

### 1. Workflow-Definitionen für Projekt-Typen

```
❌ FEHLT: templates/workflows/
   ├── intern-simple.yaml      # Leichtes internes Projekt
   ├── intern-complex.yaml     # Komplexes internes Projekt
   ├── extern-simple.yaml      # Leichtes externes Projekt
   └── extern-complex.yaml     # Komplexes externes Projekt
```

**Existiert nur:**
- `templates/project-types/feature.yaml` (generisch, keine intern/extern Unterscheidung)

### 2. Consultant kennt Workflows nicht

```
❌ FEHLT im Consultant Template:
   - Welche Workflows gibt es?
   - Wie startet man einen Workflow?
   - Wie unterscheidet man intern/extern, leicht/komplex?
```

**Existiert:**
- `templates/consultant/session.md.j2` - aber ohne Workflow-Wissen

### 3. Sub-Agent Verifikation im Workflow

```
❌ FEHLT: Feedback-Loop im laufenden Prozess
   
   Aktuell:
   Phase 1 → Quality Gate FAIL → Abbruch
   
   Gewünscht:
   Phase 1 → Sub-Agent prüft → FAIL → Korrektur → Retry
```

**Existiert:**
- `src/helix/tools/verify_phase.py` - aber nur als Tool, nicht als Sub-Agent

### 4. Workflow-Starter für Consultant

```
❌ FEHLT: Mechanismus für Consultant um Workflow zu laden
   
   Consultant: "Ok, das ist ein internes, komplexes Projekt"
            → Lädt `intern-complex.yaml`
            → Startet Phase 1
```

**Existiert:**
- `/helix/execute` API - aber Consultant weiß nicht davon

### 5. Dynamische Phasen-Generierung

```
❌ FEHLT: Consultant/Planning-Agent erstellt Phasen dynamisch
   
   Komplex → Feasibility → "Brauche 3 Dev-Phasen"
                        → Generiert phases 2-4
```

**Existiert:**
- `docs/ARCHITECTURE-ORCHESTRATOR.md` beschreibt es
- Aber nicht implementiert

---

## Roadmap: Was muss gebaut werden?

### Phase 1: Workflow-Definitionen (ADR-023)

**Erstellen:**
```
templates/workflows/
├── intern-simple.yaml
├── intern-complex.yaml
├── extern-simple.yaml
└── extern-complex.yaml
```

**Beispiel `intern-simple.yaml`:**
```yaml
name: intern-simple
description: Leichtes internes HELIX-Projekt
project_type: helix_internal
complexity: simple

phases:
  - id: planning
    type: consultant
    template: consultant/planning.md
    output: [ADR-*.md, phases.yaml]
    gate: adr_valid
    
  - id: development
    type: development
    template: developer/python.md
    gate: [syntax_check, tests_pass]
    verify_agent: true  # Sub-Agent prüft
    
  - id: documentation
    type: documentation
    template: documentation/technical.md
    gate: files_exist
    
  - id: deploy-test
    type: deploy
    target: test
    gate: e2e_pass
    
  - id: deploy-prod
    type: deploy
    target: production
    gate: integration_pass
```

### Phase 2: Consultant Workflow-Wissen (ADR-024)

**Erweitern `templates/consultant/session.md.j2`:**
```markdown
## Verfügbare Workflows

| Projekt-Typ | Workflow | Beschreibung |
|-------------|----------|--------------|
| Intern + Leicht | `intern-simple` | ADR → Dev → Test → Prod |
| Intern + Komplex | `intern-complex` | Feasibility → Planning → Dev |
| Extern + Leicht | `extern-simple` | Planning → Dev → Docs |
| Extern + Komplex | `extern-complex` | Feasibility → Planning → Dev |

## Workflow starten

Wenn du einen Workflow starten willst:
1. Erstelle `phases.yaml` basierend auf Workflow-Template
2. Rufe API auf: `curl -X POST http://localhost:8001/helix/execute`
```

### Phase 3: Sub-Agent Verifikation (ADR-025)

**Erweitern `src/helix/api/orchestrator.py`:**
```python
async def run_phase_with_verification(self, phase, max_retries=3):
    for attempt in range(max_retries):
        result = await self.run_phase(phase)
        
        # Sub-Agent prüft
        verification = await self.verify_with_subagent(result)
        
        if verification.success:
            return result
        
        # Feedback an laufenden Prozess
        await self.send_correction(phase, verification.feedback)
    
    raise MaxRetriesExceeded()
```

### Phase 4: Dynamische Phasen (ADR-026)

**Nach Feasibility:**
```python
# Planning-Agent Output
decomposed_phases:
  - id: dev-data-layer
    estimated_sessions: 1
  - id: dev-api-layer
    estimated_sessions: 2
  - id: dev-ui
    estimated_sessions: 1
```

---

## Zusammenfassung

| Was | Status | Nächster Schritt |
|-----|--------|------------------|
| Projekt-Typ Matrix | ❌ Nicht implementiert | ADR-023: Workflow-Definitionen |
| Consultant Workflow-Wissen | ❌ Fehlt | ADR-024: Template erweitern |
| Sub-Agent Verifikation | ⚠️ Tool existiert | ADR-025: In Workflow integrieren |
| Dynamische Phasen | ⚠️ Dokumentiert | ADR-026: Implementieren |
| API Endpoints | ✅ Vorhanden | - |
| UnifiedOrchestrator | ✅ Implementiert | - |

---

## Empfohlene Reihenfolge

```
ADR-023: Workflow-Definitionen (Templates)
    ↓
ADR-024: Consultant Workflow-Wissen
    ↓
ADR-025: Sub-Agent Verifikation Loop
    ↓
ADR-026: Dynamische Phasen-Generierung
```

**Geschätzter Aufwand:** 4 ADRs, ~2-3 Claude Code Sessions pro ADR

---

*Erstellt: 2025-12-26*
*Basierend auf: Conversation mit Uwe*
