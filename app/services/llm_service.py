"""Provider-agnostic LLM client for structured JSON generation.

Supports Anthropic Claude (default), OpenAI, and Google Gemini. Only the
configured provider's SDK needs to be installed/importable at runtime.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

from app.config import Settings, get_settings


class LLMError(Exception):
    pass


class LLMClient(ABC):
    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call the LLM and return a parsed JSON object."""


def _extract_json_object(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    # Strip markdown code fences if the model wrapped the JSON anyway.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("LLM response did not contain a JSON object")

    candidate = raw_text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM response was not valid JSON: {exc}") from exc


class AnthropicLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model
        self._max_tokens = settings.llm_max_output_tokens
        self._timeout = settings.llm_timeout_seconds

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/transport error uniformly
            raise LLMError(f"Anthropic API call failed: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        return _extract_json_object(text)


class OpenAILLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._max_tokens = settings.llm_max_output_tokens
        self._timeout = settings.llm_timeout_seconds

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI API call failed: {exc}") from exc

        text = response.choices[0].message.content or ""
        return _extract_json_object(text)


class GeminiLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not configured")
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config={"response_mime_type": "application/json"},
        )

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            response = await self._model.generate_content_async(
                f"{system_prompt}\n\n{user_prompt}"
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini API call failed: {exc}") from exc

        return _extract_json_object(response.text or "")


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        return AnthropicLLMClient(settings)
    if provider == "openai":
        return OpenAILLMClient(settings)
    if provider == "gemini":
        return GeminiLLMClient(settings)

    raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}")
