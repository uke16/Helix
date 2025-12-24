# Phase 5: Integration Test & Dokumentation

## Deine Aufgabe

End-to-End Tests und Dokumentation aktualisieren.

## Was du testen musst

### 1. Full Stack Test

```bash
cd /home/aiuser01/helix-v4

# API starten (falls nicht läuft)
PYTHONPATH=src python3 -m uvicorn helix.api.main:app --port 8001 &
sleep 2

# Test 1: API Health
curl http://localhost:8001/
echo "Expected: {status: running}"

# Test 2: CLI via API
./scripts/helix run projects/test-simple --dry-run
echo "Expected: Dry run output"

# Test 3: Execute echtes Projekt
./scripts/helix run projects/consultant-adr-019 --background
echo "Expected: Job ID"

# Test 4: Jobs listen
./scripts/helix jobs
echo "Expected: Job Liste"

# Test 5: OpenAI Endpoint (für Open WebUI)
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "helix-consultant", "messages": [{"role": "user", "content": "Hello"}]}'
echo "Expected: Chat completion response"
```

## Was du erstellen musst

### 1. `output/tests/integration/test_unified_api.py`

```python
"""Integration tests for Unified API."""

import pytest
import httpx

API_BASE = "http://localhost:8001"

@pytest.mark.asyncio
async def test_api_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/")
        assert response.status_code == 200
        assert "status" in response.json()

@pytest.mark.asyncio
async def test_execute_project():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/helix/execute",
            json={"project_path": "projects/test-simple"}
        )
        assert response.status_code == 200
        assert "job_id" in response.json()

@pytest.mark.asyncio
async def test_openai_chat_completions():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert response.status_code == 200
        assert "choices" in response.json()
```

### 2. `output/docs/sources/api.yaml` aktualisieren

Dokumentiere alle Endpoints.

### 3. `output/MIGRATION_COMPLETE.md`

```markdown
# ADR-022 Migration Complete

## Was wurde gemacht

1. ✅ UnifiedOrchestrator erstellt (src/helix/api/orchestrator.py)
2. ✅ API Endpoints aktualisiert
3. ✅ CLI nutzt jetzt API
4. ✅ ~2400 Zeilen toter Code entfernt
5. ✅ Integration Tests bestanden

## Vorher → Nachher

| Vorher | Nachher |
|--------|---------|
| 3 Orchestrator-Implementierungen | 1 UnifiedOrchestrator |
| CLI hatte eigene Logik | CLI ruft API auf |
| ~2400 Zeilen toter Code | Gelöscht |
| Inkonsistentes Verhalten | Ein Verhalten überall |

## Tests

- [ ] API Health Check: ✅
- [ ] CLI via API: ✅
- [ ] Execute Projekt: ✅
- [ ] OpenAI Endpoint: ✅
```

### 4. ADR-022 Status aktualisieren

```bash
# In adr/022-unified-api-architecture.md
# Ändere: status: Proposed
# Zu:     status: Implemented
```

## Erfolgskriterien

```bash
# Alle Tests müssen durchlaufen
cd /home/aiuser01/helix-v4
PYTHONPATH=src pytest tests/integration/test_unified_api.py -v

# ADR Status prüfen
grep "status:" adr/022-unified-api-architecture.md
# Sollte "status: Implemented" zeigen
```

## Checkliste

- [ ] Integration Tests erstellt
- [ ] Integration Tests laufen durch
- [ ] API Dokumentation aktualisiert
- [ ] MIGRATION_COMPLETE.md erstellt
- [ ] ADR-022 Status auf Implemented
- [ ] Open WebUI Endpoint funktioniert
