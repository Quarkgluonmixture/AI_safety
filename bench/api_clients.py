"""Unified API clients with retry and simple rate limiting."""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class ClientResult:
    """Text output plus an optional reasoning trace."""

    text: str
    reasoning_trace: str | None = None


class BaseClient(ABC):
    """Base API client with retries and rate limiting."""

    env_var: str

    def __init__(
        self,
        *,
        model: str,
        endpoint: str | None = None,
        api_key: str | None = None,
        min_interval_seconds: float = 0.0,
    ) -> None:
        self.model = model
        self.endpoint = endpoint
        self.api_key = api_key or os.getenv(self.env_var)
        self.min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call_at = 0.0
        if not self.api_key:
            raise RuntimeError(f"{self.env_var} is required")

    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool = False,
    ) -> ClientResult:
        """Generate a response for one prompt."""
        return self._generate_with_retry(prompt, max_tokens, temperature, capture_reasoning_trace)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=60), reraise=True)
    def _generate_with_retry(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool,
    ) -> ClientResult:
        """Generate once with retry behavior."""
        self._throttle()
        return self._generate_once(prompt, max_tokens, temperature, capture_reasoning_trace)

    @abstractmethod
    def _generate_once(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool,
    ) -> ClientResult:
        """Provider-specific generation call."""

    def _throttle(self) -> None:
        """Sleep until the configured minimum interval has elapsed."""
        if self.min_interval_seconds <= 0:
            return
        with self._lock:
            elapsed = time.monotonic() - self._last_call_at
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
            self._last_call_at = time.monotonic()


class OpenAIClient(BaseClient):
    """OpenAI chat-completions client."""

    env_var = "OPENAI_API_KEY"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client: Any | None = None

    def _generate_once(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool,
    ) -> ClientResult:
        """Call OpenAI once."""
        from openai import OpenAI

        if self._client is None:
            kwargs = {"api_key": self.api_key}
            if self.endpoint:
                kwargs["base_url"] = self.endpoint
            self._client = OpenAI(**kwargs)
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        message = completion.choices[0].message
        reasoning_trace = getattr(message, "reasoning_content", None) if capture_reasoning_trace else None
        return ClientResult(text=message.content or "", reasoning_trace=reasoning_trace)


class AnthropicClient(BaseClient):
    """Anthropic messages client."""

    env_var = "ANTHROPIC_API_KEY"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client: Any | None = None

    def _generate_once(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool,
    ) -> ClientResult:
        """Call Anthropic once."""
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key, base_url=self.endpoint)
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        for block in response.content:
            block_type = getattr(block, "type", "")
            if block_type == "text":
                text_parts.append(getattr(block, "text", ""))
            elif capture_reasoning_trace and block_type in {"thinking", "redacted_thinking"}:
                reasoning_parts.append(getattr(block, "thinking", "") or getattr(block, "data", ""))
        return ClientResult(text="".join(text_parts), reasoning_trace="\n".join(reasoning_parts) or None)


class GoogleClient(BaseClient):
    """Google Generative AI client."""

    env_var = "GOOGLE_API_KEY"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._model: Any | None = None

    def _generate_once(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        capture_reasoning_trace: bool,
    ) -> ClientResult:
        """Call Google once."""
        import google.generativeai as genai

        if self._model is None:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model)
        response = self._model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        return ClientResult(text=getattr(response, "text", ""), reasoning_trace=None)


class DeepSeekClient(OpenAIClient):
    """DeepSeek OpenAI-compatible client."""

    env_var = "DEEPSEEK_API_KEY"

    def __init__(self, **kwargs: Any) -> None:
        kwargs["endpoint"] = kwargs.get("endpoint") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        super().__init__(**kwargs)


CLIENTS: dict[str, type[BaseClient]] = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "google": GoogleClient,
    "deepseek": DeepSeekClient,
}


def build_client(provider: str, config: dict[str, Any]) -> BaseClient:
    """Build a concrete client from config."""
    provider_key = provider.lower()
    if provider_key not in CLIENTS:
        raise ValueError(f"unsupported provider: {provider}")
    return CLIENTS[provider_key](
        model=str(config["model"]),
        endpoint=config.get("endpoint"),
        min_interval_seconds=float(config.get("min_interval_seconds", 0.0)),
    )

