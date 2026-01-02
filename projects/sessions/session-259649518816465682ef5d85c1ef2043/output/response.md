# Root Cause Analyse: Streaming Timeout Bug

## Executive Summary

Der Bug tritt auf, weil die SSE (Server-Sent Events) Chunks **NICHT während der Claude-Ausführung gestreamt werden**, sondern erst NACH dem vollständigen Abschluss. Der Heartbeat-Task läuft zwar, aber die Events erreichen den Client nie, weil sie in einer Queue landen statt direkt gesendet zu werden.

---

## 1. Streaming-Architektur (Wie es funktionieren SOLL)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Open WebUI  │◄───│ FastAPI/SSE │◄───│ event_queue │◄───│ Claude CLI  │
│   Client    │    │  Generator  │    │  (asyncio)  │    │  (stdout)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
        ▲                                    ▲
        │                                    │
     SSE Chunks                     on_output() callback
     "[Read] ..."                   parsed JSONL events
```

**Idee:** Claude CLI gibt JSONL auf stdout aus → `on_output` callback parst es → schreibt in Queue → Generator liest aus Queue → SSE Chunk an Client.

---

## 2. Der Bug: Blockierte Event-Schleife

### Problem in `openai.py` Zeile 333-360

```python
# ADR-042: Run Claude Code in background, stream events from queue
claude_task = asyncio.create_task(
    runner.run_phase_streaming(
        phase_dir=session_path,
        on_output=on_output,  # ◄── Callback schreibt in Queue
        timeout=600,
    )
)

# Stream events from queue while Claude Code runs
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(...)  # ◄── SSE Chunk an Client
    except asyncio.TimeoutError:
        continue
```

**Das sieht korrekt aus, ABER:**

### Das eigentliche Problem: `run_phase_streaming` in `claude_runner.py`

In `claude_runner.py` Zeile 441-445:

```python
# Read stdout and stderr concurrently
await asyncio.gather(
    read_stream(process.stdout, "stdout", stdout_lines),
    read_stream(process.stderr, "stderr", stderr_lines),
)
```

Die `read_stream` Funktion **blockiert bis ALLE Zeilen gelesen sind** (bis EOF). Die `on_output` callback wird zwar für jede Zeile aufgerufen, aber:

1. Der `await asyncio.gather(...)` **blockiert den Task vollständig**
2. Während der Task blockiert ist, kann der Generator in `openai.py` nicht yielden
3. Der Client sieht nur das initiale `[Starte Claude Code...]` und dann... nichts

### Beweis: Die Race Condition

```python
# openai.py Zeile 342-350
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        # ...
    except asyncio.TimeoutError:
        continue  # ◄── Loop läuft, aber Queue ist leer!
```

Die Events werden in die Queue geschrieben via `on_output()`, **ABER** der `claude_task` ist ein einzelner awaitable der das gesamte `asyncio.gather()` abwartet. Die Queue-Events werden **synchron innerhalb von `asyncio.gather()` gesammelt**, nicht asynchron für den Generator verfügbar gemacht.

---

## 3. Timeout-Kette

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TIMEOUT KASKADE                               │
├──────────────────┬──────────────────────────────────────────────────┤
│ Open WebUI       │ ~30 Sekunden (HTTP client timeout)               │
│ nginx/Proxy      │ ~60 Sekunden (proxy_read_timeout default)        │
│ Heartbeat        │ 25 Sekunden (aber Events kommen nicht durch!)    │
│ Claude Runner    │ 600 Sekunden (10 Minuten)                        │
│ Claude CLI       │ 1800 Sekunden (30 Minuten DEFAULT_TIMEOUT)       │
└──────────────────┴──────────────────────────────────────────────────┘
```

**Das Problem:** Der Heartbeat sendet `.` in die Queue, aber die Queue wird nie gelesen weil der `while not claude_task.done()` Loop **nie `await` hat das andere Tasks laufen lässt**.

---

## 4. Root Cause: Falsches Async Pattern

### Der Code MEINT folgendes zu tun:

1. Starte Claude CLI als Background Task
2. Claude schreibt JSONL → on_output schreibt in Queue
3. Generator liest aus Queue und yielded SSE Chunks
4. Client sieht live Updates

### Der Code TUT aber folgendes:

1. Starte Claude CLI als Task
2. Task führt `asyncio.gather()` aus → **blockiert komplett**
3. Queue füllt sich, aber Generator kann nicht lesen
4. Client wartet auf HTTP response → Timeout!
5. Claude läuft weiter im Hintergrund (darum 1 Minute bis fertig)

---

## 5. Warum der Heartbeat nicht hilft

```python
async def heartbeat_task():
    """Send heartbeat every 25s to prevent timeout."""
    try:
        while True:
            await asyncio.sleep(25)
            await event_queue.put(".")  # ◄── Schreibt in Queue
    except asyncio.CancelledError:
        pass

heartbeat = asyncio.create_task(heartbeat_task())
```

Der Heartbeat läuft korrekt und schreibt `.` in die Queue. **ABER:**

Das `while not claude_task.done()` in der Generator-Funktion `_run_consultant_streaming` ist ein **synchroner Loop**, der den Generator blockiert:

```python
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        # ^^^ Dieses await gibt der Event-Loop Zeit, ABER...
        if event:
            yield _make_chunk(...)  # ◄── Yield funktioniert nicht wie erwartet!
```

Der `yield` in einer `async def` Funktion die von `StreamingResponse` verwendet wird, sollte funktionieren. **ABER** das Problem ist, dass die gesamte `_run_consultant_streaming` Funktion **erst nach dem ersten `yield` wirklich als Generator aktiviert wird**.

Da das erste yield `[Starte Claude Code...]` ist und danach der `claude_task` gestartet wird, blockiert der Task den Generator bevor weitere yields passieren können.

---

## 6. Fix-Vorschlag

### Option A: Echtes Streaming Pattern (Empfohlen)

```python
async def _run_consultant_streaming(...):
    # ... setup ...

    yield _make_chunk(..., "[Starte Claude Code...]\n\n", role="assistant")

    # NICHT asyncio.create_task + while loop, sondern:
    async for line in run_claude_with_async_iterator(session_path):
        # Parse und yield DIREKT
        event = parse_tool_call(line)
        if event:
            yield _make_chunk(..., event)
```

### Option B: Subprocess mit async readline

Statt `asyncio.gather()` für stdout/stderr, nutze echtes async streaming:

```python
async for line in process.stdout:
    await on_output("stdout", line.decode())
    # AND immediately yield to generator
```

### Option C: Separate Prozesse (Quick Fix)

Starte Claude CLI mit `subprocess.Popen` statt `asyncio.create_subprocess_exec`, und poll stdout in einem separaten Thread, der in eine thread-safe Queue schreibt.

---

## 7. Zusammenfassung

| Aspekt | Status |
|--------|--------|
| **Root Cause** | `asyncio.gather()` blockiert Generator, Events werden gequeued aber nicht gestreamt |
| **Symptom** | Client sieht nur `[Starte Claude Code...]` und `[Read]`, dann Timeout |
| **Warum 20s?** | Open WebUI HTTP Client Timeout |
| **Warum 1min im Hintergrund?** | Claude CLI läuft normal, nur HTTP Connection ist weg |
| **Heartbeat** | Funktioniert nicht, weil Generator blockiert ist |

---

## 8. Empfohlene Sofort-Maßnahme

**Prüfe die FastAPI StreamingResponse + async generator Kombination:**

```python
# Test: Funktioniert simples Streaming?
async def test_stream():
    for i in range(100):
        yield f"data: {i}\n\n"
        await asyncio.sleep(0.1)

return StreamingResponse(test_stream(), media_type="text/event-stream")
```

Wenn das funktioniert, liegt das Problem definitiv im `asyncio.gather()` Pattern.

---

<!-- STEP: what -->
