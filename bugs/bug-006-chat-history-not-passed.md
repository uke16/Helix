# Bug 006: Chat-History wird nicht an Claude Code übergeben

**Datum:** 2025-12-30
**Schwere:** KRITISCH
**Status:** ✅ GEFIXT

## Symptom

Bei Multi-Turn Konversationen im Consultant:
1. User: "Analysiere den Code"
2. Claude: Macht Analyse ✅
3. User: "Dokumentiere das in bugs/"
4. Claude: Macht **nochmal die gleiche Analyse** statt zu dokumentieren ❌

## Root Cause

```python
# openai.py - chat_completions()

# Messages werden empfangen
messages = [{"role": m.role, "content": m.content} for m in request.messages]

# Messages werden gespeichert - aber nur in messages.json
session_manager.save_messages(session_id, messages)

# CLAUDE.md wird generiert mit nur:
# - original_request (ERSTE Nachricht)
# - context (what, why, constraints)
# - NICHT die aktuelle/neue Nachricht!
await _generate_session_claude_md(session_id, session_state, context)

# Claude bekommt als Prompt:
prompt = "Read CLAUDE.md and execute all tasks described there."
```

**Problem:** Claude Code liest `messages.json` nicht. Es sieht nur `original_request` in CLAUDE.md.

## Evidenz

Session: `schau-dir-mal-8084093d91d2`

```
messages.json:
  0: user: "schau dir mal den consultant code an..."
  1: assistant: [Code-Review]
  2: user: "dokumentiere das in bugs/"

CLAUDE.md:
  original_request: "schau dir mal den consultant code an..."
  # Nachricht 2 fehlt komplett!
```

## Fix

### 1. openai.py - Messages an Template übergeben

```python
async def _generate_session_claude_md(
    session_id: str,
    state: SessionState,
    context: dict[str, str],
    messages: list[dict] = None,  # NEU
) -> None:
    content = template.render(
        # ...existing...
        messages=messages or [],  # NEU
    )
```

### 2. session.md.j2 - Chat-History einbetten

```jinja2
## Aktuelle Konversation

{% if messages and messages|length > 0 %}
{% for msg in messages %}
### {{ msg.role | capitalize }}

{{ msg.content }}

{% endfor %}
{% else %}
*Erste Nachricht - noch keine History*
{% endif %}
```

### 3. chat_completions() - Messages durchreichen

```python
await _generate_session_claude_md(
    session_id, 
    session_state, 
    context,
    messages=messages,  # NEU
)
```

## Warum ist das der richtige Fix?

1. **Standard-Pattern** - Alle LLM-APIs (OpenAI, Anthropic) senden die gesamte History bei jedem Request
2. **Explizit** - Claude sieht sofort den vollständigen Kontext
3. **Konsistent** - Gleiche Semantik wie andere Chat-Completion APIs
4. **Einfach** - Keine komplexe Logik, nur Template-Erweiterung

## Potenzielle Optimierungen (später)

- Token-Limit für sehr lange Konversationen (>20 Messages)
- Summarization für ältere Messages
- Aber: Für typische Consultant-Sessions (5-15 Messages) nicht nötig


## Fix Implementiert

**Datum:** 2025-12-30 14:42

### Änderungen:

1. **src/helix/api/routes/openai.py**
   - `_generate_session_claude_md()` um `messages` Parameter erweitert
   - `template.render()` um `messages=messages or []` erweitert
   - Aufruf in `chat_completions()` mit `messages=messages` ergänzt

2. **templates/consultant/session.md.j2**
   - Neue Sektion "Aktuelle Konversation" nach "Konversations-Kontext"
   - Jinja2 Loop über alle Messages mit role/content

### Test

API neu gestartet. Fix sollte bei nächster Multi-Turn Konversation wirksam sein.

### Verifikation

Neue Session starten und prüfen ob CLAUDE.md die vollständige Chat-History enthält.

