"""Live dashboard for Claude CLI monitoring.

This module provides both:
1. A terminal-based dashboard for CLI monitoring
2. A FastAPI router for SSE-based web dashboards

Terminal Dashboard Usage:
    dashboard = TerminalDashboard(phase_id="01-foundation")
    await dashboard.run(process_stdout)

SSE Dashboard Usage:
    from fastapi import FastAPI
    from helix.debug.live_dashboard import create_debug_router

    app = FastAPI()
    app.include_router(create_debug_router())
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator
import asyncio
import sys

from .stream_parser import StreamParser, StreamEvent, EventType
from .tool_tracker import ToolTracker
from .cost_calculator import CostCalculator
from . import events as debug_events


class TerminalDashboard:
    """Live terminal dashboard for Claude CLI execution.

    Shows:
    - Current tool being executed
    - Tool call history (last 5)
    - Running cost
    - Token usage

    Attributes:
        phase_id: The HELIX phase being monitored.
        parser: StreamParser for NDJSON parsing.
        tool_tracker: ToolTracker for tool call monitoring.
        cost_calc: CostCalculator for cost tracking.

    Example:
        dashboard = TerminalDashboard(phase_id="01-foundation")

        # Connect to stream parser
        parser = StreamParser()
        parser.on_event(dashboard.handle_event)

        # Or run standalone
        await dashboard.run(process_stdout)
    """

    # ANSI escape codes
    CLEAR_SCREEN = "\033[2J\033[H"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    def __init__(
        self,
        phase_id: str,
        model: str = "claude-sonnet-4",
        project_id: str = "live",
    ) -> None:
        """Initialize the terminal dashboard.

        Args:
            phase_id: The HELIX phase being monitored.
            model: The LLM model being used.
            project_id: Project identifier for cost tracking.
        """
        self.phase_id = phase_id
        self.parser = StreamParser()
        self.tool_tracker = ToolTracker(phase_id)
        self.cost_calc = CostCalculator(project_id=project_id, model=model)

        self._current_tool: str | None = None
        self._last_text: str = ""
        self._start_time = datetime.now()
        self._session_id: str | None = None

        # Register as event handler
        self.parser.on_event(self._handle_event)

        # Start phase cost tracking
        self.cost_calc.start_phase(phase_id)

    async def _handle_event(self, event: StreamEvent) -> None:
        """Handle a stream event and update dashboard.

        Args:
            event: The parsed StreamEvent from the parser.
        """
        if event.event_type == EventType.SYSTEM_INIT:
            self._session_id = event.session_id

        elif event.event_type == EventType.ASSISTANT_TOOL_USE:
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

        # Build the dashboard
        width = 66
        hr = "═" * width

        lines = [
            f"{self.BOLD}╔{hr}╗{self.RESET}",
            f"{self.BOLD}║  HELIX Debug Dashboard{' ' * (width - 23)}║{self.RESET}",
            f"{self.BOLD}║  Phase: {self.phase_id:<{width - 10}}║{self.RESET}",
            f"{self.BOLD}╠{hr}╣{self.RESET}",
        ]

        # Session info
        session_str = self._session_id[:20] if self._session_id else "(waiting)"
        lines.append(
            f"║  Session: {session_str:<20}  Elapsed: {elapsed:>8.1f}s{' ' * 10}║"
        )
        lines.append(f"╠{hr}╣")

        # Current activity
        if self._current_tool:
            tool_str = self._current_tool[:40]
            lines.append(
                f"║  {self.YELLOW}▶ Executing:{self.RESET} {tool_str:<{width - 15}}║"
            )
        else:
            lines.append(
                f"║  {self.GREEN}● Idle{self.RESET}{' ' * (width - 8)}║"
            )

        lines.append(f"╠{hr}╣")

        # Tool stats
        total_calls = stats["total_calls"]
        pending = stats["pending_calls"]
        lines.append(
            f"║  {self.BOLD}Tool Calls:{self.RESET} {total_calls:<5} "
            f"(pending: {pending}){' ' * (width - 32)}║"
        )

        # Tool breakdown (top 4)
        by_tool = stats.get("by_tool", {})
        sorted_tools = sorted(by_tool.items(), key=lambda x: -x[1]["count"])

        for tool_name, data in sorted_tools[:4]:
            count = data["count"]
            avg_ms = data["avg_duration_ms"]
            failures = data["failures"]

            # Visual bar
            bar_len = min(count, 20)
            bar = "█" * bar_len

            fail_str = f" {self.RED}({failures} fail){self.RESET}" if failures else ""
            line = f"║    {tool_name:<12} {count:>3} {bar:<20} {avg_ms:>6.0f}ms{fail_str}"
            # Pad to width
            visible_len = len(line) - len(fail_str) + (len(fail_str) - 9 if failures else 0)
            pad = width + 2 - visible_len
            if pad < 0:
                pad = 0
            lines.append(f"{line}{' ' * pad}║")

        lines.append(f"╠{hr}╣")

        # Cost & tokens
        if cost_data:
            in_tok = cost_data.input_tokens
            out_tok = cost_data.output_tokens
            cost = cost_data.cost_usd
            lines.append(
                f"║  {self.BOLD}Tokens:{self.RESET} {in_tok:>8,} in / {out_tok:>8,} out"
                f"{' ' * (width - 40)}║"
            )
            lines.append(
                f"║  {self.BOLD}Cost:{self.RESET}   ${cost:>8.4f} USD"
                f"{' ' * (width - 27)}║"
            )
        else:
            lines.append(f"║  {self.BOLD}Tokens:{self.RESET} (waiting for result){' ' * (width - 30)}║")
            lines.append(f"║  {self.BOLD}Cost:{self.RESET}   (calculating...){' ' * (width - 26)}║")

        lines.append(f"╠{hr}╣")

        # Recent calls
        lines.append(f"║  {self.BOLD}Recent Tool Calls:{self.RESET}{' ' * (width - 20)}║")

        for call in self.tool_tracker.get_recent(3):
            if call.success is True:
                status = f"{self.GREEN}✓{self.RESET}"
            elif call.success is False:
                status = f"{self.RED}✗{self.RESET}"
            else:
                status = f"{self.YELLOW}?{self.RESET}"

            duration = f"{call.duration_ms:.0f}ms" if call.duration_ms else "..."
            name = call.tool_name[:15]
            lines.append(f"║    {status} {name:<15} {duration:>8}{' ' * (width - 30)}║")

        # Pad if fewer than 3 recent calls
        for _ in range(3 - len(self.tool_tracker.get_recent(3))):
            lines.append(f"║{' ' * width}║")

        lines.append(f"╚{hr}╝")

        # Output
        output = "\n".join(lines)
        print(self.CLEAR_SCREEN + output, end="", flush=True)

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

    def get_summary(self) -> dict[str, Any]:
        """Get current summary without ending the dashboard.

        Returns:
            Current state of tool stats, costs, and parser summary.
        """
        return {
            "tool_stats": self.tool_tracker.get_stats(),
            "cost_summary": self.cost_calc.get_project_totals(),
            "parser_summary": self.parser.get_summary(),
        }


@dataclass
class SSEDashboard:
    """SSE-based dashboard for web clients.

    This dashboard emits debug events as Server-Sent Events for
    consumption by web dashboards.

    Attributes:
        phase_id: The HELIX phase being monitored.
        _events: Queue of events to send.
        _subscribers: Set of connected subscriber queues.
    """

    phase_id: str
    _events: list[debug_events.DebugEvent] = field(default_factory=list)
    _subscribers: set[asyncio.Queue[str]] = field(default_factory=set)

    async def emit(self, event: debug_events.DebugEvent) -> None:
        """Emit an event to all subscribers.

        Args:
            event: The debug event to emit.
        """
        self._events.append(event)
        sse_data = event.to_sse()

        for queue in self._subscribers:
            try:
                await queue.put(sse_data)
            except asyncio.QueueFull:
                # Drop event if queue is full
                pass

    def subscribe(self) -> asyncio.Queue[str]:
        """Subscribe to event stream.

        Returns:
            Queue that will receive SSE-formatted events.
        """
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        """Unsubscribe from event stream.

        Args:
            queue: The subscriber queue to remove.
        """
        self._subscribers.discard(queue)

    def get_events(self) -> list[debug_events.DebugEvent]:
        """Get all emitted events.

        Returns:
            List of all events emitted so far.
        """
        return self._events.copy()


def create_debug_router(dashboard: SSEDashboard | None = None):
    """Create FastAPI router for debug endpoints.

    Args:
        dashboard: Optional SSEDashboard instance. If None, creates new one.

    Returns:
        FastAPI APIRouter with debug endpoints.
    """
    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse

    router = APIRouter(prefix="/debug", tags=["debug"])

    # Use provided dashboard or create default
    _dashboard = dashboard or SSEDashboard(phase_id="default")

    @router.get("/stream")
    async def stream_events():
        """SSE endpoint for debug events.

        Returns:
            StreamingResponse with text/event-stream content type.
        """
        queue = _dashboard.subscribe()

        async def event_generator() -> AsyncIterator[str]:
            try:
                # Send initial connection event
                yield "event: connected\ndata: {}\n\n"

                while True:
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield data
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield ": keepalive\n\n"
            finally:
                _dashboard.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/stats")
    async def get_stats() -> dict[str, Any]:
        """Get current debug statistics.

        Returns:
            Dictionary with event counts and recent events.
        """
        events = _dashboard.get_events()
        return {
            "total_events": len(events),
            "events_by_type": _count_by_type(events),
            "recent_events": [e.to_dict() for e in events[-10:]],
        }

    @router.get("/events")
    async def get_events() -> list[dict[str, Any]]:
        """Get all debug events.

        Returns:
            List of all events as dictionaries.
        """
        return [e.to_dict() for e in _dashboard.get_events()]

    def _count_by_type(
        events: list[debug_events.DebugEvent],
    ) -> dict[str, int]:
        """Count events by type."""
        counts: dict[str, int] = {}
        for e in events:
            type_name = e.event_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    return router
