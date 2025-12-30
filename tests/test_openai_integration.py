"""Integration tests for OpenAI API routes with X-Conversation-ID (ADR-029).

Tests the HTTP-level integration to verify:
1. X-Conversation-ID header is correctly extracted
2. Sessions persist across multiple requests with same conversation ID
3. Backward compatibility for clients without the header
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))


# We need to mock the ClaudeRunner before importing the routes
@pytest.fixture(autouse=True)
def mock_claude_runner():
    """Mock ClaudeRunner for all tests."""
    with patch("helix.api.routes.openai.ClaudeRunner") as mock:
        mock_instance = MagicMock()
        mock_instance.check_availability = AsyncMock(return_value=True)
        mock_instance.run_phase = AsyncMock(return_value=MagicMock(
            success=True,
            stdout='{"type": "result", "result": "Test response"}',
            stderr="",
        ))
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Create a temporary sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def mock_session_manager(temp_sessions_dir):
    """Create a mock session manager with temp directory."""
    from helix.api.session_manager import SessionManager

    manager = SessionManager(base_path=temp_sessions_dir)

    with patch("helix.api.routes.openai.session_manager", manager):
        yield manager


@pytest.fixture
def mock_jinja_env():
    """Mock the Jinja2 template environment."""
    with patch("helix.api.routes.openai.jinja_env") as mock_env:
        mock_template = MagicMock()
        mock_template.render.return_value = "# Mock CLAUDE.md content"
        mock_env.get_template.return_value = mock_template
        yield mock_env


@pytest.fixture
def client(mock_session_manager, mock_jinja_env):
    """Create a test client with mocked dependencies."""
    from helix.api.routes.openai import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


class TestXConversationIdHeader:
    """Tests for X-Conversation-ID header handling."""

    def test_header_is_extracted(self, client, mock_session_manager):
        """Test that X-Conversation-ID header is correctly extracted."""
        conv_id = "test-conversation-12345"

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"X-Conversation-ID": conv_id},
        )

        assert response.status_code == 200

        # Check that session was created with normalized conv_id
        sessions = list(mock_session_manager.base_path.iterdir())
        assert len(sessions) == 1
        assert sessions[0].name.startswith("conv-")
        assert "test-conversation-12345" in sessions[0].name

    def test_same_conv_id_same_session(self, client, mock_session_manager):
        """Test that same X-Conversation-ID uses same session."""
        conv_id = "persistent-conversation"

        # First request
        response1 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "First message"}],
                "stream": False,
            },
            headers={"X-Conversation-ID": conv_id},
        )
        assert response1.status_code == 200

        # Second request with same conv_id
        response2 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [
                    {"role": "user", "content": "First message"},
                    {"role": "assistant", "content": "Response"},
                    {"role": "user", "content": "Second message"},
                ],
                "stream": False,
            },
            headers={"X-Conversation-ID": conv_id},
        )
        assert response2.status_code == 200

        # Should still only have one session
        sessions = list(mock_session_manager.base_path.iterdir())
        assert len(sessions) == 1

    def test_different_conv_ids_different_sessions(self, client, mock_session_manager):
        """Test that different X-Conversation-IDs create different sessions."""
        # First conversation
        response1 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"X-Conversation-ID": "conversation-1"},
        )
        assert response1.status_code == 200

        # Second conversation
        response2 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"X-Conversation-ID": "conversation-2"},
        )
        assert response2.status_code == 200

        # Should have two sessions
        sessions = list(mock_session_manager.base_path.iterdir())
        assert len(sessions) == 2


class TestBackwardCompatibility:
    """Tests for backward compatibility without X-Conversation-ID."""

    def test_works_without_header(self, client, mock_session_manager):
        """Test that requests without X-Conversation-ID still work."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello from legacy client"}],
                "stream": False,
            },
            # No X-Conversation-ID header
        )

        assert response.status_code == 200

        # Session should be created
        sessions = list(mock_session_manager.base_path.iterdir())
        assert len(sessions) == 1
        # Should not have conv- prefix (using hash-based ID)
        assert not sessions[0].name.startswith("conv-")

    def test_same_message_without_header_gets_new_session(self, client, mock_session_manager):
        """Test that same message without header creates new sessions (ADR-035 random IDs)."""
        message = "Test message for random ID generation"

        # First request
        response1 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
        )
        assert response1.status_code == 200

        # Second request with same message
        response2 = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
        )
        assert response2.status_code == 200

        # ADR-035: Without X-Conversation-ID, each request creates a new session
        sessions = list(mock_session_manager.base_path.iterdir())
        assert len(sessions) == 2
        # Both should have random session- prefix
        assert all(s.name.startswith("session-") for s in sessions)


class TestMessagePersistence:
    """Tests for message persistence across requests."""

    def test_messages_are_saved(self, client, mock_session_manager):
        """Test that messages are persisted to context/messages.json."""
        conv_id = "message-persistence-test"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": messages,
                "stream": False,
            },
            headers={"X-Conversation-ID": conv_id},
        )
        assert response.status_code == 200

        # Check messages were saved
        sessions = list(mock_session_manager.base_path.iterdir())
        messages_file = sessions[0] / "context" / "messages.json"
        assert messages_file.exists()

        saved_messages = json.loads(messages_file.read_text())
        assert len(saved_messages) == 3
        assert saved_messages[0]["content"] == "Hello"


class TestErrorHandling:
    """Tests for error handling."""

    def test_empty_messages(self, client):
        """Test handling of empty messages array."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [],
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "Fehler" in data["choices"][0]["message"]["content"]

    def test_no_user_message(self, client):
        """Test handling of messages with no user message."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "assistant", "content": "Hi"}],
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "Fehler" in data["choices"][0]["message"]["content"]


class TestOpenAIFormat:
    """Tests for OpenAI-compatible response format."""

    def test_response_format(self, client, mock_session_manager):
        """Test that response follows OpenAI format."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"X-Conversation-ID": "format-test"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "id" in data
        assert data["id"].startswith("chatcmpl-")
        assert "created" in data
        assert "model" in data
        assert "choices" in data
        assert len(data["choices"]) == 1
        assert "message" in data["choices"][0]
        assert "role" in data["choices"][0]["message"]
        assert "content" in data["choices"][0]["message"]
        assert "finish_reason" in data["choices"][0]
        assert "usage" in data

    def test_models_endpoint(self, client):
        """Test the /v1/models endpoint."""
        response = client.get("/v1/models")

        assert response.status_code == 200
        data = response.json()

        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) > 0
        assert data["data"][0]["id"] == "helix-consultant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
