# ADR-031 Dogfooding Results - Root Cause Analysis

**Datum:** 2025-12-29
**Pipeline:** ADR-031 Pipeline Bug Fixes Wave 2
**Job ID:** 8c06a489
**Ergebnis:** 6/6 Phasen erfolgreich, aber Chat abgestürzt während Ausführung

---

## Bestätigte Bugs (aus SSH-Log Analyse)

### Bug 1: Status.json nicht synchronisiert (WIEDER BESTÄTIGT!)

**Symptom (aus SSH-Log):**
```
Stream zeigt: phase_complete für status-sync, file-permissions ✅
status.json zeigt: alle Phasen "pending" ❌
```

**Beweis aus Log:**
```json
// Nach phase_complete Events
"status": "failed",
"phases": {
  "status-sync": {"status": "pending"},  // Sollte "completed" sein!
  "file-permissions": {"status": "pending"}  // Sollte "completed" sein!
}
```

**Root Cause:** IDENTISCH zu ADR-030 - stream_phase_execution() sendet Events aber 
aktualisiert nicht status.json.

**Ironie:** Wir implementieren gerade den Fix für diesen Bug... und der Bug 
verhindert dass wir den Fortschritt sehen können!

---

### Bug 2: Pfad-Mismatch bei polling-api Phase (NEU!)

**Symptom (aus SSH-Log):**
```
event: verification_failed
data: {"phase_id": "polling-api", "missing_files": ["modified/src/helix/api/routes_evolution.py"]}
```

**Aber Claude hat die Datei erstellt als:**
```
modified/src/helix/api/routes/evolution.py  (mit /routes/ Unterverzeichnis!)
```

**Root Cause:** 
1. phases.yaml definiert: `modified/src/helix/api/routes_evolution.py`
2. Das existierende Projekt hat: `src/helix/api/routes/evolution.py` (in routes/ Subdir)
3. Claude Code hat das erkannt und die Datei korrekt in routes/ erstellt
4. Aber der Verifier sucht nach dem phases.yaml Pfad

**Fix:** phases.yaml sollte den tatsächlichen Dateipfad verwenden ODER
der Verifier sollte flexible Pfadauflösung haben.

**Update:** Retry hat funktioniert! Nach dem verification_failed hat die Pipeline
die Datei korrekt unter `routes_evolution.py` erstellt (ohne Subdir).

---

### Bug 3: MCP/Chat Timeout (WIEDER BESTÄTIGT!)

**Symptom:**
Chat ist während der Pipeline-Ausführung abgestürzt.

**Beweis aus Log:**
```
event: keepalive
data: {"phase_id": null, "status": "running", "timestamp": "2025-12-28T23:07:16..."}
event: keepalive
data: {"phase_id": null, "status": "running", "timestamp": "2025-12-28T23:07:46..."}
event: keepalive
data: {"phase_id": null, "status": "running", "timestamp": "2025-12-28T23:08:16..."}
// Dann Chat-Absturz
```

**Root Cause:** Keepalives alle 30 Sekunden sind nicht genug um MCP Connection
aufrecht zu erhalten bei langen Operationen.

**Positive Erkenntnis:** Pipeline läuft weiter auch wenn Client disconnected! ✅

---

### Bug 4: Validator ignoriert routes/ Subdir-Struktur

**Symptom:** 
phases.yaml sagt `routes_evolution.py` aber echte Struktur ist `routes/evolution.py`

**Root Cause:**
```
src/helix/api/
├── routes/           # Existierendes Subdir
│   ├── evolution.py  # Echte Datei
│   └── ...
└── routes_evolution.py  # phases.yaml erwartet hier
```

Die phases.yaml wurde mit falschen Annahmen über die Projektstruktur erstellt.

**Fix:** phases.yaml vor Pipeline-Start gegen tatsächliche Projektstruktur validieren.

---

## Pipeline-Verlauf (aus SSH-Log rekonstruiert)

| Zeit | Phase | Event | Status |
|------|-------|-------|--------|
| 22:53:14 | - | pipeline_started | ✅ |
| 22:53:14 | status-sync | phase_start | ✅ |
| 22:57:48 | status-sync | verification_passed | ✅ |
| 22:57:48 | status-sync | phase_complete | ✅ |
| 22:57:48 | file-permissions | phase_start | ✅ |
| 23:02:40 | file-permissions | verification_passed (49 tests) | ✅ |
| 23:02:41 | file-permissions | phase_complete | ✅ |
| 23:02:41 | polling-api | phase_start | ✅ |
| 23:05:39 | polling-api | output complete | ✅ |
| 23:05:40 | polling-api | verification_failed (attempt 1) | ⚠️ |
| ~23:08:00 | polling-api | (retry successful) | ✅ |
| ~23:10:00 | output-validator | completed | ✅ |
| ~23:15:00 | integration-streaming | completed | ✅ |
| ~23:20:00 | tests | completed | ✅ |

**Gesamtdauer:** ~27 Minuten (22:53 - ~23:20)

---

## Manuelle Eingriffe erforderlich

### 1. Status.json korrigieren
```bash
# Alle Phasen zeigen "pending" obwohl sie abgeschlossen sind
# Muss manuell auf "completed" gesetzt werden
```

### 2. Output-Dateien deployen
```bash
# Von phases/*/output/ nach src/
# - status_sync.py
# - file_permissions.py  
# - routes_evolution.py (oder routes/evolution.py?)
# - validator.py
# - streaming.py
```

### 3. Tests verifizieren
```bash
# Neue Tests ausführen
pytest tests/evolution/test_status_sync.py
pytest tests/evolution/test_file_permissions.py
pytest tests/api/test_polling_api.py
```

---

## Erkenntnisse für ADR-032

### Neue Bugs für nächste Wave:

1. **phases.yaml Pfad-Validierung:** Pfade gegen Projektstruktur prüfen
2. **Retry-Logging:** Erfolgreiche Retries besser loggen
3. **Keepalive-Frequenz:** 30s ist zu lang, 10s wäre besser
4. **Disconnect-Recovery:** Client sollte reconnecten können

### Positive Erkenntnisse:

1. **Pipeline ist resilient:** Läuft weiter auch bei Client-Disconnect
2. **Retry funktioniert:** verification_failed bei polling-api wurde erfolgreich wiederholt
3. **Alle Phasen abgeschlossen:** Trotz Bug 1 (Status nicht sync) wurden alle Dateien erstellt

