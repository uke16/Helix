---
adr_id: "035"
title: "Consultant API Hardening - Security & Reliability Fixes"
status: Proposed

component_type: SERVICE
classification: FIX
change_scope: major

domain: helix
language: python
skills:
  - helix
  - infrastructure

files:
  create:
    - src/helix/api/middleware/rate_limiter.py
    - src/helix/api/middleware/input_validator.py
    - src/helix/config/paths.py
    - tests/api/test_rate_limiter.py
    - tests/api/test_input_validator.py
    - tests/api/test_session_security.py
  modify:
    - src/helix/api/session_manager.py
    - src/helix/api/routes/openai.py
    - src/helix/claude_runner.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - "029"
  - "034"
---

# ADR-035: Consultant API Hardening - Security & Reliability Fixes

## Status
Proposed

## Kontext

Eine kritische Code-Analyse des Consultant-Systems (Session `schau-dir-mal-8084093d91d2`) hat 19 Bugs identifiziert, davon 3 kritische Sicherheitslücken. Diese ADR konsolidiert alle straightforward Fixes, bei denen der Root Cause klar ist und keine architektonischen Entscheidungen nötig sind.

### Zusammenfassung der Bugs

| Schwere | Anzahl | Beispiele |
|---------|--------|-----------|
| KRITISCH | 3 | Predictable Session IDs, keine Input Validation, kein Rate Limiting |
| HOCH | 4 | Race Conditions, Path Traversal, keine Cleanup-Strategie |
| MITTEL | 4 | Hardcoded Paths, DRY-Verletzungen, Dead Code |
| NIEDRIG | 2 | Generisches Exception Handling |

### Quellen

- `/bugs/from-audit-consultant-code.md` - 13 neue Bugs aus Code-Audit
- `/bugs/from-controller-adr-032.md` - 5 Bugs aus Controller-Workflow
- `/bugs/from-controller-adr-034.md` - 3 Bugs aus Controller-Workflow
- `/bugs/bug-006-chat-history-not-passed.md` - Bereits gefixt

## Entscheidung

Wir implementieren die folgenden Fixes in einer konsolidierten Änderung:

### Phase 1: Security Fixes (KRITISCH)

#### Fix 1: Kryptografisch sichere Session-IDs

**Problem:** Session-IDs sind vorhersagbar (Hash der ersten Nachricht).

**Lösung:**
```python
# session_manager.py
import uuid

def _generate_session_id(self) -> str:
    """Generate cryptographically random session ID."""
    return f"session-{uuid.uuid4().hex}"

def get_or_create_session(
    self,
    first_message: str,
    conversation_id: Optional[str] = None,
) -> tuple[str, SessionState]:
    # Priority 1: Use conversation_id if provided (ADR-029)
    if conversation_id:
        session_id = self._normalize_conversation_id(conversation_id)
    else:
        # Random ID statt deterministisch
        session_id = self._generate_session_id()
    ...
```

#### Fix 2: Input Validation Middleware

**Problem:** Keine Limits für Message-Größe, keine Role-Validation.

**Lösung:**
```python
# middleware/input_validator.py
MAX_MESSAGE_LENGTH = 100_000  # 100KB
MAX_MESSAGES_PER_REQUEST = 100
VALID_ROLES = {"user", "assistant", "system"}

class InputValidator:
    @staticmethod
    def validate_chat_request(request: ChatCompletionRequest) -> None:
        if len(request.messages) > MAX_MESSAGES_PER_REQUEST:
            raise HTTPException(400, "Too many messages")

        for msg in request.messages:
            if msg.role not in VALID_ROLES:
                raise HTTPException(400, f"Invalid role: {msg.role}")
            if len(msg.content) > MAX_MESSAGE_LENGTH:
                raise HTTPException(400, "Message too long")
```

#### Fix 3: Rate Limiting

**Problem:** Unbegrenzte parallele Claude-Prozesse möglich.

**Lösung:**
```python
# middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# In openai.py
@router.post("/chat/completions")
@limiter.limit("10/minute")
async def chat_completions(request: Request, ...):
    ...
```

### Phase 2: Reliability Fixes (HOCH)

#### Fix 4: Race Condition Prevention

**Problem:** TOCTOU bei Session-Erstellung.

**Lösung:**
```python
# session_manager.py
import filelock

def get_or_create_session(...) -> tuple[str, SessionState]:
    session_path = self.sessions_dir / session_id
    lock_path = session_path / ".lock"

    # Atomic creation with file lock
    lock = filelock.FileLock(str(lock_path), timeout=5)
    with lock:
        if self.session_exists(session_id):
            return session_id, self.get_state(session_id)
        return session_id, self.create_session(...)
```

#### Fix 5: Path Traversal Prevention

**Problem:** User-Content in Pfadnamen ohne Sanitization.

**Lösung:**
```python
# session_manager.py
def _normalize_conversation_id(self, conv_id: str) -> str:
    """Normalize conversation ID for safe filesystem use."""
    # Remove path traversal
    safe_id = conv_id.replace("..", "").replace("/", "-").replace("\\", "-")
    # Only alphanumeric and hyphens
    safe_id = re.sub(r'[^a-zA-Z0-9-]', '', safe_id)
    # Limit length
    return safe_id[:64] if safe_id else "session"
```

#### Fix 6: Session Archivierung (Zip statt Löschen)

**Problem:** Sessions wachsen unbegrenzt.

**Anforderung:** Alle Daten sollen erhalten bleiben für Workflow-Analyse und Referenz. Nichts löschen!

**Lösung:**
```python
# session_manager.py
import zipfile
from datetime import datetime, timedelta

def archive_old_sessions(
    self,
    max_age_days: int = 30,
    archive_dir: Optional[Path] = None,
) -> int:
    """
    Archive sessions older than max_age_days to zip files.

    WICHTIG: Nichts wird gelöscht! Alle Daten bleiben erhalten.

    Args:
        max_age_days: Sessions älter als X Tage werden archiviert
        archive_dir: Zielverzeichnis für Archive (default: sessions/_archive/)

    Returns:
        Anzahl der archivierten Sessions
    """
    archive_dir = archive_dir or self.sessions_dir / "_archive"
    archive_dir.mkdir(exist_ok=True)

    cutoff = datetime.now() - timedelta(days=max_age_days)
    archived = 0

    for session_dir in self.sessions_dir.iterdir():
        if not session_dir.is_dir() or session_dir.name.startswith("_"):
            continue

        status_file = session_dir / "status.json"
        if not status_file.exists():
            continue

        mtime = datetime.fromtimestamp(status_file.stat().st_mtime)
        if mtime >= cutoff:
            continue

        # Zip the entire session directory
        self._archive_session(session_dir, archive_dir)
        archived += 1
        logger.info(f"Archived session: {session_dir.name}")

    return archived

def _archive_session(self, session_dir: Path, archive_dir: Path) -> Path:
    """
    Archive a single session to a zip file.

    Erhält ALLES:
    - context/messages.json (Chat-Historie)
    - status.json (Metadata)
    - CLAUDE.md (Template - für Workflow-Analyse)
    - output/ (generierte Dateien)
    - phases/ (falls vorhanden)

    Returns:
        Path to the created zip file
    """
    # Create zip filename with date prefix for easy sorting
    status = self.get_state(session_dir.name)
    created = status.created_at if status else datetime.now()
    date_prefix = created.strftime("%Y-%m")

    zip_name = f"{date_prefix}_{session_dir.name}.zip"
    zip_path = archive_dir / zip_name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in session_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(session_dir)
                zf.write(file_path, arcname)

    # Remove original directory after successful archive
    shutil.rmtree(session_dir)

    return zip_path

def create_yearly_backup(
    self,
    year: int,
    backup_dir: Optional[Path] = None,
) -> Path:
    """
    Create a yearly backup of all archived sessions from a specific year.

    Sammelt alle Zip-Dateien eines Jahres in ein großes Backup-Archiv.

    Args:
        year: Jahr für das Backup (z.B. 2024)
        backup_dir: Zielverzeichnis (default: sessions/_backups/)

    Returns:
        Path to the yearly backup file
    """
    archive_dir = self.sessions_dir / "_archive"
    backup_dir = backup_dir or self.sessions_dir / "_backups"
    backup_dir.mkdir(exist_ok=True)

    backup_name = f"helix-sessions-{year}.zip"
    backup_path = backup_dir / backup_name

    year_prefix = str(year)

    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for zip_file in archive_dir.glob(f"{year_prefix}-*.zip"):
            # Add each monthly archive to yearly backup
            zf.write(zip_file, zip_file.name)

    # Optionally remove monthly archives after yearly backup
    # (uncomment if you want to clean up after backup)
    # for zip_file in archive_dir.glob(f"{year_prefix}-*.zip"):
    #     zip_file.unlink()

    logger.info(f"Created yearly backup: {backup_path}")
    return backup_path
```

**Speicherersparnis:**
- ZIP-Kompression reduziert Größe um ~70-80% (Text komprimiert gut)
- Alle Daten bleiben erhalten für Analyse
- Yearly Backups für Langzeit-Archivierung

**Verzeichnisstruktur nach Archivierung:**
```
projects/sessions/
├── _archive/              # 30+ Tage alte Sessions
│   ├── 2025-01_session-abc123.zip
│   ├── 2025-01_session-def456.zip
│   └── 2025-02_session-ghi789.zip
├── _backups/              # Jahres-Backups
│   └── helix-sessions-2024.zip
└── [aktive-sessions]/     # Aktive Sessions (< 30 Tage)
```

### Phase 3: Code Quality (MITTEL)

#### Fix 7: Zentrale Pfad-Konfiguration

**Problem:** Hardcoded Paths an 5+ Stellen.

**Lösung:**
```python
# config/paths.py
import os
import shutil
from pathlib import Path

class PathConfig:
    """Central path configuration with environment variable support."""

    HELIX_ROOT = Path(os.environ.get(
        "HELIX_ROOT",
        Path(__file__).parent.parent.parent.parent
    ))

    VENV_PATH = Path(os.environ.get(
        "HELIX_VENV",
        HELIX_ROOT / ".venv"
    ))

    CLAUDE_CMD = os.environ.get(
        "CLAUDE_CMD",
        shutil.which("claude") or "claude"
    )

    NVM_PATH = os.environ.get(
        "NVM_BIN",
        # Fallback: Try common locations
        _find_nvm_bin()
    )

    @classmethod
    def ensure_claude_path(cls) -> None:
        """Add NVM to PATH if needed."""
        if cls.NVM_PATH and cls.NVM_PATH not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{cls.NVM_PATH}:{os.environ.get('PATH', '')}"
```

#### Fix 8: DRY für PATH-Setup

**Problem:** Gleicher Code in `_run_consultant_streaming` und `_run_consultant`.

**Lösung:**
```python
# openai.py
from helix.config.paths import PathConfig

async def _run_consultant_streaming(...):
    PathConfig.ensure_claude_path()  # Zentral
    ...

async def _run_consultant(...):
    PathConfig.ensure_claude_path()  # Zentral
    ...
```

## Implementation

### Phasenplan

```
Phase 1: Security (sofort)
├── Fix 1: Random Session IDs
├── Fix 2: Input Validation
└── Fix 3: Rate Limiting

Phase 2: Reliability (nach Security)
├── Fix 4: File Locking
├── Fix 5: Path Sanitization
└── Fix 6: Session Cleanup

Phase 3: Code Quality (nach Reliability)
├── Fix 7: Zentrale Pfade
└── Fix 8: DRY Refactoring
```

### Neue Dependencies

```toml
# pyproject.toml additions
slowapi = "^0.1.9"      # Rate limiting
filelock = "^3.13.0"    # File locking
```

### Migration

Keine Breaking Changes. Alle Fixes sind rückwärtskompatibel.

## Akzeptanzkriterien

### Security

- [ ] Session-IDs sind nicht mehr aus Message-Content vorhersagbar
- [ ] Random UUIDs werden für neue Sessions verwendet
- [ ] Bestehende Sessions mit Conversation-ID funktionieren weiter
- [ ] Input Validation lehnt ungültige Roles ab
- [ ] Input Validation lehnt Messages > 100KB ab
- [ ] Rate Limiting: Max 10 Requests/Minute pro IP
- [ ] Path Traversal Attempts werden abgefangen

### Reliability

- [ ] Parallele Session-Erstellung führt nicht zu Datenverlust
- [ ] File Locking verhindert Race Conditions
- [ ] Archiv-Job zippt Sessions älter als 30 Tage
- [ ] ALLE Session-Daten bleiben im Zip erhalten (nichts löschen!)
- [ ] Archivierung ist idempotent (mehrfache Ausführung sicher)
- [ ] Yearly Backup sammelt alle Archives eines Jahres

### Code Quality

- [ ] Keine hardcoded Pfade mehr in claude_runner.py
- [ ] Keine hardcoded Pfade mehr in openai.py
- [ ] Zentrale PathConfig wird von allen Modulen genutzt
- [ ] DRY: `ensure_claude_path()` an einer Stelle

### Tests

- [ ] Unit Tests für InputValidator
- [ ] Unit Tests für Rate Limiter
- [ ] Unit Tests für Session ID Generation
- [ ] Unit Tests für Path Sanitization
- [ ] Integration Test für Cleanup

## Konsequenzen

### Positiv

- Schließt 7 bekannte Sicherheitslücken
- Verhindert Resource Exhaustion
- Macht System portabler (keine hardcoded Pfade)
- Reduziert technische Schulden
- Verbessert Maintainability

### Negativ

- Neue Dependencies (slowapi, filelock)
- Leichte Performance-Overhead durch Validation
- Bestehende deterministische Session-IDs ändern sich

### Nicht adressiert (separate ADRs)

Die folgenden Punkte werden NICHT in dieser ADR behandelt:

1. **Singleton Pattern** (Bug 16) - Größeres Refactoring, niedrige Priorität
2. **Dead Code Meeting-System** (Bug 17) - Separate Entscheidung ob integrieren oder löschen
3. **Generisches Exception Handling** (Bug 18) - Niedrige Priorität
4. **Template Escaping** (Bug 19) - Nur relevant mit untrusted Users
5. **Secrets in Environment** (Bug 12) - Nur relevant für Multi-User-Systeme

## Dokumentation

Nach Implementation:
- Update `docs/ARCHITECTURE-MODULES.md` mit Security-Sektion
- Update `CLAUDE.md` mit neuen Environment Variables

## Referenzen

- `/bugs/INDEX.md` - Bug-Übersicht
- `/bugs/from-audit-consultant-code.md` - Detaillierte Bug-Beschreibungen
- ADR-029: Session Persistence (X-Conversation-ID)
- ADR-034: LLM-Native Flow
