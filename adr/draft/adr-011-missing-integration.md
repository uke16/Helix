# ADR-011 Implementation Gap Analysis

**Status:** Implementation Review
**Erstellt:** 2024-12-24

---

## ADR-011: Post-Phase Verification

### Was laut ADR implementiert werden sollte

1. ✅ `src/helix/evolution/verification.py` - PhaseVerifier
2. ✅ `src/helix/tools/verify_phase.py` - CLI Tool für Claude
3. ✅ `tests/evolution/test_verification.py` - Unit Tests
4. ✅ `src/helix/api/streaming.py` - Integration (Zeile 184+)
5. ✅ `templates/developer/_base.md` - Instruktion für Claude
6. ❌ `src/helix/orchestrator_legacy.py` - NICHT integriert!

---

## Problem: orchestrator_legacy.py

Die Verification ist in `streaming.py` integriert (für API/Evolution), aber NICHT in `orchestrator_legacy.py` (für CLI `helix run`).

### Aktueller Flow in orchestrator_legacy.py

```python
async def run_phase(...):
    # Phase ausführen
    claude_result = await self.claude_runner.run_phase(phase_dir)
    
    # Nur Exit-Code prüfen
    if not claude_result.success:
        result.status = "failed"
        return result
    
    # Quality Gate (falls definiert)
    if phase_config.quality_gate:
        gate_result = await self.check_quality_gate(...)
    
    # FEHLT: Post-Phase Verification!
    # Keine Prüfung ob erwartete Dateien existieren
```

### Was fehlt

```python
# Nach claude_result = await self.claude_runner.run_phase(...)

# === SOLLTE HINZUGEFÜGT WERDEN ===
from helix.evolution.verification import PhaseVerifier

if claude_result.success:
    verifier = PhaseVerifier(project_dir)
    verify_result = verifier.verify_phase_output(
        phase_id=phase_config.id,
        phase_dir=phase_dir,
        expected_files=phase_config.output  # aus phases.yaml
    )
    
    if not verify_result.success:
        # Retry oder Fail
        ...
```

---

## Warum ist das wichtig?

1. **`helix run` nutzt orchestrator_legacy.py**
   - CLI User bekommen keine Verification
   - Nur API/Streaming User (via streaming.py) bekommen Verification

2. **Inkonsistentes Verhalten**
   - API: Verification ✅
   - CLI: Verification ❌

3. **ADR-011 Akzeptanzkriterien nicht erfüllt**
   - "Nach jeder Claude Run prüft streaming.py automatisch"
   - Aber orchestrator_legacy.py ist der Hauptweg!

---

## Empfehlung

### Option A: In orchestrator_legacy.py integrieren

```python
# Ähnlich wie streaming.py Zeile 184-210
from helix.evolution.verification import PhaseVerifier

# Nach erfolgreichem Claude Run
verifier = PhaseVerifier(project_dir)
verify_result = verifier.verify_phase_output(...)

if not verify_result.success and retry_count < MAX_RETRIES:
    # Retry mit Fehlerkontext
    ...
```

### Option B: Unified Orchestrator

- orchestrator_legacy.py und orchestrator/runner.py zusammenführen
- Eine Implementation für alle Wege (CLI, API, etc.)
- Verification einmal implementieren, überall nutzen

---

## TODO

- [ ] Verification in orchestrator_legacy.py integrieren
- [ ] Tests für CLI + Verification
- [ ] ADR-011 Status auf "Partially Implemented" setzen?
