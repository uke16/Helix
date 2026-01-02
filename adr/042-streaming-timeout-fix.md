---
adr_id: "042"
title: "Streaming Timeout Fix - Live Progress während Claude Code"
status: Implemented

component_type: FIX
classification: FIX
change_scope: hotfix

files:
  modify:
    - src/helix/api/routes/openai.py
  docs:
    - adr/INDEX.md
---

# ADR-042: Streaming Timeout Fix

## Status

Implemented - 2026-01-01

## Kontext

### Problem

User-Report: Consultant-Chat "schmiert ab" - Antwort kommt nicht an.

**Symptome:**
- User sendet Anfrage von Mobile (Conduit App)
- Erhält nur "[Starte Claude Code...] Lass mich..." 
- Vollständige Antwort kommt nie an
- Zweite Nachricht erscheint nicht mal in Web App

**Root Cause Analysis:**

1. `_run_consultant_streaming()` sendet NUR `"[Starte Claude Code...]\n\n"` initial
2. Dann wartet es 3+ Minuten auf Claude Code
3. **KEIN Output während dieser Zeit**
4. Open WebUI/Conduit hat Timeout (60-120s)
5. Verbindung wird geschlossen
6. Vollständige Antwort geht ins Leere

**Betroffener Code:**

```python
# VOR dem Fix - on_output speichert nur, streamt nichts!
async def on_output(stream: str, line: str) -> None:
    """Callback for each line of output."""
    nonlocal last_tool
    if stream == "stdout":
        stdout_buffer.append(line)  # <-- Speichert nur!
```

### Beweis

Session `conv-990a7835-bf8d-4f1b-82eb-7adedb8cdb5a`:
- 4 Claude Code Runs
- Run 150410: **Kein result** - abgebrochen während Write!
- Run 150427: Hat vollständige Antwort, aber nie gestreamt
- `response.md`: 7896 bytes vollständige Antwort
- User: Hat sie nie erhalten

## Entscheidung

### Fix: Queue-basiertes Live Streaming

1. **Event Queue**: Tool Calls werden in Queue gepusht
2. **Concurrent Tasks**: Claude Code + Heartbeat + Queue Consumer
3. **Heartbeat**: Alle 25s "." senden um Verbindung aktiv zu halten
4. **Tool Call Streaming**: "[Read]", "[Write]", "[Bash]" etc. live anzeigen

## Implementation

```python
# NACH dem Fix - events werden gequeued und gestreamt
from asyncio import Queue
event_queue: Queue[str | None] = Queue()

async def on_output(stream: str, line: str) -> None:
    """Callback - NOW QUEUES FOR STREAMING."""
    if stream == "stdout":
        stdout_buffer.append(line)
        # Parse JSONL und queue Tool Calls
        try:
            data = json.loads(line)
            if data.get("type") == "assistant":
                for block in data.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        await event_queue.put(f"\n[{block.get('name')}] ")
        except json.JSONDecodeError:
            pass

# Heartbeat Task
async def heartbeat_task():
    while True:
        await asyncio.sleep(25)
        await event_queue.put(".")

# Claude Code + Queue Consumer concurrent
claude_task = asyncio.create_task(runner.run_phase_streaming(...))
while not claude_task.done():
    try:
        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
        if event:
            yield _make_chunk(..., event)
    except asyncio.TimeoutError:
        continue
```

## Akzeptanzkriterien

- [x] `on_output` queued Events statt nur zu speichern
- [x] Heartbeat Task sendet alle 25s "."
- [x] Tool Calls werden live gestreamt
- [x] Open WebUI sieht Aktivität → kein Timeout
- [x] Syntax Check passed
- [x] API neu gestartet

## Konsequenzen

### Positiv

- **Kein Timeout mehr**: Heartbeat hält Verbindung aktiv
- **Besseres UX**: User sieht was Claude tut ([Read], [Write], etc.)
- **Debugging**: Tool Calls sind jetzt sichtbar

### Negativ

- **Mehr Traffic**: Heartbeat + Tool Call Events
- **Komplexität**: Queue + concurrent Tasks

## Referenzen

- Session mit Bug: `conv-990a7835-bf8d-4f1b-82eb-7adedb8cdb5a`
- Backup: `openai.py.bak.20260101_*`
