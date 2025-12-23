"""Parse Claude CLI stream-json output into structured events.

This module parses NDJSON (Newline Delimited JSON) output from Claude CLI
when run with `--output-format stream-json --verbose`.

Example Claude CLI output:
    {"type":"system","subtype":"init","session_id":"abc123","tools":["Read","Write"]}
    {"type":"assistant","subtype":"text","text":"Ich lese die Datei..."}
    {"type":"assistant","subtype":"tool_use","tool":"Read","tool_input":{"file_path":"/foo/bar.py"}}
    {"type":"user","subtype":"tool_result","tool_use_id":"tu_1","content":"...file content..."}
    {"type":"result","subtype":"success","cost_usd":0.0234,"input_tokens":1500,"output_tokens":800}

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

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable
import json
import time


class EventType(Enum):
    """Types of events from Claude CLI stream-json.

    The values correspond to the combined "type.subtype" fields
    from the NDJSON output.
    """

    SYSTEM_INIT = "system.init"
    ASSISTANT_TEXT = "assistant.text"
    ASSISTANT_TOOL_USE = "assistant.tool_use"
    USER_TOOL_RESULT = "user.tool_result"
    RESULT_SUCCESS = "result.success"
    RESULT_ERROR = "result.error"


@dataclass
class StreamEvent:
    """A single event from Claude CLI stream-json output.

    Attributes:
        event_type: The type of event (system, assistant, user, result).
        raw_data: The original parsed JSON data.
        session_id: Claude session ID.
        timestamp: Unix timestamp when event was parsed.
        text: Text content (for ASSISTANT_TEXT events).
        tool_name: Name of the tool (for ASSISTANT_TOOL_USE events).
        tool_input: Tool input parameters (for ASSISTANT_TOOL_USE events).
        tool_use_id: Unique ID linking tool_use to tool_result.
        tool_result: Result content (for USER_TOOL_RESULT events).
        success: Whether execution succeeded (for RESULT events).
        cost_usd: Cost in USD (for RESULT events).
        input_tokens: Input token count (for RESULT events).
        output_tokens: Output token count (for RESULT events).
        tools_available: List of available tools (for SYSTEM_INIT events).
    """

    event_type: EventType
    raw_data: dict[str, Any]
    session_id: str | None = None
    timestamp: float = field(default_factory=time.time)

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

    This parser processes each line of NDJSON output from the Claude CLI
    and emits structured StreamEvent objects to registered callbacks.

    Attributes:
        _callbacks: List of registered event callbacks.
        _events: List of all parsed events.
        _session_id: Current session ID.
        _tools_available: Tools available in this session.
        _total_cost: Running total cost in USD.
        _input_tokens: Total input tokens used.
        _output_tokens: Total output tokens used.

    Example:
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

    def __init__(self) -> None:
        """Initialize the stream parser."""
        self._callbacks: list[EventCallback] = []
        self._events: list[StreamEvent] = []
        self._session_id: str | None = None
        self._tools_available: list[str] = []
        self._total_cost: float = 0.0
        self._input_tokens: int = 0
        self._output_tokens: int = 0

    def on_event(self, callback: EventCallback) -> None:
        """Register an event callback.

        The callback will be invoked for each parsed event.

        Args:
            callback: Async function that takes a StreamEvent.
        """
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
        """Parse raw JSON into StreamEvent.

        Args:
            data: Parsed JSON dictionary from Claude CLI.

        Returns:
            StreamEvent if parsing succeeded, None for unknown event types.
        """
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
            # Truncate large results to prevent memory issues
            content = data.get("content", "")
            event.tool_result = content[:1000] if content else ""

        elif event_type in (EventType.RESULT_SUCCESS, EventType.RESULT_ERROR):
            event.success = event_type == EventType.RESULT_SUCCESS
            event.cost_usd = data.get("cost_usd")
            event.input_tokens = data.get("input_tokens")
            event.output_tokens = data.get("output_tokens")

        return event

    def get_tool_calls(self) -> list[StreamEvent]:
        """Get all tool call events.

        Returns:
            List of StreamEvents with event_type ASSISTANT_TOOL_USE.
        """
        return [
            e for e in self._events if e.event_type == EventType.ASSISTANT_TOOL_USE
        ]

    def get_text_events(self) -> list[StreamEvent]:
        """Get all assistant text events.

        Returns:
            List of StreamEvents with event_type ASSISTANT_TEXT.
        """
        return [e for e in self._events if e.event_type == EventType.ASSISTANT_TEXT]

    def get_full_text(self) -> str:
        """Get the full assistant text output.

        Returns:
            Concatenated text from all ASSISTANT_TEXT events.
        """
        texts = [e.text for e in self.get_text_events() if e.text]
        return "".join(texts)

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary.

        Returns:
            Dictionary with:
            - session_id: Claude session ID
            - total_events: Total number of events parsed
            - tool_calls: Number of tool calls
            - tool_counts: Dict mapping tool name to call count
            - tools_available: List of available tools
            - cost_usd: Total cost in USD
            - input_tokens: Total input tokens
            - output_tokens: Total output tokens
        """
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

    def get_events(self) -> list[StreamEvent]:
        """Get all parsed events.

        Returns:
            List of all StreamEvents in parse order.
        """
        return self._events.copy()

    def clear(self) -> None:
        """Clear all parsed events and reset state."""
        self._events.clear()
        self._session_id = None
        self._tools_available = []
        self._total_cost = 0.0
        self._input_tokens = 0
        self._output_tokens = 0
