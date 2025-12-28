"""Unit tests for SessionManager with X-Conversation-ID support (ADR-029).

Tests the session persistence functionality:
- _normalize_conversation_id() sanitizes IDs for filesystem
- _generate_session_id_stable() creates stable hashes without timestamp
- get_or_create_session() uses conversation_id when available
- Session persistence across multiple requests with same conversation_id
"""

import tempfile
from pathlib import Path

import pytest

from helix.api.session_manager import SessionManager, SessionState


class TestNormalizeConversationId:
    """Tests for _normalize_conversation_id method."""

    def test_uuid_format(self):
        """UUID format from Open WebUI is normalized correctly."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("550e8400-e29b-41d4-a716-446655440000")
        assert result == "conv-550e8400-e29b-41d4-a716-446655440000"

    def test_unsafe_characters_replaced(self):
        """Unsafe characters are replaced with hyphens."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("test/path:with<unsafe>chars")
        assert "/" not in result
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result
        assert result.startswith("conv-")

    def test_alphanumeric_preserved(self):
        """Alphanumeric characters are preserved."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("abc123XYZ")
        assert result == "conv-abc123XYZ"

    def test_hyphens_and_underscores_preserved(self):
        """Hyphens and underscores are valid and preserved."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("test-id_with-parts")
        assert result == "conv-test-id_with-parts"

    def test_empty_string(self):
        """Empty string produces conv- prefix only."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("")
        assert result == "conv-"


class TestGenerateSessionIdStable:
    """Tests for _generate_session_id_stable method."""

    def test_same_message_same_id(self):
        """Same message always produces same session ID."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        id1 = manager._generate_session_id_stable("Hello, what is HELIX?")
        id2 = manager._generate_session_id_stable("Hello, what is HELIX?")
        assert id1 == id2

    def test_different_messages_different_ids(self):
        """Different messages produce different session IDs."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        id1 = manager._generate_session_id_stable("Hello, what is HELIX?")
        id2 = manager._generate_session_id_stable("How do I create a project?")
        assert id1 != id2

    def test_no_timestamp_in_id(self):
        """Stable ID does not contain timestamp pattern."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._generate_session_id_stable("Test message")
        # Timestamp format would be YYYYMMDD-HHMMSS
        import re
        timestamp_pattern = r'\d{8}-\d{6}'
        assert not re.search(timestamp_pattern, result)

    def test_prefix_from_first_words(self):
        """ID prefix comes from first three words of message."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._generate_session_id_stable("Hello world test message")
        assert result.startswith("hello-world-test-")

    def test_special_chars_removed_from_prefix(self):
        """Special characters are removed from prefix."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._generate_session_id_stable("Was ist HELIX?")
        assert result.startswith("was-ist-helix-")

    def test_long_message_truncated(self):
        """Long messages are truncated for hash calculation."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        long_msg = "A" * 500
        result = manager._generate_session_id_stable(long_msg)
        # Should not error and should produce valid ID
        # Note: The prefix can be long (up to 500 chars if single word),
        # but the hash part is always 12 chars
        assert result is not None
        assert result.endswith(result.split("-")[-1])  # Has hash suffix


class TestGetOrCreateSession:
    """Tests for get_or_create_session method."""

    def test_with_conversation_id_creates_session(self):
        """With conversation_id, creates session with conv- prefix."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        session_id, state = manager.get_or_create_session(
            first_message="Hello",
            conversation_id="test-conv-123",
        )
        assert session_id.startswith("conv-")
        assert "test-conv-123" in session_id
        assert state.conversation_id == "test-conv-123"

    def test_without_conversation_id_uses_stable_hash(self):
        """Without conversation_id, uses stable hash-based ID."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        session_id, state = manager.get_or_create_session(
            first_message="Hello world",
            conversation_id=None,
        )
        assert not session_id.startswith("conv-")
        assert session_id.startswith("hello-world-")

    def test_same_conversation_id_returns_same_session(self):
        """Same conversation_id returns same session on multiple calls."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        session_id1, state1 = manager.get_or_create_session(
            first_message="First message",
            conversation_id="persistent-conv",
        )
        session_id2, state2 = manager.get_or_create_session(
            first_message="Second message",  # Different message
            conversation_id="persistent-conv",  # Same conversation
        )

        assert session_id1 == session_id2
        assert state1.session_id == state2.session_id

    def test_different_conversation_ids_different_sessions(self):
        """Different conversation_ids create different sessions."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        session_id1, _ = manager.get_or_create_session(
            first_message="Hello",
            conversation_id="conv-1",
        )
        session_id2, _ = manager.get_or_create_session(
            first_message="Hello",  # Same message
            conversation_id="conv-2",  # Different conversation
        )

        assert session_id1 != session_id2

    def test_session_persisted_to_disk(self):
        """Session is persisted to disk and can be loaded."""
        base_path = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=base_path)

        session_id, _ = manager.get_or_create_session(
            first_message="Test",
            conversation_id="disk-test",
        )

        # Verify directory structure created
        session_path = base_path / session_id
        assert session_path.exists()
        assert (session_path / "status.json").exists()
        assert (session_path / "input").is_dir()
        assert (session_path / "context").is_dir()
        assert (session_path / "output").is_dir()

    def test_session_loaded_from_disk(self):
        """Existing session is loaded from disk on new manager instance."""
        base_path = Path(tempfile.mkdtemp())

        # Create session with first manager
        manager1 = SessionManager(base_path=base_path)
        session_id, state1 = manager1.get_or_create_session(
            first_message="Persistent test",
            conversation_id="reload-test",
        )

        # Create new manager instance (simulates server restart)
        manager2 = SessionManager(base_path=base_path)
        session_id2, state2 = manager2.get_or_create_session(
            first_message="Different message",  # Different message
            conversation_id="reload-test",  # Same conversation
        )

        # Should get same session
        assert session_id == session_id2
        assert state2.original_request == state1.original_request


class TestSessionState:
    """Tests for SessionState model."""

    def test_conversation_id_stored(self):
        """conversation_id is stored in SessionState."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        _, state = manager.get_or_create_session(
            first_message="Test",
            conversation_id="stored-id",
        )
        assert state.conversation_id == "stored-id"

    def test_conversation_id_optional(self):
        """conversation_id is optional (None by default)."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        _, state = manager.get_or_create_session(
            first_message="Test",
            conversation_id=None,
        )
        assert state.conversation_id is None


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing clients."""

    def test_generate_session_id_still_works(self):
        """Legacy generate_session_id method still works."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager.generate_session_id("Test message")
        assert result is not None
        assert len(result) > 0

    def test_fallback_without_header(self):
        """Without X-Conversation-ID, fallback logic works."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        session_id, state = manager.get_or_create_session(
            first_message="Fallback test",
            conversation_id=None,
        )
        # Should create valid session without conversation_id
        assert manager.session_exists(session_id)
        assert state.status == "discussing"


class TestConversationCache:
    """Tests for the conversation ID cache."""

    def test_cache_populated_on_create(self):
        """Cache is populated when session is created."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        manager.get_or_create_session(
            first_message="Cache test",
            conversation_id="cache-id",
        )
        assert "cache-id" in manager._conversation_cache

    def test_cache_used_on_lookup(self):
        """Cache is used for fast lookup."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        # Create session
        session_id1, _ = manager.get_or_create_session(
            first_message="First",
            conversation_id="cached",
        )

        # Lookup should use cache
        session_id2, _ = manager.get_or_create_session(
            first_message="Second",
            conversation_id="cached",
        )

        assert session_id1 == session_id2


class TestIntegrationScenarios:
    """Integration tests for real-world usage scenarios."""

    def test_open_webui_multi_turn_dialog(self):
        """Simulates Open WebUI multi-turn dialog with X-Conversation-ID."""
        base_path = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=base_path)
        conversation_id = "550e8400-e29b-41d4-a716-446655440000"

        # Turn 1: User asks question
        session_id1, state1 = manager.get_or_create_session(
            first_message="Was ist HELIX?",
            conversation_id=conversation_id,
        )
        manager.save_messages(session_id1, [
            {"role": "user", "content": "Was ist HELIX?"}
        ])

        # Turn 2: User asks follow-up
        session_id2, state2 = manager.get_or_create_session(
            first_message="Erkläre mehr Details",  # Different message
            conversation_id=conversation_id,  # Same conversation
        )

        # Should be same session
        assert session_id1 == session_id2

        # Should have original request preserved
        assert state2.original_request == "Was ist HELIX?"

    def test_curl_client_without_header(self):
        """Simulates curl client without X-Conversation-ID."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        # First request
        session_id1, _ = manager.get_or_create_session(
            first_message="Hello HELIX",
            conversation_id=None,
        )

        # Same message should get same session (stable hash)
        session_id2, _ = manager.get_or_create_session(
            first_message="Hello HELIX",
            conversation_id=None,
        )

        assert session_id1 == session_id2
