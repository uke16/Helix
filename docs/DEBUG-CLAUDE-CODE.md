# Debugging Claude Code Sessions

## Problem

Claude Code output is buffered when redirected to file:
```bash
# BAD - output only visible after process ends
claude ... >> log.txt 2>&1
```

## Solution

Use v3 script with line buffering:
```bash
# GOOD - live output streaming
stdbuf -oL -eL claude ... 2>&1 | tee log.txt
```

## Scripts

| Script | Output | Use Case |
|--------|--------|----------|
| `run-claude-phase-v2.sh` | Buffered | Background jobs |
| `run-claude-phase-v3.sh` | Live streaming | Debugging |

## Monitoring Running Sessions

```bash
# Check if running
ps aux | grep claude

# Check file activity
find /path -mmin -1 -type f

# Check network connections
ss -tp | grep claude

# Check CPU usage
top -p <PID>
```

## When to Kill

Kill if:
- No file changes for 10+ minutes
- 0% CPU for extended periods
- No network activity

Check first:
- Might be waiting for large API response
- Might be processing complex task
