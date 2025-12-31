---
adr_id: "040"
title: "Ralph Automation Pattern - Iterative ADR Execution with Consultant Verification"
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
    - src/helix/ralph/consultant_verify.py
    - docs/RALPH-PATTERN.md
  modify:
    - control/verify-with-consultant.sh
    - control/spawn-consultant.sh
    - templates/controller/CLAUDE.md.j2
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
- Automatische Verify-Scripts prüfen nur was reingeschrieben wurde
- Textuelle ADR-Anforderungen werden nicht geprüft
- Ralph gibt Promise aus obwohl nicht alle Phasen fertig sind

### Beispiel: ADR-039 Fehler

```
Ralph machte Phase 1 (Paths) ──► Integration Test OK ──► Promise ausgegeben
                                                              │
                                    ❌ Phase 2 (LSP) vergessen
                                    ❌ Phase 3 (Docs) vergessen
```

Das Verify-Script prüfte nur:
- Files existieren? ✅
- Tests grün? ✅

Aber NICHT:
- "ENABLE_LSP_TOOL Default soll 1 sein" (textuell im ADR)
- "ConsultantMeeting dokumentiert" (textuell im ADR)

### Lösung: Consultant als intelligentes Verify

Der Consultant LIEST das ADR und versteht ALLE Anforderungen - auch textuelle.

## Entscheidung

### 1. Incremental Goals Pattern

**Schlecht:** "Implementiere ADR komplett"
**Gut:** Phasenweise mit Tests nach jeder Phase

```
Phase 1: [Aufgabe] ──► Test ──► GRÜN? ──► weiter
Phase 2: [Aufgabe] ──► Test ──► GRÜN? ──► weiter  
Phase 3: [Aufgabe] ──► Test ──► GRÜN? ──► weiter
FINAL: Consultant Verify ──► PASSED? ──► Promise
```

### 2. Consultant-als-Verify (KERN-INNOVATION)

```bash
./control/verify-with-consultant.sh adr/XXX.md
```

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     verify-with-consultant.sh                                │
│                                                                              │
│  1. Automatische Checks (schnell, billig)                                   │
│     └── Files existieren? Tests grün? Syntax OK?                            │
│                          │                                                   │
│                          ▼                                                   │
│  2. Spawne Consultant mit:                                                  │
│     ├── ADR Inhalt (VOLLSTÄNDIG)                                            │
│     ├── Automatische Check-Ergebnisse                                       │
│     └── Frage: "Sind ALLE Anforderungen erfüllt?"                          │
│                          │                                                   │
│                          ▼                                                   │
│  3. Consultant:                                                              │
│     ├── Liest ADR (versteht textuelle Anforderungen)                        │
│     ├── Führt EIGENE Checks aus (pyright, grep, etc.)                       │
│     ├── Vergleicht mit Anforderungen                                        │
│     └── Verdict: PASSED + Promise ODER FAILED + was fehlt                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Warum Consultant besser als Script:**

| Automatisches Script | Consultant |
|---------------------|------------|
| Prüft nur was reingeschrieben | Liest ADR komplett |
| Versteht keinen Kontext | "Default soll 1 sein" → prüft :-1 vs :-0 |
| Kann keine neuen Checks | Führt pyright, grep etc. selbst aus |
| Vergisst textuelle Reqs | Versteht "dokumentiert in X" |

### 3. Ralph Section Format für ADRs

```markdown
## Ralph Automation

### Incremental Phases

| Phase | Aufgabe | Test |
|-------|---------|------|
| 1 | [Beschreibung] | `pytest tests/unit/test_X.py` |
| 2 | [Beschreibung] | `python3 -m py_compile src/X.py` |
| 3 | [Beschreibung] | `grep -q "X" docs/Y.md` |

### Final Verification

```bash
./control/verify-with-consultant.sh adr/040-*.md
```

### Completion Promise

Nur wenn Consultant "VERDICT: PASSED" sagt:
`<promise>ADR_040_COMPLETE</promise>`
```

### 4. Sub-Agent Spawn für Developer

Developer kann Consultant jederzeit spawnen:

```bash
# Code Review
./control/spawn-consultant.sh review src/helix/new_module.py

# Architektur-Frage
./control/spawn-consultant.sh analyze "Wo gehört Caching hin?"

# ADR Draft
./control/spawn-consultant.sh adr "Neues Feature X"
```

### 5. Controller CLAUDE.md Template

```markdown
# Ralph Controller für ADR-XXX

## Incremental Goals

### Phase 1: [Name]
```bash
# Aufgabe
[Code schreiben]

# Test
pytest tests/unit/test_X.py -v
# Wenn GRÜN → weiter zu Phase 2
```

### Phase 2: [Name]
```bash
# Aufgabe
[Code schreiben]

# Test
[Spezifischer Test]
# Wenn GRÜN → weiter zu Phase 3
```

### FINAL: Consultant Verification
```bash
./control/verify-with-consultant.sh adr/XXX.md
```

Nur wenn Consultant "VERDICT: PASSED" sagt:
<promise>ADR_XXX_COMPLETE</promise>
```

## Implementation

### Phase 1: Ralph Python Module

```python
# src/helix/ralph/__init__.py
"""Ralph Automation Pattern - Iterative ADR Execution."""

from .consultant_verify import ConsultantVerifier

__all__ = ["ConsultantVerifier"]
```

```python
# src/helix/ralph/consultant_verify.py
"""Consultant-based ADR verification."""

import subprocess
from pathlib import Path

class ConsultantVerifier:
    """Verify ADR completion using Consultant sub-agent."""
    
    def __init__(self, helix_root: Path):
        self.helix_root = helix_root
        self.spawn_script = helix_root / "control" / "spawn-consultant.sh"
    
    def verify_adr(self, adr_path: Path) -> tuple[bool, str]:
        """Verify ADR is complete using Consultant.
        
        Returns:
            (passed: bool, verdict: str)
        """
        # Run automatic checks first
        auto_results = self._run_auto_checks(adr_path)
        
        # Build prompt for Consultant
        adr_content = adr_path.read_text()
        prompt = self._build_verify_prompt(adr_content, auto_results)
        
        # Spawn Consultant
        result = subprocess.run(
            [str(self.spawn_script), prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        verdict = result.stdout
        passed = "VERDICT: PASSED" in verdict
        
        return passed, verdict
    
    def _run_auto_checks(self, adr_path: Path) -> str:
        """Run automatic checks (files, tests, syntax)."""
        # Implementation details...
        pass
    
    def _build_verify_prompt(self, adr_content: str, auto_results: str) -> str:
        """Build prompt for Consultant verification."""
        return f"""
Prüfe ob dieses ADR VOLLSTÄNDIG implementiert ist.

AUTOMATISCHE CHECK-ERGEBNISSE:
{auto_results}

ADR INHALT:
{adr_content}

AUFGABE:
1. Lies ALLE Anforderungen im ADR
2. Vergleiche mit automatischen Checks
3. Prüfe was die Checks NICHT abgedeckt haben
4. Führe eigene Checks aus wenn nötig

VERDICT:
Falls ALLES erfüllt: "VERDICT: PASSED"
Falls etwas fehlt: "VERDICT: FAILED" + Liste was fehlt
"""
```

### Phase 2: Docs erstellen

```markdown
# docs/RALPH-PATTERN.md

## Overview

Ralph Automation Pattern für iterative ADR-Ausführung mit Consultant-Verifikation.

## Quick Start

```bash
# 1. Controller erstellen
mkdir -p projects/claude/controller-adr-XXX
# ... CLAUDE.md mit Incremental Goals

# 2. Ralph Loop starten
/ralph-wiggum:ralph-loop "Lies CLAUDE.md..." --max-iterations 10 --completion-promise "ADR_XXX_COMPLETE"

# 3. Final Verify
./control/verify-with-consultant.sh adr/XXX.md
```

## Best Practices

1. **Incremental Goals**: Kleine Phasen mit Tests nach jeder
2. **Consultant Verify**: Nicht Script, Consultant liest ADR
3. **Sub-Agent Spawn**: Developer kann Consultant jederzeit nutzen
```

### Phase 3: Template Update

Update `templates/controller/CLAUDE.md.j2` mit Incremental Goals Pattern.

## Akzeptanzkriterien

### Must Have
- [ ] `src/helix/ralph/__init__.py` existiert
- [ ] `src/helix/ralph/consultant_verify.py` mit ConsultantVerifier
- [ ] `docs/RALPH-PATTERN.md` mit vollständiger Dokumentation
- [ ] `verify-with-consultant.sh` funktioniert für beliebige ADRs
- [ ] Unit Tests für ConsultantVerifier

### Should Have
- [ ] Controller Template mit Incremental Goals
- [ ] Beispiel-Controller für ADR-040 selbst

### Nice to Have
- [ ] CLI: `helix ralph verify adr/XXX.md`
- [ ] Dashboard für Ralph Loop Status

## Konsequenzen

### Positiv
- **Intelligente Verifikation**: Consultant versteht textuelle Anforderungen
- **Incremental Goals**: Phasenweise mit Tests verhindert "vergessene" Phasen
- **Sub-Agent Pattern**: Developer kann Consultant für Reviews nutzen
- **Selbst-korrigierend**: Ralph iteriert bis Consultant PASSED sagt

### Negativ
- **API Kosten**: Consultant-Call pro Verify (aber nur 1x am Ende)
- **Latenz**: Consultant braucht ~30-60s für Verify

### Risiken
- **Consultant-Fehler**: Consultant könnte PASSED sagen obwohl was fehlt
  - Mitigation: Automatische Checks als Baseline
- **Timeout**: Consultant könnte zu lange brauchen
  - Mitigation: 120s Timeout

## Referenzen

- [Ralph Wiggum Technique](https://ghuntley.com/ralph/)
- ADR-038: Response Enforcement (--resume Implementation)
- ADR-039: Code Quality Hardening (erster Ralph-Einsatz + Learnings)

## Dokumentation

### Zu aktualisierende Docs
- `docs/RALPH-PATTERN.md` - Neues Dokument
- `docs/ARCHITECTURE-MODULES.md` - Ralph Module Sektion
- `docs/SUB-AGENT-PATTERN.md` - Bereits erstellt

### Verlinkte ADRs
- ADR-038: Response Enforcement
- ADR-039: Code Quality Hardening

## Ralph Automation

### Incremental Phases

| Phase | Aufgabe | Test |
|-------|---------|------|
| 1 | Ralph Python Module | `python3 -m py_compile src/helix/ralph/*.py` |
| 2 | Docs erstellen | `test -f docs/RALPH-PATTERN.md` |
| 3 | Template Update | `grep -q "Incremental" templates/controller/CLAUDE.md.j2` |
| 4 | Unit Tests | `pytest tests/unit/test_ralph.py -v` |

### Final Verification

```bash
./control/verify-with-consultant.sh adr/040-ralph-automation-pattern.md
```

### Completion Promise

Nur wenn Consultant "VERDICT: PASSED" sagt:
`<promise>ADR_040_COMPLETE</promise>`
