# HELIX v4 - Known Bugs

Dokumentation bekannter Bugs die noch nicht gefixt sind.

---

## BUG-019: status.json nicht aktualisiert während Workflow
- **Gefunden:** 2025-12-22 (ADR-012 Workflow)
- **Severity:** Medium
- **Status:** OPEN
- **Beschreibung:** Während Evolution Workflow bleibt status.json auf "created", phases_completed wird nicht aktualisiert
- **Erwartetes Verhalten:** Nach jeder Phase sollte status.json aktualisiert werden
- **Workaround:** Manuelles Update

## BUG-020: Phase Outputs nicht automatisch deployed
- **Gefunden:** 2025-12-22 (ADR-012 Workflow)
- **Severity:** High
- **Status:** OPEN
- **Beschreibung:** Phase Outputs landen in phases/{N}/output/ aber werden nicht in Hauptverzeichnis kopiert
- **Erwartetes Verhalten:** Nach erfolgreichem Workflow sollte Deploy-Schritt alle Outputs kopieren
- **Workaround:** Manuelles Kopieren

## BUG-021: Test Files nicht automatisch integriert
- **Gefunden:** 2025-12-22 (ADR-012 Workflow)
- **Severity:** Medium
- **Status:** FIXED (manuell integriert)
- **Beschreibung:** tests/evolution/test_project_adr.py wurde im Workflow erstellt aber nicht integriert
- **Fix:** Manuell kopiert, 19 Tests laufen
