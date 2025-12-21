"""Multi-Provider LLM Client for HELIX v4.

Unified interface for multiple LLM providers.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml


@dataclass
class ModelConfig:
    """Configuration for a specific model.

    Attributes:
        provider: Provider name (openrouter, anthropic, openai, xai).
        model_id: The model identifier at the provider.
        base_url: API base URL for the provider.
        api_format: API format to use (openai or anthropic).
        api_key_env: Environment variable name for the API key.
    """
    provider: str
    model_id: str
    base_url: str
    api_format: str
    api_key_env: str = ""


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider.

    Attributes:
        name: Provider name.
        base_url: API base URL.
        api_format: API format (openai or anthropic).
        api_key_env: Environment variable for API key.
        models: Available models at this provider.
    """
    name: str
    base_url: str
    api_format: str
    api_key_env: str
    models: dict[str, str] = field(default_factory=dict)


class LLMClient:
    """Multi-provider LLM client with unified interface.

    Supports OpenRouter, Anthropic, OpenAI, and xAI providers.
    Configuration is loaded from llm-providers.yaml.

    Model specs can be:
    - Simple model name: "claude-3-opus" (uses default provider)
    - Provider prefixed: "anthropic/claude-3-opus"
    - Full model ID: "openrouter/anthropic/claude-3-opus"

    Example:
        client = LLMClient()

        # Simple completion
        response = await client.complete(
            model_spec="claude-3-opus",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        # With specific provider
        response = await client.complete(
            model_spec="openrouter/claude-3-opus",
            messages=[{"role": "user", "content": "Hello!"}]
        )
    """

    DEFAULT_CONFIG_PATH = Path("/home/aiuser01/helix-v4/config/llm-providers.yaml")

    DEFAULT_PROVIDERS: dict[str, ProviderConfig] = {
        "openrouter": ProviderConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_format="openai",
            api_key_env="OPENROUTER_API_KEY",
            models={
                "claude-3-opus": "anthropic/claude-3-opus",
                "claude-3-sonnet": "anthropic/claude-3-sonnet",
                "claude-3-haiku": "anthropic/claude-3-haiku",
                "gpt-4-turbo": "openai/gpt-4-turbo",
                "gpt-4o": "openai/gpt-4o",
            },
        ),
        "anthropic": ProviderConfig(
            name="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_format="anthropic",
            api_key_env="ANTHROPIC_API_KEY",
            models={
                "claude-3-opus": "claude-3-opus-20240229",
                "claude-3-sonnet": "claude-3-sonnet-20240229",
                "claude-3-haiku": "claude-3-haiku-20240307",
                "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            },
        ),
        "openai": ProviderConfig(
            name="openai",
            base_url="https://api.openai.com/v1",
            api_format="openai",
            api_key_env="OPENAI_API_KEY",
            models={
                "gpt-4-turbo": "gpt-4-turbo",
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini",
                "o1": "o1",
                "o1-mini": "o1-mini",
            },
        ),
        "xai": ProviderConfig(
            name="xai",
            base_url="https://api.x.ai/v1",
            api_format="openai",
            api_key_env="XAI_API_KEY",
            models={
                "grok-2": "grok-2",
                "grok-2-mini": "grok-2-mini",
            },
        ),
    }

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the LLM client.

        Args:
            config_path: Path to llm-providers.yaml.
                        Defaults to /home/aiuser01/helix-v4/config/llm-providers.yaml.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.providers: dict[str, ProviderConfig] = {}
        self.default_provider: str = "openrouter"
        self._load_config()

    def _load_config(self) -> None:
        """Load provider configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            self.default_provider = config.get("default_provider", "openrouter")

            for name, pconfig in config.get("providers", {}).items():
                self.providers[name] = ProviderConfig(
                    name=name,
                    base_url=pconfig.get("base_url", ""),
                    api_format=pconfig.get("api_format", "openai"),
                    api_key_env=pconfig.get("api_key_env", ""),
                    models=pconfig.get("models", {}),
                )
        else:
            self.providers = self.DEFAULT_PROVIDERS.copy()

    def resolve_model(self, model_spec: str) -> ModelConfig:
        """Resolve a model spec to a full ModelConfig.

        Args:
            model_spec: Model specification string.
                       Can be "model", "provider/model", etc.

        Returns:
            ModelConfig with full provider and model details.

        Raises:
            ValueError: If provider or model not found.
        """
        parts = model_spec.split("/")

        if len(parts) == 1:
            model_name = parts[0]
            provider_name = self.default_provider
        else:
            provider_name = parts[0]
            model_name = "/".join(parts[1:])

        if provider_name not in self.providers:
            if provider_name not in self.DEFAULT_PROVIDERS:
                raise ValueError(f"Unknown provider: {provider_name}")
            provider = self.DEFAULT_PROVIDERS[provider_name]
        else:
            provider = self.providers[provider_name]

        if model_name in provider.models:
            model_id = provider.models[model_name]
        else:
            model_id = model_name

        return ModelConfig(
            provider=provider_name,
            model_id=model_id,
            base_url=provider.base_url,
            api_format=provider.api_format,
            api_key_env=provider.api_key_env,
        )

    async def complete(
        self,
        model_spec: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate a completion from the LLM.

        Args:
            model_spec: Model specification string.
            messages: List of message dictionaries with "role" and "content".
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 to 1.0).
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated text response.

        Raises:
            ValueError: If API key is not set.
            httpx.HTTPError: If the API request fails.
        """
        config = self.resolve_model(model_spec)

        api_key = os.environ.get(config.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"API key not set. Please set {config.api_key_env} environment variable."
            )

        if config.api_format == "anthropic":
            return await self._complete_anthropic(
                config, api_key, messages, max_tokens, temperature, **kwargs
            )
        else:
            return await self._complete_openai(
                config, api_key, messages, max_tokens, temperature, **kwargs
            )

    async def _complete_openai(
        self,
        config: ModelConfig,
        api_key: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> str:
        """Complete using OpenAI-compatible API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if config.provider == "openrouter":
            headers["HTTP-Referer"] = "https://helix-v4.dev"
            headers["X-Title"] = "HELIX v4"

        payload = {
            "model": config.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _complete_anthropic(
        self,
        config: ModelConfig,
        api_key: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> str:
        """Complete using Anthropic API."""
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        system_message = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        payload: dict[str, Any] = {
            "model": config.model_id,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_message:
            payload["system"] = system_message

        payload.update(kwargs)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()

            data = response.json()
            return data["content"][0]["text"]

    def get_available_models(self, provider: str | None = None) -> list[str]:
        """Get list of available models.

        Args:
            provider: Optional provider to filter by.

        Returns:
            List of model specs.
        """
        models = []

        providers_to_check = (
            {provider: self.providers.get(provider) or self.DEFAULT_PROVIDERS.get(provider)}
            if provider
            else {**self.DEFAULT_PROVIDERS, **self.providers}
        )

        for pname, pconfig in providers_to_check.items():
            if pconfig:
                for model_name in pconfig.models:
                    models.append(f"{pname}/{model_name}")

        return sorted(models)
