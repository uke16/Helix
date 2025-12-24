# Phase 2: API Endpoints aktualisieren

## Deine Aufgabe

`streaming.py` soll den `UnifiedOrchestrator` aus Phase 1 nutzen.
Keine eigene Orchestrator-Logik mehr!

## Was du lesen musst

```bash
# 1. Den neuen Orchestrator (aus Phase 1)
cat src/helix/api/orchestrator.py

# 2. Aktuelle streaming.py (die du vereinfachst)
cat src/helix/api/streaming.py

# 3. Aktuelle routes
cat src/helix/api/routes/project.py
```

## Was du erstellen musst

### 1. `output/src/helix/api/streaming.py`

Vereinfachte Version die nur noch:
- SSE Events formatiert
- Den UnifiedOrchestrator aufruft

```python
"""Streaming - Thin wrapper um UnifiedOrchestrator."""

from .orchestrator import UnifiedOrchestrator, PhaseEvent

async def stream_project_execution(
    project_path: Path,
) -> AsyncGenerator[str, None]:
    """Stream project execution as SSE events."""
    
    orchestrator = UnifiedOrchestrator()
    
    async def emit_event(event: PhaseEvent):
        yield format_sse(event)
    
    # KEINE eigene Orchestrator-Logik mehr!
    await orchestrator.run_project(project_path, on_event=emit_event)
```

### 2. `output/src/helix/api/routes/project.py`

Aktualisierte Endpoints:
- `POST /helix/execute` - Startet Job
- `GET /helix/stream/{job_id}` - SSE Stream
- `GET /helix/jobs` - Liste Jobs
- `DELETE /helix/jobs/{job_id}` - Stop Job

## Erfolgskriterien

```bash
# 1. API starten
cd /home/aiuser01/helix-v4
cp output/src/helix/api/streaming.py src/helix/api/
cp output/src/helix/api/routes/project.py src/helix/api/routes/
PYTHONPATH=src python3 -m uvicorn helix.api.main:app --port 8001 &

# 2. Health Check
curl http://localhost:8001/
# Sollte {"status": "running"} zurückgeben

# 3. Execute Endpoint testen
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/test-simple"}'
# Sollte {"job_id": "xxx"} zurückgeben

# 4. Jobs Endpoint
curl http://localhost:8001/helix/jobs
```

## Checkliste

- [ ] `streaming.py` nutzt `UnifiedOrchestrator`
- [ ] Keine duplizierte Orchestrator-Logik
- [ ] `POST /helix/execute` funktioniert
- [ ] `GET /helix/stream/{job_id}` liefert SSE
- [ ] `GET /helix/jobs` listet Jobs
- [ ] API Health Check OK
