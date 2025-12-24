# Dateien die gelöscht werden müssen

## orchestrator_legacy.py
- Pfad: `src/helix/orchestrator_legacy.py`
- Zeilen: 417
- Grund: Ersetzt durch UnifiedOrchestrator

## orchestrator/ package
- Pfad: `src/helix/orchestrator/`
- Dateien:
  - `__init__.py` (~50 Zeilen)
  - `runner.py` (~500 Zeilen)
  - `phase_executor.py` (~300 Zeilen)
  - `data_flow.py` (~400 Zeilen)
  - `status.py` (~400 Zeilen)
- Grund: ADR-017 Design, nie genutzt, ersetzt durch UnifiedOrchestrator

## Total: ~2067 Zeilen

## ⚠️ VOR dem Löschen prüfen

```bash
# Keine Imports mehr auf diese Dateien?
grep -r "orchestrator_legacy" src/helix/
grep -r "from helix.orchestrator import" src/helix/
```
