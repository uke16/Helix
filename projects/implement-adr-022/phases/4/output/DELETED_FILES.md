# Gelöschte Dateien (Phase 4: Aufräumen)

ADR-022 Implementation - Unified API Architecture

## Zusammenfassung

| Komponente | Zeilen | Ersetzt durch |
|------------|--------|---------------|
| orchestrator_legacy.py | 417 | helix.api.orchestrator |
| orchestrator/ package | 1531 | helix.api.orchestrator |
| tests/orchestrator/ | 985 | tests/api/test_orchestrator.py |
| **Total** | **2933** | |

## orchestrator_legacy.py (417 Zeilen)

- **Pfad:** `src/helix/orchestrator_legacy.py`
- **Funktion:** CLI Orchestrator mit synchroner Ausführung
- **Ersetzt durch:** `src/helix/api/orchestrator.py` (UnifiedOrchestrator)
- **Backup:** `output/backup/orchestrator_legacy.py`

### Was wurde portiert:
- Quality Gates Logik
- Escalation Handling
- Phase Execution

## orchestrator/ Package (1531 Zeilen)

ADR-017 Design, nie vollständig implementiert.

### Dateien:

| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `__init__.py` | 50 | Package exports |
| `runner.py` | 463 | OrchestratorRunner mit async execution |
| `phase_executor.py` | 272 | PhaseExecutor für einzelne Phasen |
| `data_flow.py` | 364 | DataFlowManager für Input/Output |
| `status.py` | 382 | StatusTracker für Projekt-Status |

- **Pfad:** `src/helix/orchestrator/`
- **Funktion:** Modulares Orchestrator Design (ADR-017)
- **Status:** War nur Entwurf, nie produktiv genutzt
- **Ersetzt durch:** `src/helix/api/orchestrator.py` (UnifiedOrchestrator)
- **Backup:** `output/backup/orchestrator/`

## tests/orchestrator/ (985 Zeilen)

Tests für das alte orchestrator/ Package.

### Dateien:

| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `__init__.py` | 1 | Package marker |
| `test_runner.py` | 309 | Tests für OrchestratorRunner |
| `test_phase_executor.py` | 333 | Tests für PhaseExecutor |
| `test_data_flow.py` | 342 | Tests für DataFlowManager |

- **Pfad:** `tests/orchestrator/`
- **Funktion:** Unit tests für altes orchestrator/ Package
- **Ersetzt durch:** `tests/api/test_orchestrator.py` (20 Tests)
- **Backup:** `output/backup/tests_orchestrator/`

## Verifikation

```bash
# Alte Dateien sind weg
ls src/helix/orchestrator_legacy.py 2>&1  # No such file
ls src/helix/orchestrator/ 2>&1           # No such file
ls tests/orchestrator/ 2>&1               # No such file

# Neue API funktioniert
PYTHONPATH=src python3 -c "from helix.api.orchestrator import UnifiedOrchestrator; print('OK')"

# Tests laufen
PYTHONPATH=src python3 -m pytest tests/api/test_orchestrator.py -v  # 20 passed
PYTHONPATH=src python3 -m pytest tests/integration/test_orchestrator_workflow.py -v  # 3 passed
```

## Änderungen an bestehenden Dateien

### tests/integration/test_orchestrator_workflow.py

- Import geändert: `from helix.orchestrator import Orchestrator` -> `from helix.api.orchestrator import UnifiedOrchestrator`
- Fixture `temp_dir` -> `tmp_path` (pytest standard)
- Parameter `files=` -> `expected=` (QualityGateRunner API)
- Tests vereinfacht (keine Mocks auf gelöschte Methoden)

## Rollback

Falls nötig, können die Backups wiederhergestellt werden:

```bash
cp output/backup/orchestrator_legacy.py src/helix/
cp -r output/backup/orchestrator/ src/helix/
cp -r output/backup/tests_orchestrator/ tests/orchestrator/
```
