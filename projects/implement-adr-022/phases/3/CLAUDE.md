# Phase 3: CLI als API Client

## Deine Aufgabe

CLI soll die API aufrufen statt eigener Orchestrator-Logik.

## Was du lesen musst

```bash
# Aktuelle CLI Commands (die du änderst)
cat src/helix/cli/commands.py
cat src/helix/cli/main.py
```

## Was du erstellen musst

### 1. `output/src/helix/cli/api_client.py`

Async HTTP Client der die API aufruft:

```python
"""CLI API Client - ruft HELIX API auf."""

import httpx

API_BASE = "http://localhost:8001"

async def run_project(project_path: str, background: bool = False):
    """Run project via API."""
    async with httpx.AsyncClient(timeout=None) as client:
        # Start job
        response = await client.post(
            f"{API_BASE}/helix/execute",
            json={"project_path": project_path}
        )
        job = response.json()
        
        if background:
            return job["job_id"]
        
        # Stream events
        async with client.stream("GET", f"{API_BASE}/helix/stream/{job['job_id']}") as r:
            async for line in r.aiter_lines():
                # Handle SSE events
                ...

async def list_jobs():
    """List all jobs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/helix/jobs")
        return response.json()
```

### 2. `output/src/helix/cli/commands.py`

Aktualisiert - ruft `api_client` auf:

```python
@click.command()
@click.argument("project_path")
@click.option("--background", "-bg", is_flag=True)
def run(project_path: str, background: bool):
    """Run project via API."""
    from .api_client import run_project
    asyncio.run(run_project(project_path, background))
```

### 3. `output/scripts/helix`

Standalone Script das API startet wenn nötig:

```bash
#!/bin/bash
# Prüfe ob API läuft, starte wenn nötig
if ! curl -s http://localhost:8001/ > /dev/null; then
    echo "Starting HELIX API..."
    PYTHONPATH=src python3 -m uvicorn helix.api.main:app --port 8001 &
    sleep 2
fi

# CLI ausführen
PYTHONPATH=src python3 -m helix.cli.main "$@"
```

## Erfolgskriterien

```bash
# 1. Kopiere Dateien
cd /home/aiuser01/helix-v4
cp output/src/helix/cli/api_client.py src/helix/cli/
cp output/src/helix/cli/commands.py src/helix/cli/
cp output/scripts/helix scripts/
chmod +x scripts/helix

# 2. API muss laufen
curl http://localhost:8001/

# 3. CLI testen
./scripts/helix run projects/test-simple --dry-run
./scripts/helix jobs
./scripts/helix --help
```

## Checkliste

- [ ] `api_client.py` erstellt mit httpx
- [ ] `commands.py` ruft api_client auf
- [ ] `scripts/helix` startet API automatisch
- [ ] `helix run project` funktioniert
- [ ] `helix jobs` funktioniert
- [ ] `helix logs` funktioniert
