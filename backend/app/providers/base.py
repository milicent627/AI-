from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import AsyncGenerator


@dataclass
class ProviderResult:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class BaseProvider(ABC):
    def __init__(self, api_key: str, model_id: str, base_url: str = "", **params):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self.params = params

    @abstractmethod
    async def generate(self, messages: list[dict]) -> ProviderResult:
        ...

    @abstractmethod
    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...
