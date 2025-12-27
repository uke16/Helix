---
adr_id: "025"
title: Sub-Agent Verifikation mit Feedback-Loop
status: Implemented

project_type: helix_internal
component_type: PROCESS
classification: NEW
change_scope: major

files:
  create:
    - src/helix/verification/__init__.py
    - src/helix/verification/sub_agent.py
    - src/helix/verification/feedback.py
    - tests/test_sub_agent_verification.py
  modify:
    - src/helix/claude_runner.py
  docs:
    - docs/WORKFLOW-SYSTEM.md

depends_on:
  - ADR-023  # Workflow-Definitionen
  - ADR-024  # Consultant Workflow-Wissen
---

# ADR-025: Sub-Agent Verifikation mit Feedback-Loop

## Status

✅ Implemented (2025-12-26)

---

## Kontext

### Was ist das Problem?

Aktuell werden Phasen sequentiell ausgeführt ohne automatische Qualitätsprüfung. Wenn eine Phase fehlerhaften Output produziert, wird dies erst in späteren Phasen bemerkt.

Die Workflow-Templates (ADR-023) definieren `verify_agent: true` für Phasen, aber es gibt keine Implementation die:
1. Einen Sub-Agent zur Prüfung aufruft
2. Feedback an die laufende Session gibt
3. Retries ermöglicht (max 3x)
4. Bei finalem Fail eskaliert

### Warum muss es gelöst werden?

- Fehler sollen früh erkannt werden (Shift-Left)
- Korrekturen sollen im laufenden Prozess möglich sein
- Keine manuelle Intervention bei behebbaren Problemen

### Was passiert wenn wir nichts tun?

- Fehler propagieren durch alle nachfolgenden Phasen
- Manuelle Reviews werden nötig
- Höherer Aufwand für Fehlerkorrektur

---

## Entscheidung

### Wir entscheiden uns für:

Ein Sub-Agent Verifikationssystem mit 3-Retry-Loop und Feedback-Channel zur laufenden Session.

### Diese Entscheidung beinhaltet:

1. `SubAgentVerifier`: Prüft Phase-Output mit schnellem Model (Haiku)
2. `FeedbackChannel`: Sendet Korrekturaufforderungen an laufende Session
3. Eskalation an Consultant bei finalem Fail
4. Konfigurierbare Retries (default: 3)

### Warum diese Lösung?

- Sub-Agent ist unabhängig und kann objektiv prüfen
- Feedback-Loop ermöglicht Selbstkorrektur
- Haiku-Model ist schnell und kostengünstig für Verifikation
- 3 Retries geben genug Chancen ohne Endlos-Loop

---

## Implementation

### 1. Package-Struktur

```
src/helix/verification/
├── __init__.py
├── sub_agent.py      # SubAgentVerifier
└── feedback.py       # FeedbackChannel
```

### 2. SubAgentVerifier

```python
# src/helix/verification/sub_agent.py

"""Sub-Agent Verification with Feedback Loop.

Verifies phase output using a dedicated sub-agent and provides
feedback for corrections if verification fails.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from helix.claude_runner import ClaudeRunner


@dataclass
class VerificationResult:
    """Result from sub-agent verification."""
    success: bool
    feedback: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)


class SubAgentVerifier:
    """Verifies phase output using a sub-agent.

    The verifier spawns a lightweight Claude instance (Haiku)
    to check phase output against quality criteria.
    """

    VERIFICATION_PROMPT = '''
You are a verification agent. Check the phase output in the current directory.

Quality Gate: {quality_gate_type}
Expected Files: {expected_files}

Verify:
1. All expected files exist
2. Files have valid syntax (Python, YAML, Markdown)
3. Quality gate criteria are met

Output JSON:
```json
{{
  "success": true/false,
  "errors": ["list of errors if any"],
  "checks_passed": ["list of passed checks"],
  "feedback": "Specific feedback for fixing issues (if failed)"
}}
```
'''

    def __init__(self, max_retries: int = 3):
        """Initialize verifier.

        Args:
            max_retries: Maximum verification attempts per phase.
        """
        self.max_retries = max_retries
        self.runner = ClaudeRunner()

    async def verify_phase(
        self,
        phase_output: Path,
        quality_gate: dict,
        expected_files: list[str] | None = None,
    ) -> VerificationResult:
        """Verify phase output with sub-agent.

        Args:
            phase_output: Path to phase output directory.
            quality_gate: Quality gate configuration from phases.yaml.
            expected_files: Optional list of expected file paths.

        Returns:
            VerificationResult with success status and feedback.
        """
        prompt = self.VERIFICATION_PROMPT.format(
            quality_gate_type=quality_gate.get("type", "files_exist"),
            expected_files=expected_files or [],
        )

        result = await self.runner.run_phase(
            phase_dir=phase_output,
            prompt=prompt,
            timeout=120,  # 2 minutes for verification
            env_overrides={"CLAUDE_MODEL": "claude-3-haiku-20240307"},
        )

        return self._parse_result(result)

    def _parse_result(self, claude_result) -> VerificationResult:
        """Parse Claude result into VerificationResult."""
        if claude_result.output_json:
            return VerificationResult(
                success=claude_result.output_json.get("success", False),
                feedback=claude_result.output_json.get("feedback"),
                errors=claude_result.output_json.get("errors", []),
                checks_passed=claude_result.output_json.get("checks_passed", []),
            )

        # Fallback: Check exit code
        return VerificationResult(
            success=claude_result.success,
            feedback="Verification agent did not return structured output.",
            errors=[claude_result.stderr] if claude_result.stderr else [],
        )
```

### 3. FeedbackChannel

```python
# src/helix/verification/feedback.py

"""Feedback delivery to running Claude sessions.

Provides mechanisms to send correction feedback to
running Claude Code sessions for self-correction.
"""

from pathlib import Path
from datetime import datetime


class FeedbackChannel:
    """Delivers feedback to running Claude Code sessions.

    Feedback is delivered via a file that the session monitors.
    The session's CLAUDE.md includes instructions to check for
    feedback files periodically.
    """

    FEEDBACK_FILE = "feedback.md"

    def __init__(self, session_dir: Path):
        """Initialize feedback channel.

        Args:
            session_dir: Directory where the session runs.
        """
        self.session_dir = session_dir
        self.feedback_path = session_dir / self.FEEDBACK_FILE

    async def send(self, message: str, attempt: int) -> bool:
        """Send feedback message to session.

        Args:
            message: Feedback message with correction instructions.
            attempt: Current attempt number (1-3).

        Returns:
            True if feedback was delivered successfully.
        """
        feedback_content = f'''# Verification Feedback

**Attempt**: {attempt}/3
**Time**: {datetime.now().isoformat()}

## Issues Found

{message}

## Required Actions

Please fix the issues listed above and update your output.
After fixing, the verification will run again automatically.

---
*This feedback was generated by the Sub-Agent Verifier*
'''

        try:
            self.feedback_path.write_text(feedback_content)
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear feedback file after successful verification."""
        if self.feedback_path.exists():
            self.feedback_path.unlink()

    def has_pending_feedback(self) -> bool:
        """Check if there is pending feedback."""
        return self.feedback_path.exists()
```

### 4. Integration in ClaudeRunner

Erweitere `run_with_verification` Methode:

```python
# Ergänzung in src/helix/claude_runner.py

async def run_with_verification(
    self,
    phase_dir: Path,
    quality_gate: dict,
    max_retries: int = 3,
    on_output: OutputCallback | None = None,
    **kwargs,
) -> ClaudeResult:
    """Run phase with sub-agent verification loop.

    Args:
        phase_dir: Phase directory.
        quality_gate: Quality gate configuration.
        max_retries: Maximum verification retries.
        on_output: Optional output callback.
        **kwargs: Additional run arguments.

    Returns:
        ClaudeResult from successful run.

    Raises:
        PhaseVerificationFailed: After max_retries failed.
    """
    from helix.verification.sub_agent import SubAgentVerifier
    from helix.verification.feedback import FeedbackChannel

    verifier = SubAgentVerifier(max_retries=max_retries)
    feedback = FeedbackChannel(phase_dir)

    for attempt in range(1, max_retries + 1):
        # Run the phase
        if on_output:
            result = await self.run_phase_streaming(
                phase_dir, on_output, **kwargs
            )
        else:
            result = await self.run_phase(phase_dir, **kwargs)

        if not result.success:
            # Phase execution failed
            continue

        # Verify output
        verification = await verifier.verify_phase(
            phase_dir / "output",
            quality_gate,
        )

        if verification.success:
            feedback.clear()
            return result

        # Send feedback for next attempt
        if attempt < max_retries:
            await feedback.send(
                verification.feedback or "Verification failed",
                attempt,
            )
            # Wait briefly for feedback to be processed
            await asyncio.sleep(2)

    # Final failure
    raise PhaseVerificationFailed(
        phase_id=phase_dir.name,
        errors=verification.errors,
    )


class PhaseVerificationFailed(Exception):
    """Raised when phase verification fails after all retries."""

    def __init__(self, phase_id: str, errors: list[str]):
        self.phase_id = phase_id
        self.errors = errors
        super().__init__(
            f"Phase {phase_id} failed verification: {', '.join(errors)}"
        )
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/WORKFLOW-SYSTEM.md` | Sub-Agent Verifikation dokumentieren |
| `CLAUDE.md` | Feedback-Mechanismus erwähnen |
| `templates/consultant/workflow-guide.md` | Troubleshooting für Verifikation |

---

## Akzeptanzkriterien

### 1. SubAgentVerifier

- [x] Kann Phase-Output mit Haiku-Model prüfen
- [x] Gibt strukturierte VerificationResult zurück
- [x] Timeout von 2 Minuten konfiguriert

### 2. FeedbackChannel

- [x] Schreibt Feedback nach feedback.md
- [x] Enthält Attempt-Nummer und Timestamp
- [x] Kann Feedback nach Erfolg löschen

### 3. Integration

- [x] run_with_verification Methode implementiert
- [x] max_retries = 3 (konfigurierbar)
- [x] PhaseVerificationFailed Exception definiert

### 4. Tests

- [x] Test für erfolgreiche Verifikation
- [x] Test für Retry-Loop mit Feedback
- [x] Test für finalen Fail nach 3 Retries

> Tests implementiert in `tests/e2e/test_workflow_system.py`:
> - `TestSubAgentVerification.test_verification_success`
> - `TestSubAgentVerification.test_verification_retry_on_failure`
> - `TestSubAgentVerification.test_verification_exhausted_retries`

---

## Konsequenzen

### Vorteile

- Frühe Fehlererkennung (Shift-Left)
- Automatische Korrekturversuche
- Unabhängige Qualitätsprüfung durch Sub-Agent
- Kostengünstig durch Haiku-Model

### Nachteile / Risiken

- Zusätzliche API-Calls für Verifikation
- Feedback-File muss von Session gelesen werden
- Bei hartnäckigen Fehlern 3x Retry-Overhead

### Mitigation

- Haiku ist günstig, Overhead vertretbar
- Feedback-Mechanismus in CLAUDE.md dokumentieren
- Eskalation an Consultant bei finalem Fail

---

## Referenzen

- ADR-011: Post-Phase Verification (Grundkonzept)
- ADR-023: Workflow-Definitionen (verify_agent Flag)
- `src/helix/claude_runner.py`: Bestehender Runner
- `src/helix/tools/verify_phase.py`: Bestehendes Tool
