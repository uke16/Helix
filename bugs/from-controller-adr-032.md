# Bugs aus Controller ADR-032

**Quelle**: `/home/aiuser01/helix-v4/projects/evolution/mcp-server-032/BUGS_AND_IMPROVEMENTS.md`
**Datum**: 2025-12-30

---

## Bugs

### Bug 1: EvolutionStatus Case-Sensitivity
**Ort:** `src/helix/evolution/project.py`
**Problem:** Status-Enum akzeptiert nur lowercase (`pending`), aber manuelle status.json hatte uppercase (`PENDING`)
**Impact:** API wirft ValueError bei Projekt-Abfrage
**Fix-Vorschlag:** Case-insensitive Enum-Parsing oder bessere Validierung

### Bug 2: Fehlende Phase-Typen
**Ort:** Phase-Parser
**Problem:** `deployment` und `integration` sind keine gültigen Phase-Typen
**Gültige Typen:** review, documentation, test, meeting, consultant, development
**Fix-Vorschlag:** Deployment und Integration als Phase-Typen hinzufügen

### Bug 3: Fehlender Gate-Typ `manual`
**Ort:** Quality Gate Runner
**Problem:** `quality_gate.type: manual` wird nicht erkannt
**Gültige Typen:** files_exist, syntax_check, tests_pass, review_approved, adr_valid
**Fix-Vorschlag:** Manual Gate implementieren (wartet auf Human-Approval)

### Bug 4: Status nicht auf Ready nach Job-Abschluss
**Ort:** Job-Manager
**Problem:** Nach erfolgreichem Abschluss aller Phasen bleibt Projekt-Status auf `pending`
**Impact:** Evolution Pipeline (`/deploy`) lehnt Projekt ab
**Fix-Vorschlag:** Job-System soll Status automatisch auf `ready` setzen

### Bug 5: Integration kopiert Code nicht in finales Verzeichnis
**Ort:** Evolution Workflow - Integration Phase
**Problem:** Die Integration schreibt INTEGRATION_COMPLETE.md, aber kopiert den Code aus `new/` nicht ins HELIX Root
**Impact:** Code bleibt im Evolution-Projekt statt am finalen Ort
**Manuell gefixt:** `cp -r projects/evolution/mcp-server-032/new/mcp/* mcp/`
**Fix-Vorschlag:** Integration-Phase muss `new/*` nach konfiguriertem Ziel kopieren

---

## Fehlende Features

### Feature 1: Evolution Project Creation API
**Problem:** Kein `POST /helix/evolution/projects` Endpoint
**Impact:** Projekte müssen manuell erstellt werden

### Feature 2: Separate Test-API
**Problem:** API (Port 8001) zeigt nur Projekte aus Production-System
**Impact:** Test-Projekte in helix-v4-test sind nicht sichtbar

### Feature 3: Phase Resume
**Problem:** Job startet immer bei Phase 0, keine Resume-Funktion
**Impact:** Bei Fehler in Phase 3 werden Phase 0-2 erneut ausgeführt

---

## Verbesserungsvorschläge

1. Bessere Dokumentation der gültigen Phase-Typen und Gate-Typen
2. Schema-Validierung für phases.yaml bei Projekt-Erstellung
3. Automatische Status-Transitions (pending → developing → ready)


---

## Bestätigt auch bei ADR-034

**Bug 5 bestätigt**: Integration kopiert Code nicht.

ADR-034 hat Code erstellt in:
- `phases/02/output/modified/src/helix/api/session_manager.py`
- `phases/03/output/modified/templates/consultant/session.md.j2`
- `phases/04/output/modified/src/helix/api/routes/openai.py`

Aber der Code ist NICHT in `/home/aiuser01/helix-v4/src/` - das alte System läuft noch.

