# Root-Cause-Analyse: Streaming-Timeout-Bug

## Executive Summary

Der Streaming-Bug ist ein **Timing-Race-Condition** zwischen der Queue-basierten Event-Streaming und der asyncio Task-Execution. Das Problem liegt in `openai.py:342-350` - die Schleife wartet auf Queue-Events, aber die Events werden erst produziert wenn Claude CLI Output liefert. Bei langen Read-Operationen (>1 Sekunde ohne Output) gibt es keine Heartbeats.

## Root-Cause: 3 Bugs gefunden

### Bug 1: Queue-Timeout blockiert Heartbeat-Events (KRITISCH)

**Location:** `src/helix/api/routes/openai.py:341-350`

```python
# Stream events from queue while Claude Code runs
while not claude_task.done():
    try:
        # Wait for event with timeout
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)  # <-- BUG!
        if event:
            yield _make_chunk(...)
    except asyncio.TimeoutError:
        # No event, check if task done
        continue   # <-- Heartbeat wird NICHT gesendet!
```

**Problem:** Der Heartbeat-Task pusht zwar `.` alle 25s in die Queue, aber:
1. `asyncio.wait_for(queue.get(), timeout=1.0)` wacht nach 1s auf
2. Bei `TimeoutError` wird nur `continue` ausgeführt
3. **Es wird KEIN Chunk an den Client gesendet!**
4. Der Client sieht 20+ Sekunden keine Aktivität und bricht ab

### Bug 2: Open WebUI AIOHTTP_CLIENT_TIMEOUT = 300s (Nicht der Auslöser, aber relevant)

**Location:** Open WebUI `env.py`

```python
AIOHTTP_CLIENT_TIMEOUT = 300  # 5 Minuten default
```

Das sollte eigentlich reichen. Aber der **socket idle timeout** ist kürzer.

### Bug 3: Caddy hat keine SSE-spezifischen Timeouts

**Location:** `/home/aiuser01/Caddyfile`

```
helix2.duckdns.org:8443 {
    reverse_proxy 127.0.0.1:8090
    # KEINE flush_interval!
    # KEINE timeouts für SSE!
}
```

**Problem:** Caddy puffert möglicherweise SSE-Chunks und sendet sie nicht sofort weiter.

---

## Warum ~20 Sekunden Timeout?

Die Kette der Timeouts:

1. **Browser/Fetch API**: Kein hartes Timeout, wartet auf Chunks
2. **Open WebUI (Python/aiohttp)**: 300s total timeout, ABER...
3. **aiohttp socket read timeout**: Default 30s ohne neue Daten
4. **Caddy**: Unbekannt, aber typisch 30s keepalive

Der **20s Timeout** passt zu:
- Linux TCP keepalive probe timing (7.5s * 3 = 22.5s nach 15s initial)
- Oder ein internes aiohttp read timeout

---

## Fix-Vorschlag

### Fix 1: Heartbeat bei Queue-Timeout senden (KRITISCH)

```python
# VORHER (kaputt)
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(completion_id, created, model, event)
    except asyncio.TimeoutError:
        continue  # <-- KEIN OUTPUT!

# NACHHER (fix)
last_heartbeat = time.time()
HEARTBEAT_INTERVAL = 15  # Sekunden

while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(completion_id, created, model, event)
            last_heartbeat = time.time()
    except asyncio.TimeoutError:
        # FIX: Heartbeat senden wenn zu lange keine Aktivität
        if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
            yield _make_chunk(completion_id, created, model, " .")
            last_heartbeat = time.time()
        continue
```

### Fix 2: Caddy SSE-Konfiguration

```caddyfile
helix2.duckdns.org:8443 {
    reverse_proxy 127.0.0.1:8090 {
        flush_interval -1    # Sofortiges Flushen für SSE
        transport http {
            read_timeout 600s    # 10 Minuten für lange Streams
            write_timeout 600s
        }
    }
}
```

### Fix 3: Den separaten Heartbeat-Task entfernen

Der aktuelle Heartbeat-Task ist nutzlos, weil die Queue-Events nicht an den Client gesendet werden wenn kein anderer Output kommt.

---

## Akzeptanzkriterien für den Fix

- [ ] User erhält alle 15s ein Heartbeat-Zeichen (`.`) im SSE-Stream
- [ ] Connection bleibt auch bei 5+ Minuten Claude-Arbeit stabil
- [ ] Caddy flusht SSE-Chunks sofort
- [ ] Test: 3 Minuten Read-Operation ohne Abbruch

---

## Nächste Schritte

1. **Sofort-Fix:** `openai.py` Zeile 348 anpassen (Heartbeat bei TimeoutError)
2. **Caddy-Update:** flush_interval und timeouts setzen
3. **Test:** Lange Claude-Operation durchführen

Soll ich den Fix direkt implementieren?

<!-- STEP: generate -->
