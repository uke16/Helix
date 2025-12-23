# HELIX Debug & Observability Engine

> Live visibility into Claude CLI executions for debugging, cost tracking, and monitoring.

---

## Overview

The Debug & Observability Engine provides real-time insights into HELIX phase executions by parsing the structured NDJSON output from Claude CLI's `--output-format stream-json` mode.

### Key Features

- **Live Tool Tracking**: See which tools are being called in real-time
- **Cost Monitoring**: Track token usage and costs per phase and project
- **Timing Metrics**: Measure tool call durations and identify bottlenecks
- **SSE Dashboard**: Stream events to web dashboards via Server-Sent Events
- **Terminal Dashboard**: Live CLI monitoring with visual statistics

---

## Quick Start

### Enable Debug Mode

Run Claude CLI with stream-json output:

```bash
claude --output-format stream-json --verbose --print "Your prompt"
```

Or use the wrapper script:

```bash
./control/claude-wrapper.sh -v -- --print "Your prompt"
```

### Start Debug Session

For a full HELIX phase with terminal dashboard:

```bash
./control/helix-debug.sh -d phases/01-analysis
```

With web dashboard:

```bash
./control/helix-debug.sh -w -p 8080 phases/01-analysis
```

---

## Components

### StreamParser

Parses NDJSON events from Claude CLI:

```python
from helix.debug import StreamParser, EventType

parser = StreamParser()

async def on_event(event):
    if event.event_type == EventType.ASSISTANT_TOOL_USE:
        print(f"Tool: {event.tool_name}")
    elif event.event_type == EventType.RESULT_SUCCESS:
        print(f"Cost: ${event.cost_usd:.4f}")

parser.on_event(on_event)

# Feed lines from Claude CLI
for line in process.stdout:
    await parser.parse_line(line)

# Get summary
summary = parser.get_summary()
print(f"Total tool calls: {summary['tool_calls']}")
```

**Supported Event Types:**

| Event Type | Description |
|------------|-------------|
| `SYSTEM_INIT` | Session initialization with available tools |
| `ASSISTANT_TEXT` | Text output from the assistant |
| `ASSISTANT_TOOL_USE` | Tool call initiated |
| `USER_TOOL_RESULT` | Tool execution result |
| `RESULT_SUCCESS` | Successful completion with cost/tokens |
| `RESULT_ERROR` | Error completion |

### ToolTracker

Tracks tool calls with timing and statistics:

```python
from helix.debug import ToolTracker

tracker = ToolTracker(phase_id="01-foundation")

# On tool_use event
tracker.start_tool(
    tool_use_id="tu_123",
    tool_name="Read",
    tool_input={"file_path": "/foo/bar.py"}
)

# On tool_result event
tracker.end_tool(tool_use_id="tu_123", result="content")

# Get statistics
stats = tracker.get_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"Most used: {stats['most_used_tool']}")
print(f"By tool: {stats['by_tool']}")

# Save to file
tracker.save_to_file(Path("logs/tool-calls.jsonl"))
```

**Statistics Provided:**

- Total call count
- Calls per tool with count, duration, failures
- Most used tool
- Slowest tool (by average duration)
- Pending calls

### CostCalculator

Tracks costs per phase and project:

```python
from helix.debug import CostCalculator

calc = CostCalculator(project_id="my-project", model="claude-sonnet-4")

# Start phase
calc.start_phase("01-foundation")

# Record usage (from stream-json result event)
calc.record_usage(
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.0234  # Direct from Claude CLI
)

# Record tool calls
calc.record_tool_call()

# End phase
phase_cost = calc.end_phase()
print(f"Phase cost: ${phase_cost.cost_usd:.4f}")

# Get project totals
totals = calc.get_project_totals()
print(f"Total cost: ${totals['total_cost_usd']:.4f}")
print(f"Total tokens: {totals['total_tokens']}")

# Save to file
calc.save_to_file(Path("logs/costs.json"))
```

**Supported Models:**

| Model | Input (per 1M) | Output (per 1M) |
|-------|----------------|-----------------|
| claude-opus-4 | $15.00 | $75.00 |
| claude-sonnet-4 | $3.00 | $15.00 |
| claude-haiku-3.5 | $0.80 | $4.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |

### TerminalDashboard

Live terminal display during execution:

```python
from helix.debug.live_dashboard import TerminalDashboard
import asyncio

dashboard = TerminalDashboard(
    phase_id="01-foundation",
    model="claude-sonnet-4"
)

# Run with process stdout
summary = await dashboard.run(process.stdout)
```

**Dashboard Display:**

```
╔══════════════════════════════════════════════════════════════════╗
║  HELIX Debug Dashboard                                           ║
║  Phase: 01-foundation                                            ║
╠══════════════════════════════════════════════════════════════════╣
║  Session: abc123...         Elapsed:    45.3s                    ║
╠══════════════════════════════════════════════════════════════════╣
║  ▶ Executing: Read                                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Tool Calls: 15    (pending: 1)                                  ║
║    Read           8 ████████████████████    125ms                ║
║    Write          4 ████████              1250ms                 ║
║    Bash           3 ██████                 450ms                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Tokens:    15,234 in /    8,521 out                             ║
║  Cost:    $  0.0892 USD                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Recent Tool Calls:                                              ║
║    ✓ Read             125ms                                      ║
║    ✓ Write           1250ms                                      ║
║    ✗ Bash              45ms                                      ║
╚══════════════════════════════════════════════════════════════════╝
```

### SSE Dashboard

Stream events to web clients:

```python
from fastapi import FastAPI
from helix.debug.live_dashboard import create_debug_router

app = FastAPI()
app.include_router(create_debug_router())

# Endpoints:
# GET /debug/stream - SSE event stream
# GET /debug/stats  - Current statistics
# GET /debug/events - All events
```

**SSE Event Format:**

```
event: debug
data: {"type": "tool_call_started", "phase_id": "01", "tool_name": "Read", ...}

event: debug
data: {"type": "cost_update", "phase_id": "01", "cost_usd": 0.0234, ...}
```

---

## Control Scripts

### claude-wrapper.sh

Run Claude CLI with debug output:

```bash
# Basic usage
./control/claude-wrapper.sh -- --print "Your prompt"

# With options
./control/claude-wrapper.sh \
    -o ./debug-logs \
    -m claude-opus-4 \
    -v \
    -- --print "Complex task"
```

**Options:**

| Option | Description |
|--------|-------------|
| `-o, --output DIR` | Log output directory (default: ./logs) |
| `-m, --model MODEL` | Model to use (default: claude-sonnet-4) |
| `-v, --verbose` | Show output in terminal |
| `-h, --help` | Show help |

### helix-debug.sh

Full debug session with dashboard:

```bash
# Terminal dashboard
./control/helix-debug.sh -d phases/01-analysis

# Web dashboard on port 9000
./control/helix-debug.sh -w -p 9000 phases/01-analysis

# Both
./control/helix-debug.sh -d -w phases/01-analysis
```

**Options:**

| Option | Description |
|--------|-------------|
| `-d, --dashboard` | Launch terminal dashboard |
| `-w, --web` | Launch web dashboard (SSE) |
| `-p, --port PORT` | Web dashboard port (default: 8080) |
| `-m, --model MODEL` | Model to use |
| `-o, --output DIR` | Output directory |

---

## Claude CLI Stream-JSON Format

The `--output-format stream-json` flag produces NDJSON (Newline Delimited JSON):

```jsonl
{"type":"system","subtype":"init","session_id":"abc123","tools":["Read","Write","Bash"]}
{"type":"assistant","subtype":"text","text":"Ich lese die Datei..."}
{"type":"assistant","subtype":"tool_use","tool":"Read","tool_input":{"file_path":"/foo/bar.py"},"tool_use_id":"tu_1"}
{"type":"user","subtype":"tool_result","tool_use_id":"tu_1","content":"...file content..."}
{"type":"result","subtype":"success","cost_usd":0.0234,"input_tokens":1500,"output_tokens":800}
```

**Event Structure:**

| Field | Description |
|-------|-------------|
| `type` | Event category (system, assistant, user, result) |
| `subtype` | Specific event type (init, text, tool_use, etc.) |
| `session_id` | Claude session identifier |
| `tool` | Tool name (for tool_use events) |
| `tool_input` | Tool parameters (for tool_use events) |
| `tool_use_id` | Links tool_use to tool_result |
| `content` | Tool result content |
| `cost_usd` | Total cost in USD (for result events) |
| `input_tokens` | Input tokens used |
| `output_tokens` | Output tokens generated |

---

## Integration with ClaudeRunner

Add debug mode to ClaudeRunner:

```python
from helix.claude_runner import ClaudeRunner
from helix.debug import StreamParser, ToolTracker, CostCalculator

runner = ClaudeRunner()

async def on_event(event):
    # Handle debug events
    pass

result, debug_summary = await runner.run_phase_debug(
    phase_dir=Path("phases/01-analysis"),
    on_event=on_event,
    model="claude-sonnet-4",
)

print(f"Tool calls: {debug_summary['tool_stats']['total_calls']}")
print(f"Cost: ${debug_summary['cost_summary']['total_cost_usd']:.4f}")
```

---

## Output Files

Debug sessions produce these files:

| File | Format | Content |
|------|--------|---------|
| `stream-{timestamp}.jsonl` | NDJSON | Raw Claude CLI output |
| `tool-calls.jsonl` | JSONL | Processed tool calls |
| `costs.json` | JSON | Cost breakdown |
| `summary-{timestamp}.json` | JSON | Full session summary |

---

## Troubleshooting

### No events received

1. Verify Claude CLI version supports `--output-format stream-json`
2. Check that `--verbose` is enabled
3. Ensure stdout is not being redirected

### Cost shows as 0

1. Result events may not include cost_usd
2. Check that tokens are being recorded
3. Verify model name matches MODEL_COSTS keys

### Dashboard not updating

1. Ensure callbacks are async
2. Check for exceptions in event handlers
3. Verify StreamParser is receiving lines

---

## See Also

- [ADR-013: Debug & Observability Engine](../adr/013-debug-observability-engine.md)
- [ADR-003: Observability & Debugging](../adr/003-observability-and-debugging.md)
- [Claude CLI Documentation](https://docs.anthropic.com/claude-code/cli)
