import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderNotConfigured(Exception):
    pass


class AIProviderError(Exception):
    """Provider failure with a safe retry classification."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def is_configured() -> bool:
    return bool(os.getenv("AI_API_KEY", "").strip())


def generate_reply(messages: list[dict[str, str]], system_prompt: str | None = None, model: str | None = None) -> str:
    api_key = os.getenv("AI_API_KEY", "").strip()
    if not api_key:
        raise AIProviderNotConfigured("AI provider is not configured")
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = (model or os.getenv("AI_MODEL", "gpt-4o-mini")).strip()
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": (system_prompt or "You are a helpful, safe, concise assistant. Reply in the language used by the user.")[:4000]},
            *messages[-20:],
        ],
        "temperature": 0.7,
    }).encode("utf-8")
    request = Request(
        base_url + "/chat/completions",
        data=payload,
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("The model returned an empty response", retryable=False)
        return content.strip()[:12000]
    except HTTPError as exc:
        # Retry rate limits and server-side failures; auth and request errors are permanent.
        raise AIProviderError(
            "The AI provider request failed",
            retryable=(exc.code == 429 or 500 <= exc.code <= 599),
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise AIProviderError("The AI provider connection failed", retryable=True) from exc
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise AIProviderError("The AI provider returned an invalid response", retryable=False) from exc
