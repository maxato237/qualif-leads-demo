from typing import Protocol

from app.infra.mistral_http import ProviderError, post_json


class LLMClient(Protocol):
    def complete_json(self, messages: list[dict], max_tokens: int) -> str: ...


class MistralLLMClient:
    def __init__(self, api_key: str, model: str, timeout: float = 30):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def complete_json(self, messages: list[dict], max_tokens: int) -> str:
        """Renvoie un objet JSON sous forme de texte (mode JSON de Mistral)."""
        data = post_json(
            "/chat/completions",
            {
                "model": self._model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0,  # même message, même qualification : une démo doit être stable
                "response_format": {"type": "json_object"},
            },
            self._api_key,
            self._timeout,
        )
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError) as exc:
            raise ProviderError("Réponse Mistral inattendue") from exc
