# Nächste Session: ADR-022 Implementation

## Kontext

In der vorherigen Session haben wir:
1. Das Architektur-Chaos analysiert (3 Orchestrator-Implementierungen)
2. ADR-022 geschrieben (Unified API Architecture)
3. Ein 5-Phasen Projekt aufgesetzt (`projects/implement-adr-022/`)
4. Die Vision "Consultant als Gateway" dokumentiert

## Deine Aufgabe

Implementiere ADR-022 in 5 Phasen:

### Phase 1: UnifiedOrchestrator erstellen
```bash
cd /home/aiuser01/helix-v4
cat projects/implement-adr-022/phases/1/CLAUDE.md
```

Erstelle:
- `src/helix/api/orchestrator.py` - Der EINE Orchestrator
- `tests/api/test_orchestrator.py` - Tests
- `docs/sources/api-orchestrator.yaml` - Code-Layer Doku

### Phase 2: API Endpoints aktualisieren
```bash
cat projects/implement-adr-022/phases/2/CLAUDE.md
```

### Phase 3: CLI als API Client
```bash
cat projects/implement-adr-022/phases/3/CLAUDE.md
```

### Phase 4: Aufräumen
```bash
cat projects/implement-adr-022/phases/4/CLAUDE.md
```

Lösche:
- `src/helix/orchestrator_legacy.py`
- `src/helix/orchestrator/` (ganzes Package)

### Phase 5: Integration Test + Open WebUI
```bash
cat projects/implement-adr-022/phases/5/CLAUDE.md
```

Open WebUI Integration bedeutet:
- `/v1/chat/completions` funktioniert
- Model "helix-consultant" ist verfügbar
- Consultant kann Tools aufrufen (list_adrs, implement_adr, etc.)

## Wichtige Dateien zum Lesen

```bash
# Das ADR das du implementierst
cat adr/022-unified-api-architecture.md

# Bestehender Code (zum Konsolidieren)
cat src/helix/orchestrator_legacy.py
cat src/helix/api/streaming.py
ls src/helix/orchestrator/

# Verification (muss integriert werden)
cat src/helix/evolution/verification.py

# Die Vision für Consultant
cat adr/draft/consultant-as-gateway.md
```

## Wie du prüfst ob du fertig bist

Nach JEDER Phase:

```bash
# 1. Dateien existieren
ls -la src/helix/api/orchestrator.py

# 2. Syntax OK
python3 -m py_compile src/helix/api/orchestrator.py

# 3. Tests laufen
PYTHONPATH=src pytest tests/api/test_orchestrator.py -v

# 4. API funktioniert
curl http://localhost:8001/

# 5. CLI via API
./scripts/helix run projects/test-simple --dry-run
```

Am Ende (Phase 5):

```bash
# Open WebUI Endpoint
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "helix-consultant", "messages": [{"role": "user", "content": "Welche ADRs haben wir?"}]}'

# Alte Dateien weg
ls src/helix/orchestrator_legacy.py  # Sollte "No such file" geben

# ADR Status
grep "status:" adr/022-unified-api-architecture.md  # Sollte "Implemented" zeigen
```

## Dokumentation

Für jede neue Datei:
1. Docstrings im Code (Google-Style)
2. Code-Layer YAML in `docs/sources/`
3. Prüfen mit `docs_compiler compile`

## Wenn du fertig bist

1. ADR-022 Status auf "Implemented" setzen
2. Commit mit aussagekräftiger Message
3. Zusammenfassung was gemacht wurde

## Start

```bash
cd /home/aiuser01/helix-v4
source config/env.sh

# Lies zuerst Phase 1
cat projects/implement-adr-022/phases/1/CLAUDE.md

# Dann implementiere
```

Viel Erfolg!
