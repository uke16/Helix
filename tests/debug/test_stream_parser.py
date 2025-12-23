"""Tests for stream_parser module."""

import pytest
import json
from helix.debug.stream_parser import (
    StreamParser,
    StreamEvent,
    EventType,
)


@pytest.fixture
def parser() -> StreamParser:
    """Create a fresh StreamParser instance."""
    return StreamParser()


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types_exist(self):
        """Verify all expected event types are defined."""
        expected = [
            "SYSTEM_INIT",
            "ASSISTANT_TEXT",
            "ASSISTANT_TOOL_USE",
            "USER_TOOL_RESULT",
            "RESULT_SUCCESS",
            "RESULT_ERROR",
        ]
        for name in expected:
            assert hasattr(EventType, name), f"Missing EventType.{name}"

    def test_event_type_values(self):
        """Verify event type values match Claude CLI format."""
        assert EventType.SYSTEM_INIT.value == "system.init"
        assert EventType.ASSISTANT_TEXT.value == "assistant.text"
        assert EventType.ASSISTANT_TOOL_USE.value == "assistant.tool_use"
        assert EventType.USER_TOOL_RESULT.value == "user.tool_result"
        assert EventType.RESULT_SUCCESS.value == "result.success"
        assert EventType.RESULT_ERROR.value == "result.error"


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_create_basic_event(self):
        """Test creating a basic StreamEvent."""
        event = StreamEvent(
            event_type=EventType.ASSISTANT_TEXT,
            raw_data={"type": "assistant", "subtype": "text"},
            text="Hello",
        )
        assert event.event_type == EventType.ASSISTANT_TEXT
        assert event.text == "Hello"
        assert event.timestamp > 0

    def test_tool_use_event_fields(self):
        """Test tool use event has correct fields."""
        event = StreamEvent(
            event_type=EventType.ASSISTANT_TOOL_USE,
            raw_data={},
            tool_name="Read",
            tool_input={"file_path": "/foo/bar.py"},
            tool_use_id="tu_123",
        )
        assert event.tool_name == "Read"
        assert event.tool_input == {"file_path": "/foo/bar.py"}
        assert event.tool_use_id == "tu_123"

    def test_result_event_fields(self):
        """Test result event has correct fields."""
        event = StreamEvent(
            event_type=EventType.RESULT_SUCCESS,
            raw_data={},
            success=True,
            cost_usd=0.0234,
            input_tokens=1500,
            output_tokens=800,
        )
        assert event.success is True
        assert event.cost_usd == 0.0234
        assert event.input_tokens == 1500
        assert event.output_tokens == 800


class TestStreamParser:
    """Tests for StreamParser class."""

    @pytest.mark.asyncio
    async def test_parse_empty_line(self, parser: StreamParser):
        """Empty lines should return None."""
        result = await parser.parse_line("")
        assert result is None

        result = await parser.parse_line("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self, parser: StreamParser):
        """Invalid JSON should return None."""
        result = await parser.parse_line("not json")
        assert result is None

        result = await parser.parse_line("{invalid")
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_system_init(self, parser: StreamParser):
        """Test parsing system.init event."""
        line = json.dumps({
            "type": "system",
            "subtype": "init",
            "session_id": "abc123",
            "tools": ["Read", "Write", "Bash"],
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.SYSTEM_INIT
        assert event.session_id == "abc123"
        assert event.tools_available == ["Read", "Write", "Bash"]

    @pytest.mark.asyncio
    async def test_parse_assistant_text(self, parser: StreamParser):
        """Test parsing assistant.text event."""
        line = json.dumps({
            "type": "assistant",
            "subtype": "text",
            "text": "Ich lese die Datei...",
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.ASSISTANT_TEXT
        assert event.text == "Ich lese die Datei..."

    @pytest.mark.asyncio
    async def test_parse_tool_use(self, parser: StreamParser):
        """Test parsing assistant.tool_use event."""
        line = json.dumps({
            "type": "assistant",
            "subtype": "tool_use",
            "tool": "Read",
            "tool_input": {"file_path": "/foo/bar.py"},
            "tool_use_id": "tu_1",
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.ASSISTANT_TOOL_USE
        assert event.tool_name == "Read"
        assert event.tool_input == {"file_path": "/foo/bar.py"}
        assert event.tool_use_id == "tu_1"

    @pytest.mark.asyncio
    async def test_parse_tool_result(self, parser: StreamParser):
        """Test parsing user.tool_result event."""
        line = json.dumps({
            "type": "user",
            "subtype": "tool_result",
            "tool_use_id": "tu_1",
            "content": "file contents here",
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.USER_TOOL_RESULT
        assert event.tool_use_id == "tu_1"
        assert event.tool_result == "file contents here"

    @pytest.mark.asyncio
    async def test_parse_result_success(self, parser: StreamParser):
        """Test parsing result.success event."""
        line = json.dumps({
            "type": "result",
            "subtype": "success",
            "cost_usd": 0.0234,
            "input_tokens": 1500,
            "output_tokens": 800,
            "session_id": "abc123",
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.RESULT_SUCCESS
        assert event.success is True
        assert event.cost_usd == 0.0234
        assert event.input_tokens == 1500
        assert event.output_tokens == 800

    @pytest.mark.asyncio
    async def test_parse_result_error(self, parser: StreamParser):
        """Test parsing result.error event."""
        line = json.dumps({
            "type": "result",
            "subtype": "error",
            "cost_usd": 0.01,
            "input_tokens": 500,
            "output_tokens": 0,
        })

        event = await parser.parse_line(line)

        assert event is not None
        assert event.event_type == EventType.RESULT_ERROR
        assert event.success is False

    @pytest.mark.asyncio
    async def test_unknown_event_type_skipped(self, parser: StreamParser):
        """Unknown event types should return None."""
        line = json.dumps({
            "type": "unknown",
            "subtype": "weird",
        })

        event = await parser.parse_line(line)
        assert event is None

    @pytest.mark.asyncio
    async def test_event_callback_called(self, parser: StreamParser):
        """Callbacks should be called for each event."""
        received: list[StreamEvent] = []

        async def callback(event: StreamEvent) -> None:
            received.append(event)

        parser.on_event(callback)

        await parser.parse_line(json.dumps({
            "type": "assistant",
            "subtype": "text",
            "text": "Hello",
        }))

        assert len(received) == 1
        assert received[0].text == "Hello"

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, parser: StreamParser):
        """Multiple callbacks should all be called."""
        calls: list[str] = []

        async def callback1(event: StreamEvent) -> None:
            calls.append("cb1")

        async def callback2(event: StreamEvent) -> None:
            calls.append("cb2")

        parser.on_event(callback1)
        parser.on_event(callback2)

        await parser.parse_line(json.dumps({
            "type": "assistant",
            "subtype": "text",
            "text": "Hello",
        }))

        assert calls == ["cb1", "cb2"]

    @pytest.mark.asyncio
    async def test_get_tool_calls(self, parser: StreamParser):
        """get_tool_calls should return only tool use events."""
        # Parse mixed events
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "text", "text": "Hello"
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "tool_use",
            "tool": "Read", "tool_input": {}, "tool_use_id": "tu_1"
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "tool_use",
            "tool": "Write", "tool_input": {}, "tool_use_id": "tu_2"
        }))

        tool_calls = parser.get_tool_calls()

        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "Read"
        assert tool_calls[1].tool_name == "Write"

    @pytest.mark.asyncio
    async def test_get_summary(self, parser: StreamParser):
        """get_summary should aggregate correctly."""
        # Simulate a complete session
        await parser.parse_line(json.dumps({
            "type": "system", "subtype": "init",
            "session_id": "test123", "tools": ["Read", "Write"]
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "tool_use",
            "tool": "Read", "tool_input": {}, "tool_use_id": "tu_1"
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "tool_use",
            "tool": "Read", "tool_input": {}, "tool_use_id": "tu_2"
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "tool_use",
            "tool": "Write", "tool_input": {}, "tool_use_id": "tu_3"
        }))
        await parser.parse_line(json.dumps({
            "type": "result", "subtype": "success",
            "cost_usd": 0.05, "input_tokens": 2000, "output_tokens": 1000
        }))

        summary = parser.get_summary()

        assert summary["session_id"] == "test123"
        assert summary["total_events"] == 5
        assert summary["tool_calls"] == 3
        assert summary["tool_counts"] == {"Read": 2, "Write": 1}
        assert summary["tools_available"] == ["Read", "Write"]
        assert summary["cost_usd"] == 0.05
        assert summary["input_tokens"] == 2000
        assert summary["output_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_session_id_persisted(self, parser: StreamParser):
        """Session ID should persist across events."""
        await parser.parse_line(json.dumps({
            "type": "system", "subtype": "init",
            "session_id": "persistent123", "tools": []
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "text",
            "text": "Hello"
        }))

        events = parser.get_events()
        assert events[1].session_id == "persistent123"

    @pytest.mark.asyncio
    async def test_tool_result_truncated(self, parser: StreamParser):
        """Long tool results should be truncated."""
        long_content = "x" * 2000

        await parser.parse_line(json.dumps({
            "type": "user", "subtype": "tool_result",
            "tool_use_id": "tu_1", "content": long_content
        }))

        events = parser.get_events()
        assert len(events[0].tool_result) == 1000

    @pytest.mark.asyncio
    async def test_clear(self, parser: StreamParser):
        """clear should reset all state."""
        await parser.parse_line(json.dumps({
            "type": "system", "subtype": "init",
            "session_id": "test", "tools": ["Read"]
        }))

        parser.clear()

        assert parser.get_events() == []
        summary = parser.get_summary()
        assert summary["session_id"] is None
        assert summary["total_events"] == 0

    @pytest.mark.asyncio
    async def test_get_full_text(self, parser: StreamParser):
        """get_full_text should concatenate all text events."""
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "text", "text": "Hello "
        }))
        await parser.parse_line(json.dumps({
            "type": "assistant", "subtype": "text", "text": "World"
        }))

        assert parser.get_full_text() == "Hello World"
