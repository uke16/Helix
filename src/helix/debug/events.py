"""Debug event types for SSE streaming to dashboards.

This module defines the event types used for streaming debug information
to live dashboards via Server-Sent Events (SSE).

Usage:
    from helix.debug.events import (
        DebugEvent,
        DebugEventType,
        tool_call_started,
        cost_update,
    )

    # Create events using factory functions
    event = tool_call_started(
        phase_id="01-foundation",
        tool_name="Read",
        tool_input={"file_path": "/foo/bar.py"},
        tool_use_id="tu_123",
    )

    # Format for SSE
    sse_data = event.to_sse()
    # event: debug
    # data: {"type": "tool_call_started", ...}
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json


class DebugEventType(Enum):
    """Types of debug events emitted to dashboards.

    These events are streamed via SSE to provide real-time
    visibility into Claude CLI execution.
    """

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
    """A debug event for SSE streaming.

    Attributes:
        event_type: The type of debug event.
        phase_id: The HELIX phase this event belongs to.
        data: Additional event-specific data.
        timestamp: When the event was created.
    """

    event_type: DebugEventType
    phase_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse(self) -> str:
        """Format as SSE event string.

        Returns:
            String formatted for Server-Sent Events protocol:
            event: debug
            data: {"type": "...", ...}
        """
        event_data = {
            "type": self.event_type.value,
            "phase_id": self.phase_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }
        json_str = json.dumps(event_data, default=str)
        return f"event: debug\ndata: {json_str}\n\n"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary with all event data.
        """
        return {
            "type": self.event_type.value,
            "phase_id": self.phase_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON-formatted string of event data.
        """
        return json.dumps(self.to_dict(), default=str)


# Factory functions for common events


def phase_started(
    phase_id: str,
    phase_name: str | None = None,
    model: str | None = None,
) -> DebugEvent:
    """Create a phase_started event.

    Args:
        phase_id: The phase identifier.
        phase_name: Human-readable phase name.
        model: The LLM model being used.

    Returns:
        DebugEvent for phase start.
    """
    return DebugEvent(
        event_type=DebugEventType.PHASE_STARTED,
        phase_id=phase_id,
        data={
            "phase_name": phase_name or phase_id,
            "model": model,
        },
    )


def phase_completed(
    phase_id: str,
    duration_seconds: float,
    success: bool = True,
    tool_calls: int = 0,
    cost_usd: float | None = None,
) -> DebugEvent:
    """Create a phase_completed event.

    Args:
        phase_id: The phase identifier.
        duration_seconds: Total execution time.
        success: Whether the phase succeeded.
        tool_calls: Number of tool calls made.
        cost_usd: Total cost for the phase.

    Returns:
        DebugEvent for phase completion.
    """
    return DebugEvent(
        event_type=(
            DebugEventType.PHASE_COMPLETED if success else DebugEventType.PHASE_FAILED
        ),
        phase_id=phase_id,
        data={
            "duration_seconds": round(duration_seconds, 2),
            "success": success,
            "tool_calls": tool_calls,
            "cost_usd": round(cost_usd, 6) if cost_usd else None,
        },
    )


def tool_call_started(
    phase_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str,
) -> DebugEvent:
    """Create a tool_call_started event.

    Args:
        phase_id: The phase identifier.
        tool_name: Name of the tool being called.
        tool_input: Input parameters for the tool.
        tool_use_id: Unique ID for this tool call.

    Returns:
        DebugEvent for tool call start.
    """
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
    result_preview: str | None = None,
) -> DebugEvent:
    """Create a tool_call_completed event.

    Args:
        phase_id: The phase identifier.
        tool_name: Name of the tool.
        tool_use_id: Unique ID for this tool call.
        duration_ms: Execution time in milliseconds.
        success: Whether the tool call succeeded.
        result_preview: Truncated result for display.

    Returns:
        DebugEvent for tool call completion.
    """
    return DebugEvent(
        event_type=(
            DebugEventType.TOOL_CALL_COMPLETED
            if success
            else DebugEventType.TOOL_CALL_FAILED
        ),
        phase_id=phase_id,
        data={
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "result_preview": result_preview[:100] if result_preview else None,
        },
    )


def cost_update(
    phase_id: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> DebugEvent:
    """Create a cost_update event.

    Args:
        phase_id: The phase identifier.
        input_tokens: Input tokens consumed.
        output_tokens: Output tokens generated.
        cost_usd: Total cost in USD.

    Returns:
        DebugEvent for cost update.
    """
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


def tokens_update(
    phase_id: str,
    input_tokens: int,
    output_tokens: int,
) -> DebugEvent:
    """Create a tokens_update event.

    Args:
        phase_id: The phase identifier.
        input_tokens: Input tokens consumed.
        output_tokens: Output tokens generated.

    Returns:
        DebugEvent for token count update.
    """
    return DebugEvent(
        event_type=DebugEventType.TOKENS_UPDATE,
        phase_id=phase_id,
        data={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )


def assistant_text(phase_id: str, text: str) -> DebugEvent:
    """Create an assistant_text event.

    Args:
        phase_id: The phase identifier.
        text: The assistant text output.

    Returns:
        DebugEvent for assistant text.
    """
    return DebugEvent(
        event_type=DebugEventType.ASSISTANT_TEXT,
        phase_id=phase_id,
        data={"text": text[:500]},  # Truncate for SSE
    )


def session_initialized(
    phase_id: str,
    session_id: str,
    tools_available: list[str],
) -> DebugEvent:
    """Create a session_initialized event.

    Args:
        phase_id: The phase identifier.
        session_id: Claude session ID.
        tools_available: List of available tools.

    Returns:
        DebugEvent for session initialization.
    """
    return DebugEvent(
        event_type=DebugEventType.SESSION_INITIALIZED,
        phase_id=phase_id,
        data={
            "session_id": session_id,
            "tools_available": tools_available,
            "tools_count": len(tools_available),
        },
    )


def session_completed(
    phase_id: str,
    session_id: str,
    success: bool,
    total_tool_calls: int,
    total_cost_usd: float | None = None,
) -> DebugEvent:
    """Create a session_completed event.

    Args:
        phase_id: The phase identifier.
        session_id: Claude session ID.
        success: Whether the session completed successfully.
        total_tool_calls: Total number of tool calls made.
        total_cost_usd: Total cost for the session.

    Returns:
        DebugEvent for session completion.
    """
    return DebugEvent(
        event_type=DebugEventType.SESSION_COMPLETED,
        phase_id=phase_id,
        data={
            "session_id": session_id,
            "success": success,
            "total_tool_calls": total_tool_calls,
            "total_cost_usd": round(total_cost_usd, 6) if total_cost_usd else None,
        },
    )
