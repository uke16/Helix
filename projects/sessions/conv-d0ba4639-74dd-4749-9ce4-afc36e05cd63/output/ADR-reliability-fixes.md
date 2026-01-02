---
adr_id: "041"
title: "Reliability Fixes - Race Condition & Shell Injection"
status: Proposed

component_type: SERVICE
classification: FIX
change_scope: minor

domain: helix
language: python

files:
  modify:
    - src/helix/api/session_manager.py
    - src/helix/ralph/consultant_verify.py
    - control/spawn-consultant.sh
  create: []
  docs: []

depends_on:
  - "035"
  - "040"
---

# ADR-041: Reliability Fixes - Race Condition & Shell Injection

## Status

Proposed

## Kontext

Nach dem Security Audit (ADR-035) wurden zwei kritische Probleme identifiziert die noch nicht gefixt sind:

### Bug 10: Race Condition in Session Management

`session_manager.py:167-214` hat eine TOCTOU (Time-of-Check-Time-of-Use) Race Condition:

```python
# Aktueller Code:
if self.session_exists(session_id):      # CHECK
    state = self.get_state(session_id)   # USE
    ...
else:
    state = self.create_session(...)     # WRITE
```

Bei parallelen Requests mit gleicher `conversation_id`:
1. Request A prüft: Session existiert nicht
2. Request B prüft: Session existiert nicht
3. Request A erstellt Session
4. Request B erstellt Session (überschreibt A's State!)

**Impact**: Datenverlust bei parallelen Requests in Open WebUI.

### Bug: Shell Injection in ConsultantVerifier

`consultant_verify.py:36-42` übergibt User-kontrollierten Content als Shell-Argument:

```python
result = subprocess.run(
    [str(self.spawn_script), prompt],  # prompt = ADR-Inhalt
    ...
)
```

`spawn-consultant.sh` nutzt `$*` und `$@` - bei speziell konstruiertem ADR-Inhalt könnte Shell-Code injiziert werden.

**Impact**: Potenzielle Remote Code Execution wenn ADR-Inhalt manipuliert wird.

## Entscheidung

Wir fixen beide Bugs mit minimalen, gezielten Änderungen:

1. **File-Locking** mit `filelock` für atomare Session-Erstellung
2. **stdin statt Argument** für sichere Prompt-Übergabe an Shell-Script

## Implementation

### Fix 1: File-Locking für Session Management

Nutze `filelock` Library für atomare Session-Erstellung:

```python
from filelock import FileLock, Timeout

class SessionManager:
    LOCK_TIMEOUT = 5  # seconds

    def _get_lock_path(self, session_id: str) -> Path:
        """Get lock file path for session."""
        return self.base_path / f".{session_id}.lock"

    def get_or_create_session(
        self,
        first_message: str,
        conversation_id: Optional[str] = None,
    ) -> tuple[str, SessionState]:
        if conversation_id:
            session_id = self._normalize_conversation_id(conversation_id)
            lock_path = self._get_lock_path(session_id)

            try:
                with FileLock(lock_path, timeout=self.LOCK_TIMEOUT):
                    # Atomare Prüfung und Erstellung
                    if self.session_exists(session_id):
                        state = self.get_state(session_id)
                        if state:
                            return session_id, state

                    state = self.create_session(session_id, first_message, conversation_id)
                    return session_id, state
            except Timeout:
                # Fallback: Random ID wenn Lock nicht verfügbar
                session_id = self._generate_session_id()
                state = self.create_session(session_id, first_message, conversation_id)
                return session_id, state

        # Kein conversation_id: Random ID (kein Lock nötig)
        session_id = self._generate_session_id()
        state = self.create_session(session_id, first_message)
        return session_id, state
```

### Fix 2: Prompt via stdin statt Argument

Ändere `consultant_verify.py` um Prompt über stdin zu senden:

```python
def verify_adr(self, adr_path: Path, timeout: int = 120) -> VerifyResult:
    adr_path = Path(adr_path)
    auto_checks = self._run_auto_checks(adr_path)

    adr_content = adr_path.read_text()
    prompt = self._build_prompt(adr_content, auto_checks)

    try:
        result = subprocess.run(
            [str(self.spawn_script)],  # Keine Argumente!
            input=prompt,              # Prompt via stdin
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.helix_root)
        )
        verdict = result.stdout
    except subprocess.TimeoutExpired:
        verdict = "VERDICT: FAILED - Timeout"
    except Exception as e:
        verdict = f"VERDICT: FAILED - Error: {e}"

    passed = "VERDICT: PASSED" in verdict
    return VerifyResult(passed=passed, verdict=verdict, auto_checks=auto_checks)
```

Ändere `spawn-consultant.sh` um stdin zu lesen:

```bash
# Wenn kein Argument, lese von stdin
if [[ $# -eq 0 ]]; then
    USER_PROMPT=$(cat)
else
    # Bestehende Logik für review/analyze/adr Modi
    ...
fi
```

## Dokumentation

Keine neue Dokumentation nötig - dies sind interne Bug-Fixes.

Die bestehende Dokumentation in `docs/ARCHITECTURE-MODULES.md` (Session Management) bleibt unverändert, da die API-Schnittstelle identisch bleibt.

## Akzeptanzkriterien

- [ ] `filelock` zu requirements.txt hinzugefügt
- [ ] `get_or_create_session()` nutzt FileLock für conversation_id-basierte Sessions
- [ ] Lock-Dateien werden unter `.{session_id}.lock` erstellt
- [ ] Timeout-Fallback auf Random-ID funktioniert
- [ ] `consultant_verify.py` sendet Prompt über stdin
- [ ] `spawn-consultant.sh` kann Prompt von stdin lesen
- [ ] Bestehende Shell-Modi (review/analyze/adr) funktionieren weiterhin
- [ ] Unit Tests für Race Condition Szenario

## Konsequenzen

### Positiv

- Race Condition eliminiert - keine Datenverluste bei parallelen Requests
- Shell Injection Vektor geschlossen
- Atomare Session-Erstellung garantiert

### Negativ

- Neue Dependency: `filelock`
- Lock-Dateien im sessions/ Verzeichnis (werden mit `.` Prefix versteckt)
- Marginaler Performance-Overhead durch Locking

### Nicht adressiert (Kosmetik/Niedrig)

Diese Bugs werden NICHT in diesem ADR gefixt (zu kosmetisch):

- Bug 16: Global Singleton Pattern (works fine)
- Bug 17: Dead Code (meeting.py, expert_manager.py) - hat keinen Runtime-Impact
- Bug 18: Generische Exception catches - marginal
- Bug 19: Template Escaping - kein Security-Impact in Single-User-System
