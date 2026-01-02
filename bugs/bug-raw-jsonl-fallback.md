# Bug: Raw JSONL Output als Response

## ID
bug-raw-jsonl-fallback

## Schwere
HOCH

## Entdeckt
2025-12-30 (Session mit Uwe)

## Symptom
User bekommt rohen JSONL-Stream statt formatierter Antwort:
```json
{"type":"system","subtype":"init","cwd":...}
{"type":"assistant","message":{...}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"<tool_use_error>File does not exist...
```

## Root Cause
In `src/helix/api/routes/openai.py` Zeile 305-310:

```python
if not response_text:
    # Try to extract from stdout
    stdout = "\n".join(stdout_buffer)
    for line in stdout.strip().split("\n"):
        # ... sucht nur nach "type": "result" ...
    
    if not response_text:
        response_text = stdout or "Verarbeitung abgeschlossen."  # <-- BUG
```

Wenn Claude Code keinen `"type": "result"` Block zurückgibt (was oft passiert), 
fällt der Code auf `response_text = stdout` zurück - den GESAMTEN raw JSONL stream.

## Warum kein "type": "result"?
Claude Code gibt `"type": "result"` nur bei bestimmten Abschlüssen zurück.
Bei laufenden Konversationen oder Fehlern (wie "File does not exist") fehlt dieser Block.

## Fix
Statt raw stdout als Fallback zu nutzen, den letzten `"type": "assistant"` Block 
mit Text-Content extrahieren:

```python
if not response_text:
    # Extract last assistant text message instead of raw JSONL
    for line in reversed(stdout.strip().split("\n")):
        try:
            data = json.loads(line)
            if data.get("type") == "assistant":
                msg = data.get("message", {})
                content = msg.get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        response_text = block.get("text", "")
                        break
                if response_text:
                    break
        except json.JSONDecodeError:
            continue
    
    if not response_text:
        response_text = "Verarbeitung abgeschlossen."
```

## Betroffene Dateien
- src/helix/api/routes/openai.py

## Verwandt
- ADR-035 (API Hardening)

---

## Update 2025-12-31: Rate Limiter Parameter Bug

### Symptom
`"parameter 'request' must be an instance of starlette.requests.Request"`

### Root Cause
slowapi's `@limiter.limit()` decorator sucht nach einem Parameter namens `request` (genau dieser Name).
Der Parameter hieß aber `http_request`.

### Fix
```python
# Vorher (broken):
async def chat_completions(
    http_request: Request,
    request: ChatCompletionRequest,
    ...
)

# Nachher (working):
async def chat_completions(
    request: Request,  # MUST be named 'request' for slowapi
    chat_request: ChatCompletionRequest,
    ...
)
```

### Betroffene Dateien
- `src/helix/api/routes/openai.py`

## Status
✅ GEFIXT (Commit in routes/openai.py Zeile 387+)
