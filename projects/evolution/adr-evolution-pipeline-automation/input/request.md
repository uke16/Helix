# Feature Request: Evolution Pipeline Full Automation

## Problem

Der HELIX v4 Evolution Workflow kann aktuell NICHT vollautomatisch von Phase 1 bis deploy-prod durchlaufen:

1. **Execute API** (`/helix/execute`) unterstützt NUR diese Phase-Typen:
   - `consultant`, `development`, `test`, `review`, `documentation`, `meeting`
   - Phase-Typ `deploy` fehlt komplett

2. **Evolution Run API** (`/helix/evolution/projects/{name}/run`) ist NICHT IMPLEMENTIERT:
   - Die Funktion `run_evolution_pipeline()` fehlt in `streaming.py`
   - Der Endpoint existiert aber wirft `ImportError`

3. **Manueller Workflow** ist aktuell nötig:
   ```bash
   # 1. Execute für dev-Phasen
   curl -X POST /helix/execute -d '{"project_path": "...", "phase_filter": ["planning", "development", "verify", "documentation"]}'
   
   # 2. Manuell Deploy
   curl -X POST /helix/evolution/projects/{name}/deploy
   
   # 3. Manuell Validate  
   curl -X POST /helix/evolution/projects/{name}/validate
   
   # 4. Manuell Integrate
   curl -X POST /helix/evolution/projects/{name}/integrate
   ```

## Anforderung

Implementiere `run_evolution_pipeline()` in `src/helix/api/streaming.py` damit:

1. Ein einzelner API-Call den GESAMTEN Workflow startet
2. Alle Phasen automatisch nacheinander ablaufen
3. Bei Fehlern automatisch Retry/Escalation greift
4. Status-Updates via SSE gestreamt werden
5. `auto_integrate=True` die Production-Integration ermöglicht

## Akzeptanzkriterien

- [ ] `run_evolution_pipeline()` Funktion implementiert
- [ ] Evolution Run API funktioniert ohne ImportError
- [ ] Ein Aufruf von `/helix/evolution/projects/{name}/run?auto_integrate=true` führt kompletten Workflow aus
- [ ] SSE-Stream liefert Phase-Updates
- [ ] Bei Validation-Failure stoppt Pipeline und meldet Fehler
- [ ] Bei Success + auto_integrate=true wird automatisch integriert
- [ ] Rollback bei Integration-Failure

## Technischer Kontext

Relevante Dateien:
- `src/helix/api/streaming.py` - Hier muss `run_evolution_pipeline()` implementiert werden
- `src/helix/api/routes/evolution.py` - Importiert die fehlende Funktion (Zeile 315)
- `src/helix/api/orchestrator.py` - UnifiedOrchestrator für Phase-Execution
- `src/helix/evolution/deployer.py` - Deployer Klasse
- `src/helix/evolution/validator.py` - Validator Klasse
- `src/helix/evolution/integrator.py` - Integrator Klasse
