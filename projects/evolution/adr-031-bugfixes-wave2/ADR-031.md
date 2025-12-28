---
adr_id: "031"
title: "Pipeline Bug Fixes Wave 2"
status: Proposed

project_type: helix_internal
component_type: PROCESS
classification: FIX
change_scope: minor

files:
  create:
    - src/helix/evolution/status_sync.py
    - src/helix/evolution/file_permissions.py
    - tests/evolution/test_status_sync.py
    - tests/evolution/test_file_permissions.py
  modify:
    - src/helix/api/streaming.py
    - src/helix/api/routes_evolution.py
    - src/helix/evolution/project.py
    - src/helix/evolution/deployer.py
    - src/helix/evolution/validator.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-030  # Pipeline Reliability - Wave 1
---

# ADR-031: Pipeline Bug Fixes Wave 2

## Status

📋 Proposed

---

## Kontext

### Hintergrund

ADR-030 wurde am 2025-12-28 via Evolution Pipeline implementiert. Während des
**Dogfooding** wurden 4 zusätzliche Bugs entdeckt, die nicht in ADR-030 abgedeckt waren.

Zusätzlich wurden 4 Fixes aus ADR-030 (Fixes 6-9) nicht implementiert, da sie
außerhalb des Scopes der automatisch generierten Phasen lagen.

### Entdeckte Bugs (Dogfooding Session)

#### Bug 1: Status.json nicht synchronisiert

**Symptom:**
```
Stream: phase_complete für 6/6 Phasen ✅
status.json: 5/6 Phasen "pending" ❌
```

**Root Cause:**
Zwei parallele, nicht-synchronisierte Status-Tracking-Systeme:
1. **In-Memory JobState** - Wird von API `/helix/jobs/{id}` gelesen
2. **On-Disk status.json** - Wird von Projekt-Restart gelesen

`streaming.py` sendet SSE Events, aber aktualisiert weder JobState noch status.json.

**Code-Beweis:**
```python
# src/helix/api/streaming.py - Zeile ~180
async def stream_phase_execution(...):
    yield StreamEvent(type="phase_complete", data=...)
    # FEHLT: job_state.update_phase(phase_info)
    # FEHLT: project.update_status(phase_id, "completed")
```

#### Bug 2: Datei-Berechtigungen 0600

**Symptom:**
```bash
$ ls -la ADR-030.md
-rw------- 1 aiuser01 aiuser01 26476 Dec 28 ADR-030.md
```

**Root Cause:**
```bash
$ umask
0077  # Restrictive umask
```

Claude Code's str_replace_editor erstellt Dateien mit User-umask.
`shutil.copy2()` preserviert Source-Permissions.

#### Bug 3: MCP Timeout bei langen Streams

**Symptom:**
```
McpError: MCP error -32001: Request timed out
```

**Root Cause:**
SSH-MCP Default-Timeout: 300 Sekunden (5 Min).
Evolution Pipeline kann >10 Min dauern.

#### Bug 4: output/ vs modified/new/ Directory Mismatch

**Symptom:**
```
Verification failed: file in modified/ but verifier looks in output/
```

**Root Cause:**
```yaml
# phases.yaml
output:
  - "modified/src/helix/phase_status.py"  # ADR-030 Convention

# Aber Verifier sucht in:
phases/{id}/output/  # Alte Convention
```

### Nicht-implementierte Fixes aus ADR-030

| Fix | Beschreibung |
|-----|--------------|
| Fix 6 | Project Discovery via Definition-Files statt status.json |
| Fix 7 | Permission Normalization im Deployer |
| Fix 8 | Global Exception Handler mit strukturiertem Logging |
| Fix 9 | None-Safe Sorting bei API Responses |

---

## Entscheidung

### Wir entscheiden uns für:

Eine fokussierte Bug-Fix-Sammlung die alle Dogfooding-Bugs und die restlichen
ADR-030 Fixes in einer koordinierten Wave 2 implementiert.

### Diese Entscheidung beinhaltet:

1. **Status Sync:** Einheitliches Status-Tracking mit automatischer Persistenz
2. **Permission Fix:** Automatische Permission-Normalisierung nach File-Operations
3. **Timeout Handling:** Polling-basiertes Status-API als Alternative zu langen Streams
4. **Directory Standard:** Eindeutige output/ Convention mit Verifier-Anpassung
5. **ADR-030 Restfixes:** Fixes 6-9 vollständig implementieren

### Warum diese Lösung?

- Alle Bugs sind **root-caused** und haben klare Fixes
- Fixes sind **isoliert** und unabhängig testbar
- Kein Breaking Change an bestehenden APIs
- **Dogfooding-validiert** - Wir wissen was wirklich kaputt ist

---

## Implementation

### Fix 1: Status Synchronisation

**Neues Modul:** `src/helix/evolution/status_sync.py`

```python
"""Unified status synchronization for Evolution Pipeline.

Ensures JobState (in-memory) and status.json (on-disk) are always in sync.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhaseStatus:
    """Status of a single phase."""
    
    phase_id: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class StatusSynchronizer:
    """Keeps JobState and status.json in sync.
    
    Single source of truth: status.json
    JobState is derived from status.json on load.
    
    Usage:
        sync = StatusSynchronizer(project_path)
        sync.start_phase("phase-1")
        sync.complete_phase("phase-1")
        sync.fail_phase("phase-1", "Error message")
    """
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.status_file = project_path / "status.json"
        self._status_data: dict = self._load_status()
    
    def _load_status(self) -> dict:
        """Load status from disk."""
        if self.status_file.exists():
            return json.loads(self.status_file.read_text())
        return {
            "status": "pending",
            "current_phase": None,
            "phases": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def _save_status(self) -> None:
        """Save status to disk with atomic write."""
        self._status_data["updated_at"] = datetime.now().isoformat()
        
        # Atomic write: write to temp, then rename
        temp_file = self.status_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(self._status_data, indent=2))
        temp_file.rename(self.status_file)
        
        # Normalize permissions
        self.status_file.chmod(0o644)
        
        logger.debug(f"Status saved: {self._status_data['status']}")
    
    def start_phase(self, phase_id: str) -> None:
        """Mark phase as running."""
        self._status_data["status"] = "developing"
        self._status_data["current_phase"] = phase_id
        self._status_data["phases"][phase_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat()
        }
        self._save_status()
        logger.info(f"Phase started: {phase_id}")
    
    def complete_phase(self, phase_id: str) -> None:
        """Mark phase as completed."""
        if phase_id in self._status_data["phases"]:
            self._status_data["phases"][phase_id]["status"] = "completed"
            self._status_data["phases"][phase_id]["completed_at"] = datetime.now().isoformat()
        self._status_data["current_phase"] = None
        self._save_status()
        logger.info(f"Phase completed: {phase_id}")
    
    def fail_phase(self, phase_id: str, error: str) -> None:
        """Mark phase as failed."""
        if phase_id in self._status_data["phases"]:
            self._status_data["phases"][phase_id]["status"] = "failed"
            self._status_data["phases"][phase_id]["error"] = error
        self._status_data["current_phase"] = None
        self._status_data["status"] = "failed"
        self._status_data["error"] = error
        self._save_status()
        logger.error(f"Phase failed: {phase_id} - {error}")
    
    def mark_ready(self) -> None:
        """Mark project as ready for validation/integration."""
        self._status_data["status"] = "ready"
        self._status_data["current_phase"] = None
        self._save_status()
    
    def get_status(self) -> dict:
        """Get current status (always reads from disk for consistency)."""
        self._status_data = self._load_status()
        return self._status_data
```

**Integration in streaming.py:**

```python
# src/helix/api/streaming.py

from helix.evolution.status_sync import StatusSynchronizer

async def stream_phase_execution(
    project: EvolutionProject,
    phases: list[PhaseConfig],
    runner: ClaudeRunner
) -> AsyncIterator[StreamEvent]:
    """Execute phases with synchronized status tracking."""
    
    sync = StatusSynchronizer(project.path)
    
    for phase in phases:
        # START: Update status BEFORE execution
        sync.start_phase(phase.id)
        yield StreamEvent(type="phase_start", phase_id=phase.id)
        
        try:
            result = await runner.run_phase_streaming(project.path, phase)
            
            # COMPLETE: Update status AFTER success
            sync.complete_phase(phase.id)
            yield StreamEvent(type="phase_complete", phase_id=phase.id)
            
        except Exception as e:
            # FAIL: Update status on error
            sync.fail_phase(phase.id, str(e))
            yield StreamEvent(type="phase_failed", phase_id=phase.id, error=str(e))
            raise
    
    # All phases done
    sync.mark_ready()
    yield StreamEvent(type="pipeline_ready")
```

### Fix 2: Permission Normalization

**Neues Modul:** `src/helix/evolution/file_permissions.py`

```python
"""File permission normalization for Evolution Pipeline.

Ensures consistent permissions regardless of umask or source file permissions.
"""

from pathlib import Path
import stat
import logging

logger = logging.getLogger(__name__)

# Standard permissions
PERMISSION_FILE = 0o644      # rw-r--r--
PERMISSION_SCRIPT = 0o755    # rwxr-xr-x
PERMISSION_DIR = 0o755       # rwxr-xr-x

# File extensions that need execute permission
EXECUTABLE_EXTENSIONS = {".sh", ".bash", ".py"}  # .py nur wenn shebang


def normalize_permissions(path: Path) -> None:
    """
    Normalize file/directory permissions to standard values.
    
    - Directories: 0755
    - Scripts (.sh, .bash): 0755
    - All other files: 0644
    
    Args:
        path: File or directory to normalize
    """
    if path.is_dir():
        path.chmod(PERMISSION_DIR)
        logger.debug(f"Dir permissions: {path} → 0755")
    else:
        suffix = path.suffix.lower()
        
        # Check for shebang in .py files
        if suffix == ".py":
            try:
                first_line = path.read_text().split("\n")[0]
                if first_line.startswith("#!"):
                    path.chmod(PERMISSION_SCRIPT)
                    logger.debug(f"Script permissions: {path} → 0755")
                    return
            except Exception:
                pass
        
        if suffix in EXECUTABLE_EXTENSIONS - {".py"}:
            path.chmod(PERMISSION_SCRIPT)
            logger.debug(f"Script permissions: {path} → 0755")
        else:
            path.chmod(PERMISSION_FILE)
            logger.debug(f"File permissions: {path} → 0644")


def normalize_directory_recursive(directory: Path) -> int:
    """
    Normalize permissions for all files in a directory tree.
    
    Returns:
        Number of files/directories normalized
    """
    count = 0
    
    for path in directory.rglob("*"):
        normalize_permissions(path)
        count += 1
    
    # Also normalize the root directory
    normalize_permissions(directory)
    count += 1
    
    return count


def copy_with_permissions(src: Path, dst: Path) -> None:
    """
    Copy file and normalize permissions.
    
    Use instead of shutil.copy2() to ensure consistent permissions.
    """
    import shutil
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    normalize_permissions(dst)
    normalize_permissions(dst.parent)
```

**Integration in deployer.py:**

```python
# src/helix/evolution/deployer.py

from helix.evolution.file_permissions import copy_with_permissions, normalize_directory_recursive

class Deployer:
    """Deploys evolution project outputs to target locations."""
    
    def deploy_to_test(self, project: EvolutionProject) -> DeployResult:
        """Deploy project to test system with normalized permissions."""
        
        files_deployed = 0
        
        # Deploy new files
        for src_file in (project.path / "new").rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(project.path / "new")
                dst_file = self.test_system / rel_path
                
                copy_with_permissions(src_file, dst_file)
                files_deployed += 1
        
        # Deploy modified files
        for src_file in (project.path / "modified").rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(project.path / "modified")
                dst_file = self.test_system / rel_path
                
                copy_with_permissions(src_file, dst_file)
                files_deployed += 1
        
        # Final permission sweep
        normalize_directory_recursive(self.test_system)
        
        return DeployResult(success=True, files_deployed=files_deployed)
```

### Fix 3: Polling-basiertes Status API

**Erweiterung:** `src/helix/api/routes_evolution.py`

```python
@router.get("/evolution/projects/{name}/status")
async def get_project_status(name: str) -> dict:
    """
    Get current project status (polling-friendly).
    
    Use this endpoint for status polling instead of long SSE streams.
    Recommended polling interval: 5 seconds.
    
    Returns:
        status: Project status (pending, developing, ready, integrated, failed)
        current_phase: Currently executing phase (if any)
        phases: Dict of phase_id -> phase_status
        progress: Completion percentage (0-100)
    """
    project = project_manager.get_project(name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    status_data = project.get_status_data()
    
    # Calculate progress
    phases = status_data.get("phases", {})
    total = len(phases)
    completed = sum(1 for p in phases.values() if p.get("status") == "completed")
    progress = int((completed / total * 100) if total > 0 else 0)
    
    return {
        "status": status_data.get("status", "unknown"),
        "current_phase": status_data.get("current_phase"),
        "phases": phases,
        "progress": progress,
        "updated_at": status_data.get("updated_at"),
        "error": status_data.get("error")
    }


@router.get("/evolution/projects/{name}/logs/{phase_id}")
async def get_phase_logs(name: str, phase_id: str, tail: int = 100) -> dict:
    """
    Get logs for a specific phase.
    
    Use for debugging when a phase fails.
    
    Args:
        name: Project name
        phase_id: Phase ID
        tail: Number of lines from end (default 100)
    
    Returns:
        logs: List of log lines
        log_file: Path to full log file
    """
    project = project_manager.get_project(name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    log_file = project.path / "phases" / phase_id / "output" / "claude.log"
    
    if not log_file.exists():
        return {"logs": [], "log_file": None}
    
    lines = log_file.read_text().splitlines()
    return {
        "logs": lines[-tail:],
        "log_file": str(log_file)
    }
```

### Fix 4: Output Directory Standardization

**Anpassung:** `src/helix/evolution/validator.py`

```python
class OutputValidator:
    """Validates phase outputs with flexible directory support.
    
    Supports three output conventions:
    1. output/         - Simple flat output
    2. new/            - New files (ADR-030 style)
    3. modified/       - Modified files (ADR-030 style)
    """
    
    OUTPUT_DIRS = ["output", "new", "modified"]
    
    def find_output_files(self, phase_path: Path) -> list[Path]:
        """
        Find all output files in any of the supported directories.
        
        Returns:
            List of output file paths
        """
        files = []
        
        for dir_name in self.OUTPUT_DIRS:
            dir_path = phase_path / dir_name
            if dir_path.exists():
                files.extend(f for f in dir_path.rglob("*") if f.is_file())
        
        return files
    
    def validate_expected_outputs(
        self, 
        phase_path: Path, 
        expected: list[str]
    ) -> ValidationResult:
        """
        Validate that expected output files exist.
        
        Args:
            phase_path: Path to phase directory
            expected: List of expected file patterns from phases.yaml
        
        Returns:
            ValidationResult with found/missing files
        """
        found = []
        missing = []
        
        for pattern in expected:
            # Pattern can be "modified/src/..." or "new/tests/..." or "src/..."
            
            # Try each output directory
            file_found = False
            for dir_name in self.OUTPUT_DIRS:
                # Try pattern as-is (if it includes directory prefix)
                full_path = phase_path / pattern
                if full_path.exists():
                    found.append(str(full_path))
                    file_found = True
                    break
                
                # Try pattern with output directory prefix
                # e.g., "src/helix/foo.py" -> "output/src/helix/foo.py"
                if not pattern.startswith(tuple(self.OUTPUT_DIRS)):
                    prefixed_path = phase_path / dir_name / pattern
                    if prefixed_path.exists():
                        found.append(str(prefixed_path))
                        file_found = True
                        break
            
            if not file_found:
                missing.append(pattern)
        
        return ValidationResult(
            success=len(missing) == 0,
            found_files=found,
            missing_files=missing,
            message=f"Found {len(found)}/{len(expected)} expected files"
        )
```

### Fix 5-8: ADR-030 Restfixes

Die restlichen Fixes aus ADR-030 (Fixes 6-9) werden hier nicht erneut dokumentiert,
da sie bereits in ADR-030 vollständig spezifiziert sind. Sie werden in separaten
Phasen implementiert:

- **Fix 6:** Project Discovery → `src/helix/evolution/project_initializer.py`
- **Fix 7:** Permission Normalization → In diesem ADR als Fix 2 implementiert
- **Fix 8:** Global Exception Handler → `src/helix/api/main.py`
- **Fix 9:** None-Safe Sorting → `src/helix/api/routes_evolution.py`

---

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | StatusSynchronizer, FilePermissions Module |
| Code-Docstrings | Alle neuen Funktionen dokumentiert |
| `docs/analysis/adr-030-dogfooding-results.md` | Root Cause Analyse |

---

## Akzeptanzkriterien

### Fix 1: Status Synchronisation

- [ ] `status.json` wird bei phase_start aktualisiert
- [ ] `status.json` wird bei phase_complete aktualisiert
- [ ] `status.json` wird bei phase_failed aktualisiert
- [ ] Atomic writes (temp file + rename) für Crash-Safety
- [ ] Status kann mit `GET /evolution/projects/{name}/status` abgefragt werden
- [ ] Test: Pipeline stoppen → Restart → Status korrekt geladen

### Fix 2: Permission Normalization

- [ ] Alle Dateien haben 0644 nach Deploy
- [ ] Script-Dateien (.sh, .bash) haben 0755
- [ ] Dateien mit Shebang haben 0755
- [ ] Verzeichnisse haben 0755
- [ ] `copy_with_permissions()` wird überall verwendet
- [ ] Test: Datei mit 0600 → nach copy 0644

### Fix 3: Polling Status API

- [ ] `GET /evolution/projects/{name}/status` existiert
- [ ] Response enthält `progress` (0-100%)
- [ ] Response enthält `current_phase`
- [ ] Response enthält `phases` mit Status pro Phase
- [ ] `GET /evolution/projects/{name}/logs/{phase_id}` existiert
- [ ] Test: Polling während Pipeline-Lauf zeigt korrekten Fortschritt

### Fix 4: Output Directory Standard

- [ ] Validator findet Dateien in `output/`
- [ ] Validator findet Dateien in `new/`
- [ ] Validator findet Dateien in `modified/`
- [ ] Pattern-Matching funktioniert mit und ohne Prefix
- [ ] Test: Phase mit `modified/src/...` Output wird validiert

### Integration

- [ ] Alle 4 neuen Fixes funktionieren zusammen
- [ ] Keine Regression in bestehenden Tests
- [ ] ADR-030 Dogfooding-Bugs sind behoben

---

## Konsequenzen

### Vorteile

1. **Zuverlässige Status-Persistenz:** Pipeline kann jederzeit unterbrochen und fortgesetzt werden
2. **Konsistente Berechtigungen:** Keine Permission-Issues mehr bei File-Operations
3. **Robustes Polling:** Keine Timeouts bei langen Pipelines
4. **Flexible Output-Struktur:** Unterstützt alte und neue Conventions

### Nachteile

1. **Zusätzliche Disk I/O:** Status wird bei jeder Phase-Änderung geschrieben
2. **Polling-Overhead:** Clients müssen regelmäßig pollen statt Events zu empfangen

### Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| Atomic write schlägt fehl | Try/except mit Fallback auf direktes Schreiben |
| Permission-Änderung bricht etwas | Standard 0644/0755 ist universell kompatibel |
| Zu häufiges Polling | Empfohlenes Intervall: 5 Sekunden |

---

## Abhängigkeiten

- **ADR-030:** Pipeline Reliability Wave 1 - Voraussetzung

---

## Rollout Plan

1. **Phase 1:** Status Sync + Permissions (breaking risk: low)
2. **Phase 2:** Polling API + Output Validator (breaking risk: low)
3. **Phase 3:** Integration Tests
4. **Phase 4:** Dogfooding mit nächstem ADR

---

## Referenzen

- [ADR-030: Evolution Pipeline Reliability](030-evolution-pipeline-reliability.md)
- [docs/analysis/adr-030-dogfooding-results.md](../docs/analysis/adr-030-dogfooding-results.md)
