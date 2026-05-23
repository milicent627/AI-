from collections.abc import AsyncGenerator
from anthropic import AsyncAnthropic
from .base import BaseProvider, ProviderResult


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, model_id: str = "claude-sonnet-4-20250514", base_url: str = "", **params):
        super().__init__(api_key, model_id, base_url, **params)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncAnthropic(**kwargs)

    def _to_anthropic_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        system = None
        msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append({"role": m["role"], "content": m["content"]})
        return system, msgs

    async def generate(self, messages: list[dict]) -> ProviderResult:
        system, msgs = self._to_anthropic_messages(messages)
        kwargs = {
            "model": self.model_id,
            "messages": msgs,
            "max_tokens": self.params.get("max_tokens", 4096),
            "temperature": self.params.get("temperature", 0.8),
        }
        if system:
            kwargs["system"] = system
        response = await self.client.messages.create(**kwargs)
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text
        return ProviderResult(
            content=text,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
            model=response.model,
        )

    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        system, msgs = self._to_anthropic_messages(messages)
        kwargs = {
            "model": self.model_id,
            "messages": msgs,
            "max_tokens": self.params.get("max_tokens", 4096),
            "temperature": self.params.get("temperature", 0.8),
        }
        if system:
            kwargs["system"] = system
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        return self.client.count_tokens(text)
