# HELIX v4 Configuration

## Configuration Files

All configuration is in `/config/`:

| File | Purpose |
|------|---------|
| `llm-providers.yaml` | LLM model definitions |
| `quality-gates.yaml` | Gate configurations |
| `escalation.yaml` | Failure handling |
| `streaming.yaml` | Output streaming |
| `domain-experts.yaml` | Expert definitions |

## LLM Providers

### Supported Providers

- **OpenRouter** - Multi-model gateway
- **Anthropic** - Direct Claude access
- **OpenAI** - Direct GPT access

### Model Aliases

```yaml
# Use short names
aliases:
  opus: "openrouter:claude-opus-4"
  sonnet: "openrouter:claude-sonnet-4"
  gpt4: "openrouter:gpt-4o"
  fast: "openrouter:gpt-4o-mini"
```

### Environment Variables

```bash
HELIX_OPENROUTER_API_KEY=sk-or-...
HELIX_ANTHROPIC_API_KEY=sk-ant-...
HELIX_OPENAI_API_KEY=sk-...
```

## Quality Gates

### Gate Types

| Gate | Description |
|------|-------------|
| `files_exist` | Check output files exist |
| `syntax_check` | Validate code syntax |
| `tests_pass` | Run test suite |
| `review_approved` | LLM review approval |

### Customization

```yaml
# config/quality-gates.yaml
gates:
  syntax_check:
    config:
      languages:
        python:
          command: "python3 -m py_compile {file}"
```

## Streaming

### Levels

| Level | What's Streamed |
|-------|-----------------|
| `minimal` | Phase start/end, errors only |
| `normal` | + file changes, costs |
| `verbose` | + all events |
| `debug` | Raw Claude Code output |

### Configuration

```yaml
# config/streaming.yaml
streaming:
  default_level: "normal"
```

## Escalation

### Levels

| Level | Handling |
|-------|----------|
| Stufe 1 | Autonomous (model switch, retry) |
| Stufe 2 | Human intervention required |

### Configuration

```yaml
# config/escalation.yaml
escalation:
  max_retries_per_level: 3
  attempt_timeout: 30  # minutes
```
