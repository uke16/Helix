# Bugs and Improvements

> Abschluss-Dokumentation für ADR-032: MCP Server Hardware Teststand
> Datum: 2025-12-30

---

## Bugs gefunden

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

---

## Fehlende Features

### Feature 1: Evolution Project Creation API
**Problem:** Kein `POST /helix/evolution/projects` Endpoint
**Impact:** Projekte müssen manuell erstellt werden
**Vorschlag:**
```
POST /helix/evolution/projects
{
  "name": "mcp-server-032",
  "adr_path": "adr/032-xxx.md"
}
```

### Feature 2: Separate Test-API
**Problem:** API (Port 8001) zeigt nur Projekte aus Production-System
**Impact:** Test-Projekte in helix-v4-test sind nicht sichtbar
**Vorschlag:** Entweder separate Test-API auf Port 8002 oder konfigurierbare Projekt-Root

### Feature 3: Phase Resume
**Problem:** Job startet immer bei Phase 0, keine Resume-Funktion
**Impact:** Bei Fehler in Phase 3 werden Phase 0-2 erneut ausgeführt
**Vorschlag:** Job-Start mit `--from-phase` Option

---

## ADR Unklarheiten

### Unklarheit 1: Phase-Typen für Deploy/Integration
**ADR schreibt:** "Deploy → Validate → Integrate Pipeline"
**Problem:** Keine passenden Phase-Typen für diese Schritte
**Lösung verwendet:** `test` und `review` als Workaround

---

## Verbesserungsvorschläge

### 1. Bessere Dokumentation der gültigen Phase-Typen und Gate-Typen
Aktuell muss man den Quellcode lesen um herauszufinden welche Typen gültig sind.

### 2. Schema-Validierung für phases.yaml
Fehler werden erst zur Laufzeit erkannt, sollten schon bei Projekt-Erstellung geprüft werden.

### 3. Automatische Status-Transitions
Job-Manager sollte Projekt-Status automatisch aktualisieren:
- `pending` → `developing` (bei Job-Start)
- `developing` → `ready` (bei Job-Abschluss)

---

## Statistiken

| Metrik | Wert |
|--------|------|
| Manuelle Interventionen | 5 |
| Phasen ausgeführt | 6 |
| Dateien erstellt | 12 |
| Tests bestanden | 784 |
| Tests fehlgeschlagen | 0 |
| Gesamtdauer | ~18 Minuten |

---

## Referenzen

- [MANUAL_INTERVENTIONS.md](./MANUAL_INTERVENTIONS.md) - Detaillierte Intervention-Logs
- [ADR-032](../../adr/032-mcp-server-hardware-teststand.md) - Original ADR

### Bug 5: Integration kopiert Code nicht in finales Verzeichnis
**Ort:** Evolution Workflow - Integration Phase
**Problem:** Die Integration schreibt INTEGRATION_COMPLETE.md, aber kopiert den Code aus `new/` nicht ins HELIX Root
**Impact:** Code bleibt im Evolution-Projekt statt am finalen Ort
**Manuell gefixt:** `cp -r projects/evolution/mcp-server-032/new/mcp/* mcp/`
**Fix-Vorschlag:** Integration-Phase muss `new/*` nach konfiguriertem Ziel kopieren

