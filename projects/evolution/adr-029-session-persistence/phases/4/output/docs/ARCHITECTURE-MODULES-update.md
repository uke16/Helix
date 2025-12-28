# ADR-029 Documentation Update: Session Management

This document describes the documentation changes made for ADR-029 (Open WebUI Session Persistence - X-Conversation-ID Integration).

## Updated File

**File:** `docs/ARCHITECTURE-MODULES.md`

## Added Section

A new section "Session Management (`src/helix/api/session_manager.py`)" was added to document:

### 1. X-Conversation-ID Support (ADR-029)

The SessionManager supports persistent session mapping via the `X-Conversation-ID` HTTP header from Open WebUI. This enables true multi-turn conversations where context is preserved across requests.

### 2. Architecture Diagram

Visual flow diagram showing:
- Request with X-Conversation-ID header → `_normalize_conversation_id()` → Session lookup → Session with preserved history
- Fallback path without header → `_generate_session_id_stable()` → Stable hash-based session

### 3. Key Classes

Documented `SessionState` model with all fields including the new `conversation_id` field.

### 4. Key Methods

| Method | Description |
|--------|-------------|
| `get_or_create_session()` | Primary entry point - uses X-Conversation-ID if available |
| `_normalize_conversation_id()` | Sanitizes conversation ID for filesystem use |
| `_generate_session_id_stable()` | Fallback: stable hash without timestamp |
| `generate_session_id()` | **Deprecated** - legacy method with timestamp |

### 5. Usage Examples

Python code examples showing:
- Session creation with X-Conversation-ID
- Same conversation ID returning same session
- Fallback behavior without header

### 6. API Integration

Example showing FastAPI Header extraction:
```python
@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
):
```

### 7. Session Storage

Directory structure documentation for session storage.

### 8. Related Links

Links to:
- ADR-029 document
- API routes source file

## Location in Document

The new section was inserted before "Verification System" section, maintaining logical flow from API-related components to verification systems.
