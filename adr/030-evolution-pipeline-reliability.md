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
    - src/helix/evolution/test_baseline.py
    - src/helix/evolution/project_initializer.py
    - tests/pipeline/test_retry_handler.py
    - tests/evolution/test_baseline.py
    - tests/evolution/test_project_initializer.py
  modify:
    - src/helix/claude_runner.py
    - src/helix/api/streaming.py
    - src/helix/api/routes.py
    - src/helix/api/routes_evolution.py
    - src/helix/api/main.py
    - src/helix/phase_status.py
    - src/helix/evolution/project.py
    - src/helix/evolution/deployer.py
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

### Issue 5: Project Discovery basiert auf Runtime-Artifact

**Symptom:** `Project not found: adr-030-pipeline-reliability`

```bash
$ curl http://localhost:8001/helix/evolution/projects/adr-030-pipeline-reliability
{"error": "Project not found"}
```

**Ursache:** Projekte werden nur erkannt wenn `status.json` existiert. Das ist ein Laufzeit-Artifact, nicht Teil der Projekt-Definition. Ein Projekt sollte erkannt werden wenn `phases.yaml` oder `ADR-*.md` existiert.

**Auswirkung:** Neue Projekte müssen manuell initialisiert werden.

### Issue 6: Fehlende Verzeichnisstruktur

**Symptom:** Projekt wird nicht vollständig erkannt oder Operationen schlagen fehl.

```python
# list_new_files() crasht wenn new/ nicht existiert
def list_new_files(self) -> list[Path]:
    return list((self.path / "new").iterdir())  # FileNotFoundError!
```

**Ursache:** Evolution-Projekte erwarten `new/`, `modified/`, `phases/` Verzeichnisse, aber erzeugen sie nicht automatisch.

**Auswirkung:** Manuelle Verzeichniserstellung nötig: `mkdir -p new modified phases`

### Issue 7: Inkonsistente Datei-Berechtigungen

**Symptom:** Dateien haben Berechtigungen `0600` (nur Owner lesbar).

```bash
$ ls -la ADR-030.md
-rw------- 1 aiuser01 aiuser01 26476 Dec 28 ADR-030.md
# Sollte sein: -rw-r--r-- (0644)
```

**Ursache:** `shutil.copy2()` preserviert Source-Permissions und/oder User hat restrictive `umask` (0077).

**Auswirkung:** Andere Prozesse/User können Dateien nicht lesen, Tools wie das str_replace Tool scheitern.

### Issue 8: Fehlende Exception-Details in API

**Symptom:** `Internal Server Error` ohne Details, keine Logs verfügbar.

```bash
$ curl http://localhost:8001/helix/evolution/projects
{"error": "Internal Server Error"}  # Was ist passiert?
```

**Ursache:** Keine globale Exception-Handler in FastAPI. Unhandled Exceptions geben nur generische Fehlermeldung.

**Auswirkung:** Debugging ohne Logs sehr schwierig.

### Issue 9: Sort-Bug bei None Werten

**Symptom:** `Internal Server Error` bei `/helix/evolution/projects`.

```python
# Zeile 431 in routes_evolution.py
projects.sort(key=lambda p: p.get_status_data().get("updated_at", ""))
# Problem: .get() gibt None zurück wenn Wert explizit None ist!
# sorted() kann None nicht mit Strings vergleichen → TypeError
```

**Ursache:** `.get(key, default)` gibt default nur zurück wenn KEY FEHLT. Wenn key existiert aber `value=None`, wird `None` zurückgegeben.

**Auswirkung:** API-Endpoint crasht bei Projekten mit `updated_at: null` in status.json.


---

## Entscheidung

### Wir entscheiden uns für:

Eine koordinierte Fix-Sammlung die alle 9 Issues addressiert.

### Diese Entscheidung beinhaltet:

1. **PATH Fix:** Shell-Environment Setup im Claude Runner
2. **API Sync:** Phasen-Status in JobState synchronisieren
3. **StrEnum Backport:** Kompatibilität für Python 3.10
4. **Retry Handler:** Exponential Backoff für transiente Fehler
5. **Baseline-Tests:** Diff-basierte Test-Bewertung (pre-existing vs. new failures)
6. **Project Discovery:** Erkennung via Definition-Files statt Runtime-Artifacts
7. **Permission Normalization:** Einheitliche Berechtigungen (0644/0755)
8. **Global Exception Handler:** Strukturierte Fehlerausgabe mit Logging
9. **None-Safe Sorting:** Robuste Sortierung bei fehlenden Werten

### Warum diese Lösung?

- Alle 9 Issues sind unabhängig voneinander
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

### Fix 5: Baseline-basierte Test-Bewertung

**Problem:** Die Pipeline stoppt bei jedem einzelnen Test-Failure, auch wenn:
- Der Test schon vorher kaputt war (pre-existing failure)
- Der Test nicht zur aktuellen Änderung gehört
- Es nur 1 von 500 Tests ist (0.2% Failure Rate)

**Symptom (ADR-020):**
```
510 passed, 1 failed → Pipeline STOPPED
```
Der eine Failure war ein StrEnum-Test der schon vorher nicht funktioniert hätte.

**Lösung:** Automatische Baseline-Erkennung mit Diff-basierter Bewertung.

#### Konzept
```
VOR Pipeline:    pytest main branch → Baseline (z.B. 3 failures)
NACH Pipeline:   pytest mit Änderungen → Aktuell (z.B. 4 failures)
                         │
                         ▼
                 DIFF-ANALYSE
                 ├─ 3 failures waren schon in Baseline → IGNORIEREN
                 └─ 1 failure ist NEU → BLOCKING (Regression)
```

#### Kategorien

| Kategorie | Bedeutung | Aktion |
|-----------|-----------|--------|
| **Pre-existing** | Failure war schon in Baseline | ✅ Ignorieren |
| **Regression** | Bestehender Test jetzt kaputt | ❌ Blocking |
| **New Test Failure** | Neuer Test (aus ADR) failt | ❌ Blocking |

#### Implementation

**Datei:** `src/helix/evolution/test_baseline.py`
```python
"""Baseline-based test evaluation for Evolution Pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import subprocess
import json


@dataclass
class TestBaseline:
    """Snapshot of test results before changes."""
    
    timestamp: datetime
    commit_sha: str
    total_tests: int
    passed_tests: int
    failed_tests: set[str] = field(default_factory=set)  # nodeid format
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "commit_sha": self.commit_sha,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": list(self.failed_tests)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestBaseline":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            commit_sha=data["commit_sha"],
            total_tests=data["total_tests"],
            passed_tests=data["passed_tests"],
            failed_tests=set(data["failed_tests"])
        )


@dataclass
class TestEvaluationResult:
    """Result of baseline comparison."""
    
    passed: bool
    total_tests: int
    passed_tests: int
    
    # Categorized failures
    pre_existing: list[str]      # Already failed in baseline (OK)
    regressions: list[str]       # Newly broken existing tests (BLOCKING)
    new_test_failures: list[str] # New tests that fail (BLOCKING)
    
    # Summary
    blocking_failures: list[str]
    ignored_failures: list[str]
    
    @property
    def summary(self) -> str:
        if self.passed:
            ignored = len(self.ignored_failures)
            return (
                f"✅ Tests passed: {self.passed_tests}/{self.total_tests}"
                f"{f' ({ignored} pre-existing failures ignored)' if ignored else ''}"
            )
        else:
            return (
                f"❌ Tests failed: {len(self.blocking_failures)} blocking failures\n"
                f"   Regressions: {self.regressions}\n"
                f"   New test failures: {self.new_test_failures}"
            )


async def capture_baseline(project_root: Path) -> TestBaseline:
    """
    Capture test baseline from current state (before changes).
    
    Called at the START of pipeline execution, before any phases run.
    Uses pytest JSON output for reliable parsing.
    """
    result = subprocess.run(
        ["python3", "-m", "pytest", "--json-report", "--json-report-file=/dev/stdout", "-q"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": f"{project_root}/src"}
    )
    
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Fallback: parse pytest output manually
        return _parse_pytest_text_output(result.stdout, result.stderr)
    
    failed = {
        test["nodeid"]
        for test in report.get("tests", [])
        if test["outcome"] == "failed"
    }
    
    summary = report.get("summary", {})
    
    return TestBaseline(
        timestamp=datetime.now(),
        commit_sha=_get_current_commit(project_root),
        total_tests=summary.get("total", 0),
        passed_tests=summary.get("passed", 0),
        failed_tests=failed
    )


def evaluate_against_baseline(
    current_failures: set[str],
    current_total: int,
    current_passed: int,
    baseline: TestBaseline,
    adr_test_files: list[str]
) -> TestEvaluationResult:
    """
    Compare current test results against baseline.
    
    Args:
        current_failures: Set of failed test nodeids from current run
        current_total: Total tests in current run
        current_passed: Passed tests in current run
        baseline: Baseline captured before changes
        adr_test_files: Test files created by this ADR (from files.create)
    
    Returns:
        TestEvaluationResult with categorized failures
    """
    # Pre-existing: failures that were already in baseline
    pre_existing = current_failures & baseline.failed_tests
    
    # New failures: not in baseline
    new_failures = current_failures - baseline.failed_tests
    
    # Split new failures: from ADR tests vs regressions in existing tests
    new_test_failures = []
    regressions = []
    
    for failure in new_failures:
        # Check if this test file was created by the ADR
        test_file = failure.split("::")[0]
        if any(test_file.endswith(adr_file.lstrip("./")) for adr_file in adr_test_files):
            new_test_failures.append(failure)
        else:
            regressions.append(failure)
    
    # Blocking = regressions + new test failures
    blocking = regressions + new_test_failures
    
    return TestEvaluationResult(
        passed=len(blocking) == 0,
        total_tests=current_total,
        passed_tests=current_passed,
        pre_existing=list(pre_existing),
        regressions=regressions,
        new_test_failures=new_test_failures,
        blocking_failures=blocking,
        ignored_failures=list(pre_existing)
    )


def _get_current_commit(project_root: Path) -> str:
    """Get current git commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()[:8]
```

**Integration in Pipeline:** `src/helix/evolution/validator.py`
```python
async def validate_with_baseline(
    project: EvolutionProject,
    baseline: TestBaseline
) -> ValidationResult:
    """
    Validate project with baseline comparison.
    
    Only NEW failures block integration.
    Pre-existing failures are logged but ignored.
    """
    # Get ADR test files
    adr = project.get_adr()
    adr_test_files = [
        f for f in adr.files.get("create", [])
        if f.startswith("tests/") or "/tests/" in f
    ]
    
    # Run pytest on test system
    test_result = await run_pytest_json(project.test_system_path)
    
    current_failures = {t["nodeid"] for t in test_result["tests"] if t["outcome"] == "failed"}
    
    # Evaluate against baseline
    eval_result = evaluate_against_baseline(
        current_failures=current_failures,
        current_total=test_result["summary"]["total"],
        current_passed=test_result["summary"]["passed"],
        baseline=baseline,
        adr_test_files=adr_test_files
    )
    
    # Log details
    if eval_result.ignored_failures:
        logger.info(
            f"Ignoring {len(eval_result.ignored_failures)} pre-existing failures: "
            f"{eval_result.ignored_failures[:5]}..."
        )
    
    if eval_result.passed:
        return ValidationResult(success=True, message=eval_result.summary)
    else:
        return ValidationResult(
            success=False,
            message=eval_result.summary,
            details={
                "regressions": eval_result.regressions,
                "new_test_failures": eval_result.new_test_failures,
                "pre_existing_ignored": eval_result.ignored_failures
            }
        )
```

**Pipeline-Erweiterung:** `src/helix/api/routes_evolution.py`
```python
@router.post("/evolution/projects/{name}/run")
async def run_evolution_pipeline(name: str, auto_integrate: bool = False):
    """Run evolution pipeline with baseline-based validation."""
    
    project = project_manager.get_project(name)
    
    # STEP 1: Capture baseline BEFORE any changes
    logger.info("Capturing test baseline...")
    baseline = await capture_baseline(project.production_path)
    logger.info(
        f"Baseline: {baseline.passed_tests}/{baseline.total_tests} passed, "
        f"{len(baseline.failed_tests)} pre-existing failures"
    )
    
    # STEP 2: Execute phases
    async for event in execute_phases(project):
        yield event
    
    # STEP 3: Deploy to test system
    await deploy_to_test(project)
    
    # STEP 4: Validate with baseline comparison
    validation = await validate_with_baseline(project, baseline)
    
    if validation.success:
        logger.info(validation.message)
        if auto_integrate:
            await integrate_project(project)
    else:
        logger.error(validation.message)
        # Pipeline stops but with detailed breakdown
```

#### Beispiel-Output

**Szenario:** ADR-020 mit dem StrEnum-Problem
```
=== Baseline Capture ===
Commit: 61d0428 (main)
Tests: 453 passed, 3 failed
Pre-existing failures:
  - tests/legacy/test_old_export.py::test_deprecated
  - tests/integration/test_external.py::test_flaky
  - tests/docs/test_reverse_index.py::test_file_status_string_enum

=== After ADR-020 ===
Tests: 509 passed, 4 failed

=== Baseline Comparison ===
Pre-existing (ignored): 3
  - tests/legacy/test_old_export.py::test_deprecated
  - tests/integration/test_external.py::test_flaky  
  - tests/docs/test_reverse_index.py::test_file_status_string_enum

Regressions: 0
New test failures: 1
  - tests/docs/test_skill_selector.py::test_edge_case  ← BLOCKING

❌ Pipeline stopped: 1 blocking failure (new test)
```

vs. wenn der StrEnum-Test der einzige Failure ist:
```
=== Baseline Comparison ===
Pre-existing (ignored): 1
  - tests/docs/test_reverse_index.py::test_file_status_string_enum

Regressions: 0
New test failures: 0

✅ Tests passed: 510/511 (1 pre-existing failure ignored)
→ Proceeding to integration
```

#### Optional: Permanente Ausnahmen

Für Tests die **immer** ignoriert werden sollen (unabhängig von Baseline):

**Datei:** `tests/.permanent_skips` (optional)
```yaml
# Tests die IMMER ignoriert werden - nur für Sonderfälle!
# Normalerweise reicht die automatische Baseline-Erkennung.

tests/integration/test_external_api.py::test_paid_service:
  reason: "Benötigt API-Key der nur in Prod existiert"
  
tests/e2e/test_browser.py::test_selenium:
  reason: "Kein Browser in CI-Environment"
```

Diese werden VOR der Baseline-Analyse entfernt.

### Fix 6: Project Discovery & Initialization

**Problem:** Projekte werden nur erkannt wenn `status.json` existiert, und die erforderliche Verzeichnisstruktur muss manuell erstellt werden.

**Root Cause:** 
- Project Discovery basiert auf Laufzeit-Artifact (`status.json`) statt Definition-Files
- Keine Lazy Initialization von Verzeichnissen und Status

**Datei:** `src/helix/evolution/project_initializer.py`

```python
"""Project discovery and lazy initialization."""

from pathlib import Path
from datetime import datetime
import json
from typing import Optional


class ProjectInitializer:
    """Handles project discovery and automatic initialization."""
    
    DEFINITION_FILES = [
        "phases.yaml",
        "spec.yaml",
    ]
    DEFINITION_PATTERNS = [
        "ADR-*.md",
        "*-adr.md",
    ]
    REQUIRED_DIRS = ["new", "modified", "phases"]
    
    @classmethod
    def is_valid_project(cls, path: Path) -> bool:
        """
        Check if path contains a valid project definition.
        
        A project is valid if ANY definition file exists.
        Does NOT require status.json (that's a runtime artifact).
        """
        # Check exact files
        for filename in cls.DEFINITION_FILES:
            if (path / filename).exists():
                return True
        
        # Check patterns
        for pattern in cls.DEFINITION_PATTERNS:
            if list(path.glob(pattern)):
                return True
        
        return False
    
    @classmethod
    def ensure_structure(cls, path: Path) -> None:
        """
        Ensure all required directories exist.
        Called lazily on first access.
        """
        for dir_name in cls.REQUIRED_DIRS:
            (path / dir_name).mkdir(exist_ok=True)
    
    @classmethod
    def ensure_status_file(cls, path: Path) -> Path:
        """
        Ensure status.json exists with proper defaults.
        Creates it if missing, never overwrites existing.
        """
        status_file = path / "status.json"
        
        if not status_file.exists():
            status = {
                "status": "pending",
                "current_phase": None,
                "phases": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),  # Never None!
                "error": None
            }
            status_file.write_text(json.dumps(status, indent=2))
        
        return status_file
    
    @classmethod
    def initialize_project(cls, path: Path) -> None:
        """
        Full project initialization.
        - Create required directories
        - Create status.json if missing
        - Set proper permissions
        """
        cls.ensure_structure(path)
        cls.ensure_status_file(path)
```

**Integration in ProjectManager:** `src/helix/evolution/project.py`

```python
from helix.evolution.project_initializer import ProjectInitializer

class ProjectManager:
    """Manages evolution projects."""
    
    def get_project(self, name: str) -> Optional[EvolutionProject]:
        """Get project by name with lazy initialization."""
        path = self.projects_dir / name
        
        if not path.exists():
            return None
        
        # Check for valid project definition (not status.json!)
        if not ProjectInitializer.is_valid_project(path):
            return None
        
        # Lazy initialization
        ProjectInitializer.initialize_project(path)
        
        return EvolutionProject(path)
    
    def list_projects(self) -> list[EvolutionProject]:
        """List all valid projects."""
        projects = []
        
        for path in self.projects_dir.iterdir():
            if path.is_dir() and ProjectInitializer.is_valid_project(path):
                ProjectInitializer.initialize_project(path)
                projects.append(EvolutionProject(path))
        
        return projects
```

### Fix 7: File Permission Normalization

**Problem:** Dateien haben inkonsistente Berechtigungen abhängig von umask und Source-Permissions.

**Root Cause:** `shutil.copy2()` preserviert Source-Permissions, User-umask kann restrictiv sein.

**Datei:** `src/helix/evolution/deployer.py` (erweitern)

```python
import stat
from pathlib import Path
import shutil


# Standard permissions for different file types
FILE_PERMISSIONS = {
    ".py": 0o644,
    ".md": 0o644,
    ".yaml": 0o644,
    ".yml": 0o644,
    ".json": 0o644,
    ".txt": 0o644,
    ".sh": 0o755,   # Scripts need execute
    ".bash": 0o755,
}

DEFAULT_FILE_PERMISSION = 0o644
DEFAULT_DIR_PERMISSION = 0o755


def normalize_permissions(file_path: Path) -> None:
    """
    Set standard permissions regardless of umask or source.
    
    Files: 0644 (0755 for scripts)
    Directories: 0755
    """
    if file_path.is_dir():
        file_path.chmod(DEFAULT_DIR_PERMISSION)
    else:
        suffix = file_path.suffix.lower()
        mode = FILE_PERMISSIONS.get(suffix, DEFAULT_FILE_PERMISSION)
        file_path.chmod(mode)


def copy_with_permissions(src: Path, dst: Path) -> None:
    """Copy file and normalize permissions."""
    shutil.copy2(src, dst)
    normalize_permissions(dst)


def deploy_directory(src_dir: Path, dst_dir: Path) -> int:
    """
    Deploy all files from src to dst with normalized permissions.
    
    Returns: Number of files copied
    """
    count = 0
    
    for src_file in src_dir.rglob("*"):
        if src_file.is_file():
            rel_path = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel_path
            
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            normalize_permissions(dst_file.parent)
            
            copy_with_permissions(src_file, dst_file)
            count += 1
    
    return count
```

### Fix 8: Global Exception Handling & Logging

**Problem:** API gibt nur "Internal Server Error" zurück, keine Details, keine Logs.

**Root Cause:** Keine globale Exception-Handler, Logging nicht konfiguriert.

**Datei:** `src/helix/api/main.py` (erweitern)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import logging
import os
from pathlib import Path

# Configure logging
LOG_DIR = Path("/home/aiuser01/helix-v4/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "api.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(title="HELIX API")

# Environment check for debug mode
DEBUG = os.environ.get("HELIX_DEBUG", "false").lower() == "true"


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Log all unhandled exceptions with full traceback.
    Returns structured error response.
    """
    # Log full traceback
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        exc_info=exc
    )
    
    # Build response
    error_response = {
        "error": "Internal Server Error",
        "type": type(exc).__name__,
        "message": str(exc),
        "path": str(request.url.path),
    }
    
    # Include traceback in debug mode
    if DEBUG:
        error_response["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging."""
    logger.debug(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"Response: {response.status_code}")
    return response
```

### Fix 9: None-Safe Sorting

**Problem:** `projects.sort()` crasht wenn `updated_at` None ist.

**Root Cause:** `.get(key, default)` gibt None zurück wenn Wert explizit None ist (nicht nur wenn Key fehlt).

**Datei:** `src/helix/api/routes_evolution.py` (erweitern)

```python
def get_sort_key(project: EvolutionProject) -> str:
    """
    Get sort key for project, handling None values.
    
    Uses 'or' pattern: value or default
    - If value is None -> returns default
    - If value is empty string -> returns default
    - Otherwise returns value
    """
    status_data = project.get_status_data()
    
    # The 'or' pattern handles both missing keys AND explicit None
    updated_at = status_data.get("updated_at") or ""
    
    return updated_at


@router.get("/evolution/projects")
async def list_evolution_projects():
    """List all evolution projects, sorted by last update."""
    projects = project_manager.list_projects()
    
    # Sort with None-safe key function
    projects.sort(key=get_sort_key, reverse=True)
    
    return {
        "projects": [p.to_dict() for p in projects],
        "count": len(projects)
    }
```

**Alternative (defensive):** Status-Initialisierung mit guaranteed non-None:

```python
# In ProjectInitializer.ensure_status_file()
status = {
    "status": "pending",
    "current_phase": None,
    "phases": {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),  # NEVER None!
    "error": None
}
```

Damit wird `updated_at` nie None sein, da es bei der Initialisierung immer gesetzt wird.



---



---

## Konsequenzen Fix 5

### Vorteile

1. **Keine manuelle Pflege:** Baseline wird automatisch erfasst
2. **Fair:** Nur NEUE Probleme blockieren, nicht geerbte
3. **Transparent:** Klare Kategorisierung im Output
4. **Realistisch:** Alte Tech Debt blockiert nicht neue Features

### Nachteile

1. **Baseline-Zeit:** Extra pytest-Run am Anfang (~30s)
2. **Speicher:** Baseline muss während Pipeline gehalten werden

### Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| Baseline veraltet bei langer Pipeline | Baseline gilt für diesen Run, nächster Run = neue Baseline |
| Flaky Tests mal in Baseline, mal nicht | Flaky Tests sollten generell gefixt werden |
| Baseline-Capture schlägt fehl | Fallback: Threshold-basiert (95% müssen passen) |


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

## Akzeptanzkriterien Fix 5

- [ ] Baseline wird automatisch vor Pipeline-Start erfasst
- [ ] Baseline enthält: commit_sha, timestamp, failed_tests Set
- [ ] Pre-existing failures werden ignoriert (nicht blocking)
- [ ] Regressions (bestehende Tests neu kaputt) sind blocking
- [ ] Neue Test-Failures (aus ADR files.create) sind blocking
- [ ] Pipeline-Output zeigt klare Kategorisierung
- [ ] Test: 510/511 passed mit 1 pre-existing → ✅ Integration
- [ ] Test: 510/511 passed mit 1 regression → ❌ Blocked
- [ ] Test: Neuer Test aus ADR failt → ❌ Blocked
- [ ] Optional: `.permanent_skips` für Sonderfälle

### Fix 6: Project Discovery

- [ ] Projekte werden erkannt wenn `phases.yaml` existiert
- [ ] Projekte werden erkannt wenn `ADR-*.md` existiert  
- [ ] `status.json` wird automatisch erstellt bei erstem Zugriff
- [ ] Verzeichnisse `new/`, `modified/`, `phases/` werden automatisch erstellt
- [ ] Test: Neues Projekt ohne status.json wird korrekt erkannt

### Fix 7: Permission Normalization

- [ ] Alle Dateien haben Berechtigungen 0644 nach Deploy
- [ ] Script-Dateien (.sh, .bash) haben 0755
- [ ] Verzeichnisse haben 0755
- [ ] `copy_with_permissions()` wird in allen Deployern verwendet
- [ ] Test: Datei mit 0600 Source wird zu 0644 nach Deploy

### Fix 8: Global Exception Handler

- [ ] Alle unhandled Exceptions werden geloggt (in `logs/api.log`)
- [ ] API gibt strukturierte Fehlerantwort mit `type`, `message`, `path`
- [ ] Traceback wird in Debug-Mode inkludiert (`HELIX_DEBUG=true`)
- [ ] Request-Logging für alle Endpoints
- [ ] Test: Exception in Endpoint → strukturierte 500-Response + Log

### Fix 9: None-Safe Sorting

- [ ] `projects.sort()` crasht nicht bei `updated_at: null`
- [ ] Projekte mit None-Werten werden am Ende sortiert
- [ ] `status.json` wird immer mit non-None `updated_at` initialisiert
- [ ] Test: Projekt mit `"updated_at": null` → kein Crash

### Integration

- [ ] Alle 9 Fixes funktionieren zusammen
- [ ] Keine Regression in bestehenden Pipelines
- [ ] Pipeline-Ausführung ist stabiler als zuvor

---

## Konsequenzen

### Vorteile

1. **Höhere Zuverlässigkeit:** Transiente Fehler führen nicht mehr zu sofortigem Abbruch
2. **Bessere Observability:** Phasen-Status ist via API sichtbar
3. **Breitere Kompatibilität:** Python 3.10 wird unterstützt
4. **Weniger manuelle Intervention:** Automatische Retries reduzieren Wartungsaufwand
5. **Faire Test-Bewertung:** Nur neue Failures blockieren, pre-existing werden ignoriert
6. **Automatische Initialisierung:** Projekte funktionieren ohne manuelle Setup-Schritte
7. **Konsistente Berechtigungen:** Keine Permission-Issues bei File-Operationen
8. **Besseres Debugging:** Strukturierte Fehler mit Logs statt generischer 500-Errors
9. **Robuste API:** None-Werte verursachen keine Crashes mehr

### Nachteile

1. **Komplexität:** Retry-Logik muss korrekt implementiert werden
2. **Latenz:** Retries verzögern die Gesamt-Ausführung bei Fehlern
3. **Baseline-Overhead:** Extra pytest-Run am Anfang (~30s)
4. **Lazy Init:** Erste Projektabfrage kann langsamer sein (Verzeichnisse erstellen)

### Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| Endlos-Retries | Max 3 Retries fest konfiguriert |
| Falsche Error-Kategorisierung | Pattern-Liste wartbar, einfach erweiterbar |
| Race Conditions bei JobState | JobState-Updates sind thread-safe |
| Baseline veraltet bei langer Pipeline | Baseline gilt pro Run, nächster Run = neue Baseline |
| Flaky Tests mal in Baseline, mal nicht | Flaky Tests sollten generell gefixt werden |
| Permission-Änderungen brechen etwas | Standard 0644/0755 ist universell kompatibel |
| Debug-Mode leakt sensible Daten | Nur lokal aktivieren via Env-Variable |

---

## Abhängigkeiten

- **ADR-011:** Post-Phase Verification - Integriert mit Retry
- **ADR-025:** Sub-Agent Verifikation - Retry vor Verification

---

## Rollout Plan

### Welle 1: Quick Fixes (sofort, breaking risk: low)
1. **Fix 3:** StrEnum Backport
2. **Fix 7:** Permission Normalization  
3. **Fix 9:** None-Safe Sorting

### Welle 2: Infrastructure (nach Tests)
4. **Fix 1:** pytest PATH Fix
5. **Fix 6:** Project Discovery & Initialization
6. **Fix 8:** Global Exception Handler

### Welle 3: Pipeline Logic (nach Integration Tests)
7. **Fix 2:** Job Status API Sync
8. **Fix 4:** Retry Handler
9. **Fix 5:** Baseline-basierte Test-Bewertung

---

## Referenzen

- [ADR-011: Post-Phase Verification](011-post-phase-verification.md)
- [ADR-025: Sub-Agent Verifikation](025-sub-agent-verification.md)
- [Python StrEnum Documentation](https://docs.python.org/3/library/enum.html#enum.StrEnum)
