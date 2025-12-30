"""Session Manager for HELIX Consultant.

Manages consultant sessions where Claude Code instances
conduct multi-turn dialogs with users.

Enhanced with ADR-029: X-Conversation-ID support for Open WebUI integration.
Uses stable conversation IDs from headers for persistent session mapping.

Refactored with ADR-034: LLM-Native flow instead of State-Machine.
Removed index-based step detection and trigger-word matching.
The LLM now determines the conversation step and reports it via markers.

Security Hardened with ADR-035:
- Cryptographically secure session IDs using uuid4 (Fix 1)
- Session IDs are no longer predictable from message content
"""

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class SessionState(BaseModel):
    """State of a consultant session."""
    session_id: str
    status: str  # new, discussing, ready, executed
    step: str  # what, why, constraints, generate, done
    created_at: datetime
    updated_at: datetime
    original_request: str
    project_name: str | None = None
    conversation_id: str | None = None  # X-Conversation-ID from Open WebUI


class SessionManager:
    """Manages consultant sessions on filesystem.

    Each session is a directory under projects/sessions/{session_id}/
    containing CLAUDE.md, status.json, and context files.

    Supports X-Conversation-ID header (ADR-029) for persistent session mapping.
    When Open WebUI sends X-Conversation-ID, the same conversation always
    maps to the same session, enabling true multi-turn dialogs.

    ADR-034: Step detection is now handled by the LLM, not Python.
    This manager only extracts metadata; the LLM reports its step via markers.

    ADR-035: Session IDs are now cryptographically random (uuid4).
    This prevents session ID prediction attacks.
    """

    def __init__(self, base_path: Path | None = None):
        if base_path is None:
            # Default to helix-v4/projects/sessions
            base_path = Path(__file__).parent.parent.parent.parent / "projects" / "sessions"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        # Cache for conversation_id -> session_id mapping
        self._conversation_cache: dict[str, str] = {}

    def _normalize_conversation_id(self, conversation_id: str) -> str:
        """Normalize conversation ID to valid directory name.

        Args:
            conversation_id: Raw conversation ID from X-Conversation-ID header.

        Returns:
            Sanitized ID suitable for filesystem use.
        """
        # Remove any unsafe characters, keep alphanumeric and hyphens
        safe_id = "".join(
            c if c.isalnum() or c in "-_" else "-"
            for c in conversation_id
        )
        # Prefix to distinguish from hash-based IDs
        return f"conv-{safe_id}"

    def _generate_session_id(self) -> str:
        """Generate cryptographically random session ID.

        ADR-035 Fix 1: Uses uuid4 for unpredictable session IDs.
        This prevents attackers from guessing or predicting session IDs
        based on message content.

        Returns:
            Random session ID in format 'session-{uuid4_hex}'.
        """
        return f"session-{uuid.uuid4().hex}"

    def _generate_session_id_stable(self, first_message: str) -> str:
        """Generate stable session ID from first message (no timestamp).

        DEPRECATED: This method is kept for backward compatibility only.
        New sessions should use _generate_session_id() for security.

        NOTE: This is the stable version without timestamp, ensuring
        the same message always maps to the same session.

        Args:
            first_message: The first user message.

        Returns:
            Hash-based session ID without timestamp component.
        """
        # Clean the message for ID generation
        clean_msg = re.sub(r'[^a-zA-Z0-9\s]', '', first_message.lower())
        words = clean_msg.split()[:3]  # First 3 words
        prefix = '-'.join(words) if words else 'session'

        # Truncate message to avoid very long hashes
        truncated = first_message[:200]
        hash_input = f"helix-session:{truncated}"
        msg_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        return f"{prefix}-{msg_hash}"

    def generate_session_id(self, first_message: str) -> str:
        """Generate session ID from first user message + timestamp.

        DEPRECATED: Use get_or_create_session() with conversation_id instead.
        This method is kept for backward compatibility.
        """
        # Clean the message for ID generation
        clean_msg = re.sub(r'[^a-zA-Z0-9\s]', '', first_message.lower())
        words = clean_msg.split()[:3]  # First 3 words
        prefix = '-'.join(words) if words else 'session'

        # Add hash of full message for uniqueness
        msg_hash = hashlib.md5(first_message.encode()).hexdigest()[:8]

        # Timestamp for additional uniqueness
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

        return f"{prefix}-{msg_hash}-{timestamp}"

    def get_or_create_session(
        self,
        first_message: str,
        conversation_id: Optional[str] = None,
    ) -> tuple[str, SessionState]:
        """Get existing session or create a new one.

        This is the primary method for session management with Open WebUI.
        Uses X-Conversation-ID for stable session mapping when available.

        ADR-035 Fix 1: When no conversation_id is provided, generates a
        cryptographically random session ID using uuid4 instead of
        deriving it from message content.

        Args:
            first_message: The first/current message in the conversation.
            conversation_id: Optional X-Conversation-ID from Open WebUI header.

        Returns:
            Tuple of (session_id, SessionState).
        """
        # Priority 1: Use conversation_id if provided (ADR-029)
        if conversation_id:
            session_id = self._normalize_conversation_id(conversation_id)

            # Check cache first
            if conversation_id in self._conversation_cache:
                cached_id = self._conversation_cache[conversation_id]
                if self.session_exists(cached_id):
                    state = self.get_state(cached_id)
                    if state:
                        return cached_id, state

            # Check if session exists on disk
            if self.session_exists(session_id):
                state = self.get_state(session_id)
                if state:
                    self._conversation_cache[conversation_id] = session_id
                    return session_id, state

            # Create new session with conversation_id-based ID
            state = self.create_session(session_id, first_message, conversation_id)
            self._conversation_cache[conversation_id] = session_id
            return session_id, state

        # ADR-035 Fix 1: Use cryptographically random ID instead of hash-based
        # This prevents session ID prediction attacks
        session_id = self._generate_session_id()

        # Create new session with random ID
        state = self.create_session(session_id, first_message)
        return session_id, state

    def get_session_id_from_messages(self, messages: list[dict]) -> str | None:
        """Extract session ID from message history.

        Uses the first user message to generate consistent ID.
        """
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                if content:
                    return self._find_or_create_session_id(content, messages)
        return None

    def _find_or_create_session_id(self, first_message: str, messages: list[dict]) -> str:
        """Find existing session or create new ID.

        Searches for session matching first message hash.
        """
        msg_hash = hashlib.md5(first_message.encode()).hexdigest()[:8]

        # Search existing sessions
        for session_dir in self.base_path.iterdir():
            if session_dir.is_dir() and msg_hash in session_dir.name:
                return session_dir.name

        # No existing session - create new ID with uuid4 (ADR-035)
        return self._generate_session_id()

    def session_exists(self, session_id: str) -> bool:
        """Check if session directory exists."""
        return (self.base_path / session_id).exists()

    def get_session_path(self, session_id: str) -> Path:
        """Get path to session directory."""
        return self.base_path / session_id

    def create_session(
        self,
        session_id: str,
        original_request: str,
        conversation_id: Optional[str] = None,
    ) -> SessionState:
        """Create new session directory structure.

        Args:
            session_id: The session ID to use.
            original_request: The original user request/message.
            conversation_id: Optional X-Conversation-ID from Open WebUI.

        Returns:
            SessionState for the new session.
        """
        session_path = self.base_path / session_id

        # Create directories
        (session_path / "input").mkdir(parents=True, exist_ok=True)
        (session_path / "context").mkdir(exist_ok=True)
        (session_path / "output").mkdir(exist_ok=True)
        (session_path / "logs").mkdir(exist_ok=True)

        # Write original request
        (session_path / "input" / "request.md").write_text(
            f"# User Request\n\n{original_request}\n"
        )

        # Create initial state
        state = SessionState(
            session_id=session_id,
            status="discussing",
            step="what",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            original_request=original_request,
            conversation_id=conversation_id,
        )

        self._save_state(session_id, state)

        return state

    def get_state(self, session_id: str) -> SessionState | None:
        """Load session state from status.json."""
        status_file = self.base_path / session_id / "status.json"
        if not status_file.exists():
            return None

        data = json.loads(status_file.read_text())
        return SessionState(**data)

    def _save_state(self, session_id: str, state: SessionState) -> None:
        """Save session state to status.json."""
        status_file = self.base_path / session_id / "status.json"
        state.updated_at = datetime.now()
        status_file.write_text(state.model_dump_json(indent=2))

    def update_state(
        self,
        session_id: str,
        status: str | None = None,
        step: str | None = None,
        project_name: str | None = None,
    ) -> SessionState | None:
        """Update session state."""
        state = self.get_state(session_id)
        if not state:
            return None

        if status:
            state.status = status
        if step:
            state.step = step
        if project_name:
            state.project_name = project_name

        self._save_state(session_id, state)
        return state

    def save_messages(self, session_id: str, messages: list[dict]) -> None:
        """Save complete message history."""
        messages_file = self.base_path / session_id / "context" / "messages.json"
        messages_file.write_text(json.dumps(messages, indent=2, default=str))

    def save_context(self, session_id: str, key: str, content: str) -> None:
        """Save context file (what.md, why.md, constraints.md)."""
        context_file = self.base_path / session_id / "context" / f"{key}.md"
        context_file.write_text(content)

    def get_context(self, session_id: str) -> dict[str, str]:
        """Load all context files."""
        context_dir = self.base_path / session_id / "context"
        context = {}

        for f in context_dir.glob("*.md"):
            context[f.stem] = f.read_text()

        return context

    def get_output(self, session_id: str, filename: str) -> str | None:
        """Read output file."""
        output_file = self.base_path / session_id / "output" / filename
        if output_file.exists():
            return output_file.read_text()
        return None

    def has_spec(self, session_id: str) -> bool:
        """Check if ADR or spec.yaml has been generated.

        Checks for ADR first (new way), then spec.yaml (legacy).
        """
        output_dir = self.base_path / session_id / "output"

        # Check for ADR first
        adr_files = list(output_dir.glob("ADR-*.md"))
        if adr_files:
            return True

        # Fallback to spec.yaml (legacy)
        spec_file = output_dir / "spec.yaml"
        return spec_file.exists()

    def has_adr(self, session_id: str) -> bool:
        """Check if an ADR has been generated."""
        output_dir = self.base_path / session_id / "output"
        return bool(list(output_dir.glob("ADR-*.md")))

    def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
        """Extract basic conversation metadata from message history.

        ADR-034: This function no longer performs step detection.
        Step detection is handled by the LLM, which reports its current
        step via markers in its response (<!-- STEP: X -->).

        This function only extracts:
        - original_request: The first user message
        - message_count: Total number of messages

        Args:
            messages: List of message dictionaries with 'role' and 'content'.

        Returns:
            Dictionary with conversation metadata (NOT including step).
        """
        state = {
            "original_request": "",
            "message_count": len(messages),
        }

        # Extract first user message as original request
        user_messages = [m for m in messages if m.get('role') == 'user']
        if user_messages:
            state["original_request"] = user_messages[0].get('content', '')

        return state

    def extract_step_from_response(self, response_text: str) -> str | None:
        """Extract step marker from LLM response.

        ADR-034: The LLM sets a step marker at the end of its response:
        <!-- STEP: what|why|constraints|generate|finalize|done -->

        This marker is used for observability and logging, NOT for flow control.
        The LLM decides the conversation step based on context; Python just
        extracts and records it.

        Args:
            response_text: The full text of the LLM response.

        Returns:
            The step name if found (e.g., 'what', 'generate'), or None.

        Examples:
            >>> mgr.extract_step_from_response("Here's my answer\\n<!-- STEP: why -->")
            'why'
            >>> mgr.extract_step_from_response("No marker here")
            None
        """
        match = re.search(r'<!--\s*STEP:\s*(\w+)\s*-->', response_text)
        if match:
            return match.group(1).lower()
        return None

    def list_sessions(self, limit: int = 20) -> list[SessionState]:
        """List recent sessions."""
        sessions = []
        for session_dir in sorted(self.base_path.iterdir(), reverse=True):
            if session_dir.is_dir():
                state = self.get_state(session_dir.name)
                if state:
                    sessions.append(state)
                if len(sessions) >= limit:
                    break
        return sessions


# Global instance
session_manager = SessionManager()
