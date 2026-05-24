from .base import BaseProvider
from .openai_provider import OpenAIProvider
from ..models.model_config import ProviderType, ModelConfig


PROVIDER_MAP = {
    ProviderType.custom: OpenAIProvider,
}


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    def get_or_create(self, config: ModelConfig) -> BaseProvider:
        if config.id in self._providers:
            return self._providers[config.id]

        cls = PROVIDER_MAP.get(config.provider)
        if cls is None:
            raise ValueError(f"Unsupported provider: {config.provider}")

        params = {
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            **config.extra_params,
        }
        provider = cls(
            api_key=config.api_key,
            model_id=config.model_id,
            base_url=config.base_url,
            **params,
        )
        self._providers[config.id] = provider
        return provider

    def clear(self):
        self._providers.clear()
