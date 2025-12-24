# Integration Test Szenarien

## 1. API Health Check
```bash
curl http://localhost:8001/
# Expected: {"status": "running", ...}
```

## 2. Execute Project
```bash
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/test-simple"}'
# Expected: {"job_id": "xxx"}
```

## 3. Stream Events
```bash
curl http://localhost:8001/helix/stream/{job_id}
# Expected: SSE stream with phase events
```

## 4. CLI via API
```bash
./scripts/helix run projects/test-simple --dry-run
# Expected: Dry run output

./scripts/helix jobs
# Expected: Job list
```

## 5. OpenAI Endpoint (für Open WebUI)
```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "helix-consultant", "messages": [{"role": "user", "content": "Hello"}]}'
# Expected: {"choices": [...]}
```

## 6. Cleanup Verification
```bash
# Alte Dateien sollten nicht mehr existieren
ls src/helix/orchestrator_legacy.py  # Sollte fehlen
ls src/helix/orchestrator/           # Sollte fehlen

# Keine Import Errors
python3 -c "import helix; print('OK')"
```
