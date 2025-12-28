"""Session Manager wrapper for HELIX.

This module provides the SessionManager interface as defined in ADR-029.
It wraps the actual implementation at helix.api.session_manager.

ADR-029: X-Conversation-ID support for Open WebUI integration.
Uses stable conversation IDs from headers for persistent session mapping.
"""

# Re-export from actual location
from helix.api.session_manager import (
    SessionManager,
    SessionState,
    session_manager,
)

__all__ = ["SessionManager", "SessionState", "session_manager"]
