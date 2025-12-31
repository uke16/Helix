---
adr_id: "040"
title: "Ralph Automation Pattern - Iterative ADR Execution"
status: Proposed

component_type: PROCESS
classification: NEW
change_scope: major

domain: "helix"
language: "python"
skills:
  - helix
  - controller
  - automation

files:
  create:
    - src/helix/ralph/__init__.py
    - src/helix/ralph/promises.py
    - src/helix/ralph/sub_agent.py
    - docs/RALPH-PATTERN.md
  modify:
    - templates/controller/CLAUDE.md.j2
    - templates/adr/template.md.j2
  docs:
    - docs/ARCHITECTURE-MODULES.md
    - adr/INDEX.md
---

## Status

Proposed - 2025-12-31

## Kontext

### Problem

ADR-Implementierung war bisher manuell und fehleranfällig:
- Controller vergessen `files.modify` Schritte
- Keine automatische Verifikation ob Integration funktioniert
- Kein Retry bei Fehlern
- Sub-Agenten (Consultant) werden nicht getestet

### Lösung: Ralph Pattern

Das Ralph Wiggum Pattern (benannt nach Geoffrey Huntley's Technik) ermöglicht:
- Iterative Ausführung bis Erfolg
- Klare Completion Promises
- Sub-Agent Freigabe (Controller testet Consultant)
- Selbst-Korrektur durch Dateisystem-Feedback

### Beweis

ADR-039 wurde erfolgreich mit Ralph implementiert:
- 1 Iteration
- 13 Dateien migriert
- 83 Unit Tests grün
- Integration Test bestanden (Sub-Agent Consultant antwortete)

## Entscheidung

### 1. Ralph Section in allen ADRs

Jedes ADR mit `component_type: TOOL|NODE|AGENT|SERVICE|PROCESS` bekommt eine Ralph Section:

```markdown
## Ralph Automation

### Master Promise
`<promise>ADR_XXX_COMPLETE</promise>`

### Phasen-Promises

| Phase | Rolle | Promise | Kriterien |
|-------|-------|---------|-----------|
| 1 | Developer | `IMPLEMENTATION_COMPLETE` | Code geschrieben, Syntax OK |
| 2 | Tester | `UNIT_TESTS_PASSED` | pytest grün |
| 3 | Integrator | `INTEGRATION_VERIFIED` | Sub-Agent Test OK |
| 4 | Reviewer | `REVIEW_APPROVED` | Checkliste erfüllt |
| 5 | Dokumentierer | `DOCS_COMPLETE` | Docs aktualisiert |

### Sub-Agent Freigabe

```bash
# Integration Test - Sub-Agent muss antworten
curl -s -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Test"}]}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
content = data.get('choices',[{}])[0].get('message',{}).get('content','')
assert len(content) > 50, 'Sub-Agent Response zu kurz'
print('SUB_AGENT_OK')
"
```
```

### 2. Standard Completion Promises

#### Developer Promise: `IMPLEMENTATION_COMPLETE`

```yaml
kriterien:
  - Alle files.create Dateien existieren
  - Alle files.modify Änderungen gemacht
  - python3 -m py_compile für alle .py Dateien
  - Keine hardcoded Paths (/home/aiuser01)
  - Kein sys.path.insert() (außer in Tests)
```

#### Tester Promise: `UNIT_TESTS_PASSED`

```yaml
kriterien:
  - pytest tests/unit/ -v --tb=short
  - Alle Tests PASSED
  - Coverage > 80% für neue Dateien (optional)
```

#### Integrator Promise: `INTEGRATION_VERIFIED`

```yaml
kriterien:
  - API startet auf Port 8001
  - Health Check: GET /health → 200
  - Sub-Agent Test: Consultant antwortet
  - Response > 50 Zeichen
  - Response ist kein Raw-JSONL
  - Response enthält nicht nur STEP-Marker
```

#### Reviewer Promise: `REVIEW_APPROVED`

```yaml
kriterien:
  - ADR Akzeptanzkriterien erfüllt
  - Code Style konsistent
  - Keine Security Issues
  - Error Handling vorhanden
  - Logging für kritische Pfade
```

#### Dokumentierer Promise: `DOCS_COMPLETE`

```yaml
kriterien:
  - Docstrings für alle public Functions
  - ARCHITECTURE-MODULES.md aktualisiert (wenn neues Modul)
  - README.md aktualisiert (wenn neues Feature)
  - ADR in INDEX.md eingetragen
```

### 3. Sub-Agent Freigabe Pattern

Das kritischste Pattern: **Der Controller testet den Consultant**

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH CONTROLLER                          │
│                                                              │
│  /ralph-loop "Implementiere ADR-XXX..."                     │
│       --max-iterations 10                                    │
│       --completion-promise "ADR_XXX_COMPLETE"               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Iteration 1                                          │    │
│  │   ├── Code schreiben                                │    │
│  │   ├── Unit Tests laufen lassen                      │    │
│  │   ├── Tests FAILED? → Iteration 2                   │    │
│  │   └── Tests PASSED? → Weiter                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Integration Test (SUB-AGENT FREIGABE)               │    │
│  │                                                      │    │
│  │   1. API neu starten                                │    │
│  │   2. curl POST /v1/chat/completions                 │    │
│  │   3. Consultant (SUB-AGENT) antwortet               │    │
│  │   4. Response validieren:                           │    │
│  │      - len(content) > 50                            │    │
│  │      - "STEP" not in content[:50]                   │    │
│  │      - Kein JSONL                                   │    │
│  │   5. PASSED? → <promise>INTEGRATION_VERIFIED</promise>│   │
│  │      FAILED? → Nächste Iteration                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  <promise>ADR_XXX_COMPLETE</promise>                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4. Universelle Patterns

#### Reviewer Pattern (universell)

```markdown
## Reviewer Checkliste

- [ ] ADR Akzeptanzkriterien alle erfüllt
- [ ] Keine TODO/FIXME im Code (außer dokumentiert)
- [ ] Error Messages sind hilfreich
- [ ] Keine sensitive Daten in Logs
- [ ] Edge Cases behandelt

Wenn alle Checkboxen ✓: <promise>REVIEW_APPROVED</promise>
```

#### Dokumentierer Pattern (universell)

```markdown
## Dokumentation Checkliste

- [ ] Alle public Functions haben Docstrings
- [ ] Modul-Level Docstring vorhanden
- [ ] Beispiele in Docstrings wo sinnvoll
- [ ] ARCHITECTURE-MODULES.md aktualisiert
- [ ] ADR in INDEX.md eingetragen

Wenn alle Checkboxen ✓: <promise>DOCS_COMPLETE</promise>
```

## Implementation

### Phase 1: Promise Registry

```python
# src/helix/ralph/promises.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class CompletionPromise:
    """A completion promise for Ralph loops."""
    name: str
    role: str  # developer, tester, integrator, reviewer, documenter
    criteria: list[str]
    validator: Callable[[], bool]

STANDARD_PROMISES = {
    "UNIT_TESTS_PASSED": CompletionPromise(
        name="UNIT_TESTS_PASSED",
        role="tester",
        criteria=["pytest tests/unit/ passes"],
        validator=lambda: run_pytest() == 0,
    ),
    "INTEGRATION_VERIFIED": CompletionPromise(
        name="INTEGRATION_VERIFIED",
        role="integrator",
        criteria=["API healthy", "Sub-agent responds"],
        validator=lambda: check_integration(),
    ),
}
```

### Phase 2: Sub-Agent Validator

```python
# src/helix/ralph/sub_agent.py
import httpx

async def validate_sub_agent(
    api_url: str = "http://localhost:8001",
    min_response_length: int = 50,
) -> bool:
    """Validate that the sub-agent (Consultant) responds correctly."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{api_url}/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Was ist HELIX?"}],
                "stream": False,
            },
        )
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Validation criteria
        if len(content) < min_response_length:
            return False
        if "STEP" in content[:50]:  # Only STEP marker, no real content
            return False
        if content.startswith("{"):  # Raw JSONL
            return False
            
        return True
```

### Phase 3: ADR Template Update

```jinja2
{# templates/adr/template.md.j2 #}
{% if component_type in ['TOOL', 'NODE', 'AGENT', 'SERVICE', 'PROCESS'] %}
## Ralph Automation

### Master Promise
`<promise>ADR_{{ adr_id }}_COMPLETE</promise>`

### Phasen-Promises

| Phase | Rolle | Promise | Kriterien |
|-------|-------|---------|-----------|
| 1 | Developer | `IMPLEMENTATION_COMPLETE` | {{ implementation_criteria | default('Code geschrieben') }} |
| 2 | Tester | `UNIT_TESTS_PASSED` | pytest grün |
| 3 | Integrator | `INTEGRATION_VERIFIED` | Sub-Agent Test OK |
| 4 | Reviewer | `REVIEW_APPROVED` | ADR Kriterien erfüllt |
| 5 | Dokumentierer | `DOCS_COMPLETE` | Docs aktualisiert |

### Sub-Agent Test

```bash
{{ sub_agent_test | default('curl -s http://localhost:8001/health') }}
```
{% endif %}
```

## Akzeptanzkriterien

### Must Have
- [ ] Standard Promises definiert (5 Rollen)
- [ ] Sub-Agent Freigabe Pattern dokumentiert
- [ ] ADR Template enthält Ralph Section
- [ ] Controller Template nutzt Ralph

### Should Have
- [ ] Promise Registry in Python implementiert
- [ ] Sub-Agent Validator Funktion
- [ ] Automatische Promise-Erkennung im ADR

### Nice to Have
- [ ] Dashboard für Ralph Loop Status
- [ ] Metrics für Iterationen pro ADR
- [ ] Automatische Retry-Strategie Optimierung

## Konsequenzen

### Positiv
- **Garantierte Integration**: Sub-Agent Test beweist dass Änderungen funktionieren
- **Selbst-Korrektur**: Ralph iteriert bis Erfolg
- **Standardisierung**: Gleiche Promises für alle ADRs
- **Nachvollziehbarkeit**: status.md dokumentiert jeden Schritt

### Negativ
- **API Kosten**: Mehr Iterationen = mehr Claude Aufrufe
- **Zeitaufwand**: Ralph Loops können lange dauern
- **Komplexität**: Neues Konzept für Team

### Risiken
- **Endlos-Loops**: max-iterations als Sicherheit
- **False Positives**: Sub-Agent Test muss robust sein
- **Ressourcen**: Mehrere Claude-Instanzen parallel

## Referenzen

- [Ralph Wiggum Technique](https://ghuntley.com/ralph/) - Original Konzept
- [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator) - Reference Implementation
- ADR-038: Response Enforcement - Basis für Sub-Agent Validation
- ADR-039: Code Quality Hardening - Erster erfolgreicher Ralph-Einsatz

## Ralph Automation

### Master Promise
`<promise>ADR_040_COMPLETE</promise>`

### Phasen-Promises

| Phase | Rolle | Promise | Kriterien |
|-------|-------|---------|-----------|
| 1 | Developer | `IMPLEMENTATION_COMPLETE` | promises.py, sub_agent.py erstellt |
| 2 | Tester | `UNIT_TESTS_PASSED` | pytest für Ralph Module |
| 3 | Integrator | `INTEGRATION_VERIFIED` | Ralph Controller funktioniert |
| 4 | Reviewer | `REVIEW_APPROVED` | Pattern dokumentiert |
| 5 | Dokumentierer | `DOCS_COMPLETE` | RALPH-PATTERN.md erstellt |

### Sub-Agent Test

```bash
# Test: Ralph Controller kann Bubblesort implementieren
cd /tmp/ralph-test
/ralph-loop "Implementiere Bubblesort" --max-iterations 3 --completion-promise "TESTS_PASSING"
# Erwartet: bubblesort.py + test_bubblesort.py + pytest grün
```

## Dokumentation

### Zu aktualisierende Docs
- `docs/RALPH-PATTERN.md` - Neues Dokument für Ralph Pattern
- `docs/ARCHITECTURE-MODULES.md` - Ralph Module Sektion
- `templates/controller/CLAUDE.md.j2` - Ralph Integration
- `templates/adr/template.md.j2` - Ralph Section Template

### Verlinkte ADRs
- ADR-038: Response Enforcement
- ADR-039: Code Quality Hardening (erster Ralph-Einsatz)
