# Phase 1 Input: UnifiedOrchestrator Requirements

## Zu konsolidierende Quellen

1. **orchestrator_legacy.py** (417 Zeilen)
   - Pfad: `src/helix/orchestrator_legacy.py`
   - Features: Quality Gates, Escalation, Phase Loading
   
2. **streaming.py** (400+ Zeilen)
   - Pfad: `src/helix/api/streaming.py`
   - Features: Verification (ADR-011), SSE Events
   
3. **orchestrator/ package** (~2000 Zeilen)
   - Pfad: `src/helix/orchestrator/`
   - Features: DataFlowManager, StatusTracker (NICHT genutzt)

## Pflicht-Features im UnifiedOrchestrator

### 1. Phase Execution
- PhaseLoader nutzen
- ClaudeRunner aufrufen
- Retry bei Fehler

### 2. Verification (ADR-011)
- PhaseVerifier aus `helix.evolution.verification`
- `verify_phase_output()` nach JEDER Phase
- Retry bei Verification Failure

### 3. Quality Gates
- QualityGateRunner aus `helix.quality_gates`
- Gate Check nach erfolgreicher Verification
- Escalation bei Gate Failure

### 4. Escalation (ADR-004)
- EscalationManager aus `helix.escalation`
- Model Switch möglich
- Human-in-the-Loop als letzter Ausweg

### 5. Event Callbacks
- `on_event` Callback für SSE Streaming
- Events: phase_start, phase_complete, verification_failed, gate_failed, project_complete

## Beispiel Interface

```python
class UnifiedOrchestrator:
    async def run_project(
        self,
        project_path: Path,
        on_event: Callable[[PhaseEvent], None] | None = None,
    ) -> ProjectResult:
        """Run project with all features."""
        pass
```
