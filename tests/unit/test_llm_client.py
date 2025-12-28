import pytest

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
