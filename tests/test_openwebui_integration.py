"""Integration tests for Open WebUI API route with X-Conversation-ID (ADR-029).

Tests the OpenAI-compatible chat completions endpoint:
- X-Conversation-ID header extraction and usage
- Session persistence across multiple requests
- Backward compatibility without header
- Streaming and non-streaming responses
"""

import asyncio
import json
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router and models
from helix.api.routes.openai import router, session_manager
from helix.api.models import ChatCompletionRequest, ChatMessage


@pytest.fixture
def app():
    """Create FastAPI test application."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_sessions_dir():
    """Create temporary sessions directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_session_manager(temp_sessions_dir):
    """Patch session manager to use temp directory."""
    from helix.api.session_manager import SessionManager
    manager = SessionManager(base_path=temp_sessions_dir)
    with patch('helix.api.routes.openai.session_manager', manager):
        yield manager


class TestXConversationIdHeader:
    """Tests for X-Conversation-ID header extraction."""

    def test_header_extracted_from_request(self, client, mock_session_manager):
        """X-Conversation-ID header is correctly extracted."""
        conversation_id = str(uuid.uuid4())

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Test response"

            response = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200
            # Session should be created with conversation_id
            session_id = f"conv-{conversation_id}"
            assert mock_session_manager.session_exists(session_id)

    def test_header_case_insensitive(self, client, mock_session_manager):
        """X-Conversation-ID header works regardless of case."""
        conversation_id = "test-case-insensitive"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Test response"

            # FastAPI/Starlette normalizes headers to lowercase
            response = client.post(
                "/v1/chat/completions",
                headers={"x-conversation-id": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200

    def test_header_with_uuid_format(self, client, mock_session_manager):
        """UUID format conversation IDs work correctly."""
        conversation_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Test response"

            response = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "What is HELIX?"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200


class TestSessionPersistence:
    """Tests for session persistence across requests."""

    def test_same_conversation_id_reuses_session(self, client, mock_session_manager):
        """Multiple requests with same X-Conversation-ID use same session."""
        conversation_id = "persistent-session-test"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Response"

            # First request
            response1 = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "First message"}],
                    "stream": False,
                },
            )

            # Second request with same conversation ID
            response2 = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [
                        {"role": "user", "content": "First message"},
                        {"role": "assistant", "content": "Response"},
                        {"role": "user", "content": "Second message"},
                    ],
                    "stream": False,
                },
            )

            assert response1.status_code == 200
            assert response2.status_code == 200

            # Should only have one session directory
            session_id = f"conv-{conversation_id}"
            assert mock_session_manager.session_exists(session_id)

            # Verify state preserved original request
            state = mock_session_manager.get_state(session_id)
            assert state is not None
            assert state.original_request == "First message"

    def test_different_conversation_ids_create_different_sessions(
        self, client, mock_session_manager
    ):
        """Different conversation IDs create separate sessions."""
        conv_id_1 = "conversation-1"
        conv_id_2 = "conversation-2"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Response"

            client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conv_id_1},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hello from conv 1"}],
                    "stream": False,
                },
            )

            client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conv_id_2},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hello from conv 2"}],
                    "stream": False,
                },
            )

            # Should have two separate sessions
            assert mock_session_manager.session_exists(f"conv-{conv_id_1}")
            assert mock_session_manager.session_exists(f"conv-{conv_id_2}")

    def test_messages_saved_to_session(self, client, mock_session_manager):
        """Messages are saved to session context directory."""
        conversation_id = "messages-test"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Response"

            messages = [
                {"role": "user", "content": "What is HELIX?"},
                {"role": "assistant", "content": "HELIX is..."},
                {"role": "user", "content": "Tell me more"},
            ]

            client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": messages,
                    "stream": False,
                },
            )

            # Verify messages saved
            session_id = f"conv-{conversation_id}"
            messages_file = mock_session_manager.base_path / session_id / "context" / "messages.json"
            assert messages_file.exists()

            saved_messages = json.loads(messages_file.read_text())
            assert len(saved_messages) == 3
            assert saved_messages[0]["content"] == "What is HELIX?"


class TestBackwardCompatibility:
    """Tests for backward compatibility without X-Conversation-ID."""

    def test_request_without_header_still_works(self, client, mock_session_manager):
        """Requests without X-Conversation-ID header work correctly."""
        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Response without header"

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "No header test"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["choices"][0]["message"]["content"] == "Response without header"

    def test_fallback_creates_new_sessions(self, client, mock_session_manager):
        """Without header, each request creates new session (ADR-035 random IDs)."""
        message = "Message for random ID generation"

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Response"

            # First request
            client.post(
                "/v1/chat/completions",
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
            )

            # Count sessions before second request
            sessions_before = list(mock_session_manager.base_path.iterdir())

            # Second request with exact same message
            client.post(
                "/v1/chat/completions",
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
            )

            # ADR-035: Without header, each request creates new session
            sessions_after = list(mock_session_manager.base_path.iterdir())
            assert len(sessions_after) == len(sessions_before) + 1
            # All should have random session- prefix
            assert all(s.name.startswith("session-") for s in sessions_after)


class TestOpenAICompatibility:
    """Tests for OpenAI API compatibility."""

    def test_response_format_matches_openai(self, client, mock_session_manager):
        """Response format matches OpenAI chat completions API."""
        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Hello! How can I help?"

            response = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": "format-test"},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Check OpenAI format
            assert "id" in data
            assert data["id"].startswith("chatcmpl-")
            assert "created" in data
            assert "model" in data
            assert data["model"] == "helix-consultant"
            assert "choices" in data
            assert len(data["choices"]) == 1
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert data["choices"][0]["finish_reason"] == "stop"
            assert "usage" in data

    def test_models_endpoint(self, client):
        """GET /v1/models returns available models."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert len(data["data"]) > 0

        model = data["data"][0]
        assert model["id"] == "helix-consultant"
        assert model["owned_by"] == "helix"


class TestErrorHandling:
    """Tests for error handling."""

    def test_empty_messages_returns_error(self, client):
        """Request with empty messages returns error."""
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

    def test_no_user_message_returns_error(self, client):
        """Request without user message returns error."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "assistant", "content": "I am assistant"}],
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "Fehler" in data["choices"][0]["message"]["content"]


class TestMultiTurnDialog:
    """Tests for multi-turn dialog scenarios."""

    def test_open_webui_typical_flow(self, client, mock_session_manager):
        """Simulates typical Open WebUI multi-turn conversation."""
        conversation_id = str(uuid.uuid4())

        with patch('helix.api.routes.openai._run_consultant', new_callable=AsyncMock) as mock_run:
            # Turn 1
            mock_run.return_value = "HELIX ist ein AI Development System."
            response1 = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Was ist HELIX?"}],
                    "stream": False,
                },
            )

            # Turn 2
            mock_run.return_value = "HELIX orchestriert Claude Code Instanzen."
            response2 = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [
                        {"role": "user", "content": "Was ist HELIX?"},
                        {"role": "assistant", "content": "HELIX ist ein AI Development System."},
                        {"role": "user", "content": "Wie funktioniert es?"},
                    ],
                    "stream": False,
                },
            )

            # Turn 3
            mock_run.return_value = "Du kannst ein neues Projekt mit helix new erstellen."
            response3 = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": conversation_id},
                json={
                    "model": "helix-consultant",
                    "messages": [
                        {"role": "user", "content": "Was ist HELIX?"},
                        {"role": "assistant", "content": "HELIX ist ein AI Development System."},
                        {"role": "user", "content": "Wie funktioniert es?"},
                        {"role": "assistant", "content": "HELIX orchestriert Claude Code Instanzen."},
                        {"role": "user", "content": "Wie starte ich ein Projekt?"},
                    ],
                    "stream": False,
                },
            )

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response3.status_code == 200

            # All should use same session
            session_id = f"conv-{conversation_id}"
            assert mock_session_manager.session_exists(session_id)

            # Verify messages saved
            messages_file = mock_session_manager.base_path / session_id / "context" / "messages.json"
            saved_messages = json.loads(messages_file.read_text())
            assert len(saved_messages) == 5  # Last request had 5 messages

    def test_context_preserved_across_server_restart(self, temp_sessions_dir):
        """Simulates session recovery after server restart."""
        conversation_id = "restart-test"
        session_id = f"conv-{conversation_id}"

        # Simulate first server instance
        from helix.api.session_manager import SessionManager
        manager1 = SessionManager(base_path=temp_sessions_dir)

        _, state1 = manager1.get_or_create_session(
            first_message="Initial message",
            conversation_id=conversation_id,
        )
        manager1.save_messages(session_id, [
            {"role": "user", "content": "Initial message"},
            {"role": "assistant", "content": "Response 1"},
        ])

        # Simulate server restart with new manager instance
        manager2 = SessionManager(base_path=temp_sessions_dir)

        _, state2 = manager2.get_or_create_session(
            first_message="This message is ignored",  # Different message
            conversation_id=conversation_id,  # Same conversation
        )

        # Should recover original session
        assert state2.original_request == "Initial message"
        assert state2.session_id == session_id


class TestStreamingResponses:
    """Tests for streaming response mode."""

    def test_streaming_request_returns_sse(self, client, mock_session_manager):
        """Streaming request returns server-sent events."""
        with patch('helix.api.routes.openai._run_consultant_streaming') as mock_stream:
            async def mock_generator():
                yield 'data: {"id":"test","choices":[{"delta":{"content":"Hello"}}]}\n\n'
                yield 'data: [DONE]\n\n'

            mock_stream.return_value = mock_generator()

            response = client.post(
                "/v1/chat/completions",
                headers={"X-Conversation-ID": "stream-test"},
                json={
                    "model": "helix-consultant",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
