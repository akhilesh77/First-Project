"""xAI Grok client (OpenAI-compatible Chat Completions API)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import (
    get_llm_api_key,
    get_llm_base_url,
    get_llm_max_tokens,
    get_llm_model,
    get_llm_temperature,
    get_llm_timeout_seconds,
)

logger = logging.getLogger(__name__)


class GrokClientError(Exception):
    """Raised when the Grok API call fails after retries."""


class GrokClient:
    """HTTP client for xAI Grok via https://api.x.ai/v1/chat/completions."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or get_llm_api_key()
        self._base_url = (base_url or get_llm_base_url()).rstrip("/")
        self._model = model or get_llm_model()
        self._timeout = timeout_seconds if timeout_seconds is not None else get_llm_timeout_seconds()
        self._temperature = temperature if temperature is not None else get_llm_temperature()
        self._max_tokens = max_tokens if max_tokens is not None else get_llm_max_tokens()
        self._max_retries = max_retries

        if not self._api_key:
            raise GrokClientError("LLM API key is not configured (set XAI_API_KEY or LLM_API_KEY)")

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Call Grok and return assistant message content."""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    wait = 2**attempt
                    logger.warning("Grok rate limit; retry in %ss", wait)
                    time.sleep(wait)
                    continue
                if response.status_code >= 500:
                    wait = 2**attempt
                    logger.warning("Grok server error %s; retry in %ss", response.status_code, wait)
                    time.sleep(wait)
                    continue
                if response.status_code >= 400:
                    raise GrokClientError(
                        f"Grok API error {response.status_code}: {response.text[:500]}"
                    )
                data = response.json()
                return self._extract_content(data)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("Grok request timeout (attempt %s)", attempt + 1)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("Grok HTTP error (attempt %s): %s", attempt + 1, exc)

        raise GrokClientError(f"Grok request failed after retries: {last_error}")

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise GrokClientError("Grok response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content or not str(content).strip():
            raise GrokClientError("Grok response missing message content")
        return str(content).strip()
