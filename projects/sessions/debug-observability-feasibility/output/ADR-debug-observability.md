---
adr_id: "013"
title: "Debug & Observability Engine für HELIX Workflows"
status: Proposed
component_type: SERVICE
classification: NEW
change_scope: major
domain: helix
language: python
skills:
  - helix
  - observability
files:
  create:
    - src/helix/debug/__init__.py
    - src/helix/debug/stream_parser.py
    - src/helix/debug/tool_tracker.py
    - src/helix/debug/live_dashboard.py
    - tests/debug/test_stream_parser.py
    - control/helix-debug.sh
  modify:
    - control/claude-wrapper.sh
  docs:
    - docs/DEBUGGING.md
depends_on: ["003", "011"]
---

# ADR-013: Debug & Observability Engine für HELIX Workflows

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

HELIX führt Claude Code Instanzen aus, aber wir haben **keine Live-Sichtbarkeit** auf:

1. **Tool Calls**: Welche Tools werden aufgerufen? Mit welchen Parametern?
2. **Fortschritt**: Was passiert gerade in der Phase? Wo steckt der Workflow fest?
3. **Kosten**: Was kosten einzelne Phasen? Was kostet das Projekt insgesamt?
4. **Debugging**: Warum ist eine Phase fehlgeschlagen? Was war der letzte Tool Call?

### Aktuelle Situation

```
┌─────────────────────────────────────────────────────────────────┐
│  HEUTE: Blackbox                                                 │
│                                                                  │
│  ClaudeRunner                                                    │
│     │                                                            │
│     ├── --print                                                  │
│     ├── --dangerously-skip-permissions                          │
│     │                                                            │
│     └── stdout/stderr → Plain Text (unstrukturiert)             │
│                                                                  │
│  Problem:                                                        │
│  • Keine Tool Call Sichtbarkeit                                  │
│  • Keine Token/Cost Informationen                                │
│  • Keine strukturierte Analyse möglich                           │
└─────────────────────────────────────────────────────────────────┘
```

### Entdeckung: Claude CLI stream-json

Die Claude CLI hat ein eingebautes Feature für strukturierte Observability:

```bash
claude --output-format stream-json --verbose
```

Dies gibt strukturierte NDJSON Events aus:

```jsonl
{"type":"system","subtype":"init","session_id":"abc123","tools":["Read","Write","Bash",...]}
{"type":"assistant","subtype":"text","text":"Ich lese die Datei...","session_id":"abc123"}
{"type":"assistant","subtype":"tool_use","tool":"Read","tool_input":{"file_path":"/foo/bar.py"},"tool_use_id":"tu_1"}
{"type":"user","subtype":"tool_result","tool_use_id":"tu_1","content":"...file content..."}
{"type":"result","subtype":"success","cost_usd":0.0234,"input_tokens":1500,"output_tokens":800,"session_id":"abc123"}
```

### Warum muss es gelöst werden?

1. **Debugging**: Ohne Sichtbarkeit können wir nicht verstehen warum Phasen fehlschlagen
2. **Cost Control**: Ohne Tracking können wir keine Budgets setzen
3. **Optimization**: Ohne Metriken können wir nicht optimieren
4. **Compliance**: Audit-Logs benötigen strukturierte Tool Call History

### Was passiert wenn wir nichts tun?

- HELIX bleibt eine Blackbox
- Debugging erfolgt durch manuelle Log-Analyse
- Kosten-Tracking ist Schätzung statt Messung
- Kein Live-Dashboard möglich

---

## Entscheidung

### Wir entscheiden uns für:

Eine **Debug & Observability Engine** die:
1. Claude CLI mit `--output-format stream-json --verbose` aufruft
2. Die NDJSON Events live parst
3. Tool Calls, Text, und Metriken extrahiert
4. Ein Live Dashboard über SSE bereitstellt
5. Kosten pro Phase/Projekt trackt

### Diese Entscheidung beinhaltet:

```
┌─────────────────────────────────────────────────────────────────┐
│  ZIEL: Live Observability                                        │
│                                                                  │
│  ClaudeRunner (modified)                                         │
│     │                                                            │
│     ├── --output-format stream-json                              │
│     ├── --verbose                                                │
│     ├── --dangerously-skip-permissions                          │
│     │                                                            │
│     └── stdout → StreamParser                                    │
│                    │                                             │
│                    ├── ToolTracker  → tool_call events           │
│                    ├── CostCalculator → cost metrics             │
│                    └── EventEmitter → SSE Dashboard              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Warum diese Lösung?

1. **Native Support**: Claude CLI bietet stream-json bereits an
2. **Keine Middleware**: Direkte Integration, keine zusätzlichen Services
3. **Live Streaming**: Events kommen in Echtzeit
4. **Vollständige Daten**: Token Usage, Costs, Tool Calls alles dabei

### Welche Alternativen wurden betrachtet?

1. **Log-Parsing nach Ausführung**: Nicht gewählt weil keine Live-Sichtbarkeit
2. **Prometheus/Grafana**: Nicht gewählt weil zu viel Infrastruktur-Overhead
3. **Eigenes Tracing**: Nicht gewählt weil Claude CLI bereits alles liefert

---

## Implementation

### 1. Stream Parser (`src/helix/debug/stream_parser.py`)

Parst NDJSON Events von Claude CLI:

```python
# src/helix/debug/stream_parser.py
"""Parse Claude CLI stream-json output into structured events."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable
import json


class EventType(Enum):
    """Types of events from Claude CLI stream-json."""
    SYSTEM_INIT = "system.init"
    ASSISTANT_TEXT = "assistant.text"
    ASSISTANT_TOOL_USE = "assistant.tool_use"
    USER_TOOL_RESULT = "user.tool_result"
    RESULT_SUCCESS = "result.success"
    RESULT_ERROR = "result.error"


@dataclass
class StreamEvent:
    """A single event from Claude CLI stream-json output."""
    event_type: EventType
    raw_data: dict[str, Any]
    session_id: str | None = None
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    # Text events
    text: str | None = None

    # Tool events
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    tool_result: str | None = None

    # Result events
    success: bool | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    # Init events
    tools_available: list[str] | None = None


# Type alias for event callback
EventCallback = Callable[[StreamEvent], Awaitable[None]]


class StreamParser:
    """Parse Claude CLI stream-json NDJSON output.

    Usage:
        parser = StreamParser()

        async def on_event(event: StreamEvent):
            if event.event_type == EventType.ASSISTANT_TOOL_USE:
                print(f"Tool call: {event.tool_name}")

        parser.on_event(on_event)

        # Feed lines from Claude CLI stdout
        for line in stdout.split('\\n'):
            await parser.parse_line(line)

        # Get summary at the end
        summary = parser.get_summary()
    """

    def __init__(self):
        self._callbacks: list[EventCallback] = []
        self._events: list[StreamEvent] = []
        self._session_id: str | None = None
        self._tools_available: list[str] = []
        self._total_cost: float = 0.0
        self._input_tokens: int = 0
        self._output_tokens: int = 0

    def on_event(self, callback: EventCallback) -> None:
        """Register an event callback."""
        self._callbacks.append(callback)

    async def parse_line(self, line: str) -> StreamEvent | None:
        """Parse a single NDJSON line and emit event.

        Args:
            line: A single line of NDJSON output from Claude CLI.

        Returns:
            The parsed StreamEvent, or None if line is empty/invalid.
        """
        line = line.strip()
        if not line:
            return None

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON, might be plain text output
            return None

        event = self._parse_event(data)
        if event:
            self._events.append(event)

            # Update running totals
            if event.cost_usd is not None:
                self._total_cost = event.cost_usd
            if event.input_tokens is not None:
                self._input_tokens = event.input_tokens
            if event.output_tokens is not None:
                self._output_tokens = event.output_tokens

            # Notify callbacks
            for callback in self._callbacks:
                await callback(event)

        return event

    def _parse_event(self, data: dict[str, Any]) -> StreamEvent | None:
        """Parse raw JSON into StreamEvent."""
        event_type_str = data.get("type", "")
        subtype = data.get("subtype", "")
        combined_type = f"{event_type_str}.{subtype}" if subtype else event_type_str

        # Map to EventType
        try:
            event_type = EventType(combined_type)
        except ValueError:
            # Unknown event type, skip
            return None

        session_id = data.get("session_id")
        if session_id:
            self._session_id = session_id

        event = StreamEvent(
            event_type=event_type,
            raw_data=data,
            session_id=self._session_id,
        )

        # Parse type-specific fields
        if event_type == EventType.SYSTEM_INIT:
            event.tools_available = data.get("tools", [])
            self._tools_available = event.tools_available

        elif event_type == EventType.ASSISTANT_TEXT:
            event.text = data.get("text", "")

        elif event_type == EventType.ASSISTANT_TOOL_USE:
            event.tool_name = data.get("tool")
            event.tool_input = data.get("tool_input", {})
            event.tool_use_id = data.get("tool_use_id")

        elif event_type == EventType.USER_TOOL_RESULT:
            event.tool_use_id = data.get("tool_use_id")
            event.tool_result = data.get("content", "")[:1000]  # Truncate large results

        elif event_type in (EventType.RESULT_SUCCESS, EventType.RESULT_ERROR):
            event.success = event_type == EventType.RESULT_SUCCESS
            event.cost_usd = data.get("cost_usd")
            event.input_tokens = data.get("input_tokens")
            event.output_tokens = data.get("output_tokens")

        return event

    def get_tool_calls(self) -> list[StreamEvent]:
        """Get all tool call events."""
        return [e for e in self._events
                if e.event_type == EventType.ASSISTANT_TOOL_USE]

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        tool_calls = self.get_tool_calls()
        tool_counts: dict[str, int] = {}
        for tc in tool_calls:
            name = tc.tool_name or "unknown"
            tool_counts[name] = tool_counts.get(name, 0) + 1

        return {
            "session_id": self._session_id,
            "total_events": len(self._events),
            "tool_calls": len(tool_calls),
            "tool_counts": tool_counts,
            "tools_available": self._tools_available,
            "cost_usd": self._total_cost,
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
        }
```

### 2. Tool Tracker (`src/helix/debug/tool_tracker.py`)

Trackt Tool Calls mit Timing und Ergebnissen:

```python
# src/helix/debug/tool_tracker.py
"""Track tool calls with timing, parameters, and results."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json
from pathlib import Path


@dataclass
class ToolCall:
    """A tracked tool call with full context."""
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None = None
    result: str | None = None
    success: bool | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "tool_use_id": self.tool_use_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_preview": self.result[:200] if self.result else None,
            "success": self.success,
            "duration_ms": self.duration_ms,
        }


class ToolTracker:
    """Track all tool calls for a phase execution.

    Usage:
        tracker = ToolTracker(phase_id="01-foundation")

        # On tool_use event
        tracker.start_tool(tool_use_id, tool_name, tool_input)

        # On tool_result event
        tracker.end_tool(tool_use_id, result)

        # Get summary
        stats = tracker.get_stats()
        print(f"Total calls: {stats['total_calls']}")
        print(f"Most used: {stats['most_used_tool']}")

        # Save to file
        tracker.save_to_file(phase_dir / "logs" / "tool-calls.jsonl")
    """

    def __init__(self, phase_id: str):
        self.phase_id = phase_id
        self._pending: dict[str, ToolCall] = {}  # tool_use_id -> ToolCall
        self._completed: list[ToolCall] = []

    def start_tool(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any]
    ) -> ToolCall:
        """Record the start of a tool call."""
        call = ToolCall(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            started_at=datetime.now(),
        )
        self._pending[tool_use_id] = call
        return call

    def end_tool(
        self,
        tool_use_id: str,
        result: str | None = None,
        success: bool = True
    ) -> ToolCall | None:
        """Record the completion of a tool call."""
        if tool_use_id not in self._pending:
            return None

        call = self._pending.pop(tool_use_id)
        call.completed_at = datetime.now()
        call.result = result
        call.success = success
        call.duration_ms = (
            (call.completed_at - call.started_at).total_seconds() * 1000
        )

        self._completed.append(call)
        return call

    def get_all_calls(self) -> list[ToolCall]:
        """Get all completed tool calls."""
        return self._completed.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about tool usage."""
        if not self._completed:
            return {
                "total_calls": 0,
                "total_duration_ms": 0,
                "by_tool": {},
                "most_used_tool": None,
                "slowest_tool": None,
            }

        by_tool: dict[str, dict[str, Any]] = {}

        for call in self._completed:
            name = call.tool_name
            if name not in by_tool:
                by_tool[name] = {
                    "count": 0,
                    "total_duration_ms": 0,
                    "avg_duration_ms": 0,
                    "failures": 0,
                }

            by_tool[name]["count"] += 1
            if call.duration_ms:
                by_tool[name]["total_duration_ms"] += call.duration_ms
            if call.success is False:
                by_tool[name]["failures"] += 1

        # Calculate averages
        for name in by_tool:
            count = by_tool[name]["count"]
            if count > 0:
                by_tool[name]["avg_duration_ms"] = (
                    by_tool[name]["total_duration_ms"] / count
                )

        # Find most used and slowest
        most_used = max(by_tool.keys(), key=lambda t: by_tool[t]["count"])
        slowest = max(by_tool.keys(), key=lambda t: by_tool[t]["avg_duration_ms"])

        total_duration = sum(
            c.duration_ms for c in self._completed
            if c.duration_ms is not None
        )

        return {
            "phase_id": self.phase_id,
            "total_calls": len(self._completed),
            "total_duration_ms": total_duration,
            "by_tool": by_tool,
            "most_used_tool": most_used,
            "slowest_tool": slowest,
            "pending_calls": len(self._pending),
        }

    def save_to_file(self, file_path: Path) -> None:
        """Save all tool calls to JSONL file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for call in self._completed:
                f.write(json.dumps(call.to_dict(), ensure_ascii=False) + "\n")

    def get_recent(self, n: int = 5) -> list[ToolCall]:
        """Get the n most recent tool calls."""
        return self._completed[-n:]
```

### 3. Cost Calculator (`src/helix/debug/cost_calculator.py`)

Berechnet und trackt Kosten:

```python
# src/helix/debug/cost_calculator.py
"""Calculate and track costs per phase and project."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json
from pathlib import Path


# Cost per 1M tokens (USD) - Updated December 2024
MODEL_COSTS: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},

    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},

    # Default fallback
    "default": {"input": 3.00, "output": 15.00},
}


@dataclass
class PhaseCost:
    """Cost breakdown for a single phase."""
    phase_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    tool_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds(),
            "tool_calls": self.tool_calls,
        }

    def duration_seconds(self) -> float | None:
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class CostCalculator:
    """Calculate and track costs for HELIX phases.

    Usage:
        calc = CostCalculator(project_id="my-project")

        # Start a phase
        calc.start_phase("01-foundation", model="claude-sonnet-4")

        # Record usage (called when stream-json result event arrives)
        calc.record_usage(input_tokens=1500, output_tokens=800, cost_usd=0.0234)

        # End phase
        summary = calc.end_phase()

        # Get project totals
        totals = calc.get_project_totals()
        print(f"Total cost: ${totals['total_cost_usd']:.4f}")
    """

    def __init__(self, project_id: str, model: str = "claude-sonnet-4"):
        self.project_id = project_id
        self.default_model = model
        self._phases: dict[str, PhaseCost] = {}
        self._current_phase: PhaseCost | None = None

    def start_phase(
        self,
        phase_id: str,
        model: str | None = None
    ) -> PhaseCost:
        """Start tracking a new phase."""
        phase = PhaseCost(
            phase_id=phase_id,
            model=model or self.default_model,
        )
        self._current_phase = phase
        return phase

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | None = None,
    ) -> None:
        """Record token usage for current phase.

        If cost_usd is provided (from Claude CLI), use it directly.
        Otherwise, calculate from tokens.
        """
        if not self._current_phase:
            return

        self._current_phase.input_tokens += input_tokens
        self._current_phase.output_tokens += output_tokens

        if cost_usd is not None:
            self._current_phase.cost_usd = cost_usd
        else:
            # Calculate from tokens
            self._current_phase.cost_usd = self._calculate_cost(
                input_tokens=self._current_phase.input_tokens,
                output_tokens=self._current_phase.output_tokens,
                model=self._current_phase.model,
            )

    def record_tool_call(self) -> None:
        """Record a tool call for current phase."""
        if self._current_phase:
            self._current_phase.tool_calls += 1

    def end_phase(self) -> PhaseCost | None:
        """End the current phase and return its cost data."""
        if not self._current_phase:
            return None

        self._current_phase.completed_at = datetime.now()
        self._phases[self._current_phase.phase_id] = self._current_phase

        result = self._current_phase
        self._current_phase = None
        return result

    def get_phase(self, phase_id: str) -> PhaseCost | None:
        """Get cost data for a specific phase."""
        return self._phases.get(phase_id)

    def get_current_phase(self) -> PhaseCost | None:
        """Get the current (in-progress) phase."""
        return self._current_phase

    def get_project_totals(self) -> dict[str, Any]:
        """Get aggregated cost data for the entire project."""
        total_input = sum(p.input_tokens for p in self._phases.values())
        total_output = sum(p.output_tokens for p in self._phases.values())
        total_cost = sum(p.cost_usd for p in self._phases.values())
        total_tool_calls = sum(p.tool_calls for p in self._phases.values())
        total_duration = sum(
            p.duration_seconds() or 0
            for p in self._phases.values()
        )

        return {
            "project_id": self.project_id,
            "phases_completed": len(self._phases),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 6),
            "total_tool_calls": total_tool_calls,
            "total_duration_seconds": round(total_duration, 2),
            "cost_per_phase": {
                pid: round(p.cost_usd, 6)
                for pid, p in self._phases.items()
            },
        }

    def save_to_file(self, file_path: Path) -> None:
        """Save project cost data to JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project_id": self.project_id,
            "generated_at": datetime.now().isoformat(),
            "totals": self.get_project_totals(),
            "phases": {
                pid: p.to_dict()
                for pid, p in self._phases.items()
            },
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """Calculate cost in USD for given tokens and model."""
        # Find matching model costs
        costs = MODEL_COSTS.get("default")

        model_lower = model.lower()
        for model_key, model_costs in MODEL_COSTS.items():
            if model_key in model_lower or model_lower in model_key:
                costs = model_costs
                break

        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost
```

### 4. Events Module (`src/helix/debug/events.py`)

Event-Typen für SSE Dashboard:

```python
# src/helix/debug/events.py
"""Debug event types for SSE streaming to dashboards."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any
import json


class DebugEventType(Enum):
    """Types of debug events emitted to dashboards."""

    # Phase lifecycle
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"

    # Tool tracking
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"

    # Assistant output
    ASSISTANT_TEXT = "assistant_text"

    # Cost/metrics
    COST_UPDATE = "cost_update"
    TOKENS_UPDATE = "tokens_update"

    # Session
    SESSION_INITIALIZED = "session_initialized"
    SESSION_COMPLETED = "session_completed"


@dataclass
class DebugEvent:
    """A debug event for SSE streaming."""

    event_type: DebugEventType
    phase_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse(self) -> str:
        """Format as SSE event string."""
        event_data = {
            "type": self.event_type.value,
            "phase_id": self.phase_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }
        json_str = json.dumps(event_data, default=str)
        return f"event: debug\ndata: {json_str}\n\n"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.event_type.value,
            "phase_id": self.phase_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


# Factory functions for common events

def tool_call_started(
    phase_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str,
) -> DebugEvent:
    """Create a tool_call_started event."""
    # Truncate large inputs for display
    display_input = {
        k: (str(v)[:100] + "..." if len(str(v)) > 100 else v)
        for k, v in tool_input.items()
    }

    return DebugEvent(
        event_type=DebugEventType.TOOL_CALL_STARTED,
        phase_id=phase_id,
        data={
            "tool_name": tool_name,
            "tool_input": display_input,
            "tool_use_id": tool_use_id,
        },
    )


def tool_call_completed(
    phase_id: str,
    tool_name: str,
    tool_use_id: str,
    duration_ms: float,
    success: bool = True,
) -> DebugEvent:
    """Create a tool_call_completed event."""
    return DebugEvent(
        event_type=(
            DebugEventType.TOOL_CALL_COMPLETED if success
            else DebugEventType.TOOL_CALL_FAILED
        ),
        phase_id=phase_id,
        data={
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        },
    )


def cost_update(
    phase_id: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> DebugEvent:
    """Create a cost_update event."""
    return DebugEvent(
        event_type=DebugEventType.COST_UPDATE,
        phase_id=phase_id,
        data={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost_usd, 6),
        },
    )


def assistant_text(phase_id: str, text: str) -> DebugEvent:
    """Create an assistant_text event."""
    return DebugEvent(
        event_type=DebugEventType.ASSISTANT_TEXT,
        phase_id=phase_id,
        data={"text": text[:500]},  # Truncate for SSE
    )
```

### 5. Dashboard CLI (`src/helix/debug/dashboard.py`)

Terminal-Dashboard für Live-Monitoring:

```python
# src/helix/debug/dashboard.py
"""Terminal dashboard for live Claude CLI monitoring."""

from dataclasses import dataclass
from datetime import datetime
import asyncio
import sys
from typing import Any

from .stream_parser import StreamParser, StreamEvent, EventType
from .tool_tracker import ToolTracker
from .cost_calculator import CostCalculator


class TerminalDashboard:
    """Live terminal dashboard for Claude CLI execution.

    Shows:
    - Current tool being executed
    - Tool call history (last 5)
    - Running cost
    - Token usage

    Usage:
        dashboard = TerminalDashboard(phase_id="01-foundation")

        # Connect to stream parser
        parser = StreamParser()
        parser.on_event(dashboard.handle_event)

        # Or run standalone
        await dashboard.run(process_stdout)
    """

    CLEAR_SCREEN = "\033[2J\033[H"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    def __init__(self, phase_id: str, model: str = "claude-sonnet-4"):
        self.phase_id = phase_id
        self.parser = StreamParser()
        self.tool_tracker = ToolTracker(phase_id)
        self.cost_calc = CostCalculator(project_id="live", model=model)

        self._current_tool: str | None = None
        self._last_text: str = ""
        self._start_time = datetime.now()

        # Register as event handler
        self.parser.on_event(self._handle_event)

        # Start phase cost tracking
        self.cost_calc.start_phase(phase_id)

    async def _handle_event(self, event: StreamEvent) -> None:
        """Handle a stream event and update dashboard."""
        if event.event_type == EventType.ASSISTANT_TOOL_USE:
            self._current_tool = event.tool_name
            if event.tool_use_id and event.tool_name and event.tool_input:
                self.tool_tracker.start_tool(
                    event.tool_use_id,
                    event.tool_name,
                    event.tool_input,
                )
                self.cost_calc.record_tool_call()

        elif event.event_type == EventType.USER_TOOL_RESULT:
            self._current_tool = None
            if event.tool_use_id:
                self.tool_tracker.end_tool(
                    event.tool_use_id,
                    event.tool_result,
                )

        elif event.event_type == EventType.ASSISTANT_TEXT:
            self._last_text = event.text or ""

        elif event.event_type in (EventType.RESULT_SUCCESS, EventType.RESULT_ERROR):
            if event.input_tokens and event.output_tokens:
                self.cost_calc.record_usage(
                    input_tokens=event.input_tokens,
                    output_tokens=event.output_tokens,
                    cost_usd=event.cost_usd,
                )

        # Redraw dashboard
        self._render()

    def _render(self) -> None:
        """Render the dashboard to terminal."""
        elapsed = (datetime.now() - self._start_time).total_seconds()
        stats = self.tool_tracker.get_stats()
        cost_data = self.cost_calc.get_current_phase()

        lines = [
            f"{self.BOLD}╔══════════════════════════════════════════════════════════════╗{self.RESET}",
            f"{self.BOLD}║  HELIX Debug Dashboard - Phase: {self.phase_id:<26} ║{self.RESET}",
            f"{self.BOLD}╠══════════════════════════════════════════════════════════════╣{self.RESET}",
            f"║  Elapsed: {elapsed:>8.1f}s                                         ║",
            f"╠══════════════════════════════════════════════════════════════╣",
        ]

        # Current activity
        if self._current_tool:
            lines.append(f"║  {self.YELLOW}▶ Executing:{self.RESET} {self._current_tool:<45} ║")
        else:
            lines.append(f"║  {self.GREEN}● Idle{self.RESET}                                                   ║")

        lines.append(f"╠══════════════════════════════════════════════════════════════╣")

        # Tool stats
        lines.append(f"║  {self.BOLD}Tool Calls:{self.RESET} {stats['total_calls']:<5}                                      ║")

        # Tool breakdown
        by_tool = stats.get("by_tool", {})
        for tool_name, data in list(by_tool.items())[:4]:
            count = data["count"]
            bar = "█" * min(count, 20)
            lines.append(f"║    {tool_name:<12} {count:>3} {bar:<20}       ║")

        lines.append(f"╠══════════════════════════════════════════════════════════════╣")

        # Cost & tokens
        if cost_data:
            lines.append(f"║  {self.BOLD}Tokens:{self.RESET} {cost_data.input_tokens:>8} in / {cost_data.output_tokens:>8} out              ║")
            lines.append(f"║  {self.BOLD}Cost:{self.RESET}   ${cost_data.cost_usd:>8.4f} USD                               ║")
        else:
            lines.append(f"║  {self.BOLD}Tokens:{self.RESET} (waiting for result)                              ║")
            lines.append(f"║  {self.BOLD}Cost:{self.RESET}   (calculating...)                                  ║")

        lines.append(f"╠══════════════════════════════════════════════════════════════╣")

        # Recent calls
        lines.append(f"║  {self.BOLD}Recent Tool Calls:{self.RESET}                                          ║")
        for call in self.tool_tracker.get_recent(3):
            status = f"{self.GREEN}✓{self.RESET}" if call.success else f"{self.RED}✗{self.RESET}"
            duration = f"{call.duration_ms:.0f}ms" if call.duration_ms else "..."
            lines.append(f"║    {status} {call.tool_name:<15} {duration:>8}                       ║")

        lines.append(f"╚══════════════════════════════════════════════════════════════╝")

        # Output
        print(self.CLEAR_SCREEN, end="")
        print("\n".join(lines))

    async def run(self, stdout_stream: asyncio.StreamReader) -> dict[str, Any]:
        """Run dashboard with live output stream.

        Args:
            stdout_stream: Async stream from Claude CLI stdout.

        Returns:
            Final summary including tool stats and costs.
        """
        self._render()

        while True:
            line = await stdout_stream.readline()
            if not line:
                break

            line_str = line.decode("utf-8", errors="replace").strip()
            await self.parser.parse_line(line_str)

        # Final render
        self._render()

        # End cost tracking
        self.cost_calc.end_phase()

        return {
            "tool_stats": self.tool_tracker.get_stats(),
            "cost_summary": self.cost_calc.get_project_totals(),
            "parser_summary": self.parser.get_summary(),
        }
```

### 6. Control Script (`control/debug-claude.sh`)

Wrapper zum Starten von Claude mit Debug-Output:

```bash
#!/bin/bash
# control/debug-claude.sh
# Run Claude CLI with stream-json output for debugging

set -euo pipefail

# Defaults
PHASE_DIR="${1:-.}"
MODEL="${CLAUDE_MODEL:-claude-sonnet-4}"
OUTPUT_DIR="${PHASE_DIR}/logs"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Run Claude with stream-json
echo "Starting Claude in debug mode..."
echo "  Phase directory: $PHASE_DIR"
echo "  Model: $MODEL"
echo "  Output: $OUTPUT_DIR"

# Use script to capture output while preserving interactivity
stdbuf -oL -eL claude \
    --print \
    --output-format stream-json \
    --verbose \
    --dangerously-skip-permissions \
    2>&1 | tee "$OUTPUT_DIR/claude-stream-${TIMESTAMP}.jsonl"

echo ""
echo "Debug session complete. Output saved to:"
echo "  $OUTPUT_DIR/claude-stream-${TIMESTAMP}.jsonl"
```

### 7. ClaudeRunner Integration

Änderungen an `src/helix/claude_runner.py`:

```python
# In ClaudeRunner._build_command() - add new parameter

def _build_command(
    self,
    extra_args: list[str] | None = None,
    debug_mode: bool = False,
) -> list[str]:
    """Build the Claude CLI command.

    Args:
        extra_args: Additional arguments for Claude CLI.
        debug_mode: If True, use stream-json output format.
    """
    cmd = []

    if self.use_stdbuf:
        cmd.extend(["stdbuf", "-oL", "-eL"])

    cmd.extend([
        self.claude_cmd,
        "--print",
        "--dangerously-skip-permissions",
    ])

    if debug_mode:
        cmd.extend([
            "--output-format", "stream-json",
            "--verbose",
        ])

    if extra_args:
        cmd.extend(extra_args)

    return cmd


# New method for debug streaming
async def run_phase_debug(
    self,
    phase_dir: Path,
    on_event: Callable[[StreamEvent], Awaitable[None]],
    model: str | None = None,
    prompt: str | None = None,
    timeout: int | None = None,
) -> tuple[ClaudeResult, dict[str, Any]]:
    """Run Claude with debug mode and structured event streaming.

    Args:
        phase_dir: Phase directory to run in.
        on_event: Callback for each StreamEvent.
        model: Optional model to use.
        prompt: Optional prompt override.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (ClaudeResult, debug_summary).
    """
    from .debug.stream_parser import StreamParser
    from .debug.tool_tracker import ToolTracker
    from .debug.cost_calculator import CostCalculator

    parser = StreamParser()
    tracker = ToolTracker(phase_id=phase_dir.name)
    costs = CostCalculator(project_id=phase_dir.parent.parent.name)
    costs.start_phase(phase_dir.name)

    async def handle_event(event: StreamEvent) -> None:
        # Update tracker/costs
        if event.event_type == EventType.ASSISTANT_TOOL_USE:
            if event.tool_use_id and event.tool_name:
                tracker.start_tool(
                    event.tool_use_id,
                    event.tool_name,
                    event.tool_input or {},
                )
                costs.record_tool_call()

        elif event.event_type == EventType.USER_TOOL_RESULT:
            if event.tool_use_id:
                tracker.end_tool(event.tool_use_id, event.tool_result)

        elif event.event_type in (EventType.RESULT_SUCCESS, EventType.RESULT_ERROR):
            if event.input_tokens and event.output_tokens:
                costs.record_usage(
                    input_tokens=event.input_tokens,
                    output_tokens=event.output_tokens,
                    cost_usd=event.cost_usd,
                )

        # Forward to caller
        await on_event(event)

    parser.on_event(handle_event)

    # Run with debug mode
    cmd = self._build_command(debug_mode=True)
    # ... rest of process execution similar to run_phase_streaming
    # but parsing NDJSON instead of plain text

    costs.end_phase()

    summary = {
        "tool_stats": tracker.get_stats(),
        "cost_summary": costs.get_project_totals(),
        "parser_summary": parser.get_summary(),
    }

    return result, summary
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/DEBUG-OBSERVABILITY.md` | Neue Datei - Vollständige Dokumentation |
| `skills/helix/debug/SKILL.md` | Neuer Skill für Debug-Nutzung |
| `CLAUDE.md` | Section für Debug-Modus |
| `docs/ARCHITECTURE-MODULES.md` | Debug-Modul hinzufügen |

### Neue Dokumentation

- [ ] `docs/DEBUG-OBSERVABILITY.md` mit:
  - Stream-JSON Format Beschreibung
  - Dashboard Nutzung
  - API Endpoints für Debug Events
  - Kosten-Tracking Konfiguration

---

## Akzeptanzkriterien

### 1. Stream Parser

- [ ] StreamParser parst alle Claude CLI stream-json Events korrekt
- [ ] EventType enum deckt alle relevanten Event-Typen ab
- [ ] Callbacks werden für jedes Event aufgerufen
- [ ] get_summary() liefert korrekte Aggregation

### 2. Tool Tracking

- [ ] ToolTracker erfasst Start/Ende aller Tool Calls
- [ ] Timing (duration_ms) wird korrekt berechnet
- [ ] get_stats() zeigt Tool-Breakdown
- [ ] JSONL Export funktioniert

### 3. Cost Calculation

- [ ] Kosten werden aus stream-json result event extrahiert
- [ ] Fallback-Berechnung wenn cost_usd nicht vorhanden
- [ ] Phase-Level und Project-Level Aggregation
- [ ] JSON Export funktioniert

### 4. Integration

- [ ] ClaudeRunner.run_phase_debug() funktioniert
- [ ] SSE Events werden an Dashboard gestreamt
- [ ] control/debug-claude.sh startet Debug-Session
- [ ] Bestehende run_phase() Methoden funktionieren weiterhin

### 5. Tests

- [ ] Unit Tests für StreamParser
- [ ] Unit Tests für ToolTracker
- [ ] Unit Tests für CostCalculator
- [ ] Integration Test mit Mock Claude Output

---

## Konsequenzen

### Vorteile

1. **Live Sichtbarkeit**: Echtzeit-Einblick in Claude Code Ausführung
2. **Strukturierte Daten**: JSON statt unstrukturierter Text
3. **Kosten-Tracking**: Exakte Kosten pro Phase und Projekt
4. **Debugging**: Schnelle Identifikation von Problemen
5. **Native Integration**: Nutzt Claude CLI Features, keine Middleware

### Nachteile / Risiken

1. **Output Format Abhängigkeit**: stream-json Format könnte sich ändern
2. **Mehr Daten**: Erhöhte Log-Größe durch strukturierte Events
3. **Komplexität**: Zusätzliche Parsing-Logik

### Mitigation

1. Format-Änderungen: EventType als Enum erlaubt einfaches Mapping
2. Log-Größe: Rotation und Komprimierung implementieren
3. Komplexität: Gute Test-Coverage und Dokumentation

---

## Referenzen

- ADR-003: Observability & Debugging (Grundlagen)
- ADR-011: Post-Phase Verification (Integration)
- Claude CLI Dokumentation: `claude --help`
- NDJSON Spezifikation: http://ndjson.org/
