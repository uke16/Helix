# Technical Debt aus Consultant Code Audit

**Quelle**: Session `schau-dir-mal-8084093d91d2` - Kritische Bewertung des Consultant Codes
**Datum**: 2025-12-30
**Analyst**: HELIX Meta-Consultant

---

## Kategorisierung

| Kategorie | Anzahl | Beschreibung |
|-----------|--------|--------------|
| KRITISCH | 3 | Sicherheitsrisiken, sofort fixen |
| HOCH | 4 | Funktionale Probleme |
| MITTEL | 4 | Technische Schulden |
| NIEDRIG | 2 | Code-Hygiene |

---

## KRITISCH

### Bug 7: Predictable Session IDs (Sicherheitsrisiko)
**Schwere:** KRITISCH
**Ort:** `src/helix/api/session_manager.py:76-98`
**Problem:**
- Session-ID wird aus User-Content generiert: `hashlib.sha256(first_message[:200])`
- Deterministisch: Gleiche Nachricht = Gleiche Session-ID
- Angreifer kann Session-ID vorhersagen wenn er erste Nachricht kennt

**Code:**
```python
def _generate_session_id_stable(self, first_message: str) -> str:
    clean_msg = re.sub(r'[^a-zA-Z0-9\s]', '', first_message.lower())
    words = clean_msg.split()[:3]
    prefix = '-'.join(words) if words else 'session'

    truncated = first_message[:200]
    hash_input = f"helix-session:{truncated}"
    msg_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    return f"{prefix}-{msg_hash}"
```

**Fix:** Kryptografisch zufällige Session-IDs:
```python
session_id = f"session-{uuid.uuid4().hex}"
```

**Status:** Offen → ADR-035

---

### Bug 8: Fehlende Input Validation
**Schwere:** KRITISCH
**Ort:** `src/helix/api/routes/openai.py:100-119`
**Problem:**
- Keine Längenlimits für `message.content` (DoS-Vektor)
- `role` wird nicht validiert (beliebige Strings möglich)
- Keine Sanitization vor Template-Rendering

**Risiken:**
1. DoS durch riesige Messages (100MB+ Content)
2. Prompt Injection durch ungefilterten Content
3. Potential XSS wenn Content in Web-UI angezeigt wird

**Fix:**
```python
MAX_MESSAGE_LENGTH = 100_000  # 100KB pro Message
VALID_ROLES = {"user", "assistant", "system"}

for msg in request.messages:
    if msg.role not in VALID_ROLES:
        return _error_response(f"Invalid role: {msg.role}")
    if len(msg.content) > MAX_MESSAGE_LENGTH:
        return _error_response("Message too long")
```

**Status:** Offen → ADR-035

---

### Bug 9: Kein Rate Limiting
**Schwere:** KRITISCH
**Ort:** `src/helix/api/routes/openai.py`
**Problem:**
- Jeder Request startet Claude-Prozess (bis 10min Laufzeit)
- Keine Begrenzung paralleler Requests
- Keine Begrenzung pro IP/User

**Risiken:**
1. Resource Exhaustion (100 parallele Claude-Prozesse)
2. Kosten-Explosion (Anthropic API)
3. System-Instabilität

**Fix:** Rate Limiting Middleware:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/v1/chat/completions")
@limiter.limit("10/minute")
async def chat_completions(...):
```

**Status:** Offen → ADR-035

---

## HOCH

### Bug 10: Race Condition bei Session-Erstellung
**Schwere:** HOCH
**Ort:** `src/helix/api/session_manager.py:149-158`
**Problem:** TOCTOU (Time-of-Check-Time-of-Use)
```python
if self.session_exists(session_id):  # Check
    state = self.get_state(session_id)
    ...
# Zwei parallele Requests können beide hier landen
state = self.create_session(...)  # Use
```

**Impact:** Doppelte Session-Erstellung, Datenverlust

**Fix:** File-Locking:
```python
import filelock
lock = filelock.FileLock(f"{session_path}/.lock")
with lock:
    if not self.session_exists(session_id):
        self.create_session(...)
```

**Status:** Offen → ADR-035

---

### Bug 11: Keine Session-Archivierungs-Strategie
**Schwere:** HOCH
**Ort:** `src/helix/api/session_manager.py`
**Problem:**
- Sessions werden erstellt aber nie archiviert
- `projects/sessions/` wächst unbegrenzt
- Jede Session ~500KB (CLAUDE.md, messages.json, output/)

**Impact:** Disk-Space-Erschöpfung nach Wochen/Monaten

**Fix:** Zip-Archivierung statt Löschen (alle Daten bleiben für Analyse erhalten):
```python
def archive_old_sessions(self, max_age_days: int = 30) -> int:
    """Archive sessions older than max_age_days to zip files.

    NICHTS WIRD GELÖSCHT - Alle Daten bleiben erhalten.
    """
    for session_dir in self.sessions_dir.iterdir():
        if older_than_cutoff(session_dir):
            # Zip entire directory to _archive/
            self._archive_session(session_dir)

def create_yearly_backup(self, year: int) -> Path:
    """Create yearly backup of all archived sessions."""
    # Collect all monthly archives into one yearly backup
```

**Verzeichnisstruktur:**
```
sessions/
├── _archive/         # 30+ Tage alt (gezippt)
├── _backups/         # Jahres-Backups
└── [aktive sessions]
```

**Status:** Offen → ADR-035

---

### Bug 12: Secrets in Subprocess Environment
**Schwere:** HOCH
**Ort:** `src/helix/claude_runner.py:503-507`
**Problem:**
```python
api_key = os.environ.get(config.api_key_env, "")
if api_key:
    env["ANTHROPIC_API_KEY"] = api_key
```

API-Keys sind in `/proc/<pid>/environ` lesbar für alle User auf dem System.

**Fix:**
- Keyfile statt Environment Variable
- Oder: Restricted permissions auf Prozess

**Status:** Offen (niedriger Priorität für Single-User-System)

---

### Bug 13: Path Traversal bei Session-ID (Sicherheitsrisiko)
**Schwere:** HOCH
**Ort:** `src/helix/api/session_manager.py:76-98`
**Problem:**
Die ersten 3 Wörter der Nachricht werden zu Verzeichnisnamen.
Input: `"../../etc/passwd ist interessant"`
Output: Session-ID mit `../../etc/passwd` prefix

**Fix:** Striktere Sanitization:
```python
def _sanitize_session_prefix(self, words: list[str]) -> str:
    # Remove path traversal
    safe_words = [w for w in words if not w.startswith('.')]
    # Only alphanumeric
    safe_words = [re.sub(r'[^a-z0-9]', '', w) for w in safe_words]
    return '-'.join(safe_words[:3]) or 'session'
```

**Status:** Offen → ADR-035

---

## MITTEL

### Bug 14: Hardcoded Paths überall
**Schwere:** MITTEL
**Orte:**
- `src/helix/claude_runner.py:77-79`
- `src/helix/api/routes/openai.py:250`
- `src/helix/consultant/expert_manager.py:79`

**Problem:**
```python
DEFAULT_CLAUDE_CMD = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin/claude"
DEFAULT_VENV_PATH = Path("/home/aiuser01/helix-v4/.venv")
nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
```

**Impact:** Nicht portabel, muss bei jedem Umzug angepasst werden

**Fix:** Environment Variables oder zentrale Config:
```python
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", shutil.which("claude") or "claude")
VENV_PATH = Path(os.environ.get("HELIX_VENV", ".venv"))
```

**Status:** Offen → ADR-035

---

### Bug 15: Duplizierter PATH-Setup
**Schwere:** MITTEL
**Orte:**
- `src/helix/api/routes/openai.py:250-251`
- `src/helix/api/routes/openai.py:393-394`

**Problem:** DRY-Verletzung
```python
# In _run_consultant_streaming:
nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"

# Gleicher Code in _run_consultant:
nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"
```

**Fix:** Zentrale `_ensure_claude_path()` Funktion

**Status:** Offen → ADR-035

---

### Bug 16: Globaler Singleton Pattern
**Schwere:** MITTEL
**Ort:** `src/helix/api/session_manager.py:406-407`

**Problem:**
```python
# Global instance
session_manager = SessionManager()
```

Erschwert Testing und schafft implizite Abhängigkeiten.

**Fix:** FastAPI Dependency Injection:
```python
def get_session_manager() -> SessionManager:
    return SessionManager()

@router.post("/chat/completions")
async def chat_completions(
    manager: SessionManager = Depends(get_session_manager),
    ...
)
```

**Status:** Offen (Refactoring, niedrige Priorität)

---

### Bug 17: Dead Code - Meeting/Expert System
**Schwere:** MITTEL
**Orte:**
- `src/helix/consultant/meeting.py` (~300 Zeilen)
- `src/helix/consultant/expert_manager.py` (~300 Zeilen)

**Problem:**
- 600+ Zeilen Code die nie aufgerufen werden
- `openai.py` nutzt das Meeting-System nicht
- Alles läuft über simples Template-System

**Fix:** Entweder integrieren oder entfernen

**Status:** Offen (Cleanup, niedrige Priorität)

---

## NIEDRIG

### Bug 18: Generisches Exception Handling
**Schwere:** NIEDRIG
**Ort:** `src/helix/consultant/meeting.py:279-295`

**Problem:**
```python
except (json.JSONDecodeError, AttributeError):
    # Fallback to keyword-based selection
    return ExpertSelection(...)
```

`AttributeError` ist zu breit - könnte echte Bugs verbergen.

**Fix:** Spezifischere Exceptions, Logging hinzufügen

**Status:** Offen

---

### Bug 19: Template Rendering ohne Markdown Escaping
**Schwere:** NIEDRIG (für internes System)
**Ort:** `src/helix/api/routes/openai.py:199-211`

**Problem:**
```python
content = template.render(
    original_request=state.original_request,  # User-Input!
    messages=messages or [],  # User-Input!
)
```

User-Content wird ungefiltert in Markdown geschrieben.

**Risiko:** Markdown-Injection in CLAUDE.md

**Mitigation:** Nur relevant wenn böswillige User Zugang haben.

**Status:** Offen (niedriger Priorität für Single-User-System)

---

## Zusammenfassung für ADR-035

Die folgenden Bugs sollten in ADR-035 zusammengefasst werden:

### Sofort fixen (Security):
- Bug 7: Predictable Session IDs
- Bug 8: Fehlende Input Validation
- Bug 9: Kein Rate Limiting
- Bug 10: Race Condition
- Bug 13: Path Traversal

### Bald fixen (Reliability):
- Bug 11: Session Archivierung (Zip, nichts löschen!)
- Bug 14: Hardcoded Paths
- Bug 15: Duplizierter PATH-Setup

### Später (Refactoring):
- Bug 16: Singleton Pattern
- Bug 17: Dead Code
- Bug 18: Exception Handling
- Bug 19: Template Escaping
