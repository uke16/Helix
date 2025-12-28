# ADR-030 Ergänzungen

> Diese Ergänzungen wurden nach Review des ADR-030 identifiziert und müssen in der Implementation berücksichtigt werden.

## 1. Force Flag (KRITISCH)

Der Evolution-Run Endpoint hat bereits einen `force` Parameter:

```python
# In evolution.py Zeile 296
async def run_evolution_project(
    name: str,
    background_tasks: BackgroundTasks,
    auto_integrate: bool = False,
    force: bool = False,  # <-- Dieser Parameter!
):
```

### Erforderliche Änderung

```python
async def run_evolution_pipeline(
    job: Job,
    project: "EvolutionProject",
    auto_integrate: bool = False,
    force: bool = False,  # <-- Hinzufügen!
) -> None:
    # Am Anfang der Funktion:
    if not force and project.get_status() == EvolutionStatus.INTEGRATED:
        await _emit_pipeline_failed(job.job_id, "pre-check", 
            "Project already integrated. Use force=true to re-run.")
        return
```

## 2. Import Statement (KRITISCH)

Der Code verwendet `OrchestratorEvent` aber importiert es nicht.

### Korrekter Import-Block

```python
from .orchestrator import UnifiedOrchestrator, PhaseEvent as OrchestratorEvent
from .models import PhaseEvent, JobStatus, PhaseStatus
from .job_manager import job_manager, Job
from helix.evolution import (
    Deployer, 
    Validator, 
    Integrator,
    EvolutionStatus,
)
```

## 3. Projekt-Status Update (WICHTIG)

Der Code muss den Projekt-Status in `status.json` aktualisieren:

### Erforderliche Änderungen

```python
# Nach Step 1 (Execute):
project.set_status(EvolutionStatus.READY)

# Nach Step 2 (Deploy):
project.set_status(EvolutionStatus.DEPLOYED)

# Nach Step 3 (Validate) wenn erfolgreich:
project.set_status(EvolutionStatus.VALIDATING)  # Während Validation
# Nach erfolgreicher Validation: Status bleibt DEPLOYED

# Nach Step 4 (Integrate) wenn erfolgreich:
project.set_status(EvolutionStatus.INTEGRATED)

# Bei Fehler:
project.set_status(EvolutionStatus.FAILED)
project.set_error(error_message)
```

## 4. Concurrent Execution Guard (EMPFOHLEN)

```python
async def run_evolution_pipeline(...):
    # Am Anfang:
    current_status = project.get_status()
    if current_status in [
        EvolutionStatus.DEVELOPING,
        EvolutionStatus.VALIDATING,
    ]:
        await _emit_pipeline_failed(job.job_id, "pre-check",
            f"Pipeline already running (status: {current_status.value})")
        return
    
    # Status auf DEVELOPING setzen um Concurrent Execution zu verhindern
    project.set_status(EvolutionStatus.DEVELOPING)
```

## 5. Zusätzliche Akzeptanzkriterien

Diese sollten zum ADR hinzugefügt werden:

- [ ] `force` Parameter wird unterstützt
- [ ] Bereits integrierte Projekte können mit force=true erneut ausgeführt werden
- [ ] Projekt-Status (status.json) wird bei jedem Schritt aktualisiert
- [ ] Concurrent Execution auf gleichem Projekt wird verhindert
- [ ] Import-Statements sind vollständig und korrekt

## 6. Vollständiger korrigierter Code

```python
# Am Anfang von streaming.py hinzufügen:
from helix.evolution import (
    Deployer, 
    Validator, 
    Integrator,
    EvolutionStatus,
    EvolutionProject,
)

async def run_evolution_pipeline(
    job: Job,
    project: EvolutionProject,
    auto_integrate: bool = False,
    force: bool = False,
) -> None:
    """Run complete evolution pipeline with streaming events."""
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
        
        # ... rest of implementation as in ADR-030 ...
        
        # After successful integration:
        project.set_status(EvolutionStatus.INTEGRATED)
        
    except Exception as e:
        project.set_status(EvolutionStatus.FAILED)
        project.set_error(str(e))
        # ... error handling ...
```

---

## 7. Existierende Bugs in evolution.py (BEREITS GEFIXT)

Während der Analyse wurden folgende Bugs gefunden, die durch einen früheren "Bug 12 fix" eingeführt wurden:

| Endpoint | Problem | Fix |
|----------|---------|-----|
| `get_project` | `force` verwendet ohne Definition | `force: bool = False` hinzugefügt |
| `deploy_project` | `force` verwendet ohne Definition | `force: bool = False` hinzugefügt |
| `validate_project` | `force` verwendet ohne Definition | `force: bool = False` hinzugefügt |
| `integrate_project` | `force` verwendet ohne Definition | `force: bool = False` hinzugefügt |

**Status:** Diese Bugs wurden am 28.12.2025 direkt in `/home/aiuser01/helix-v4/src/helix/api/routes/evolution.py` gefixt.

### Betroffener Code (vor Fix)

```python
# Bug 12 fix: Guard against re-running integrated projects
if project.get_status() == EvolutionStatus.INTEGRATED and not force:
    raise HTTPException(...)
```

Der Code referenzierte `force` ohne dass der Parameter in der Funktionssignatur definiert war.

### Korrigierte Funktionssignaturen

```python
async def get_project(name: str, force: bool = False):
async def deploy_project(name: str, request: DeployRequest = DeployRequest(), force: bool = False):
async def validate_project(name: str, force: bool = False):
async def integrate_project(name: str, force: bool = False):
```

## Zusammenfassung aller Lücken

| # | Lücke | Kritikalität | Status |
|---|-------|--------------|--------|
| 1 | `force` Flag in `run_evolution_pipeline` | 🔴 Kritisch | Im ADR beschrieben |
| 2 | Import unvollständig | 🔴 Kritisch | Im ADR beschrieben |
| 3 | Projekt-Status Update | 🟡 Wichtig | Im ADR beschrieben |
| 4 | Concurrent Execution Guard | 🟡 Wichtig | Im ADR beschrieben |
| 5 | Timeout Handling | 🟢 Optional | Im ADR beschrieben |
| 6 | `force` Bugs in evolution.py | 🔴 Kritisch | ✅ GEFIXT |
