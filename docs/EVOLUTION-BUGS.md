# Evolution System - Gefundene Bugs

## Bug 1: Phase Output vs. new/modified Struktur

**Problem:** 
- `/helix/execute` schreibt Output nach `phases/N/output/`
- Evolution Deployer erwartet `new/` und `modified/` Verzeichnisse
- Manuelle Konsolidierung nötig

**Erwartet:**
- Entweder: Deployer liest aus `phases/*/output/`
- Oder: Nach Phase-Completion automatisch nach `new/`/`modified/` kopieren

**Workaround:** Manuell `new/` erstellt und Dateien konsolidiert

---

## Bug 2: status.json Status "planning" nicht erkannt

**Problem:**
- status.json hatte `"status": "planning"` 
- EvolutionStatus Enum hat nur: pending, developing, ready, deployed, validating, integrated, failed
- Deploy schlägt fehl: `'planning' is not a valid EvolutionStatus`

**Erwartet:**
- Entweder: "planning" in Enum aufnehmen
- Oder: status.json mit korrektem initialen Status erstellen

**Workaround:** status.json manuell auf "ready" gesetzt

---

## Bug 3: Circular Import in quality_gates Package

**Problem:**
- `src/helix/quality_gates.py` (Modul) existiert
- `src/helix/quality_gates/` (Package) wird deployed
- `quality_gates/__init__.py` importiert `adr_gate`
- `adr_gate.py` importiert von `helix.quality_gates` 
- → Circular Import!

**Erwartet:**
- Claude Code sollte wissen dass es ein `quality_gates.py` Modul gibt
- Oder: Architecture Decision: Package statt Modul verwenden

**Workaround:** Keiner - Validation schlägt fehl (korrekt!)

---

## Bug 4: Validate gibt success=false trotz 41 passed, 0 failed

**Problem:**
```json
{
    "success": false,
    "message": "Full validation: 41 passed, 0 failed",
    ...
}
```
- 5 Collection Errors (wegen Circular Import)
- Aber success=false obwohl 41 passed und 0 failed?

**Erwartet:**
- success sollte true sein wenn failed=0 UND keine collection errors
- Oder: Collection errors als failures zählen

---

## Bug 5: Evolution Project findet neue Dateien nicht

**Problem:**
```json
{
    "files": {
        "new": 0,
        "modified": 0
    }
}
```
- Nach Deploy zeigt API 0 files
- Obwohl 18 files deployed wurden

**Erwartet:**
- API sollte korrekte Datei-Anzahl anzeigen

---

## Architektur-Problem: Modul vs. Package Konflikt

**Situation:**
- `src/helix/quality_gates.py` - existierendes Modul mit GateResult, QualityGateRunner
- Phase 4 erstellt `src/helix/quality_gates/` Package mit adr_gate.py

**Problem:**
- Python kann nicht beides haben (Modul UND Package mit gleichem Namen)
- Deployer überschreibt/ergänzt ohne Konflikt-Check

**Lösungsoptionen:**
1. quality_gates.py → quality_gates/__init__.py migrieren (Breaking Change)
2. adr_gate in anderes Package (z.B. `helix/adr/gate.py`)
3. Keine neuen Packages mit Namen die als Module existieren

---

## Bug 6: streaming.py generiert keine CLAUDE.md

**Problem:**
- `src/helix/orchestrator.py` hat `_generate_claude_md()` Methode (Zeile 287)
- `src/helix/api/streaming.py` nutzt den Orchestrator NICHT
- streaming.py läuft direkt mit ClaudeRunner ohne CLAUDE.md zu generieren
- Deshalb müssen CLAUDE.md manuell erstellt werden

**Erwartet:**
- streaming.py sollte vor jeder Phase CLAUDE.md aus Template generieren
- Oder: Orchestrator nutzen statt direktem ClaudeRunner

**Fix:**
CLAUDE.md Generierung in streaming.py einbauen vor Phase-Execution

---

## Bug 7: Template name mapping fehlt

**Problem:**
- Phase type ist "development" aber Template heisst "developer/python.md"
- TemplateEngine sucht nach "development.md" → nicht gefunden
- CLAUDE.md wird nicht generiert

**Fix:**
- Mapping in streaming.py: development → developer/python, etc.

---
