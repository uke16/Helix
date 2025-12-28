---
adr_id: "030"
title: Evolution Pipeline Full Automation
status: Proposed

project_type: helix_internal
component_type: SERVICE
classification: NEW
change_scope: minor

files:
  create: []
  modify:
    - src/helix/api/streaming.py
  docs:
    - docs/ARCHITECTURE-MODULES.md
    - skills/helix/evolution.md

depends_on:
  - ADR-022
---

# ADR-030: Evolution Pipeline Full Automation

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

Der HELIX v4 Evolution Workflow kann aktuell NICHT vollautomatisch von Phase 1 bis zur Production-Integration durchlaufen:

1. **Execute API** (`/helix/execute`) unterstützt nur diese Phase-Typen:
   - `consultant`, `development`, `test`, `review`, `documentation`, `meeting`
   - Phase-Typ `deploy` fehlt komplett

2. **Evolution Run API** (`/helix/evolution/projects/{name}/run`) ist nicht vollständig implementiert:
   - Die Funktion `run_evolution_pipeline()` fehlt in `streaming.py`
   - Der Endpoint existiert und importiert die fehlende Funktion (Zeile 315)
   - Dies führt zu einem `ImportError` beim Aufruf

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

### Warum muss es gelöst werden?

- **Automatisierung**: HELIX soll sich selbst weiterentwickeln können ohne manuellen Eingriff
- **Konsistenz**: Der gesamte Workflow sollte über eine API kontrollierbar sein
- **Feedback**: Status-Updates via SSE ermöglichen Echtzeit-Monitoring
- **Sicherheit**: Eingebaute Rollback-Mechanismen bei Fehlern

### Was passiert wenn wir nichts tun?

- Evolution-Projekte können nicht vollautomatisch ausgeführt werden
- Jeder Evolution-Durchlauf erfordert 4+ manuelle API-Aufrufe
- Bei Fehlern fehlt koordiniertes Error-Handling
- Keine einheitliche SSE-Streaming für den gesamten Workflow

---

## Entscheidung

### Wir entscheiden uns für:

Implementierung einer `run_evolution_pipeline()` Funktion in `src/helix/api/streaming.py`, die den gesamten Evolution-Workflow als eine SSE-streamende Coroutine orchestriert.

### Diese Entscheidung beinhaltet:

1. **Neue Funktion** `run_evolution_pipeline(job, project, auto_integrate)` in streaming.py
2. **Nutzung bestehender Komponenten**:
   - `UnifiedOrchestrator` für Phase-Execution
   - `Deployer` für Test-System-Deployment
   - `Validator` für Syntax/Unit/E2E-Tests
   - `Integrator` für Production-Integration
3. **SSE-Events** für jeden Workflow-Schritt
4. **Automatisches Rollback** bei Validierungsfehlern
5. **Optional auto_integrate** für automatische Production-Integration

### Warum diese Lösung?

- Nutzt existierende, getestete Komponenten (Deployer, Validator, Integrator)
- Konsistent mit bestehendem `run_project_with_streaming()` Pattern
- Minimaler Eingriff - nur eine neue Funktion
- SSE-Streaming bereits etabliert via job_manager

### Welche Alternativen wurden betrachtet?

1. **Neuer Endpoint statt Funktion**: Nicht gewählt - der Endpoint existiert bereits, es fehlt nur die Implementierung
2. **Separater Evolution-Orchestrator**: Nicht gewählt - würde Duplication mit UnifiedOrchestrator erzeugen
3. **CLI-basierter Workflow**: Nicht gewählt - nicht API-freundlich, keine SSE-Integration

---

## Implementation

### 1. Neue Funktion in streaming.py

**Änderung in:** `src/helix/api/streaming.py`

```python
# Nach den bestehenden Imports hinzufügen:
from helix.evolution import Deployer, Validator, Integrator

async def run_evolution_pipeline(
    job: Job,
    project: "EvolutionProject",  # Type hint als String um zirkulären Import zu vermeiden
    auto_integrate: bool = False,
) -> None:
    """Run complete evolution pipeline with streaming events.

    Pipeline steps:
    1. Execute all project phases (via UnifiedOrchestrator)
    2. Deploy to test system (via Deployer)
    3. Validate in test system (via Validator)
    4. Integrate to production (via Integrator) - if auto_integrate=True and validation passes

    Args:
        job: Job instance for tracking
        project: EvolutionProject to execute
        auto_integrate: Whether to automatically integrate on successful validation
    """
    print(f"[EVOLUTION] Starting pipeline for {project.name}")

    try:
        await job_manager.update_job(job.job_id, status=JobStatus.RUNNING)

        # Emit pipeline start event
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_started",
            data={
                "project": project.name,
                "auto_integrate": auto_integrate,
            }
        ))

        # Step 1: Execute project phases
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "execute", "description": "Executing project phases"}
        ))

        orchestrator = UnifiedOrchestrator()

        async def on_phase_event(event: OrchestratorEvent) -> None:
            """Forward orchestrator events."""
            api_event = PhaseEvent(
                event_type=event.event_type,
                phase_id=event.phase_id or None,
                data=event.data,
                timestamp=event.timestamp,
            )
            await job_manager.emit_event(job.job_id, api_event)

        result = await orchestrator.run_project(
            project_path=project.path,
            on_event=on_phase_event,
        )

        if not result.success:
            error_msg = "; ".join(result.errors) if result.errors else "Phase execution failed"
            await _emit_pipeline_failed(job.job_id, "execute", error_msg)
            return

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "execute", "phases_completed": result.phases_completed}
        ))

        # Step 2: Deploy to test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "deploy", "description": "Deploying to test system"}
        ))

        deployer = Deployer()
        deploy_result = await deployer.full_deploy(project)

        if not deploy_result.success:
            await _emit_pipeline_failed(job.job_id, "deploy", deploy_result.error or deploy_result.message)
            return

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "deploy", "files_copied": deploy_result.files_copied}
        ))

        # Step 3: Validate in test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "validate", "description": "Running validation suite"}
        ))

        validator = Validator()
        validation_result = await validator.full_validation()

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="validation_result",
            data={
                "success": validation_result.success,
                "passed": validation_result.passed,
                "failed": validation_result.failed,
                "errors": validation_result.errors[:5],  # Limit errors
            }
        ))

        if not validation_result.success:
            # Rollback test system
            await deployer.rollback()
            await _emit_pipeline_failed(job.job_id, "validate", "; ".join(validation_result.errors[:3]))
            return

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "validate", "passed": validation_result.passed}
        ))

        # Step 4: Integrate to production (if auto_integrate)
        if auto_integrate:
            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_started",
                data={"step": "integrate", "description": "Integrating to production"}
            ))

            integrator = Integrator()
            integration_result = await integrator.full_integration(project)

            if not integration_result.success:
                # Integrator handles its own rollback
                await _emit_pipeline_failed(job.job_id, "integrate", integration_result.error or integration_result.message)
                return

            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="step_completed",
                data={
                    "step": "integrate",
                    "files_integrated": integration_result.files_integrated,
                    "backup_tag": integration_result.backup_tag,
                }
            ))

        # Pipeline complete
        await job_manager.update_job(job.job_id, status=JobStatus.COMPLETED)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_completed",
            data={
                "project": project.name,
                "integrated": auto_integrate,
            }
        ))

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[EVOLUTION] Pipeline error: {error_msg}")
        await job_manager.update_job(
            job.job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="pipeline_failed",
            data={"error": str(e)}
        ))


async def _emit_pipeline_failed(job_id: str, step: str, error: str) -> None:
    """Emit pipeline failure event and update job status."""
    await job_manager.update_job(
        job_id,
        status=JobStatus.FAILED,
        error=f"Failed at {step}: {error}"
    )
    await job_manager.emit_event(job_id, PhaseEvent(
        event_type="pipeline_failed",
        data={"step": step, "error": error}
    ))
```

### 2. Import Statement anpassen

Der Import in `src/helix/api/routes/evolution.py` (Zeile 315) funktioniert bereits:
```python
from ..streaming import run_evolution_pipeline
```

### 3. SSE Event-Typen

Die Pipeline emittiert folgende Events:

| Event | Beschreibung |
|-------|--------------|
| `pipeline_started` | Pipeline beginnt |
| `step_started` | Ein Schritt (execute/deploy/validate/integrate) beginnt |
| `step_completed` | Ein Schritt ist erfolgreich abgeschlossen |
| `validation_result` | Validierungsergebnis mit Details |
| `pipeline_completed` | Pipeline erfolgreich beendet |
| `pipeline_failed` | Pipeline mit Fehler abgebrochen |

Zusätzlich werden alle Phase-Events vom UnifiedOrchestrator durchgereicht.

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | Evolution Pipeline Section aktualisieren |
| `skills/helix/evolution.md` | API-Dokumentation für `/run` Endpoint |
| `CLAUDE.md` | Evolution API Reference aktualisieren |

---

## Akzeptanzkriterien

### 1. Funktionalität

- [ ] `run_evolution_pipeline()` Funktion ist implementiert
- [ ] Evolution Run API funktioniert ohne ImportError
- [ ] Ein Aufruf von `/helix/evolution/projects/{name}/run` führt kompletten Workflow aus
- [ ] SSE-Stream liefert Phase-Updates für alle Schritte
- [ ] Bei Validation-Failure stoppt Pipeline und meldet Fehler

### 2. Auto-Integration

- [ ] Bei Success + `auto_integrate=true` wird automatisch integriert
- [ ] Backup-Tag wird vor Integration erstellt
- [ ] Rollback bei Integration-Failure

### 3. Qualität

- [ ] Syntax-Check besteht (py_compile)
- [ ] Unit Tests vorhanden und grün
- [ ] Keine Breaking Changes an bestehenden Endpoints

### 4. Dokumentation

- [ ] API-Dokumentation aktualisiert
- [ ] SSE Event-Typen dokumentiert

---

## Konsequenzen

### Vorteile

- **Ein API-Call** für den gesamten Evolution-Workflow
- **Echtzeit-Feedback** via SSE für alle Schritte
- **Automatisches Rollback** bei Validierungsfehlern
- **Optionale Auto-Integration** für vollständige Automatisierung
- **Konsistente Error-Handling** über alle Schritte

### Nachteile / Risiken

- **Lange Laufzeit**: Pipeline kann mehrere Minuten dauern (Phase-Execution + Tests)
- **Komplexität**: Fehler in einem Schritt beeinflussen nachfolgende Schritte

### Mitigation

- SSE-Streaming ermöglicht Echtzeit-Monitoring der langen Laufzeit
- Klare Fehlermeldungen mit Step-Information
- Automatisches Rollback minimiert Risiko bei Fehlern

---

## Referenzen

- ADR-022: Unified API Architecture
- `src/helix/api/routes/evolution.py`: Bestehender Endpoint (Zeile 291-349)
- `src/helix/evolution/deployer.py`: Deployer-Implementierung
- `src/helix/evolution/validator.py`: Validator-Implementierung
- `src/helix/evolution/integrator.py`: Integrator-Implementierung
