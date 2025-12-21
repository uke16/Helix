# HELIX v4 Bootstrap - Phase 06: Configuration

Create configuration files for HELIX v4.

## Target Directory

`/home/aiuser01/helix-v4/config/`

## Files to Create

### 1. `/home/aiuser01/helix-v4/config/llm-providers.yaml`

```yaml
# HELIX v4 LLM Provider Configuration

providers:
  openrouter:
    name: "OpenRouter"
    base_url: "https://openrouter.ai/api/v1"
    api_format: "openai"
    env_key: "HELIX_OPENROUTER_API_KEY"
    models:
      gpt-4o:
        id: "openai/gpt-4o"
        context_window: 128000
        cost_per_1m_input: 2.50
        cost_per_1m_output: 10.00
        supports_tools: true
        supports_vision: true
      gpt-4o-mini:
        id: "openai/gpt-4o-mini"
        context_window: 128000
        cost_per_1m_input: 0.15
        cost_per_1m_output: 0.60
        supports_tools: true
        supports_vision: true
      claude-sonnet-4:
        id: "anthropic/claude-sonnet-4"
        context_window: 200000
        cost_per_1m_input: 3.00
        cost_per_1m_output: 15.00
        supports_tools: true
        supports_vision: true
      claude-opus-4:
        id: "anthropic/claude-opus-4"
        context_window: 200000
        cost_per_1m_input: 15.00
        cost_per_1m_output: 75.00
        supports_tools: true
        supports_vision: true
      gemini-2-flash:
        id: "google/gemini-2.0-flash-001"
        context_window: 1000000
        cost_per_1m_input: 0.10
        cost_per_1m_output: 0.40
        supports_tools: true
        supports_vision: true
      llama-3-70b:
        id: "meta-llama/llama-3.3-70b-instruct"
        context_window: 131072
        cost_per_1m_input: 0.50
        cost_per_1m_output: 0.75
        supports_tools: false
        supports_vision: false

  anthropic:
    name: "Anthropic Direct"
    base_url: "https://api.anthropic.com/v1"
    api_format: "anthropic"
    env_key: "HELIX_ANTHROPIC_API_KEY"
    models:
      claude-sonnet-4:
        id: "claude-sonnet-4-20250514"
        context_window: 200000
        cost_per_1m_input: 3.00
        cost_per_1m_output: 15.00
        supports_tools: true
        supports_vision: true
      claude-opus-4:
        id: "claude-opus-4-20250514"
        context_window: 200000
        cost_per_1m_input: 15.00
        cost_per_1m_output: 75.00
        supports_tools: true
        supports_vision: true

  openai:
    name: "OpenAI Direct"
    base_url: "https://api.openai.com/v1"
    api_format: "openai"
    env_key: "HELIX_OPENAI_API_KEY"
    models:
      gpt-4o:
        id: "gpt-4o"
        context_window: 128000
        cost_per_1m_input: 5.00
        cost_per_1m_output: 15.00
        supports_tools: true
        supports_vision: true
      gpt-4o-mini:
        id: "gpt-4o-mini"
        context_window: 128000
        cost_per_1m_input: 0.15
        cost_per_1m_output: 0.60
        supports_tools: true
        supports_vision: true

# Default model configuration
defaults:
  # For consultant discussions (needs good reasoning)
  consultant: "openrouter:claude-opus-4"
  
  # For code development (fast, good at code)
  developer: "openrouter:claude-sonnet-4"
  
  # For code review (thorough)
  reviewer: "openrouter:claude-opus-4"
  
  # For quick tasks (cheap and fast)
  utility: "openrouter:gpt-4o-mini"

# Model aliases for convenience
aliases:
  opus: "openrouter:claude-opus-4"
  sonnet: "openrouter:claude-sonnet-4"
  gpt4: "openrouter:gpt-4o"
  fast: "openrouter:gpt-4o-mini"
  cheap: "openrouter:gemini-2-flash"
```

### 2. `/home/aiuser01/helix-v4/config/quality-gates.yaml`

```yaml
# HELIX v4 Quality Gate Configuration

gates:
  files_exist:
    description: "Check that specified files exist"
    type: "deterministic"
    config:
      fail_on_missing: true

  syntax_check:
    description: "Check syntax validity of generated code"
    type: "deterministic"
    config:
      languages:
        python:
          command: "python3 -m py_compile {file}"
          extensions: [".py"]
        typescript:
          command: "npx tsc --noEmit {file}"
          extensions: [".ts", ".tsx"]
        yaml:
          command: "python3 -c \"import yaml; yaml.safe_load(open('{file}'))\""
          extensions: [".yaml", ".yml"]
        json:
          command: "python3 -c \"import json; json.load(open('{file}'))\""
          extensions: [".json"]

  tests_pass:
    description: "Run test suite and require passing"
    type: "deterministic"
    config:
      python:
        command: "pytest {path} -v"
        coverage_threshold: 80
      typescript:
        command: "npm test"

  lint_pass:
    description: "Run linter and require no errors"
    type: "deterministic"
    config:
      python:
        command: "ruff check {path}"
        auto_fix: false
      typescript:
        command: "npx eslint {path}"

  review_approved:
    description: "Require LLM review approval"
    type: "llm"
    config:
      model: "openrouter:claude-opus-4"
      min_approval_score: 0.8
      require_no_high_severity: true

# Gate combinations for different phase types
phase_gates:
  development:
    required:
      - syntax_check
    optional:
      - lint_pass
  
  review:
    required:
      - review_approved
  
  test:
    required:
      - tests_pass
    optional:
      - lint_pass

  documentation:
    required:
      - files_exist
```

### 3. `/home/aiuser01/helix-v4/config/escalation.yaml`

```yaml
# HELIX v4 Escalation Configuration

escalation:
  # Maximum retries before escalating
  max_retries_per_level: 3
  
  # Timeout for each attempt (minutes)
  attempt_timeout: 30
  
  levels:
    # Level 1: Autonomous recovery (Consultant handles)
    stufe_1:
      name: "Autonomous Recovery"
      description: "Consultant tries to fix issues automatically"
      actions:
        - type: "model_switch"
          description: "Try a different/better model"
          models:
            - "openrouter:claude-opus-4"
            - "openrouter:gpt-4o"
        - type: "hint_generation"
          description: "Generate hints from error analysis"
        - type: "plan_revision"
          description: "Revise the approach/plan"
        - type: "context_expansion"
          description: "Load additional skills/context"
      max_attempts: 3
    
    # Level 2: Human in the Loop
    stufe_2:
      name: "Human in the Loop"
      description: "Requires human intervention"
      actions:
        - type: "notification"
          channels:
            - "api_event"  # SSE event to frontend
            - "log"        # Log entry
        - type: "pause"
          description: "Pause execution and wait for human input"
      wait_timeout_hours: 24

# Error patterns and handling
error_patterns:
  - pattern: "syntax.*error"
    level: "stufe_1"
    action: "hint_generation"
    
  - pattern: "permission.*denied"
    level: "stufe_2"
    action: "notification"
    
  - pattern: "api.*rate.*limit"
    level: "stufe_1"
    action: "model_switch"
    
  - pattern: "timeout"
    level: "stufe_1"
    action: "model_switch"
    
  - pattern: "out.*of.*memory"
    level: "stufe_2"
    action: "notification"
```

### 4. `/home/aiuser01/helix-v4/config/streaming.yaml`

```yaml
# HELIX v4 Streaming Configuration

streaming:
  # Default streaming level
  default_level: "normal"
  
  levels:
    # Minimal: Only phase transitions and errors
    minimal:
      include:
        - phase_start
        - phase_end
        - error
        - completed
        - failed
      claude_output: false
    
    # Normal: Phase info + key events
    normal:
      include:
        - phase_start
        - phase_end
        - file_created
        - file_modified
        - error
        - cost_update
        - completed
        - failed
      claude_output:
        enabled: true
        max_lines_per_event: 20
        throttle_ms: 500
    
    # Verbose: Everything
    verbose:
      include:
        - phase_start
        - phase_end
        - file_created
        - file_modified
        - file_deleted
        - tool_call
        - error
        - warning
        - cost_update
        - token_update
        - completed
        - failed
        - heartbeat
      claude_output:
        enabled: true
        max_lines_per_event: 100
        throttle_ms: 100
    
    # Debug: Full raw output
    debug:
      include: ["*"]
      claude_output:
        enabled: true
        raw: true  # No filtering

  # Filter patterns for Claude Code output
  output_filters:
    # Hide thinking/internal messages
    exclude_patterns:
      - "^Thinking\\.\\.\\."
      - "^Processing\\.\\.\\."
      - "^\\s*$"  # Empty lines
    
    # Highlight important messages
    highlight_patterns:
      - pattern: "^(Created|Modified|Deleted):"
        style: "success"
      - pattern: "^Error:"
        style: "error"
      - pattern: "^Warning:"
        style: "warning"

  # Heartbeat configuration
  heartbeat:
    interval_seconds: 15
    enabled: true
```

## Instructions

1. Create all 4 configuration files in `/home/aiuser01/helix-v4/config/`
2. Ensure YAML is valid
3. All content in English
4. Create `output/result.json` when done

## Output

```json
{
  "status": "success",
  "files_created": [
    "config/llm-providers.yaml",
    "config/quality-gates.yaml",
    "config/escalation.yaml",
    "config/streaming.yaml"
  ]
}
```
