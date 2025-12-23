"""Debug & Observability Engine for HELIX Workflows.

This package provides live visibility into Claude CLI executions:
- StreamParser for NDJSON output parsing
- ToolTracker for tool call monitoring
- CostCalculator for token/cost tracking
- LiveDashboard for SSE events

Usage:
    from helix.debug import StreamParser, ToolTracker, CostCalculator

    # Parse Claude CLI stream-json output
    parser = StreamParser()
    parser.on_event(my_handler)
    await parser.parse_line(line)

    # Track tool calls
    tracker = ToolTracker(phase_id="01-foundation")
    tracker.start_tool(tool_use_id, tool_name, tool_input)
    tracker.end_tool(tool_use_id, result)
    stats = tracker.get_stats()

    # Calculate costs
    calc = CostCalculator(project_id="my-project")
    calc.start_phase("01-foundation")
    calc.record_usage(input_tokens=1500, output_tokens=800)
    totals = calc.get_project_totals()
"""

from helix.debug.stream_parser import (
    EventType,
    StreamEvent,
    StreamParser,
    EventCallback,
)
from helix.debug.tool_tracker import (
    ToolCall,
    ToolTracker,
)
from helix.debug.cost_calculator import (
    MODEL_COSTS,
    PhaseCost,
    CostCalculator,
)
from helix.debug.events import (
    DebugEventType,
    DebugEvent,
    tool_call_started,
    tool_call_completed,
    cost_update,
    assistant_text,
)

__all__ = [
    # Stream Parser
    "EventType",
    "StreamEvent",
    "StreamParser",
    "EventCallback",
    # Tool Tracker
    "ToolCall",
    "ToolTracker",
    # Cost Calculator
    "MODEL_COSTS",
    "PhaseCost",
    "CostCalculator",
    # Events
    "DebugEventType",
    "DebugEvent",
    "tool_call_started",
    "tool_call_completed",
    "cost_update",
    "assistant_text",
]
