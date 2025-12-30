# Manual Interventions Log

> Dokumentiere hier JEDEN manuellen Eingriff der nötig war.
> Diese Doku ist Input für Workflow-Verbesserungen.

---

## Template

```markdown
## Intervention {n} - Phase {x}

**Timestamp:** YYYY-MM-DD HH:MM
**Problem:** Was ist passiert?
**Ursache:** Warum? (soweit bekannt)
**Lösung:** Was hast du manuell gemacht?
**Vorschlag:** Wie könnte der Workflow das automatisch lösen?
**Kategorie:** [BUG|MISSING_FEATURE|UNCLEAR_ADR|EXTERNAL_DEPENDENCY|OTHER]
```

---

## Interventions

### Intervention 1 - Setup

**Timestamp:** 2025-12-30 13:00
**Problem:** HELIX API (Port 8001) zeigt nur Projekte aus `helix-v4/projects/evolution/`, nicht aus `helix-v4-test/projects/evolution/`. Das mcp-server-032 Projekt wurde im Test-System erstellt aber die Production-API findet es nicht.
**Ursache:** Die API ist gegen das Production-System konfiguriert. Es gibt keinen separaten Test-API-Server.
**Lösung:** Projekt aus helix-v4-test nach helix-v4 kopieren damit die API es findet.
**Vorschlag:** Entweder separate Test-API auf Port 8002 oder Konfigurationsoption für Projekt-Root.
**Kategorie:** MISSING_FEATURE

---

### Intervention 2 - Status Case Bug

**Timestamp:** 2025-12-30 13:05
**Problem:** API Fehler "'PENDING' is not a valid EvolutionStatus". Die status.json hatte `"status": "PENDING"` (uppercase).
**Ursache:** Die status.json wurde manuell erstellt mit Großbuchstaben. Der EvolutionStatus Enum verwendet lowercase Werte (`pending`, `ready`, etc.).
**Lösung:** Status in status.json von `"PENDING"` auf `"pending"` geändert.
**Vorschlag:** Entweder case-insensitive Status-Parsing oder Validierung bei Projekt-Erstellung.
**Kategorie:** BUG

---

### Intervention 3 - Invalid Phase Types

**Timestamp:** 2025-12-30 13:10
**Problem:** Job fehlgeschlagen mit "Invalid phase type 'deployment' for phase 'phase-4-deploy'. Valid types: {'review', 'documentation', 'test', 'meeting', 'consultant', 'development'}"
**Ursache:** phases.yaml enthielt `type: deployment` und `type: integration` - diese Phase-Typen existieren nicht.
**Lösung:** Phase 4 geändert auf `type: test`, Phase 5 auf `type: review`.
**Vorschlag:** Entweder `deployment` und `integration` als Phase-Typen hinzufügen, oder Validierung bei Projekt-Erstellung.
**Kategorie:** BUG

---

### Intervention 4 - Unknown Gate Type Manual

**Timestamp:** 2025-12-30 13:56
**Problem:** Job fehlgeschlagen mit "Phase phase-3-test: Unknown gate type: manual"
**Ursache:** phases.yaml enthielt `quality_gate.type: manual` für Phasen 3, 4 und 5. Der Gate-Typ `manual` existiert nicht.
**Lösung:** Alle `quality_gate.type: manual` durch `quality_gate.type: files_exist` ersetzen und passende required_files/output definieren.
**Vorschlag:** Entweder `manual` Gate-Typ implementieren (wartet auf Human-Approval), oder bessere Dokumentation der verfügbaren Gate-Typen.
**Kategorie:** BUG

