# HELIX v4 - Modulare Architektur

## Designprinzipien

1. **Single Responsibility** - Jedes Modul hat EINE Aufgabe
2. **Lose Kopplung** - Module kommunizieren über definierte Interfaces
3. **Dependency Injection** - Abhängigkeiten werden übergeben, nicht hardcoded
4. **Testbarkeit** - Jedes Modul ist einzeln testbar

---

## Modul-Übersicht

```
src/helix/
│
├── __init__.py                 # Package + Version
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  CORE LAYER - Orchestrierung & Workflow                 │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  orchestrator.py          # Workflow-Steuerung          │
│   │    └── Orchestrator                                     │
│   │        ├── run_project()                                │
│   │        ├── run_phase()                                  │
│   │        └── Nutzt: PhaseLoader, ClaudeRunner, QualityGates│
│   │                                                          │
├── │  phase_loader.py          # Phasen-Definition           │
│   │    └── PhaseLoader                                      │
│   │        ├── load_phases()                                │
│   │        └── Nutzt: SpecValidator                         │
│   │                                                          │
├── │  spec_validator.py        # Schema-Validierung          │
│   │    └── SpecValidator                                    │
│   │        └── validate() → ValidationResult                │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  EXECUTION LAYER - Claude Code & LLM                    │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  claude_runner.py         # Claude Code Subprocess      │
│   │    └── ClaudeRunner                                     │
│   │        ├── run_phase()                                  │
│   │        └── get_claude_env()                             │
│   │                                                          │
├── │  llm_client.py            # Multi-Provider LLM          │
│   │    └── LLMClient                                        │
│   │        ├── resolve_model()                              │
│   │        ├── complete()                                   │
│   │        └── Unterstützt: OpenRouter, Anthropic, OpenAI   │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  CONTEXT LAYER - Templates & Skills                     │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  template_engine.py       # Jinja2 Templates            │
│   │    └── TemplateEngine                                   │
│   │        ├── render_claude_md()                           │
│   │        └── get_template()                               │
│   │                                                          │
├── │  context_manager.py       # Skill-Verwaltung            │
│   │    └── ContextManager                                   │
│   │        ├── prepare_phase_context()                      │
│   │        ├── get_skills_for_domain()                      │
│   │        └── create_symlinks()                            │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  QUALITY LAYER - Gates & Escalation                     │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  quality_gates.py         # Deterministische Prüfungen  │
│   │    └── QualityGateRunner                                │
│   │        ├── check_files_exist()                          │
│   │        ├── check_syntax()                               │
│   │        ├── check_tests_pass()                           │
│   │        └── Returns: GateResult                          │
│   │                                                          │
├── │  escalation.py            # 2-Stufen Escalation         │
│   │    └── EscalationManager                                │
│   │        ├── handle_gate_failure()                        │
│   │        ├── trigger_stufe_1() → Consultant-autonom       │
│   │        └── trigger_stufe_2() → Human-in-Loop            │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── consultant/                  # CONSULTANT PACKAGE
│   ├── __init__.py
│   ├── meeting.py              # Agentic Meeting
│   │    └── ConsultantMeeting
│   │        ├── run()
│   │        ├── analyze_request()
│   │        ├── run_expert_analyses()
│   │        └── synthesize()
│   │
│   └── expert_manager.py       # Domain-Experten
│        └── ExpertManager
│            ├── load_experts()
│            ├── select_experts()
│            └── setup_expert_directory()
│
├── observability/               # OBSERVABILITY PACKAGE
│   ├── __init__.py
│   ├── logger.py               # 3-Ebenen Logging
│   │    └── HelixLogger
│   │        ├── log_tool_call()
│   │        ├── log_phase_start/end()
│   │        └── log_error()
│   │
│   └── metrics.py              # Metriken
│        └── MetricsCollector
│            ├── start/end_project()
│            ├── start/end_phase()
│            └── record_tokens/cost()
│
└── cli/                         # CLI PACKAGE
    ├── __init__.py
    ├── main.py                 # Click Entry Point
    │    └── main()
    │
    └── commands.py             # Commands
         ├── cmd_run()
         ├── cmd_status()
         ├── cmd_debug()
         └── cmd_costs()
```

---

## Abhängigkeitsgraph

```
                    CLI (main.py)
                         │
                         ▼
                   Orchestrator
                    /    |    \
                   /     |     \
                  ▼      ▼      ▼
           PhaseLoader  ClaudeRunner  QualityGates
               │            │              │
               ▼            ▼              ▼
         SpecValidator  LLMClient    EscalationManager
                            │              │
                            ▼              ▼
                       (OpenRouter)  ConsultantMeeting
                                          │
                                          ▼
                                    ExpertManager
                                          │
                                          ▼
                                    ContextManager
                                          │
                                          ▼
                                    TemplateEngine
```

---

## Interface-Beispiele

### Orchestrator → QualityGates

```python
# Lose Kopplung durch Interface
class Orchestrator:
    def __init__(self, gate_runner: QualityGateRunner = None):
        self.gates = gate_runner or QualityGateRunner()
    
    async def run_phase(self, phase_dir: Path, config: PhaseConfig):
        result = await self._execute_phase(phase_dir)
        
        # Quality Gate prüfen
        gate_result = self.gates.check(
            phase_dir=phase_dir,
            gate_config=config.quality_gate
        )
        
        if not gate_result.passed:
            return await self.escalation.handle_failure(...)
```

### LLMClient → Provider-Abstraktion

```python
# Provider-unabhängiges Interface
class LLMClient:
    async def complete(self, model_spec: str, messages: list) -> str:
        """Einheitliche API für alle Provider."""
        config = self.resolve_model(model_spec)  # "openrouter:gpt-4o"
        
        if config.api_format == "openai":
            return await self._complete_openai(config, messages)
        elif config.api_format == "anthropic":
            return await self._complete_anthropic(config, messages)
```

### Testbarkeit durch DI

```python
# Unit Test mit Mock
def test_orchestrator_handles_gate_failure():
    mock_gates = Mock(spec=QualityGateRunner)
    mock_gates.check.return_value = GateResult(passed=False, ...)
    
    orchestrator = Orchestrator(gate_runner=mock_gates)
    result = await orchestrator.run_phase(...)
    
    assert mock_gates.check.called
    assert result.escalated
```

---

## Datei-Konventionen

| Typ | Konvention | Beispiel |
|-----|------------|----------|
| Module | `snake_case.py` | `template_engine.py` |
| Klassen | `PascalCase` | `TemplateEngine` |
| Funktionen | `snake_case` | `render_claude_md()` |
| Konstanten | `UPPER_CASE` | `DEFAULT_MODEL` |
| Private | `_prefix` | `_load_config()` |

---

## Package-Struktur Regeln

1. **Ein Package = Ein Concern**
   - `consultant/` = Alles zum Meeting-System
   - `observability/` = Alles zu Logging/Metrics

2. **`__init__.py` exportiert Public API**
   ```python
   # consultant/__init__.py
   from .meeting import ConsultantMeeting
   from .expert_manager import ExpertManager
   
   __all__ = ["ConsultantMeeting", "ExpertManager"]
   ```

3. **Interne Module beginnen mit `_`**
   ```
   consultant/
   ├── meeting.py          # Public
   ├── expert_manager.py   # Public
   └── _utils.py           # Intern
   ```

---

*Erstellt: 2025-12-21*
