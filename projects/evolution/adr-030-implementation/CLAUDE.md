# ADR-030 Implementation: Evolution Pipeline Full Automation

## Mission

1. **Implementiere** `run_evolution_pipeline()` in HELIX v4
2. **Teste** die Implementation mit dem `pipeline-test` Projekt
3. **Validiere** dass der komplette Workflow funktioniert

---

## Phase 1: Implementation

### Schritt 1.1: Lies die Spezifikation

```bash
cat /home/aiuser01/helix-v4/projects/evolution/adr-030-implementation/input/ADR-030-evolution-pipeline-full-automation.md
cat /home/aiuser01/helix-v4/projects/evolution/adr-030-implementation/input/ADR-030-ERGAENZUNGEN.md
```

### Schritt 1.2: Prüfe aktuelle streaming.py

```bash
cat /home/aiuser01/helix-v4/src/helix/api/streaming.py
```

### Schritt 1.3: Implementiere run_evolution_pipeline()

Editiere `/home/aiuser01/helix-v4/src/helix/api/streaming.py` und füge am Ende hinzu:

```python
# Evolution Pipeline - ADR-030
from helix.evolution import (
    Deployer,
    Validator,
    Integrator,
    EvolutionStatus,
)
from helix.evolution.project import EvolutionProject


async def run_evolution_pipeline(
    job: Job,
    project: EvolutionProject,
    auto_integrate: bool = False,
    force: bool = False,
) -> None:
    """Run complete evolution pipeline with streaming events.

    Pipeline steps:
    1. Pre-checks (force, concurrent execution)
    2. Execute all project phases (via UnifiedOrchestrator)
    3. Deploy to test system (via Deployer)
    4. Validate in test system (via Validator)
    5. Integrate to production (via Integrator) - if auto_integrate=True

    Args:
        job: Job instance for tracking
        project: EvolutionProject to execute
        auto_integrate: Whether to automatically integrate on successful validation
        force: Whether to force re-run on already integrated projects
    """
    print(f"[EVOLUTION] Starting pipeline for {project.name}")

    try:
        # Pre-check: Already integrated?
        current_status = project.get_status()
        if not force and current_status == EvolutionStatus.INTEGRATED:
            await _emit_pipeline_failed(job.job_id, "pre-check",
                "Project already integrated. Use force=true to re-run.")
            return

        # Pre-check: Already running?
        if current_status in [EvolutionStatus.DEVELOPING, EvolutionStatus.VALIDATING]:
            await _emit_pipeline_failed(job.job_id, "pre-check",
                f"Pipeline already running (status: {current_status.value})")
            return

        # Mark as developing
        project.set_status(EvolutionStatus.DEVELOPING)

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
            project.set_status(EvolutionStatus.FAILED)
            error_msg = "; ".join(result.errors) if result.errors else "Phase execution failed"
            await _emit_pipeline_failed(job.job_id, "execute", error_msg)
            return

        project.set_status(EvolutionStatus.READY)
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
            project.set_status(EvolutionStatus.FAILED)
            await _emit_pipeline_failed(job.job_id, "deploy", deploy_result.error or deploy_result.message)
            return

        project.set_status(EvolutionStatus.DEPLOYED)
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_completed",
            data={"step": "deploy", "files_copied": deploy_result.files_copied}
        ))

        # Step 3: Validate in test system
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="step_started",
            data={"step": "validate", "description": "Running validation suite"}
        ))

        project.set_status(EvolutionStatus.VALIDATING)
        validator = Validator()
        validation_result = await validator.full_validation()

        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="validation_result",
            data={
                "success": validation_result.success,
                "passed": validation_result.passed,
                "failed": validation_result.failed,
                "errors": validation_result.errors[:5] if validation_result.errors else [],
            }
        ))

        if not validation_result.success:
            # Rollback test system
            await deployer.rollback()
            project.set_status(EvolutionStatus.FAILED)
            error_summary = "; ".join(validation_result.errors[:3]) if validation_result.errors else "Validation failed"
            await _emit_pipeline_failed(job.job_id, "validate", error_summary)
            return

        project.set_status(EvolutionStatus.DEPLOYED)  # Back to deployed after validation
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
                project.set_status(EvolutionStatus.FAILED)
                await _emit_pipeline_failed(job.job_id, "integrate", 
                    integration_result.error or integration_result.message)
                return

            project.set_status(EvolutionStatus.INTEGRATED)
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
        print(f"[EVOLUTION] Pipeline completed for {project.name}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[EVOLUTION] Pipeline error: {error_msg}")
        try:
            project.set_status(EvolutionStatus.FAILED)
        except:
            pass
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
    print(f"[EVOLUTION] Pipeline failed at {step}: {error}")
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

### Schritt 1.4: Syntax-Check

```bash
cd /home/aiuser01/helix-v4
python3 -c "import ast; ast.parse(open('src/helix/api/streaming.py').read())" && echo "✓ Syntax OK"
```

### Schritt 1.5: Server Restart

```bash
/home/aiuser01/helix-v4/control/helix-control.sh restart
sleep 5
curl -s http://localhost:8001/health | python3 -m json.tool
```

---

## Phase 2: Test mit pipeline-test Projekt

### Schritt 2.1: Prüfe Test-Projekt

```bash
curl -s http://localhost:8001/helix/evolution/projects/pipeline-test | python3 -m json.tool
```

### Schritt 2.2: Setze Status auf "ready" falls nötig

```bash
cat > /home/aiuser01/helix-v4/projects/evolution/pipeline-test/status.json << 'EOF'
{
  "project_id": "pipeline-test",
  "title": "Pipeline Test Project",
  "status": "ready",
  "workflow": "intern-simple",
  "created_at": "2025-12-28T17:40:00.000000",
  "phases": {
    "planning": "finished",
    "development": "finished"
  }
}
EOF
```

### Schritt 2.3: Starte Evolution-Pipeline

```bash
curl -s -X POST "http://localhost:8001/helix/evolution/projects/pipeline-test/run?auto_integrate=false&force=true" | python3 -m json.tool
```

### Schritt 2.4: Verfolge Job-Status

Hole die job_id aus dem vorherigen Response und prüfe:

```bash
# Ersetze {job_id} mit der tatsächlichen ID
curl -s http://localhost:8001/helix/jobs/{job_id} | python3 -m json.tool
```

### Schritt 2.5: Bei Fehlern - Logs prüfen

```bash
/home/aiuser01/helix-v4/control/helix-control.sh logs 100 | tail -50
```

---

## Phase 3: Dokumentation

Erstelle die Output-Dateien:

### output/implementation-summary.md

Dokumentiere was implementiert wurde:
- Welche Änderungen an streaming.py
- Welche Funktionen hinzugefügt
- Welche Imports ergänzt

### output/test-results.md

Dokumentiere die Test-Ergebnisse:
- Job-ID und Status
- Pipeline-Schritte die durchlaufen wurden
- Eventuelle Fehler und deren Behebung
- Finale Validierung

---

## Erfolgskriterien

- [ ] `run_evolution_pipeline()` implementiert in streaming.py
- [ ] `_emit_pipeline_failed()` Helper implementiert
- [ ] Syntax-Check besteht
- [ ] Server startet ohne Fehler
- [ ] `/helix/evolution/projects/pipeline-test/run` Endpoint antwortet
- [ ] Pipeline läuft durch (oder Fehler sind dokumentiert und behoben)
- [ ] Output-Dateien erstellt

---

## Hinweise

1. **Bei ImportError**: Prüfe ob alle Imports am Anfang von streaming.py korrekt sind
2. **Bei NameError**: Prüfe ob `OrchestratorEvent` korrekt importiert ist (als Alias von `PhaseEvent`)
3. **Bei Timeout**: Die Pipeline kann mehrere Minuten dauern - das ist normal
4. **Server-Logs**: Immer `/home/aiuser01/helix-v4/control/helix-control.sh logs 50` prüfen bei Problemen
