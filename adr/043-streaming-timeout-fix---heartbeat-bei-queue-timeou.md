---
adr_id: "043"
title: "Streaming Timeout Fix - Heartbeat bei Queue-Timeout"
status: Proposed

component_type: SERVICE
classification: FIX
change_scope: minor

domain: "helix"
language: "python"
skills:
  - helix
  - infrastructure

files:
  create: []
  modify:
    - src/helix/api/routes/openai.py
  docs: []

depends_on:
  - "ADR-013"
  - "ADR-027"
---

# ADR-043: Streaming Timeout Fix - Heartbeat bei Queue-Timeout

## Status
Proposed

## Kontext

Es gibt einen kritischen Streaming-Bug der dazu führt, dass:
1. User sendet Nachricht an Consultant (via Open WebUI)
2. User sieht nur "[Starte Claude Code...]" und "[Read]"
3. Connection bricht nach ~20 Sekunden ab
4. Claude-Prozess läuft im Hintergrund WEITER und produziert vollständige Antwort
5. Diese Antwort erreicht den User NIE

### Architektur
```
Browser -> Caddy (8443) -> Open WebUI (8090) -> HELIX API (8001) -> Claude CLI
                SSE Stream <--------------------------------------
```

### Root-Cause

Der Bug liegt in `openai.py:341-350`. Die Event-Loop wartet auf Queue-Events mit 1s Timeout, sendet aber bei TimeoutError KEINEN Heartbeat an den Client:

```python
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(...)
    except asyncio.TimeoutError:
        continue   # <-- BUG: Kein Output an Client!
```

Der separate Heartbeat-Task pusht zwar `.` in die Queue, aber diese Queue-Events werden bei mangelndem Claude-Output nie gesendet - die Schleife landet im `except asyncio.TimeoutError` und macht `continue` ohne zu yielden.

## Entscheidung

### Fix 1: Heartbeat direkt im Exception-Handler senden

Statt auf Queue-Events zu warten, senden wir den Heartbeat direkt wenn zu lange keine Aktivität war:

```python
last_heartbeat = time.time()
HEARTBEAT_INTERVAL = 15  # Sekunden - sicher unter 20s Timeout

while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(completion_id, created, model, event)
            last_heartbeat = time.time()
    except asyncio.TimeoutError:
        # FIX: Heartbeat senden wenn zu lange keine Aktivität
        now = time.time()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            yield _make_chunk(completion_id, created, model, " .")
            last_heartbeat = now
        continue
```

### Fix 2: Separaten Heartbeat-Task entfernen

Der Heartbeat-Task (Zeilen 318-325) ist mit diesem Fix obsolet und kann entfernt werden.

### Fix 3: Caddy SSE-Konfiguration (optional, aber empfohlen)

```caddyfile
helix2.duckdns.org:8443 {
    reverse_proxy 127.0.0.1:8090 {
        flush_interval -1    # Sofortiges Flushen für SSE
        transport http {
            read_timeout 600s
            write_timeout 600s
        }
    }
}
```

## Implementation

### Änderungen in `src/helix/api/routes/openai.py`

1. **Zeile 286:** `last_heartbeat` Variable hinzufügen
2. **Zeilen 318-325:** Heartbeat-Task entfernen (obsolet)
3. **Zeilen 341-350:** Exception-Handler mit direktem Heartbeat-Yield erweitern
4. **Zeilen 353-357:** Heartbeat-Cancel Code entfernen

## Akzeptanzkriterien

- [ ] User erhält alle 15s ein Heartbeat-Zeichen im SSE-Stream
- [ ] Connection bleibt bei 5+ Minuten Claude-Arbeit stabil
- [ ] Keine Regression: Normale Streaming-Responses funktionieren weiterhin
- [ ] Test: Consultant-Session mit 3+ Minuten Read-Operation ohne Abbruch
- [ ] Log-Eintrag bei jedem Heartbeat für Debugging

## Konsequenzen

### Positiv
- SSE-Verbindung bleibt auch bei langen Claude-Operationen stabil
- Einfacher Fix mit minimalen Änderungen
- Entfernung des redundanten Heartbeat-Tasks vereinfacht Code

### Negativ
- Heartbeat-Zeichen (` .`) erscheinen im User-Output (minimal störend)
- 15s ist konservativ - könnte auf 25s erhöht werden wenn stabil

## Alternativen betrachtet

1. **HTTP/2 Server Push**: Zu komplex, nicht von allen Clients unterstützt
2. **WebSocket statt SSE**: Großer Umbau, nicht nötig
3. **aiohttp timeout erhöhen**: Löst nicht das fundamentale Problem

## Dokumentation

- Code-Kommentare in openai.py erklären den Heartbeat-Mechanismus
- ADR-042 erwähnt den ursprünglichen Queue-Ansatz (dieser ADR korrigiert ihn)
- Keine externe Dokumentation nötig da interner Fix
