"""Environment-driven settings for the link-analysis service."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic | openai | gemini

    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    request_timeout_seconds: float = float(os.getenv("FETCH_TIMEOUT_SECONDS", "10"))
    max_html_bytes: int = int(os.getenv("MAX_HTML_BYTES", "1_500_000"))
    max_content_chars_for_llm: int = int(os.getenv("MAX_CONTENT_CHARS_FOR_LLM", "6000"))

    llm_max_output_tokens: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2000"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
