# Evolution System - Bug Status

## Fixed Workflow Bugs ✅

| Bug | Problem | Fix |
|-----|---------|-----|
| 1 | Phase Output in phases/N/output/ statt new/ | consolidate_phase_outputs() |
| 2 | "planning" Status nicht erkannt | Added to EvolutionStatus enum |
| 4 | Validation Message zeigt keine Errors | Added error count |
| 6 | streaming.py generiert keine CLAUDE.md | TemplateEngine integration |
| 7 | Template erwartet 'project' Variable | Updated _base.md |
| 8 | Template extends Pfad falsch | Fixed to "developer/_base.md" |

## Open Workflow Bugs 🔴

### Bug 5: files count = 0 nach Deploy
- **Status:** Cosmetic - zählt nicht korrekt nach consolidate
- **Impact:** Low - Deploy funktioniert trotzdem

### Bug 9: Pre-existing Test Failures
- **Problem:** Beide Systeme (prod + test) haben failing tests
- **Ursache:** API-Signaturen in Code vs Tests stimmen nicht überein
- **Beispiele:**
  - `TemplateEngine.render()` existiert nicht (sollte `render_claude_md()` sein)
  - `QualityGateRunner.check_files_exist(files=...)` - falscher Parameter
  - `EscalationManager.determine_level()` existiert nicht
- **Impact:** High - macht Validate unzuverlässig
- **Fix:** Tests an aktuelle API anpassen

## ADR-System Project Bugs 🟡

### Bug 3: Phase 4 würde Circular Import verursachen
- **Problem:** phases.yaml definiert `new/src/helix/quality_gates/adr_gate.py`
- **Konflikt:** `src/helix/quality_gates.py` Modul existiert bereits
- **Fix:** Phase 4 CLAUDE.md muss `helix.adr.gate` verwenden

---

## Evolution Workflow - Was passiert bei jedem Schritt?

### 1. Execute (`/helix/execute`)
- Generiert CLAUDE.md aus Template
- Startet Claude CLI mit Streaming
- Claude schreibt Output nach `phases/N/new/` oder `phases/N/output/`

### 2. Deploy (`/helix/evolution/.../deploy`)
- `consolidate_phase_outputs()` sammelt alle Outputs in project `new/`
- Kopiert nach `helix-v4-test/`
- Startet Test-API neu

### 3. Validate (`/helix/evolution/.../validate`)
- Syntax Check (py_compile)
- Unit Tests (pytest)
- E2E Tests (API health)
- **Fixt NICHTS automatisch!** Nur Report.

### 4. Bei Fehlern
- **Option A:** Phase nochmal ausführen (CLAUDE.md verbessern)
- **Option B:** Manuell fixen
- **Option C:** Tests fixen wenn API korrekt ist

### 5. Integrate (`/helix/evolution/.../integrate`)
- Nur wenn Validate erfolgreich
- Kopiert von Test nach Production
- Git commit + tag
