from collections.abc import AsyncGenerator
from openai import AsyncOpenAI
from .base import BaseProvider, ProviderResult


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, model_id: str = "gpt-4o", base_url: str = "", **params):
        super().__init__(api_key, model_id, base_url, **params)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)

    async def generate(self, messages: list[dict]) -> ProviderResult:
        response = await self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            temperature=self.params.get("temperature", 0.8),
            max_tokens=self.params.get("max_tokens", 4096),
        )
        choice = response.choices[0]
        return ProviderResult(
            content=choice.message.content or "",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model,
        )

    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            temperature=self.params.get("temperature", 0.8),
            max_tokens=self.params.get("max_tokens", 4096),
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str) -> int:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(self.model_id)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
