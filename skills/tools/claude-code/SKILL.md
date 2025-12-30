# Claude Code CLI Skill

> Best practices for running Claude Code programmatically.
>
> Read this when starting Claude Code from scripts, tmux, or automation.

---

## Overview

Claude Code has two main execution modes:

| Mode | Flag | Use Case | Persistence |
|------|------|----------|-------------|
| **Headless** | `-p` / `--print` | Single tasks, CI/CD, automation | No - exits after completion |
| **Interactive** | (none) | Multi-step workflows, supervision | Yes - runs until quit |

---

## Quick Reference

### Headless Mode (Single Tasks)

```bash
# Simple task
claude -p "Fix all linting errors"

# With specific tools allowed
claude -p "Review code" --allowedTools "Read,Grep"

# With JSON output
claude -p "Analyze codebase" --output-format json

# Full automation
claude -p "Implement feature" \
  --dangerously-skip-permissions \
  --allowedTools "Bash,Read,Write,Edit" \
  --output-format stream-json
```

### Interactive Mode (tmux - One-Liner)

```bash
# Start Claude Code in detached tmux session (ONE-LINER)
NODE_DIR="$HOME/.nvm/versions/node/v20.19.6/bin" && \
tmux new-session -d -s claude-session -c /path/to/project \
  "export PATH=$NODE_DIR:\$PATH; claude --dangerously-skip-permissions; exec bash" && \
sleep 3 && tmux send-keys -t claude-session Down Enter && \
echo "Started: tmux attach -t claude-session"
```

**Components:**
1. `NODE_DIR` - Set full path to node binaries (nvm install location)
2. `tmux new-session -d -s <name>` - Create detached session
3. `-c /path/to/project` - Set working directory
4. `export PATH=...` - Make node/claude available
5. `sleep 3 && tmux send-keys Down Enter` - Accept permissions dialog

---

## NVM Installation Considerations

When Claude Code is installed via nvm, the `claude` binary is a symlink:

```
~/.nvm/versions/node/v20.19.6/bin/claude 
  → ../lib/node_modules/@anthropic-ai/claude-code/cli.js
```

**Problem:** Non-interactive shells (nohup, tmux) don't source `.bashrc`, so:
- `claude` is not in PATH
- `/usr/bin/env node` fails

**Solution:** Always set PATH explicitly:

```bash
export PATH="$HOME/.nvm/versions/node/v20.19.6/bin:$PATH"
```

---

## Interactive Mode Details

### Starting with tmux

```bash
# 1. Create session with explicit PATH
NODE_DIR="$HOME/.nvm/versions/node/v20.19.6/bin"
tmux new-session -d -s my-session -c /working/dir \
  "export PATH=$NODE_DIR:\$PATH; claude --dangerously-skip-permissions; exec bash"

# 2. Accept permissions dialog (Down + Enter)
sleep 3
tmux send-keys -t my-session Down
sleep 0.5
tmux send-keys -t my-session Enter

# 3. Optionally send initial prompt
sleep 3
tmux send-keys -t my-session "Read CLAUDE.md and start working" Enter
```

### Monitoring

```bash
# View current output
tmux capture-pane -t my-session -p

# View last 50 lines
tmux capture-pane -t my-session -p | tail -50

# Attach to session (interactive)
tmux attach -t my-session

# List all sessions
tmux list-sessions
```

### Session Management

```bash
# Kill session
tmux kill-session -t my-session

# Send Ctrl+C to interrupt
tmux send-keys -t my-session C-c

# Detach (from attached session)
# Press: Ctrl+B, then D
```

---

## Headless Mode Details

### Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `text` | Plain text (default) | Human reading |
| `json` | Single JSON object | Programmatic parsing |
| `stream-json` | NDJSON stream | Real-time processing |

### Continuing Conversations

```bash
# Continue most recent session
claude -p "Now fix the tests" --continue

# Resume specific session
claude -p "Continue from here" --resume <session-id>

# Get session ID from previous run
session_id=$(claude -p "Start task" --output-format json | jq -r '.session_id')
```

### System Prompts

```bash
# Append to default prompt
claude -p "Review code" \
  --append-system-prompt "Focus on security vulnerabilities"

# Replace entire system prompt
claude -p "Custom task" \
  --system-prompt "You are a security auditor..."
```

---

## HELIX Controller Pattern

For HELIX evolution controllers that supervise multi-phase workflows:

```bash
#!/bin/bash
# Start controller for ADR-XXX
ADR_NUM="032"
PROJECT_DIR="/home/aiuser01/helix-v4/projects/claude/controller-adr-$ADR_NUM"
SESSION_NAME="adr-$ADR_NUM"
NODE_DIR="$HOME/.nvm/versions/node/v20.19.6/bin"

# Kill existing session
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Start new session
tmux new-session -d -s $SESSION_NAME -c $PROJECT_DIR \
  "export PATH=$NODE_DIR:\$PATH; claude --dangerously-skip-permissions; exec bash"

# Accept permissions
sleep 3
tmux send-keys -t $SESSION_NAME Down
sleep 0.5
tmux send-keys -t $SESSION_NAME Enter

# Wait for UI to load
sleep 4

# Send initial task
tmux send-keys -t $SESSION_NAME "Read CLAUDE.md and execute controller tasks" Enter

echo "Controller started: tmux attach -t $SESSION_NAME"
```

---

## Common Issues

### "claude: command not found"

**Cause:** nvm not sourced in non-interactive shell

**Fix:** Use full path or set PATH:
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.6/bin:$PATH"
```

### "/usr/bin/env: 'node': No such file or directory"

**Cause:** Same as above - node not in PATH

**Fix:** Same solution

### "Input must be provided... when using --print"

**Cause:** Using `-p` without a prompt (needs interactive mode)

**Fix:** Either provide prompt with `-p` or use interactive mode:
```bash
# Headless with prompt
claude -p "Your task here"

# Interactive (no -p)
claude --dangerously-skip-permissions
```

### Permission dialog not accepting

**Cause:** Timing issue with tmux key sending

**Fix:** Add delays:
```bash
sleep 3
tmux send-keys -t session Down
sleep 0.5
tmux send-keys -t session Enter
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key (usually configured) |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Disable telemetry |
| `ENABLE_LSP_TOOL` | Enable LSP integration |

---

## See Also

- [Anthropic Headless Docs](https://code.claude.com/docs/en/headless)
- [helix/SKILL.md](../helix/SKILL.md) - HELIX orchestration
- [infrastructure/SKILL.md](../infrastructure/SKILL.md) - Docker/Server setup
