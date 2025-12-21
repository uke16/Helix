import pytest
from unittest.mock import AsyncMock, patch

from helix.llm_client import LLMClient, ModelConfig


class TestLLMClient:
    """Tests for LLMClient."""

    def test_resolve_model_openrouter(self):
        """Should resolve OpenRouter model string."""
        client = LLMClient()
        config = client.resolve_model("openrouter:gpt-4o")

        assert isinstance(config, ModelConfig)
        assert config.provider == "openrouter"
        assert "gpt-4o" in config.model_id

    def test_resolve_model_alias(self):
        """Should resolve model aliases."""
        client = LLMClient()
        config = client.resolve_model("opus")

        assert isinstance(config, ModelConfig)
        assert "opus" in config.model_id.lower() or "claude" in config.model_id.lower()

    def test_resolve_model_invalid(self):
        """Should raise for invalid model."""
        client = LLMClient()

        with pytest.raises(ValueError):
            client.resolve_model("invalid:model")

    @pytest.mark.asyncio
    async def test_complete_mock(self, mock_llm_response):
        """Should call LLM and return response."""
        client = LLMClient()

        with patch.object(client, "_call_api", new_callable=AsyncMock) as mock:
            mock.return_value = mock_llm_response

            result = await client.complete(
                model="openrouter:gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert "Test response" in result.content
