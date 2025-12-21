# HELIX v4 Bootstrap - Offene Entscheidungen

> **Ziel:** Wir entscheiden die Architektur, dann baut Claude Code das System selbst.
> 
> Das erste Projekt in `projects/internal/helix-v4-bootstrap/` ist HELIX v4 selbst!

---

## 🔴 MUSS entschieden werden (Blocker)

### 1. Claude Code Ausführungs-Modus

**Frage:** Wie starten wir Claude Code pro Phase?

| Option | Pro | Contra |
|--------|-----|--------|
| **A) Interaktiv** (`claude`) | User kann eingreifen | Nicht automatisierbar |
| **B) Non-Interactive** (`claude --print`) | Automatisierbar | Keine Rückfragen möglich |
| **C) Hybrid** | Consultant interaktiv, Rest non-interactive | Komplexer |

**Empfehlung:** Option C - Consultant braucht Dialog, Developer/Reviewer können autonom laufen.

---

### 2. OpenRouter vs. Direkt-API

**Frage:** Nutzen wir OpenRouter oder direkte Anthropic API?

| Option | Pro | Contra |
|--------|-----|--------|
| **A) OpenRouter** | Vendor-unabhängig, Fallbacks | Extra Dependency, Latenz |
| **B) Direkt Anthropic** | Einfacher, schneller | Vendor-Lock |
| **C) Konfigurierbar** | Flexibel | Mehr Code |

**Empfehlung:** Option C - Default OpenRouter, aber umschaltbar.

---

### 3. Projekt-Typen

**Frage:** Welche Projekt-Typen gibt es?

```
projects/
├── internal/           # HELIX selbst entwickeln
│   └── helix-v4-bootstrap/
│
└── external/           # Externe Projekte
    ├── pdm/            # PDM Domain
    └── erp/            # ERP Domain
```

**Zu entscheiden:**
- [ ] Gibt es weitere Typen? (z.B. `experimental/`, `customer/`)
- [ ] Unterschiedliche Permissions pro Typ?

---

### 4. Spec-Format (YAML Schema)

**Frage:** Was MUSS in einer Spec stehen?

```yaml
# Minimal-Schema - reicht das?
meta:
  id: string (required)
  domain: string (required)
  language: string (optional, auto-detect)
  
implementation:
  summary: string (required)
  files_to_create: list (required)
  files_to_modify: list (optional)
  acceptance_criteria: list (required)
  
context:
  relevant_docs: list (optional)
  dependencies: list (optional)
```

**Zu entscheiden:**
- [ ] Schema finalisieren
- [ ] Validierung implementieren?

---

### 5. Quality Gate Verhalten bei Failure

**Frage:** Was passiert wenn ein Quality Gate fehlschlägt?

| Option | Beschreibung |
|--------|--------------|
| **A) Retry** | Gleiche Phase nochmal (max 3x) |
| **B) Escalation** | Meeting mit Consultant + betroffener Agent |
| **C) Abort** | Projekt stoppen, User informieren |
| **D) Konfigurierbar** | Pro Gate einstellbar |

**Empfehlung:** Option D - QG1/QG4 → Retry, QG2/QG3 → Escalation

---

## 🟡 SOLLTE entschieden werden (Wichtig)

### 6. Template-Vererbung

**Frage:** Wie funktioniert Template-Vererbung?

```
templates/developer/_base.md      # Basis für alle Developer
templates/developer/python.md     # Extends _base.md
templates/developer/python-async.md  # Extends python.md ?
```

**Zu entscheiden:**
- [ ] Wie tief darf Vererbung gehen?
- [ ] Gibt es "Mixins" (z.B. `+testing.md`, `+docker.md`)?

---

### 7. Skill-Kategorien

**Frage:** Welche Skill-Kategorien brauchen wir initial?

```
skills/
├── languages/       # Python, C++, Go, etc.
├── tools/           # Git, Docker, K8s, etc.
├── domains/         # PDM, ERP, etc.
├── helix/           # HELIX-spezifisch
└── patterns/        # Design Patterns?
```

**Zu entscheiden:**
- [ ] Initiale Kategorien festlegen
- [ ] Welche Skills von v3 migrieren?

---

### 8. Observability Level

**Frage:** Wie viel loggen wir?

| Level | Was wird geloggt |
|-------|------------------|
| **Minimal** | Nur Errors + Gate Results |
| **Standard** | + Tool Calls + Metriken |
| **Verbose** | + Voller Transcript + Token Details |
| **Debug** | + Interne Orchestrator-State |

**Empfehlung:** Standard als Default, Verbose/Debug per Flag.

---

### 9. Consultant Meeting Format

**Frage:** Wie läuft ein Consultant Meeting ab?

| Phase | Beschreibung |
|-------|--------------|
| 1. Request | User beschreibt was er will |
| 2. Clarification | Consultant fragt nach |
| 3. Context | Consultant liest Domain-Docs |
| 4. Proposal | Consultant schlägt Spec vor |
| 5. Refinement | User gibt Feedback |
| 6. Final | Spec wird geschrieben |

**Zu entscheiden:**
- [ ] Wie viele Iterationen maximal?
- [ ] Wann ist "gut genug"?

---

### 10. Test-Strategie für Bootstrap

**Frage:** Welche Tests brauchen wir für HELIX v4 selbst?

```
tests/
├── unit/
│   ├── test_template_engine.py
│   ├── test_quality_gates.py
│   └── test_context_manager.py
│
├── integration/
│   ├── test_phase_execution.py
│   └── test_orchestrator.py
│
└── e2e/
    ├── test_simple_project.py      # Minimal-Projekt
    ├── test_python_feature.py      # Python Feature
    └── test_full_workflow.py       # Alle Phasen
```

**Zu entscheiden:**
- [ ] Welche E2E Tests sind Minimum?
- [ ] Wie testen wir Claude Code Output? (Mocking vs. Real)

---

## 🟢 KANN später entschieden werden

### 11. Open WebUI Integration
- Wie genau? API? Custom Frontend?

### 12. Multi-User Support
- Brauchen wir User-Isolation?

### 13. Rollback-Mechanismus
- Können wir Phasen rückgängig machen?

### 14. Parallelisierung
- Können mehrere Phasen parallel laufen?

### 15. Cost Limits
- Abbruch bei X$ pro Projekt?

---

## Bootstrap-Projekt Phasen

Wenn alle MUSS-Entscheidungen getroffen sind:

```
Phase 1: Foundation (Claude Code baut)
├── src/helix/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── template_engine.py
│   ├── context_manager.py
│   └── quality_gates.py
├── templates/
│   └── (Basis-Templates)
└── tests/unit/

Phase 2: Templates & Skills (Claude Code baut)
├── templates/
│   ├── consultant/
│   ├── developer/
│   ├── reviewer/
│   └── documentation/
└── skills/
    └── (Migriert von v3)

Phase 3: Integration (Claude Code baut)
├── tests/integration/
└── CLI Tool

Phase 4: E2E Testing (Claude Code testet sich selbst!)
├── Ein echtes Mini-Projekt durchführen
└── Verify: Funktioniert der Workflow?

Phase 5: Open WebUI (Optional)
└── API Integration
```

---

## Nächste Schritte

1. **Jetzt:** MUSS-Entscheidungen treffen (1-5)
2. **Dann:** SOLLTE-Entscheidungen treffen (6-10)
3. **Dann:** Bootstrap-Projekt Spec schreiben
4. **Dann:** Claude Code startet Phase 1

---

*Erstellt: 2025-12-21*
