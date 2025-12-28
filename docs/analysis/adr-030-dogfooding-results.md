# ADR-030 Dogfooding Results - Root Cause Analysis

**Datum:** 2025-12-28
**Pipeline:** ADR-030 Evolution Pipeline Reliability
**Ergebnis:** 6/6 Phasen erfolgreich, aber mit manuellen Eingriffen

---

## Bestätigte Bugs

### Bug 1: Status.json nicht synchronisiert (Issue #2)

**Symptom:**
```
Stream zeigt: phase_complete für alle 6 Phasen
status.json zeigt: 5 von 6 Phasen "pending"
```

**Root Cause:**
Die `stream_phase_execution()` Funktion sendet SSE Events, aber aktualisiert nicht 
die `status.json` Datei. Es gibt zwei parallele Status-Tracking-Systeme:
1. In-Memory `JobState` (für API)
2. On-Disk `status.json` (für Persistenz)

Diese sind nicht synchronisiert.

**Beweis:**
```python
# src/helix/api/streaming.py - sendet nur Events
yield StreamEvent(type="phase_complete", data=...)

# Aber KEIN Update zu status.json oder JobState.phases
```

**Fix erforderlich in:**
- `src/helix/api/streaming.py` - JobState.update_phase() aufrufen
- `src/helix/evolution/project.py` - status.json schreiben

---

### Bug 2: Datei-Berechtigungen 0600 (Issue #7)

**Symptom:**
```bash
$ ls -la ADR-030.md
-rw------- 1 aiuser01 aiuser01 26476 Dec 28 ADR-030.md
# Sollte sein: -rw-r--r-- (0644)
```

**Root Cause:**
1. Claude Code's `str_replace_editor` Tool erstellt Dateien mit User's umask
2. User hat restrictive umask (0077)
3. `shutil.copy2()` preserviert Source-Permissions

**Beweis:**
```bash
$ umask
0077
$ touch testfile && ls -la testfile
-rw------- 1 aiuser01 aiuser01 0 Dec 28 testfile
```

**Fix erforderlich in:**
- `src/helix/evolution/deployer.py` - normalize_permissions() nach jedem copy
- Oder: Wrapper um str_replace_editor Tool

---

### Bug 3: MCP Timeout bei langen Streams (NEU!)

**Symptom:**
```
McpError: MCP error -32001: Request timed out
```
Nach ca. 5 Minuten Stream-Zeit.

**Root Cause:**
Das SSH-MCP Tool hat ein Default-Timeout von 300 Sekunden (5 Min).
Lange Pipeline-Läufe überschreiten dieses Timeout.

**Beweis:**
```
curl -s -N "http://localhost:8001/helix/stream/{id}" --max-time 300
# Nach 300s → Timeout
```

**Workaround:**
Kürzere curl-Aufrufe mit `--max-time 120` und mehrfaches Abrufen.

**Fix erforderlich:**
- Entweder: MCP Timeout erhöhen
- Oder: Polling-basiertes Status-API statt lange Streams

---

### Bug 4: output/ vs modified/new/ Directory Mismatch (NEU!)

**Symptom:**
```
Verification failed: output file placed in modified/ but verifier looks in output/
```

**Root Cause:**
Die phases.yaml definiert:
```yaml
output:
  - "modified/src/helix/phase_status.py"
```

Aber der Verifier sucht in `phases/{id}/output/`.

Es gibt Inkonsistenz zwischen:
- ADR-030: Erwartet `modified/` und `new/`
- phases.yaml: Definiert `output:` Liste
- Verifier: Sucht in `output/`

**Beweis aus Stream:**
```
Issue Found: output file modified/src/helix/phase_status.py was placed in modified/
Verifier looks for files in output/
Resolution: Copied file to output/src/helix/phase_status.py
```

**Fix erforderlich:**
- Entweder: Verifier anpassen für `modified/` und `new/`
- Oder: phases.yaml Schema dokumentieren/standardisieren

---

## Nicht-implementierte Fixes aus ADR-030

Diese wurden dokumentiert aber nicht durch die Pipeline implementiert:

| Fix | Beschreibung | Status |
|-----|--------------|--------|
| Fix 6 | Project Discovery via Definition-Files | ❌ Nicht implementiert |
| Fix 7 | Permission Normalization im Deployer | ❌ Nicht implementiert |
| Fix 8 | Global Exception Handler | ❌ Nicht implementiert |
| Fix 9 | None-Safe Sorting | ❌ Nicht implementiert |

---

## Empfehlung

Erstelle **ADR-031: Pipeline Bug Fixes Wave 2** mit:

1. Status Synchronisation (Bug 1)
2. Permission Normalization (Bug 2)
3. Stream Timeout Handling (Bug 3)
4. Output Directory Standardization (Bug 4)
5. Restliche Fixes 6-9 aus ADR-030

