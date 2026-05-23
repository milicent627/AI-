from .openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key: str, model_id: str = "deepseek-chat", base_url: str = "", **params):
        if not base_url:
            base_url = "https://api.deepseek.com"
        super().__init__(api_key, model_id, base_url, **params)
