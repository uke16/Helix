---
adr_id: "030"
title: "Evolution Pipeline Reliability"
status: Proposed

project_type: helix_internal
component_type: PROCESS
classification: FIX
change_scope: minor

files:
  create:
    - src/helix/pipeline/retry_handler.py
    - tests/pipeline/test_retry_handler.py
  modify:
    - src/helix/claude_runner.py
    - src/helix/api/streaming.py
    - src/helix/api/routes.py
    - src/helix/phase_status.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-011  # Post-Phase Verification
  - ADR-025  # Sub-Agent Verifikation
---

# ADR-030: Evolution Pipeline Reliability

## Status

📋 Proposed

---

## Kontext

### Das Problem

Bei der Ausführung von Evolution Pipelines wurden 4 systematische Issues identifiziert, die die Zuverlässigkeit und Beobachtbarkeit beeinträchtigen:

### Issue 1: pytest PATH Issue (Exit 127)

**Symptom:** Claude Code Instanzen können `pytest` nicht finden.

```bash
$ pytest tests/
/bin/bash: pytest: command not found
Exit code: 127
```

**Ursache:** Der Claude Code Runner startet Bash ohne aktivierte Python-Umgebung. Das helix virtualenv wird nicht geladen.

**Auswirkung:** Phasen mit `quality_gate: tests_pass` schlagen fehl, obwohl Tests korrekt wären.

### Issue 2: Job Status API zeigt keine Phasen

**Symptom:** `GET /helix/jobs/{id}` gibt `phases: []` zurück, obwohl Phasen laufen.

```json
{
  "id": "job-123",
  "status": "running",
  "phases": []  // <- Sollte Phasen enthalten
}
```

**Ursache:** Die Phasen-Information wird während der Ausführung nicht in `JobState` geschrieben. Nur `status.json` wird aktualisiert, aber die API liest aus dem In-Memory `JobState`.

**Auswirkung:** Keine Sichtbarkeit über den Fortschritt via API. User müssen manuell `status.json` lesen.

### Issue 3: StrEnum Test-Kompatibilität

**Symptom:** Tests mit `StrEnum` schlagen auf Python 3.10 fehl.

```python
# src/helix/phase_status.py
class PhaseStatus(StrEnum):  # Python 3.11+
    PENDING = "pending"
```

**Ursache:** `StrEnum` wurde erst in Python 3.11 in die stdlib aufgenommen. HELIX deklariert Python 3.10+ Kompatibilität.

**Auswirkung:** CI/CD Pipelines auf Python 3.10 Systemen brechen.

### Issue 4: Keine automatische Retry bei kleinen Fehlern

**Symptom:** Transiente Fehler (Netzwerk, API Throttling) führen zu sofortigem Phase-Fail.

```
Phase 2: API Error 429 Too Many Requests
Status: FAILED
```

**Ursache:** Es gibt keinen Retry-Mechanismus für transiente Fehler. Jeder Fehler führt sofort zum Abbruch.

**Auswirkung:** Unnötige manuelle Neustarts bei temporären Problemen.

---

## Entscheidung

### Wir entscheiden uns für:

Eine koordinierte Fix-Sammlung die alle 4 Issues addressiert.

### Diese Entscheidung beinhaltet:

1. **PATH Fix:** Shell-Environment Setup im Claude Runner
2. **API Sync:** Phasen-Status in JobState synchronisieren
3. **StrEnum Backport:** Kompatibilität für Python 3.10
4. **Retry Handler:** Exponential Backoff für transiente Fehler

### Warum diese Lösung?

- Alle 4 Issues sind unabhängig voneinander
- Jeder Fix ist isoliert und testbar
- Kein Breaking Change an bestehenden APIs
- Backward-kompatibel

---

## Implementation

### Fix 1: pytest PATH Issue

**Datei:** `src/helix/claude_runner.py`

Das Shell-Environment muss den helix virtualenv aktivieren bevor Befehle ausgeführt werden:

```python
# src/helix/claude_runner.py

class ClaudeRunner:
    """Claude Code CLI wrapper with environment setup."""

    def __init__(self, venv_path: Path | None = None):
        self.venv_path = venv_path or Path("/home/aiuser01/helix-v4/.venv")

    def _get_shell_env(self) -> dict[str, str]:
        """Get shell environment with virtualenv activated."""
        env = os.environ.copy()

        if self.venv_path.exists():
            venv_bin = self.venv_path / "bin"
            env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
            env["VIRTUAL_ENV"] = str(self.venv_path)

        return env

    async def run_phase_streaming(
        self,
        project_path: Path,
        phase: PhaseConfig,
        **kwargs
    ) -> PhaseResult:
        """Run a phase with proper environment setup."""
        env = self._get_shell_env()

        # Verify pytest is accessible
        pytest_check = subprocess.run(
            ["which", "pytest"],
            env=env,
            capture_output=True
        )
        if pytest_check.returncode != 0:
            raise EnvironmentError(
                f"pytest not found in PATH. "
                f"Ensure virtualenv at {self.venv_path} is valid."
            )

        # ... rest of implementation
```

### Fix 2: Job Status API Phasen-Synchronisation

**Datei:** `src/helix/api/streaming.py`

Die Phase-Updates müssen in den JobState geschrieben werden:

```python
# src/helix/api/streaming.py

async def stream_phase_execution(
    job_id: str,
    job_state: JobState,
    phases: list[PhaseConfig],
    runner: ClaudeRunner
) -> AsyncIterator[StreamEvent]:
    """Execute phases with JobState synchronization."""

    for phase in phases:
        # Update JobState BEFORE starting phase
        phase_info = PhaseInfo(
            id=phase.id,
            name=phase.name,
            status=PhaseStatus.RUNNING,
            started_at=datetime.now()
        )
        job_state.add_phase(phase_info)

        yield StreamEvent(type="phase_start", data=phase_info.dict())

        try:
            result = await runner.run_phase_streaming(...)

            # Update JobState AFTER phase completion
            phase_info.status = PhaseStatus.COMPLETED if result.success else PhaseStatus.FAILED
            phase_info.completed_at = datetime.now()
            job_state.update_phase(phase_info)

            yield StreamEvent(type="phase_complete", data=phase_info.dict())

        except Exception as e:
            phase_info.status = PhaseStatus.FAILED
            phase_info.error = str(e)
            job_state.update_phase(phase_info)
            raise
```

**Datei:** `src/helix/api/routes.py`

Der Endpoint muss die Phasen aus JobState lesen:

```python
# src/helix/api/routes.py

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get job status including phase information."""
    job_state = job_manager.get_job(job_id)

    if not job_state:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        id=job_id,
        status=job_state.status,
        phases=[p.dict() for p in job_state.phases],  # <- Phasen inkludieren
        started_at=job_state.started_at,
        completed_at=job_state.completed_at,
        error=job_state.error
    )
```

### Fix 3: StrEnum Python 3.10 Kompatibilität

**Datei:** `src/helix/phase_status.py`

Fallback für Python < 3.11:

```python
# src/helix/phase_status.py

"""Phase status enumeration with Python 3.10 compatibility."""

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Backport for Python 3.10
    class StrEnum(str, Enum):
        """String enumeration compatible with Python 3.10+."""

        def __str__(self) -> str:
            return self.value

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}.{self.name}"


class PhaseStatus(StrEnum):
    """Status of a pipeline phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### Fix 4: Automatische Retry bei transienten Fehlern

**Datei:** `src/helix/pipeline/retry_handler.py`

Neues Modul für Retry-Logik:

```python
# src/helix/pipeline/retry_handler.py

"""Retry handler for transient pipeline errors."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(Enum):
    """Categorization of errors for retry decisions."""

    TRANSIENT = "transient"      # Network, throttling - retry
    PERMANENT = "permanent"       # Syntax, logic - no retry
    UNKNOWN = "unknown"          # Default - retry once


# Patterns that indicate transient errors
TRANSIENT_PATTERNS = [
    "429",
    "Too Many Requests",
    "rate limit",
    "timeout",
    "connection reset",
    "temporary failure",
    "ETIMEDOUT",
    "ECONNRESET",
]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an error to determine retry strategy."""
    error_msg = str(error).lower()

    for pattern in TRANSIENT_PATTERNS:
        if pattern.lower() in error_msg:
            return ErrorCategory.TRANSIENT

    # Permanent errors - no retry
    if any(p in error_msg for p in ["syntax", "import", "name error"]):
        return ErrorCategory.PERMANENT

    return ErrorCategory.UNKNOWN


async def with_retry(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
    error_context: str = "operation"
) -> T:
    """Execute an async function with retry on transient errors.

    Args:
        func: Async function to execute
        config: Retry configuration (uses defaults if None)
        error_context: Context string for error messages

    Returns:
        Result of the function

    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e
            category = categorize_error(e)

            if category == ErrorCategory.PERMANENT:
                logger.warning(
                    f"{error_context}: Permanent error, no retry. {e}"
                )
                raise

            if attempt >= config.max_retries:
                logger.error(
                    f"{error_context}: Max retries ({config.max_retries}) "
                    f"exhausted. Last error: {e}"
                )
                raise

            delay = min(
                config.initial_delay * (config.exponential_base ** attempt),
                config.max_delay
            )

            logger.info(
                f"{error_context}: Attempt {attempt + 1} failed ({category.value}), "
                f"retrying in {delay:.1f}s. Error: {e}"
            )

            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    raise last_error  # type: ignore
```

**Integration in streaming.py:**

```python
# src/helix/api/streaming.py

from helix.pipeline.retry_handler import with_retry, RetryConfig

async def stream_phase_execution(...):
    for phase in phases:
        # ... phase setup ...

        result = await with_retry(
            lambda: runner.run_phase_streaming(project_path, phase),
            config=RetryConfig(max_retries=2),
            error_context=f"Phase {phase.id}: {phase.name}"
        )
```

---

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | Retry Handler Modul dokumentieren |
| Code-Docstrings | Alle neuen Funktionen dokumentieren |

---

## Akzeptanzkriterien

### Fix 1: pytest PATH

- [ ] `pytest` ist in Claude Code Bash-Sessions verfügbar
- [ ] Test: Phase mit `quality_gate: tests_pass` läuft erfolgreich
- [ ] Fehler bei fehlendem virtualenv ist aussagekräftig

### Fix 2: Job Status API

- [ ] `GET /helix/jobs/{id}` gibt `phases` Array zurück
- [ ] Jede Phase hat `id`, `name`, `status`, `started_at`
- [ ] Abgeschlossene Phasen haben `completed_at`
- [ ] Test: E2E Test für Job-Status während Ausführung

### Fix 3: StrEnum Kompatibilität

- [ ] Tests laufen auf Python 3.10
- [ ] Tests laufen auf Python 3.11+
- [ ] `PhaseStatus` Enum funktioniert identisch auf beiden Versionen

### Fix 4: Retry Handler

- [ ] Transiente Fehler (429, timeout) werden automatisch wiederholt
- [ ] Permanente Fehler (SyntaxError) werden nicht wiederholt
- [ ] Max 3 Retries mit exponential backoff
- [ ] Retry-Versuche werden geloggt
- [ ] Unit Tests für `categorize_error` und `with_retry`

### Integration

- [ ] Alle 4 Fixes funktionieren zusammen
- [ ] Keine Regression in bestehenden Pipelines
- [ ] Pipeline-Ausführung ist stabiler als zuvor

---

## Konsequenzen

### Vorteile

1. **Höhere Zuverlässigkeit:** Transiente Fehler führen nicht mehr zu sofortigem Abbruch
2. **Bessere Observability:** Phasen-Status ist via API sichtbar
3. **Breitere Kompatibilität:** Python 3.10 wird unterstützt
4. **Weniger manuelle Intervention:** Automatische Retries reduzieren Wartungsaufwand

### Nachteile

1. **Komplexität:** Retry-Logik muss korrekt implementiert werden
2. **Latenz:** Retries verzögern die Gesamt-Ausführung bei Fehlern

### Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| Endlos-Retries | Max 3 Retries fest konfiguriert |
| Falsche Error-Kategorisierung | Pattern-Liste wartbar, einfach erweiterbar |
| Race Conditions bei JobState | JobState-Updates sind thread-safe |

---

## Abhängigkeiten

- **ADR-011:** Post-Phase Verification - Integriert mit Retry
- **ADR-025:** Sub-Agent Verifikation - Retry vor Verification

---

## Rollout Plan

1. **Phase 1:** StrEnum Fix (sofort, breaking risk: low)
2. **Phase 2:** Job Status API Fix (nach Tests)
3. **Phase 3:** pytest PATH Fix (nach Tests)
4. **Phase 4:** Retry Handler (nach Integration Tests)

---

## Referenzen

- [ADR-011: Post-Phase Verification](011-post-phase-verification.md)
- [ADR-025: Sub-Agent Verifikation](025-sub-agent-verification.md)
- [Python StrEnum Documentation](https://docs.python.org/3/library/enum.html#enum.StrEnum)
