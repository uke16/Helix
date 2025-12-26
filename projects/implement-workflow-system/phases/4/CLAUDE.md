# Phase 4: Sub-Agent Verifikation (ADR-025)

Du bist ein Claude Code Entwickler der Sub-Agent Verifikation mit Feedback-Loop implementiert.

---

## 🎯 Ziel

Implementiere einen Verifikations-Loop der:
1. Nach jeder Phase einen Sub-Agent zur Prüfung aufruft
2. Bei Fail: Feedback an die **gleiche Session** gibt (max 3x)
3. Bei finalem Fail: An Consultant eskaliert, dann abbricht

---

## 📚 Zuerst lesen

1. `src/helix/api/orchestrator.py` - UnifiedOrchestrator
2. `src/helix/tools/verify_phase.py` - Bestehendes Verify-Tool
3. `adr/011-post-phase-verification.md` - Verification ADR
4. `docs/ROADMAP-CONSULTANT-WORKFLOWS.md` - Entscheidungen Q6-Q8

---

## 📋 Aufgaben

### 1. ADR-025 erstellen

```yaml
---
adr_id: "025"
title: "Sub-Agent Verifikation mit Feedback-Loop"
status: Proposed
project_type: helix_internal
component_type: PROCESS
classification: NEW

files:
  create:
    - src/helix/verification/sub_agent.py
    - src/helix/verification/feedback.py
  modify:
    - src/helix/api/orchestrator.py
---
```

### 2. Sub-Agent Verifier implementieren

`src/helix/verification/sub_agent.py`:

```python
"""Sub-Agent Verification with Feedback Loop."""

from dataclasses import dataclass
from typing import Optional
from helix.claude_runner import ClaudeRunner

@dataclass
class VerificationResult:
    success: bool
    feedback: Optional[str] = None
    errors: list[str] = None
    
class SubAgentVerifier:
    """Verifies phase output using a sub-agent."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.runner = ClaudeRunner()
    
    async def verify_phase(
        self, 
        phase_output: Path,
        quality_gate: dict
    ) -> VerificationResult:
        """
        Verify phase output with sub-agent.
        
        The sub-agent checks:
        - Expected files exist
        - Syntax is valid
        - Quality gate criteria met
        """
        prompt = self._build_verification_prompt(phase_output, quality_gate)
        
        result = await self.runner.run_prompt(
            prompt,
            working_dir=phase_output,
            model="haiku"  # Schnelles Model für Verifikation
        )
        
        return self._parse_verification_result(result)
    
    async def send_feedback(
        self,
        session_id: str,
        feedback: str
    ) -> bool:
        """
        Send feedback to running session.
        
        Uses Claude Code's ability to receive follow-up messages.
        """
        # Implementation: Send message to existing session
        pass
```

### 3. Orchestrator erweitern

In `src/helix/api/orchestrator.py`:

```python
async def run_phase_with_verification(
    self, 
    phase: Phase,
    max_retries: int = 3
) -> PhaseResult:
    """Run phase with sub-agent verification loop."""
    
    verifier = SubAgentVerifier(max_retries=max_retries)
    
    for attempt in range(max_retries):
        # Run the phase
        result = await self.run_phase(phase)
        
        if not result.success:
            # Phase itself failed
            continue
            
        # Sub-agent verifies
        verification = await verifier.verify_phase(
            result.output_path,
            phase.quality_gate
        )
        
        if verification.success:
            return result
        
        # Send feedback to same session
        if attempt < max_retries - 1:
            await verifier.send_feedback(
                result.session_id,
                verification.feedback
            )
    
    # Final fail - escalate
    await self.escalate_to_consultant(phase, verification)
    raise PhaseVerificationFailed(phase.id, verification.errors)
```

### 4. Feedback-Mechanismus

`src/helix/verification/feedback.py`:

```python
"""Feedback delivery to running Claude sessions."""

class FeedbackChannel:
    """Delivers feedback to running Claude Code sessions."""
    
    async def send(self, session_id: str, message: str) -> bool:
        """
        Send feedback message to session.
        
        Options:
        1. Write to session's input file
        2. Use Claude Code's conversation continuation
        3. Signal via file system
        """
        # Die Session liest periodisch nach neuem Input
        feedback_file = self.get_feedback_path(session_id)
        feedback_file.write_text(message)
        return True
```

---

## 📁 Output

| Datei | Beschreibung |
|-------|--------------|
| `output/adr/025-sub-agent-verification.md` | ADR |
| `output/src/helix/verification/__init__.py` | Package |
| `output/src/helix/verification/sub_agent.py` | Verifier |
| `output/src/helix/verification/feedback.py` | Feedback-Channel |
| `output/src/helix/api/orchestrator.py` | Modified (diff) |
| `output/tests/test_sub_agent_verification.py` | Tests |

---

## ✅ Quality Gate

- [ ] ADR-025 valide
- [ ] SubAgentVerifier implementiert
- [ ] max_retries = 3 (konfigurierbar)
- [ ] Feedback wird in gleicher Session empfangen
- [ ] Eskalation zu Consultant bei finalem Fail
- [ ] Tests für Retry-Logic

---

## 🔗 Entscheidungen

| Q | Antwort |
|---|---------|
| Q6 | 3x Retries für jede Phase mit Sub-Agent |
| Q7 | Erst Eskalation an Consultant, dann Abbruch |
| Q8 | Gleiche Session bekommt Feedback |
