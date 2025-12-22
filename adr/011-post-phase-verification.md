---
adr_id: "011"
title: "Post-Phase Verification System"
status: Implemented

component_type: PROCESS
classification: NEW
change_scope: major

files:
  create:
    - src/helix/evolution/verification.py
    - src/helix/tools/verify_phase.py
    - tests/evolution/test_verification.py
  modify:
    - src/helix/api/streaming.py
    - templates/developer/_base.md
    - templates/developer/python.md
  docs:
    - docs/ARCHITECTURE-EVOLUTION.md
    - CLAUDE.md

depends_on:
  - "012"
---

# ADR-011: Post-Phase Verification System

## Status
📋 Proposed

---

## Kontext

### Das Problem

Im Evolution Workflow fehlt eine kritische Komponente: **Nach jeder Claude Code Phase wird nicht geprüft ob die erwarteten Dateien tatsächlich erstellt wurden.**

#### Aktueller Zustand (`streaming.py:145-183`)

```
Phase X läuft (Claude Code)
    ↓
Exit Code = 0?
    ↓
✅ Phase als "completed" markiert
    ↓
Weiter zu Phase X+1
```

Der Code in `streaming.py` prüft nur:
```python
result = await runner.run_phase_streaming(...)
status = PhaseStatus.COMPLETED if result.success else PhaseStatus.FAILED
```

**Was fehlt:** Niemand prüft ob Claude die Dateien wirklich erstellt hat die in `phases.yaml` unter `output:` definiert sind oder im ADR unter `files.create`.

#### Konkretes Problem aus der Praxis

```yaml
# phases.yaml
- id: "2"
  name: "ADR Parser"
  output:
    - new/src/helix/adr/parser.py
    - new/tests/adr/test_parser.py
```

Claude Code beendete mit Exit 0, aber:
- Manchmal schrieb Claude nach `output/` statt `new/`
- Manchmal fehlten Tests komplett
- Manchmal hatte der Code Syntax-Fehler

### ADR-001: ADR als Single Source of Truth

Mit ADR-001 haben wir beschlossen dass ADRs die Single Source of Truth sind. Jedes ADR enthält bereits:

```yaml
files:
  create:
    - src/helix/module.py
    - tests/test_module.py
  modify:
    - src/helix/__init__.py
```

Diese Information existiert - sie wird nur nicht zur Verification genutzt!

### Das ADR-System ist bereit

Das existierende ADR-System (`helix.adr.parser`) kann Files bereits extrahieren:

```python
from helix.adr import ADRParser

parser = ADRParser()
adr = parser.parse_file(Path("ADR-feature.md"))

adr.metadata.files.create   # ["src/module.py", ...]
adr.metadata.files.modify   # ["src/__init__.py", ...]
```

---

## Entscheidung

**Wir implementieren ein Hybrid-System für Post-Phase Verification:**

### 1. Tool für Claude (Self-Verification)

Claude erhält ein Tool `verify_phase_output` das vor Beendigung aufgerufen werden soll:

```python
# Claude kann aufrufen:
verify_phase_output(
    expected_files=["new/src/module.py", "new/tests/test_module.py"]
)
# → Returns: {"success": True, "missing": [], "syntax_errors": []}
```

**Vorteile:**
- Schnell (keine neue Claude-Session)
- Kostengünstig
- Claude hat den Kontext und kann selbst korrigieren
- Sofortiges Feedback

**Instruktion in Template:**
```markdown
## Before You Finish

IMPORTANT: Before ending your session, run the verification tool:

    verify_phase_output

This checks that all expected files exist and have valid syntax.
If verification fails, fix the issues before completing.
```

### 2. Externes Safety Net (Post-Phase Check)

Nach jedem Claude Run prüft `streaming.py` automatisch:

```
Phase X beendet (Exit 0)
    ↓
Verification Check:
  - Existieren alle expected files?
  - Syntax-Check (Python AST)
    ↓
❌ Fehler gefunden?
    ↓
Retry (max 2x) mit Fehlerkontext
    ↓
✅ Alles ok → Weiter zu Phase X+1
```

**Max 2 Retries** um Endlos-Loops zu vermeiden. Danach: Phase als FAILED markieren.

### Warum beides?

| Szenario | Self-Verification | External Safety Net |
|----------|-------------------|---------------------|
| Claude vergisst Tool aufzurufen | ❌ | ✅ |
| Schnelles Feedback während Arbeit | ✅ | ❌ |
| Korrektur mit vollem Kontext | ✅ | ⚠️ (reduziert) |
| Garantierte Prüfung | ❌ | ✅ |

→ Kombination ist optimal: Claude versucht selbst zu verifizieren, externes System ist das Safety Net.

---

## Implementation

### 1. `src/helix/evolution/verification.py`

Zentrale Verification-Logik:

```python
"""Post-phase verification for HELIX Evolution projects."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import ast

from helix.adr import ADRParser


@dataclass
class VerificationResult:
    """Result of a phase output verification."""
    success: bool
    missing_files: list[str] = field(default_factory=list)
    syntax_errors: dict[str, str] = field(default_factory=dict)
    found_files: list[str] = field(default_factory=list)
    message: str = ""


class PhaseVerifier:
    """Verify phase outputs against ADR expectations."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.adr = self._load_adr()

    def _load_adr(self) -> Optional["ADRDocument"]:
        """Load ADR from project directory."""
        parser = ADRParser()

        # Find ADR file (ADR-*.md)
        adr_files = list(self.project_path.glob("ADR-*.md"))
        if not adr_files:
            return None

        return parser.parse_file(adr_files[0])

    def verify_phase_output(
        self,
        phase_id: str,
        phase_dir: Path,
        expected_files: list[str] | None = None,
    ) -> VerificationResult:
        """Verify that a phase produced expected outputs.

        Args:
            phase_id: ID of the phase
            phase_dir: Directory where phase ran
            expected_files: Override expected files (from phases.yaml)

        Returns:
            VerificationResult with details
        """
        # Get expected files from ADR or parameter
        if expected_files is None and self.adr:
            expected_files = self.adr.metadata.files.create

        if not expected_files:
            return VerificationResult(
                success=True,
                message="No expected files defined"
            )

        missing = []
        found = []
        syntax_errors = {}

        for file_path in expected_files:
            # Check multiple candidate locations
            candidates = [
                phase_dir / "output" / file_path,
                phase_dir / file_path,
                self.project_path / "new" / file_path,
                self.project_path / file_path,
            ]

            found_path = None
            for candidate in candidates:
                if candidate.exists():
                    found_path = candidate
                    break

            if found_path:
                found.append(str(found_path))

                # Syntax check for Python files
                if found_path.suffix == ".py":
                    error = self._check_python_syntax(found_path)
                    if error:
                        syntax_errors[str(found_path)] = error
            else:
                missing.append(file_path)

        success = len(missing) == 0 and len(syntax_errors) == 0

        message = f"Found {len(found)}/{len(expected_files)} files"
        if missing:
            message += f", missing: {missing}"
        if syntax_errors:
            message += f", syntax errors in {len(syntax_errors)} files"

        return VerificationResult(
            success=success,
            missing_files=missing,
            syntax_errors=syntax_errors,
            found_files=found,
            message=message,
        )

    def _check_python_syntax(self, file_path: Path) -> str | None:
        """Check Python file syntax using AST.

        Returns:
            Error message if syntax error, None if valid
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return str(e)

    def format_retry_prompt(self, result: VerificationResult) -> str:
        """Format a prompt for Claude to fix verification errors.

        Args:
            result: Failed verification result

        Returns:
            Prompt text to send to Claude
        """
        lines = [
            "# Verification Failed - Please Fix",
            "",
            "The phase verification found issues that need to be fixed:",
            "",
        ]

        if result.missing_files:
            lines.append("## Missing Files")
            lines.append("")
            for f in result.missing_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if result.syntax_errors:
            lines.append("## Syntax Errors")
            lines.append("")
            for path, error in result.syntax_errors.items():
                lines.append(f"- `{path}`: {error}")
            lines.append("")

        lines.append("Please create/fix these files and run verification again.")

        return "\n".join(lines)
```

### 2. `src/helix/tools/verify_phase.py`

Tool für Claude zum Selbst-Aufruf:

```python
"""Verification tool for Claude to check phase output."""

import json
from pathlib import Path
from helix.evolution.verification import PhaseVerifier, VerificationResult


def verify_phase_output(
    expected_files: list[str] | None = None,
    phase_dir: str = ".",
) -> dict:
    """Verify that expected phase outputs exist.

    Call this tool before ending your session to ensure all
    expected files have been created.

    Args:
        expected_files: List of expected file paths (optional,
            defaults to files from ADR)
        phase_dir: Phase working directory (default: current)

    Returns:
        Dict with verification results:
        - success: bool
        - missing: list of missing files
        - syntax_errors: dict of file -> error
        - message: human-readable summary

    Example:
        >>> verify_phase_output()
        {"success": True, "missing": [], "message": "All 3 files found"}

        >>> verify_phase_output(expected_files=["src/module.py"])
        {"success": False, "missing": ["src/module.py"], ...}
    """
    phase_path = Path(phase_dir).resolve()
    project_path = phase_path.parent.parent  # phases/{id}/ -> project/

    verifier = PhaseVerifier(project_path)
    result = verifier.verify_phase_output(
        phase_id="current",
        phase_dir=phase_path,
        expected_files=expected_files,
    )

    return {
        "success": result.success,
        "missing": result.missing_files,
        "syntax_errors": result.syntax_errors,
        "found": result.found_files,
        "message": result.message,
    }


# CLI interface for testing
if __name__ == "__main__":
    import sys
    result = verify_phase_output()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
```

### 3. Änderung: `src/helix/api/streaming.py`

Verification nach jeder Phase einbauen (ab Zeile 145):

```python
# In run_project_with_streaming(), nach result = await runner.run_phase_streaming():

# === NEW: Post-Phase Verification ===
from helix.evolution.verification import PhaseVerifier

if result.success:
    verifier = PhaseVerifier(project_path)

    # Get expected files from phases.yaml if available
    expected_files = getattr(phase, 'output', None)

    verify_result = verifier.verify_phase_output(
        phase_id=phase.id,
        phase_dir=phase_dir,
        expected_files=expected_files,
    )

    if not verify_result.success:
        # Emit verification failure
        await job_manager.emit_event(job.job_id, PhaseEvent(
            event_type="verification_failed",
            phase_id=phase.id,
            data={
                "missing_files": verify_result.missing_files,
                "syntax_errors": verify_result.syntax_errors,
                "message": verify_result.message,
            }
        ))

        # Check retry count
        retry_count = getattr(phase, '_retry_count', 0)

        if retry_count < 2:
            # Retry with error context
            phase._retry_count = retry_count + 1

            # Append error context to CLAUDE.md
            retry_prompt = verifier.format_retry_prompt(verify_result)
            retry_file = phase_dir / "VERIFICATION_ERRORS.md"
            retry_file.write_text(retry_prompt, encoding="utf-8")

            await job_manager.emit_event(job.job_id, PhaseEvent(
                event_type="phase_retry",
                phase_id=phase.id,
                data={"retry_number": retry_count + 1, "max_retries": 2}
            ))

            # Re-run phase (recursive call or loop)
            # ... implementation details ...
        else:
            # Max retries reached
            result.success = False
            result.stderr = f"Verification failed after 2 retries: {verify_result.message}"
# === END NEW ===
```

### 4. Änderung: `templates/developer/_base.md`

Instruktion für Claude hinzufügen:

```markdown
# Developer Base Template

You are a software developer working on HELIX v4 projects.

## Project Context

Phase: {{ phase_name }} ({{ phase_id }})
{% if phase_description %}
{{ phase_description }}
{% endif %}

## Expected Output Files

{% if adr_files_create %}
Create these files (from ADR):
{% for file in adr_files_create %}
- `{{ file }}`
{% endfor %}
{% endif %}

{% if phase_output %}
Phase-specific outputs:
{% for file in phase_output %}
- `{{ file }}`
{% endfor %}
{% endif %}

## Before You Finish

**IMPORTANT**: Before ending your session, verify your output:

1. Check that ALL expected files listed above exist
2. Ensure all Python files have valid syntax
3. Run the verification tool:

```
python -m helix.tools.verify_phase
```

If verification fails, fix the issues before completing.

## Output Directory

Write all output files to `output/` directory:
- `output/src/` - Source files
- `output/tests/` - Test files

## Quality Gate

Ensure your implementation passes the quality gate defined in phases.yaml.
```

---

## Dokumentation

### Zu aktualisierende Dokumente

1. **docs/ARCHITECTURE-EVOLUTION.md**
   - Post-Phase Verification Section hinzufügen
   - Workflow-Diagramm erweitern

2. **CLAUDE.md**
   - Quality Gates Reference um `verify_output` erweitern
   - Developer-Rolle Instruktionen aktualisieren

---

## Akzeptanzkriterien

### Funktionale Kriterien

- [ ] `PhaseVerifier` kann Files aus ADR extrahieren und auf Existenz prüfen
- [ ] `PhaseVerifier` führt Syntax-Check für Python Files durch
- [ ] `verify_phase_output` Tool kann von Claude aufgerufen werden
- [ ] `streaming.py` führt automatische Verification nach jeder Phase durch
- [ ] Bei Verification-Fehler wird max 2x retry mit Fehlerkontext durchgeführt
- [ ] Nach 2 fehlgeschlagenen Retries wird Phase als FAILED markiert

### Template-Kriterien

- [ ] Templates zeigen erwartete Output-Files aus ADR
- [ ] Templates enthalten Instruktion zur Verification vor Beendigung
- [ ] Templates zeigen Syntax für Verification-Tool Aufruf

### Test-Kriterien

- [ ] Unit-Tests für `PhaseVerifier.verify_phase_output()`
- [ ] Unit-Tests für `PhaseVerifier._check_python_syntax()`
- [ ] Integration-Test: Phase mit fehlenden Files wird als FAILED markiert
- [ ] Integration-Test: Retry-Mechanismus funktioniert

---

## Konsequenzen

### Positiv

1. **Garantierte Output-Qualität**: Jede Phase wird auf tatsächliche Outputs geprüft
2. **Frühe Fehlererkennung**: Syntax-Fehler werden sofort gefunden, nicht erst bei Tests
3. **Selbst-Korrektur**: Claude kann Fehler selbst beheben (billiger als neue Session)
4. **Safety Net**: Externes System fängt ab was Claude vergisst
5. **Keine Endlos-Loops**: Max 2 Retries garantiert Terminierung

### Negativ

1. **Leicht höhere Latenz**: Verification-Check nach jeder Phase
2. **Komplexität**: Zwei Systeme (Self-Verification + External) statt einem

### Neutral

1. **Retry-Kosten**: Bei Fehlern werden zusätzliche Claude-Sessions gestartet (aber das ist besser als manuelle Korrektur)
2. **ADR-Abhängigkeit**: Verification basiert auf ADR.files - ohne ADR keine automatische File-Liste

---

## Referenzen

- [ADR-001: ADR als Single Source of Truth](../../adr/001-adr-as-single-source-of-truth.md)
- [ARCHITECTURE-EVOLUTION.md](../../docs/ARCHITECTURE-EVOLUTION.md)
- [helix.adr.parser](../../src/helix/adr/parser.py)
- [streaming.py](../../src/helix/api/streaming.py)
