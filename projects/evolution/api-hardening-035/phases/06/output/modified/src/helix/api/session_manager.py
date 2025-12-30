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
- File locking prevents TOCTOU race conditions (Fix 4)
- Path traversal prevention in conversation ID normalization (Fix 5)
- Session archivierung: old sessions are zipped, never deleted (Fix 6)
"""

import hashlib
import json
import logging
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import filelock
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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

    ADR-035 Fix 4: File locking prevents race conditions during session creation.
    Uses filelock to ensure atomic session creation.

    ADR-035 Fix 5: Path traversal prevention in conversation ID normalization.
    Removes path traversal sequences and limits to safe characters.

    ADR-035 Fix 6: Session archivierung - old sessions are zipped, never deleted.
    All session data is preserved in compressed archives.
    """

    # Lock timeout in seconds
    LOCK_TIMEOUT = 5

    # Maximum length for normalized conversation IDs (ADR-035 Fix 5)
    MAX_CONVERSATION_ID_LENGTH = 64

    # Archive settings (ADR-035 Fix 6)
    DEFAULT_ARCHIVE_AGE_DAYS = 30
    ARCHIVE_DIR_NAME = "_archive"
    BACKUP_DIR_NAME = "_backups"

    def __init__(self, base_path: Path | None = None):
        if base_path is None:
            # Default to helix-v4/projects/sessions
            base_path = Path(__file__).parent.parent.parent.parent / "projects" / "sessions"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        # Cache for conversation_id -> session_id mapping
        self._conversation_cache: dict[str, str] = {}
        # Lock directory for session locks
        self._lock_dir = self.base_path / ".locks"
        self._lock_dir.mkdir(exist_ok=True)

    def _get_session_lock(self, session_id: str) -> filelock.FileLock:
        """Get a file lock for a session.

        ADR-035 Fix 4: Uses file-based locking to prevent TOCTOU race conditions
        during session creation and modification.

        Args:
            session_id: The session ID to lock.

        Returns:
            FileLock object for the session.
        """
        lock_file = self._lock_dir / f"{session_id}.lock"
        return filelock.FileLock(str(lock_file), timeout=self.LOCK_TIMEOUT)

    def _normalize_conversation_id(self, conversation_id: str) -> str:
        """Normalize conversation ID to safe directory name.

        ADR-035 Fix 5: Prevents path traversal attacks by sanitizing
        user-provided conversation IDs before using them as directory names.

        Security measures:
        1. Remove path traversal sequences (.., /, \\)
        2. Only allow alphanumeric characters and hyphens
        3. Limit length to 64 characters
        4. Return fallback "session" if result is empty

        Args:
            conversation_id: Raw conversation ID from X-Conversation-ID header.

        Returns:
            Sanitized ID suitable for safe filesystem use.

        Examples:
            >>> mgr._normalize_conversation_id("abc-123")
            'conv-abc-123'
            >>> mgr._normalize_conversation_id("../../../etc/passwd")
            'conv-etcpasswd'
            >>> mgr._normalize_conversation_id("a" * 100)
            'conv-aaaa...' (64 chars max)
        """
        # Step 1: Remove path traversal sequences
        safe_id = conversation_id.replace("..", "").replace("/", "-").replace("\\", "-")

        # Step 2: Only keep alphanumeric characters and hyphens
        safe_id = re.sub(r'[^a-zA-Z0-9-]', '', safe_id)

        # Step 3: Collapse multiple consecutive hyphens
        safe_id = re.sub(r'-+', '-', safe_id)

        # Step 4: Remove leading/trailing hyphens
        safe_id = safe_id.strip('-')

        # Step 5: Limit length (accounting for 'conv-' prefix)
        max_id_length = self.MAX_CONVERSATION_ID_LENGTH - 5  # 5 = len('conv-')
        safe_id = safe_id[:max_id_length] if safe_id else ""

        # Step 6: Fallback to "session" if empty
        if not safe_id:
            safe_id = "session"

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

        ADR-035 Fix 4: Uses file locking to prevent TOCTOU race conditions.
        This ensures atomic session creation even with parallel requests.

        ADR-035 Fix 5: Conversation IDs are sanitized to prevent path traversal.

        Args:
            first_message: The first/current message in the conversation.
            conversation_id: Optional X-Conversation-ID from Open WebUI header.

        Returns:
            Tuple of (session_id, SessionState).
        """
        # Priority 1: Use conversation_id if provided (ADR-029)
        if conversation_id:
            session_id = self._normalize_conversation_id(conversation_id)

            # Check cache first (no lock needed for cache lookup)
            if conversation_id in self._conversation_cache:
                cached_id = self._conversation_cache[conversation_id]
                if self.session_exists(cached_id):
                    state = self.get_state(cached_id)
                    if state:
                        return cached_id, state

            # ADR-035 Fix 4: Use file lock for atomic check-and-create
            lock = self._get_session_lock(session_id)
            try:
                with lock:
                    # Double-check after acquiring lock
                    if self.session_exists(session_id):
                        state = self.get_state(session_id)
                        if state:
                            self._conversation_cache[conversation_id] = session_id
                            return session_id, state

                    # Create new session with conversation_id-based ID
                    state = self.create_session(session_id, first_message, conversation_id)
                    self._conversation_cache[conversation_id] = session_id
                    return session_id, state
            except filelock.Timeout:
                # If we can't acquire lock, another process is creating
                # Wait and retry by checking if session now exists
                if self.session_exists(session_id):
                    state = self.get_state(session_id)
                    if state:
                        self._conversation_cache[conversation_id] = session_id
                        return session_id, state
                # Re-raise if session still doesn't exist
                raise

        # ADR-035 Fix 1: Use cryptographically random ID instead of hash-based
        # This prevents session ID prediction attacks
        session_id = self._generate_session_id()

        # ADR-035 Fix 4: Use file lock for atomic session creation
        lock = self._get_session_lock(session_id)
        try:
            with lock:
                # Create new session with random ID
                state = self.create_session(session_id, first_message)
                return session_id, state
        except filelock.Timeout:
            # Extremely unlikely with random UUID, but handle gracefully
            # Try with a new random ID
            session_id = self._generate_session_id()
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

        Note: This method should be called within a lock context from
        get_or_create_session() to prevent race conditions (ADR-035 Fix 4).

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
            if session_dir.is_dir() and not session_dir.name.startswith("_"):
                state = self.get_state(session_dir.name)
                if state:
                    sessions.append(state)
                if len(sessions) >= limit:
                    break
        return sessions

    # =========================================================================
    # ADR-035 Fix 6: Session Archivierung
    # =========================================================================

    def archive_old_sessions(
        self,
        max_age_days: int = DEFAULT_ARCHIVE_AGE_DAYS,
        archive_dir: Optional[Path] = None,
    ) -> int:
        """Archive sessions older than max_age_days to zip files.

        ADR-035 Fix 6: Sessions are archived, NEVER deleted.
        All data is preserved in compressed zip files for future analysis.

        This method:
        1. Scans all session directories
        2. Checks status.json modification time
        3. Zips sessions older than max_age_days
        4. Removes original directory ONLY after successful archive

        Args:
            max_age_days: Sessions older than this are archived (default: 30).
            archive_dir: Target directory for archives (default: sessions/_archive/).

        Returns:
            Number of sessions archived.

        Example:
            >>> mgr.archive_old_sessions(max_age_days=30)
            5  # Archived 5 sessions
        """
        archive_dir = archive_dir or self.base_path / self.ARCHIVE_DIR_NAME
        archive_dir.mkdir(exist_ok=True)

        cutoff = datetime.now() - timedelta(days=max_age_days)
        archived = 0

        for session_dir in self.base_path.iterdir():
            # Skip non-directories and special directories
            if not session_dir.is_dir():
                continue
            if session_dir.name.startswith("_") or session_dir.name.startswith("."):
                continue

            status_file = session_dir / "status.json"
            if not status_file.exists():
                continue

            # Check modification time
            try:
                mtime = datetime.fromtimestamp(status_file.stat().st_mtime)
            except OSError as e:
                logger.warning(f"Could not stat {status_file}: {e}")
                continue

            if mtime >= cutoff:
                # Session is still fresh, skip
                continue

            # Archive the session
            try:
                self._archive_session(session_dir, archive_dir)
                archived += 1
                logger.info(f"Archived session: {session_dir.name}")
            except Exception as e:
                logger.error(f"Failed to archive session {session_dir.name}: {e}")
                # Continue with other sessions

        return archived

    def _archive_session(self, session_dir: Path, archive_dir: Path) -> Path:
        """Archive a single session to a zip file.

        ADR-035 Fix 6: Preserves ALL session data:
        - context/messages.json (Chat history)
        - status.json (Metadata)
        - CLAUDE.md (Template - for workflow analysis)
        - input/ (Original requests)
        - output/ (Generated files)
        - logs/ (Execution logs)
        - phases/ (If present)

        The zip filename includes a date prefix for easy sorting:
        YYYY-MM_session-id.zip

        Args:
            session_dir: Path to the session directory to archive.
            archive_dir: Path to the archive directory.

        Returns:
            Path to the created zip file.

        Raises:
            Exception: If archiving fails (original directory is NOT deleted).
        """
        # Get session state for created_at date
        try:
            state = self.get_state(session_dir.name)
            if state:
                created = state.created_at
            else:
                # Fallback to directory creation time
                created = datetime.fromtimestamp(session_dir.stat().st_ctime)
        except Exception:
            created = datetime.now()

        # Create zip filename with date prefix for sorting
        date_prefix = created.strftime("%Y-%m")
        zip_name = f"{date_prefix}_{session_dir.name}.zip"
        zip_path = archive_dir / zip_name

        # Don't overwrite existing archives
        if zip_path.exists():
            logger.warning(f"Archive already exists, skipping: {zip_path}")
            return zip_path

        # Create the zip archive
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in session_dir.rglob("*"):
                    if file_path.is_file():
                        # Use relative path within the archive
                        arcname = file_path.relative_to(session_dir)
                        zf.write(file_path, arcname)

            # Verify the archive was created successfully
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                raise RuntimeError(f"Archive creation failed: {zip_path}")

            # Remove original directory ONLY after successful archive
            shutil.rmtree(session_dir)

        except Exception as e:
            # Clean up partial archive if it exists
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except OSError:
                    pass
            raise RuntimeError(f"Failed to archive {session_dir.name}: {e}") from e

        return zip_path

    def create_yearly_backup(
        self,
        year: int,
        backup_dir: Optional[Path] = None,
    ) -> Path:
        """Create a yearly backup of all archived sessions from a specific year.

        ADR-035 Fix 6: Collects all zip files from a year into a single
        large backup archive for long-term storage.

        This creates a consolidated backup containing all monthly archives
        from the specified year. The original monthly archives are preserved.

        Args:
            year: Year for the backup (e.g., 2024, 2025).
            backup_dir: Target directory for backups (default: sessions/_backups/).

        Returns:
            Path to the yearly backup file.

        Example:
            >>> mgr.create_yearly_backup(2024)
            Path('/path/to/sessions/_backups/helix-sessions-2024.zip')

        Note:
            To also clean up monthly archives after yearly backup,
            use list_archived_sessions() and manually remove them.
        """
        archive_dir = self.base_path / self.ARCHIVE_DIR_NAME
        backup_dir = backup_dir or self.base_path / self.BACKUP_DIR_NAME
        backup_dir.mkdir(exist_ok=True)

        backup_name = f"helix-sessions-{year}.zip"
        backup_path = backup_dir / backup_name

        year_prefix = str(year)

        # Find all archives from the specified year
        matching_archives = list(archive_dir.glob(f"{year_prefix}-*.zip"))

        if not matching_archives:
            logger.warning(f"No archives found for year {year}")
            # Return path even if empty (consistent API)
            # Create empty backup as marker
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add a README to explain empty backup
                zf.writestr(
                    "README.txt",
                    f"No sessions archived for year {year}.\n"
                )
            return backup_path

        # Create the yearly backup
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for zip_file in sorted(matching_archives):
                # Add each monthly archive to yearly backup
                zf.write(zip_file, zip_file.name)

        logger.info(
            f"Created yearly backup: {backup_path} "
            f"({len(matching_archives)} archives)"
        )

        return backup_path

    def list_archived_sessions(self, year: Optional[int] = None) -> list[Path]:
        """List all archived session zip files.

        Args:
            year: Optional year to filter by (e.g., 2024).

        Returns:
            List of paths to archived zip files, sorted by name.
        """
        archive_dir = self.base_path / self.ARCHIVE_DIR_NAME
        if not archive_dir.exists():
            return []

        if year:
            pattern = f"{year}-*.zip"
        else:
            pattern = "*.zip"

        return sorted(archive_dir.glob(pattern))

    def get_archive_stats(self) -> dict[str, Any]:
        """Get statistics about archived sessions.

        Returns:
            Dictionary with archive statistics:
            - total_archives: Number of archived sessions
            - total_size_bytes: Total size of all archives
            - archives_by_year: Count per year
            - yearly_backups: List of yearly backup files
        """
        archive_dir = self.base_path / self.ARCHIVE_DIR_NAME
        backup_dir = self.base_path / self.BACKUP_DIR_NAME

        stats: dict[str, Any] = {
            "total_archives": 0,
            "total_size_bytes": 0,
            "archives_by_year": {},
            "yearly_backups": [],
        }

        if archive_dir.exists():
            for zip_file in archive_dir.glob("*.zip"):
                stats["total_archives"] += 1
                stats["total_size_bytes"] += zip_file.stat().st_size

                # Extract year from filename (YYYY-MM_session.zip)
                year = zip_file.name[:4]
                if year.isdigit():
                    stats["archives_by_year"][year] = (
                        stats["archives_by_year"].get(year, 0) + 1
                    )

        if backup_dir.exists():
            stats["yearly_backups"] = [
                f.name for f in sorted(backup_dir.glob("helix-sessions-*.zip"))
            ]

        return stats


# Global instance
session_manager = SessionManager()
