"""Provider-agnostic LLM client (OpenRouter / OpenAI-compatible) with retries.

The client speaks the OpenAI Chat Completions wire format, which OpenRouter
implements. It exposes both a blocking :meth:`complete` and a token
:meth:`stream`. When no API key is configured (``settings.use_mock_llm``) the
client reports itself unavailable; callers (the Narrator) then fall back to a
deterministic template so the platform runs fully offline.

Reliability: transient failures are retried with exponential backoff; a
persistent failure raises :class:`LLMError`, which the agent treats as a signal
to degrade to the template narrator rather than surfacing a stack trace.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)

Message = dict[str, str]


class LLMClient:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.timeout = settings.llm_timeout_seconds

    @property
    def available(self) -> bool:
        return not settings.use_mock_llm

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter attribution headers (harmless elsewhere).
            "HTTP-Referer": settings.openrouter_referer,
            "X-Title": settings.openrouter_title,
        }

    def _payload(self, messages: list[Message], *, json_mode: bool, stream: bool) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "stream": stream,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=6),
        reraise=True,
    )
    def complete(self, messages: list[Message], *, json_mode: bool = False) -> str:
        if not self.available:
            raise LLMError("LLM is not configured (running in offline mock mode).")
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, json_mode=json_mode, stream=False),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMError(f"Malformed LLM response: {exc}") from exc

    def stream(self, messages: list[Message]) -> Iterator[str]:
        """Yield content deltas as they arrive (OpenRouter SSE)."""
        if not self.available:
            raise LLMError("LLM is not configured (running in offline mock mode).")
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(messages, json_mode=False, stream=True),
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
                if delta:
                    yield delta


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
