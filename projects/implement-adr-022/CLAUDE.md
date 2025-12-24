# HELIX Projekt: ADR-022 Implementation

Du implementierst ADR-022: Unified API Architecture.

## ⚠️ WICHTIG: Was "fertig" bedeutet

Du bist NICHT fertig wenn du Code geschrieben hast.
Du bist fertig wenn:

1. ✅ Alle Dateien in `output/` existieren
2. ✅ Alle Tests laufen durch
3. ✅ Die Integration funktioniert
4. ✅ Du es SELBST getestet hast

## 🎯 Dein Ziel

Nach diesem Projekt:
- `helix run project` funktioniert via API
- Es gibt nur EINE Orchestrator-Implementierung
- ~2000 Zeilen toter Code sind gelöscht
- Open WebUI kann die API nutzen

## 📋 So prüfst du ob du fertig bist

### Nach JEDER Phase:

```bash
# 1. Prüfe ob Output-Dateien existieren
ls -la output/

# 2. Prüfe Python Syntax
python3 -m py_compile output/src/helix/api/orchestrator.py

# 3. Führe Tests aus
cd /home/aiuser01/helix-v4
PYTHONPATH=src pytest output/tests/ -v

# 4. Prüfe ob API läuft
curl http://localhost:8001/

# 5. Wenn API nicht läuft, starte sie:
PYTHONPATH=src python3 -m uvicorn helix.api.main:app --port 8001 &
```

### Am Ende des Projekts:

```bash
# End-to-End Test
cd /home/aiuser01/helix-v4

# 1. API Health Check
curl http://localhost:8001/

# 2. CLI via API testen
PYTHONPATH=src python3 -m helix.cli.main run projects/test-project --dry-run

# 3. OpenAI Endpoint testen
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "helix-consultant", "messages": [{"role": "user", "content": "Hello"}]}'

# 4. Prüfe dass alte Dateien gelöscht sind
ls src/helix/orchestrator_legacy.py  # Sollte "No such file" geben
ls src/helix/orchestrator/           # Sollte "No such file" geben
```

## 📁 Projekt-Struktur

```
projects/implement-adr-022/
├── CLAUDE.md              ← Du bist hier
├── phases.yaml            ← Phasen-Definition
└── phases/
    ├── 1/                 ← UnifiedOrchestrator
    │   ├── CLAUDE.md      ← Phase-spezifische Anweisungen
    │   ├── input/         ← Was du lesen sollst
    │   └── output/        ← Was du erstellen sollst
    ├── 2/                 ← API Endpoints
    ├── 3/                 ← CLI als Client
    ├── 4/                 ← Aufräumen
    └── 5/                 ← Integration Test
```

## 🔧 HELIX Tools die du nutzen sollst

### 1. ADR Tool - Validiere ADR Format
```bash
PYTHONPATH=src python3 -m helix.tools.adr_tool validate adr/022-unified-api-architecture.md
```

### 2. Verify Phase - Prüfe deine Outputs
```bash
PYTHONPATH=src python3 -m helix.tools.verify_phase --phase-dir phases/1
```

### 3. Docs Compiler - Regeneriere Dokumentation
```bash
PYTHONPATH=src python3 -m helix.tools.docs_compiler compile
```

## 📖 Was du lesen sollst

Bevor du anfängst:

1. **ADR-022** (das implementierst du):
   ```bash
   cat adr/022-unified-api-architecture.md
   ```

2. **Bestehender Code** (den du konsolidierst):
   ```bash
   cat src/helix/orchestrator_legacy.py
   cat src/helix/api/streaming.py
   ls src/helix/orchestrator/
   ```

3. **ADR-011** (Verification die du integrieren musst):
   ```bash
   cat adr/011-post-phase-verification.md
   cat src/helix/evolution/verification.py
   ```

## ⚡ Quick Reference

| Was | Befehl |
|-----|--------|
| Tests ausführen | `PYTHONPATH=src pytest tests/ -v` |
| API starten | `PYTHONPATH=src uvicorn helix.api.main:app --port 8001` |
| API Health | `curl http://localhost:8001/` |
| CLI Help | `PYTHONPATH=src python3 -m helix.cli.main --help` |
| Phase verifizieren | `PYTHONPATH=src python3 -m helix.tools.verify_phase` |

## 🚫 Was du NICHT tun sollst

1. **NICHT** einfach Code schreiben ohne zu testen
2. **NICHT** Phase als fertig markieren ohne Verification
3. **NICHT** alte Dateien löschen ohne Backup
4. **NICHT** API Änderungen machen ohne Endpoint-Test
5. **NICHT** vergessen die Dokumentation zu aktualisieren

## ✅ Checkliste pro Phase

Bevor du zur nächsten Phase gehst:

- [ ] Alle output/ Dateien erstellt?
- [ ] Python Syntax OK? (`python3 -m py_compile ...`)
- [ ] Tests geschrieben und laufen durch?
- [ ] Keine neuen Linter-Errors?
- [ ] Integration getestet (API call, CLI call)?
- [ ] Dokumentation aktualisiert wenn nötig?
