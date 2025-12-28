---
adr_id: "029"
title: "Open WebUI Session Persistence - X-Conversation-ID Integration"
status: Proposed

project_type: helix_internal
component_type: SERVICE
classification: FIX
change_scope: minor

domain: helix
language: python
skills:
  - helix
  - api

files:
  create: []
  modify:
    - src/helix/session/manager.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-000
  - ADR-022
---

# ADR-029: Open WebUI Session Persistence - X-Conversation-ID Integration

## Status
📋 Proposed

## Kontext

### Das Problem

Bei der Integration mit Open WebUI wird für **jeden Chat-Request eine neue Session erstellt**, obwohl der User im gleichen Chat weiterschreibt:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IST-ZUSTAND: NEUE SESSION PRO REQUEST                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Open WebUI: Conversation "My Chat"                                         │
│   ─────────────────────────────────                                          │
│   User: "Hallo, was ist HELIX?"      → Session ID: hash(msg+timestamp_1)    │
│   Claude: "HELIX ist ein System..." ← Session: abc-123-def                  │
│                                                                              │
│   User: "Erkläre mehr Details"       → Session ID: hash(msg+timestamp_2)    │
│   Claude: "Ähh... was war nochmal   ← Session: xyz-789-uvw (NEUE SESSION!) │
│            die Frage?"                                                       │
│                                                                              │
│   ⚠️ PROBLEM: Keine History, kein Kontext!                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**User Experience Impact:**
- Jede Nachricht startet eine neue Session
- Keine Konversations-History
- Claude hat keinen Kontext aus vorherigen Nachrichten
- Frustrierende Nutzererfahrung

### Root Cause Analyse

Der `SessionManager` generiert die Session-ID aus:

```python
# Aktueller Code in session/manager.py
def _generate_session_id(self, first_message: str) -> str:
    timestamp = datetime.now().isoformat()  # ← PROBLEM!
    hash_input = f"{first_message}:{timestamp}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:12]
```

**Das Problem:** Der `timestamp` ändert sich bei jedem Request, selbst wenn es die gleiche Conversation ist.

### Was Open WebUI liefert

Open WebUI sendet bei jedem Request einen `X-Conversation-ID` Header:

```http
POST /v1/chat/completions HTTP/1.1
Host: localhost:8001
Content-Type: application/json
X-Conversation-ID: 550e8400-e29b-41d4-a716-446655440000  ← STABILER ID!
Authorization: Bearer ...

{
  "model": "helix-consultant",
  "messages": [...]
}
```

Dieser Header ist **stabil pro Conversation** und sollte für die Session-Zuordnung verwendet werden.

## Entscheidung

Wir ändern den `SessionManager`, um den `X-Conversation-ID` Header als primäre Session-Zuordnung zu verwenden:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOLL-ZUSTAND: PERSISTENTE SESSIONS                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Open WebUI: Conversation "My Chat" (ID: 550e8400-...)                     │
│   ─────────────────────────────────────────────────────                     │
│   User: "Hallo, was ist HELIX?"      → Session: 550e8400... (aus Header)    │
│   Claude: "HELIX ist ein System..." ← History wird gespeichert              │
│                                                                              │
│   User: "Erkläre mehr Details"       → Session: 550e8400... (gleiche!)      │
│   Claude: "Wie erwähnt, HELIX ist   ← Hat vollen Kontext aus History       │
│            ein AI Orchestration..."                                          │
│                                                                              │
│   ✅ LÖSUNG: Persistente Session mit History!                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design-Prinzipien

1. **Header First**: `X-Conversation-ID` hat Priorität
2. **Fallback**: Ohne Header → alte Logik (Hash-basiert, aber ohne Timestamp)
3. **Backward Compatible**: Keine Breaking Changes für andere Clients
4. **Simple**: Minimale Code-Änderungen

## Implementation

### 1. SessionManager Änderungen

`src/helix/session/manager.py`:

```python
"""Session Manager with X-Conversation-ID support."""

import hashlib
from typing import Optional
from pathlib import Path


class SessionManager:
    """Manages consultant sessions with Open WebUI integration.

    Supports X-Conversation-ID header for persistent session mapping.
    Falls back to message-based hashing for other clients.
    """

    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = sessions_dir
        self._sessions: dict[str, "Session"] = {}

    def get_or_create_session(
        self,
        first_message: str,
        conversation_id: Optional[str] = None,
    ) -> "Session":
        """Get existing session or create a new one.

        Args:
            first_message: The first message in the conversation.
            conversation_id: Optional X-Conversation-ID from Open WebUI.

        Returns:
            Session object (existing or newly created).
        """
        # Priority 1: Use conversation_id if provided
        if conversation_id:
            session_id = self._normalize_conversation_id(conversation_id)
        else:
            # Fallback: Hash-based ID (without timestamp!)
            session_id = self._generate_session_id(first_message)

        # Check for existing session
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Check on disk
        session_dir = self.sessions_dir / session_id
        if session_dir.exists():
            session = Session.load(session_dir)
            self._sessions[session_id] = session
            return session

        # Create new session
        session = Session.create(
            session_id=session_id,
            session_dir=session_dir,
            first_message=first_message,
        )
        self._sessions[session_id] = session
        return session

    def _normalize_conversation_id(self, conversation_id: str) -> str:
        """Normalize conversation ID to valid directory name.

        Args:
            conversation_id: Raw conversation ID from header.

        Returns:
            Sanitized ID suitable for filesystem.
        """
        # Remove any unsafe characters
        safe_id = "".join(
            c if c.isalnum() or c in "-_" else "-"
            for c in conversation_id
        )
        # Prefix to distinguish from hash-based IDs
        return f"conv-{safe_id}"

    def _generate_session_id(self, first_message: str) -> str:
        """Generate session ID from first message (fallback).

        NOTE: No timestamp! This ensures same message → same session.

        Args:
            first_message: The first user message.

        Returns:
            Hash-based session ID.
        """
        # Truncate message to avoid very long hashes
        truncated = first_message[:200]
        hash_input = f"helix-session:{truncated}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
```

### 2. API Route Änderung

`src/helix/api/routes/openai.py` - Header extraction:

```python
from fastapi import Header

@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
) -> StreamingResponse:
    """OpenAI-compatible chat endpoint with Open WebUI support.

    Extracts X-Conversation-ID header for persistent session mapping.
    """
    # Get or create session with conversation ID
    session = session_manager.get_or_create_session(
        first_message=request.messages[-1].content,
        conversation_id=x_conversation_id,
    )

    # ... rest of handler
```

### 3. Session History Persistence

Die Session muss Messages speichern und laden können:

```python
# In session/session.py

class Session:
    """A consultant session with message history."""

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_messages()

    def get_messages(self) -> list[dict]:
        """Get all messages in this session."""
        return self.messages.copy()

    def _save_messages(self) -> None:
        """Persist messages to disk."""
        messages_file = self.session_dir / "context" / "messages.json"
        messages_file.parent.mkdir(parents=True, exist_ok=True)
        messages_file.write_text(json.dumps(self.messages, indent=2))

    @classmethod
    def load(cls, session_dir: Path) -> "Session":
        """Load session from disk."""
        messages_file = session_dir / "context" / "messages.json"
        messages = []
        if messages_file.exists():
            messages = json.loads(messages_file.read_text())

        session = cls(session_dir=session_dir)
        session.messages = messages
        return session
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | SessionManager X-Conversation-ID Support |

## Akzeptanzkriterien

### Funktionalität

- [ ] Session bleibt über mehrere Requests gleich (bei gleichem X-Conversation-ID)
- [ ] Messages werden in `context/messages.json` gespeichert
- [ ] Session wird bei bestehendem Verzeichnis korrekt geladen
- [ ] Fallback auf Hash-basierte ID funktioniert ohne Header

### Integration

- [ ] Open WebUI Conversations haben persistente Sessions
- [ ] Andere Clients (curl, etc.) funktionieren weiterhin
- [ ] Keine Breaking Changes in API

### Tests

- [ ] Unit Test: _normalize_conversation_id()
- [ ] Unit Test: _generate_session_id() ohne Timestamp
- [ ] Integration Test: Mehrere Requests mit gleichem X-Conversation-ID
- [ ] E2E Test: Open WebUI Chat bleibt in gleicher Session

## Konsequenzen

### Vorteile

| Vorteil | Beschreibung |
|---------|--------------|
| **Persistente History** | Messages bleiben über Requests erhalten |
| **Kontext bleibt** | Claude weiß was vorher gesagt wurde |
| **Bessere UX** | Natürliche Konversation möglich |
| **Einfacher Fix** | Minimale Code-Änderungen |

### Nachteile

| Nachteil | Mitigation |
|----------|------------|
| Session-Wachstum | TTL für alte Sessions (optional) |
| Disk Usage | Messages sind Text, sehr klein |

### Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Header fehlt | Niedrig | Niedrig | Fallback-Logik vorhanden |
| ID-Collision | Sehr niedrig | Niedrig | UUID-Format von Open WebUI |

## Referenzen

- Open WebUI API Documentation
- OpenAI Chat Completions API Spec
- HELIX Session Manager (existierender Code)
