# ADR-029 Documentation Update: Session Management

This document describes the documentation updates made for ADR-029 (Open WebUI Session Persistence - X-Conversation-ID Integration).

## Updated Files

### docs/ARCHITECTURE-MODULES.md

A new section **Session Management (`src/helix/api/session_manager.py`)** was added (lines 600-736) covering:

1. **X-Conversation-ID Support** - Explains the header-based session mapping for Open WebUI integration

2. **Architecture Diagram** - ASCII diagram showing the session mapping flow:
   - Request with X-Conversation-ID header → normalized session ID
   - Fallback for requests without header (stable hash-based ID)

3. **Key Classes**
   - `SessionState` model with `conversation_id` field
   - `SessionManager` class documentation

4. **Key Methods**
   | Method | Description |
   |--------|-------------|
   | `get_or_create_session()` | Primary entry point with X-Conversation-ID support |
   | `_normalize_conversation_id()` | Sanitizes conversation ID for filesystem |
   | `_generate_session_id_stable()` | Fallback: stable hash without timestamp |

5. **Usage Examples**
   - With X-Conversation-ID (Open WebUI)
   - Without header (fallback for curl, etc.)

6. **API Integration**
   - Shows how `/v1/chat/completions` extracts the header

7. **Session Storage Structure**
   - Directory layout for sessions with context/messages.json

## Code Documentation

The implementation files already contain comprehensive docstrings:

### src/helix/api/session_manager.py
- Module docstring referencing ADR-029
- Class docstring for SessionManager explaining X-Conversation-ID support
- Method docstrings for all key methods

### src/helix/api/routes/openai.py
- Module docstring referencing ADR-029 session persistence
- Function docstring for `chat_completions` explaining X-Conversation-ID extraction

## References

- [ADR-029: Open WebUI Session Persistence](../../../ADR-029.md)
- [ARCHITECTURE-MODULES.md Session Management Section](../../../../../docs/ARCHITECTURE-MODULES.md#session-management-srchexixapisession_managerpy)
