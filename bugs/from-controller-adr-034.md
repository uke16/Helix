# Bugs aus Controller ADR-034

**Quelle**: `/home/aiuser01/helix-v4/projects/evolution/consultant-refactor-034/BUGS_AND_IMPROVEMENTS.md`
**Datum**: 2025-12-30

---

## Bugs

### Bug 1: Phase-Typ Inkonsistenz
**Schwere:** Minor
**Ort:** SKILL.md vs Code
**Problem:** Dokumentation beschreibt Phase-Typ als `testing`, Code akzeptiert nur `test`
**Fix-Vorschlag:** Dokumentation oder Code anpassen, Alias hinzufügen

### Bug 2: pytest nicht im Quality Gate PATH
**Schwere:** Medium
**Ort:** Quality Gates
**Problem:** Quality Gate `tests_pass` führt pytest aus, aber pytest ist im Execution-Kontext nicht im PATH (Exit Code 127)
**Workaround:** Quality Gate zu `files_exist` geändert
**Fix-Vorschlag:** `python -m pytest` nutzen oder PATH konfigurierbar machen

### Bug 3: /helix/execute ignoriert status.json
**Schwere:** Medium
**Ort:** HELIX API / Job Manager
**Problem:** Nach manueller Korrektur von status.json startet Job trotzdem alle Phasen von vorne
**Impact:** Keine Resume-Funktion bei Fehlern
**Fix-Vorschlag:** `--resume` oder `--from-phase` Parameter implementieren

---

## Improvements

### Improvement 1: LLM-Native Flow als Best Practice
**Priorität:** Medium
**Beschreibung:** Das Pattern von ADR-034 (LLM setzt Step-Marker statt Python-Detection) sollte dokumentiert und für andere Agenten übernommen werden

### Improvement 2: Step-Marker Extraktion als Utility
**Priorität:** Low
**Beschreibung:** `extract_step_from_response()` als wiederverwendbare Utility in `helix/utils/markers.py` extrahieren

### Improvement 3: Step-Marker Enforcement
**Priorität:** Medium
**Beschreibung:** Quality Gate oder Response Hook der prüft ob STEP Marker vorhanden ist (wie vom User vorgeschlagen)

