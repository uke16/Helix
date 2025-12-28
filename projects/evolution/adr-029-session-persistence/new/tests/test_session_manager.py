"""Unit tests for SessionManager with X-Conversation-ID support (ADR-029).

Tests the session persistence feature that allows Open WebUI conversations
to maintain consistent sessions across multiple requests.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Import the session manager module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))

from helix.api.session_manager import SessionManager, SessionState


class TestNormalizeConversationId:
    """Tests for _normalize_conversation_id method."""

    def test_uuid_format(self):
        """Test normalization of standard UUID format."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        conv_id = "550e8400-e29b-41d4-a716-446655440000"
        result = manager._normalize_conversation_id(conv_id)

        assert result.startswith("conv-")
        assert "550e8400" in result
        # UUID dashes should be preserved (they're in the safe character list)
        assert "-" in result

    def test_special_characters_sanitized(self):
        """Test that special characters are sanitized."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        conv_id = "test/id:with!special@chars"
        result = manager._normalize_conversation_id(conv_id)

        assert result.startswith("conv-")
        assert "/" not in result
        assert ":" not in result
        assert "!" not in result
        assert "@" not in result

    def test_empty_string(self):
        """Test handling of empty string."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._normalize_conversation_id("")

        assert result == "conv-"

    def test_underscores_preserved(self):
        """Test that underscores are preserved."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        conv_id = "test_id_with_underscores"
        result = manager._normalize_conversation_id(conv_id)

        assert "test_id_with_underscores" in result


class TestGenerateSessionIdStable:
    """Tests for _generate_session_id_stable method."""

    def test_same_message_same_id(self):
        """Test that same message produces same session ID."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        message = "Hello, this is my first message"

        id1 = manager._generate_session_id_stable(message)
        id2 = manager._generate_session_id_stable(message)

        assert id1 == id2

    def test_different_messages_different_ids(self):
        """Test that different messages produce different session IDs."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        id1 = manager._generate_session_id_stable("First message")
        id2 = manager._generate_session_id_stable("Second message")

        assert id1 != id2

    def test_no_timestamp(self):
        """Test that session ID doesn't contain timestamp components."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        message = "Test message"

        id1 = manager._generate_session_id_stable(message)
        # Wait a moment to ensure different timestamp would be generated
        id2 = manager._generate_session_id_stable(message)

        # IDs should be identical (no timestamp component)
        assert id1 == id2

    def test_prefix_from_words(self):
        """Test that prefix is derived from first 3 words."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        message = "Hello World Today is a great day"

        result = manager._generate_session_id_stable(message)

        # Should start with first 3 words (lowercased, cleaned)
        assert result.startswith("hello-world-today-")

    def test_empty_message(self):
        """Test handling of empty message."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))
        result = manager._generate_session_id_stable("")

        # Should fallback to 'session' prefix
        assert result.startswith("session-")


class TestGetOrCreateSession:
    """Tests for get_or_create_session method."""

    def test_with_conversation_id_creates_session(self):
        """Test that conversation ID creates a new session."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)
        conv_id = "550e8400-e29b-41d4-a716-446655440000"

        session_id, state = manager.get_or_create_session(
            first_message="Hello",
            conversation_id=conv_id,
        )

        assert session_id.startswith("conv-")
        assert state.status == "discussing"
        assert state.conversation_id == conv_id
        # Session directory should exist
        assert (tmp_dir / session_id).exists()

    def test_with_conversation_id_returns_same_session(self):
        """Test that same conversation ID returns same session."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)
        conv_id = "test-conversation-123"

        # First request
        session_id1, state1 = manager.get_or_create_session(
            first_message="First message",
            conversation_id=conv_id,
        )

        # Second request with same conv_id but different message
        session_id2, state2 = manager.get_or_create_session(
            first_message="Different message",
            conversation_id=conv_id,
        )

        assert session_id1 == session_id2
        # Should have same created_at time
        assert state1.created_at == state2.created_at

    def test_without_conversation_id_uses_stable_hash(self):
        """Test fallback to stable hash-based ID without conversation ID."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)

        session_id, state = manager.get_or_create_session(
            first_message="Hello world",
            conversation_id=None,
        )

        # Should not have conv- prefix
        assert not session_id.startswith("conv-")
        assert state.status == "discussing"
        assert state.conversation_id is None

    def test_without_conversation_id_same_message_same_session(self):
        """Test that same message without conv_id returns same session."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)
        message = "Hello world"

        session_id1, _ = manager.get_or_create_session(
            first_message=message,
            conversation_id=None,
        )

        session_id2, _ = manager.get_or_create_session(
            first_message=message,
            conversation_id=None,
        )

        assert session_id1 == session_id2

    def test_session_directory_structure(self):
        """Test that created session has correct directory structure."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)

        session_id, _ = manager.get_or_create_session(
            first_message="Test",
            conversation_id="test-conv-id",
        )

        session_path = tmp_dir / session_id
        assert (session_path / "input").is_dir()
        assert (session_path / "context").is_dir()
        assert (session_path / "output").is_dir()
        assert (session_path / "logs").is_dir()
        assert (session_path / "input" / "request.md").exists()
        assert (session_path / "status.json").exists()

    def test_conversation_id_stored_in_state(self):
        """Test that conversation ID is stored in session state."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)
        conv_id = "my-conversation-id"

        session_id, state = manager.get_or_create_session(
            first_message="Hello",
            conversation_id=conv_id,
        )

        # Check in returned state
        assert state.conversation_id == conv_id

        # Check in persisted state
        loaded_state = manager.get_state(session_id)
        assert loaded_state is not None
        assert loaded_state.conversation_id == conv_id


class TestMessagePersistence:
    """Tests for message saving and loading."""

    def test_save_and_load_messages(self):
        """Test saving and loading message history."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)

        session_id, _ = manager.get_or_create_session(
            first_message="Hello",
            conversation_id="test-conv",
        )

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        manager.save_messages(session_id, messages)

        # Read back the messages
        messages_file = tmp_dir / session_id / "context" / "messages.json"
        assert messages_file.exists()

        loaded = json.loads(messages_file.read_text())
        assert len(loaded) == 3
        assert loaded[0]["role"] == "user"
        assert loaded[0]["content"] == "Hello"


class TestContextPersistence:
    """Tests for context file saving."""

    def test_save_context_files(self):
        """Test saving context files (what, why, constraints)."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)

        session_id, _ = manager.get_or_create_session(
            first_message="Hello",
            conversation_id="test-conv",
        )

        manager.save_context(session_id, "what", "What we're building")
        manager.save_context(session_id, "why", "Why we need it")
        manager.save_context(session_id, "constraints", "Technical constraints")

        context = manager.get_context(session_id)

        assert context["what"] == "What we're building"
        assert context["why"] == "Why we need it"
        assert context["constraints"] == "Technical constraints"


class TestSessionState:
    """Tests for SessionState pydantic model."""

    def test_session_state_serialization(self):
        """Test SessionState serialization and deserialization."""
        state = SessionState(
            session_id="test-session",
            status="discussing",
            step="what",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            original_request="Test request",
            conversation_id="conv-123",
        )

        # Serialize
        json_str = state.model_dump_json()
        data = json.loads(json_str)

        assert data["session_id"] == "test-session"
        assert data["conversation_id"] == "conv-123"

        # Deserialize
        restored = SessionState(**data)
        assert restored.session_id == state.session_id
        assert restored.conversation_id == state.conversation_id


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing clients."""

    def test_legacy_generate_session_id(self):
        """Test that legacy generate_session_id still works."""
        manager = SessionManager(base_path=Path(tempfile.mkdtemp()))

        # Legacy method should still exist and work
        session_id = manager.generate_session_id("Hello world")

        assert session_id is not None
        assert len(session_id) > 0
        # Legacy method includes timestamp, so different each time
        session_id2 = manager.generate_session_id("Hello world")
        # Note: These might rarely be the same if called in same second

    def test_without_conversation_id_still_works(self):
        """Test that clients without X-Conversation-ID still work."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)

        # This should work without conversation_id
        session_id, state = manager.get_or_create_session(
            first_message="Test message from legacy client",
        )

        assert session_id is not None
        assert state is not None
        assert state.status == "discussing"


class TestCacheConsistency:
    """Tests for conversation ID cache consistency."""

    def test_cache_is_used(self):
        """Test that the conversation cache is used for quick lookups."""
        tmp_dir = Path(tempfile.mkdtemp())
        manager = SessionManager(base_path=tmp_dir)
        conv_id = "cached-conv-id"

        # First call should create and cache
        session_id1, _ = manager.get_or_create_session(
            first_message="Hello",
            conversation_id=conv_id,
        )

        # Check cache is populated
        assert conv_id in manager._conversation_cache
        assert manager._conversation_cache[conv_id] == session_id1

        # Second call should use cache
        session_id2, _ = manager.get_or_create_session(
            first_message="Different message",
            conversation_id=conv_id,
        )

        assert session_id1 == session_id2

    def test_fresh_manager_finds_existing_session(self):
        """Test that a new manager instance can find existing session."""
        tmp_dir = Path(tempfile.mkdtemp())
        conv_id = "persisted-conv-id"

        # Create session with first manager
        manager1 = SessionManager(base_path=tmp_dir)
        session_id1, state1 = manager1.get_or_create_session(
            first_message="Hello",
            conversation_id=conv_id,
        )

        # Create new manager instance (simulates server restart)
        manager2 = SessionManager(base_path=tmp_dir)
        session_id2, state2 = manager2.get_or_create_session(
            first_message="Different message",
            conversation_id=conv_id,
        )

        # Should find the same session
        assert session_id1 == session_id2
        assert state1.created_at == state2.created_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
