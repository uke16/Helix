"""Session Manager for HELIX Consultant.

Manages consultant sessions where Claude Code instances
conduct multi-turn dialogs with users.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

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
    

class SessionManager:
    """Manages consultant sessions on filesystem.
    
    Each session is a directory under projects/sessions/{session_id}/
    containing CLAUDE.md, status.json, and context files.
    """
    
    def __init__(self, base_path: Path | None = None):
        if base_path is None:
            # Default to helix-v4/projects/sessions
            base_path = Path(__file__).parent.parent.parent.parent / "projects" / "sessions"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def generate_session_id(self, first_message: str) -> str:
        """Generate session ID from first user message + timestamp.
        
        This ensures the same chat in Open WebUI maps to same session.
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
        
        # No existing session - create new ID
        return self.generate_session_id(first_message)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session directory exists."""
        return (self.base_path / session_id).exists()
    
    def get_session_path(self, session_id: str) -> Path:
        """Get path to session directory."""
        return self.base_path / session_id
    
    def create_session(self, session_id: str, original_request: str) -> SessionState:
        """Create new session directory structure."""
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
        """Extract conversation state from message history.
        
        Analyzes the messages to determine:
        - What step we're on (what/why/constraints/generate)
        - What answers have been given
        - What the original request was
        """
        state = {
            "original_request": "",
            "step": "what",
            "answers": {
                "what": None,
                "why": None,
                "constraints": None,
            },
            "message_count": len(messages),
        }
        
        # Extract user messages
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        if user_messages:
            state["original_request"] = user_messages[0].get('content', '')
        
        # Analyze conversation flow
        # Pattern: User request → Assistant asks "what" → User answers → Assistant asks "why" → ...
        
        if len(user_messages) >= 2:
            state["answers"]["what"] = user_messages[1].get('content', '')
            state["step"] = "why"
        
        if len(user_messages) >= 3:
            state["answers"]["why"] = user_messages[2].get('content', '')
            state["step"] = "constraints"
        
        if len(user_messages) >= 4:
            state["answers"]["constraints"] = user_messages[3].get('content', '')
            state["step"] = "generate"
        
        # Check if user said "start" or similar
        if user_messages:
            last_msg = user_messages[-1].get('content', '').lower()
            if any(word in last_msg for word in ['start', 'starte', 'ja', 'yes', 'los', 'go']):
                if state["step"] == "generate":
                    state["step"] = "execute"
        
        return state
    
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
