from functools import lru_cache
from typing import Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    firestarter_api_key: Optional[str] = Field(default=None, alias="FIRESTARTER_API_KEY")

    # Firecrawl
    firecrawl_api_key: str = Field(..., alias="FIRECRAWL_API_KEY")
    firecrawl_base_url: HttpUrl = Field("https://api.firecrawl.dev/v2", alias="FIRECRAWL_BASE_URL")
    firecrawl_poll_interval_ms: int = Field(1000, ge=200, le=10_000, alias="FIRECRAWL_POLL_INTERVAL_MS")
    firecrawl_poll_timeout_ms: int = Field(90_000, ge=5_000, le=180_000, alias="FIRECRAWL_POLL_TIMEOUT_MS")

    # Upstash Search
    upstash_search_rest_url: HttpUrl = Field(..., alias="UPSTASH_SEARCH_REST_URL")
    upstash_search_rest_token: str = Field(..., alias="UPSTASH_SEARCH_REST_TOKEN")
    upstash_search_index: str = Field("firestarter", alias="UPSTASH_SEARCH_INDEX")

    # Redis (optional, parity with TS)
    upstash_redis_rest_url: Optional[HttpUrl] = Field(None, alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: Optional[str] = Field(None, alias="UPSTASH_REDIS_REST_TOKEN")

    # AI providers
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(800, alias="AI_MAX_TOKENS")
    ai_system_prompt: str = Field(
        "You are a friendly assistant. If a user greets you or engages in small talk, "
        "respond politely without referencing the website. For questions about the website, "
        "answer using ONLY the provided context below. Do not use any other knowledge. "
        "If the context isn't sufficient to answer, say so explicitly.",
        alias="AI_SYSTEM_PROMPT",
    )

    # Search display limits
    search_max_results: int = Field(100, alias="SEARCH_MAX_RESULTS")
    search_max_context_docs: int = Field(10, alias="SEARCH_MAX_CONTEXT_DOCS")
    search_max_context_length: int = Field(1500, alias="SEARCH_MAX_CONTEXT_LENGTH")
    search_max_sources_display: int = Field(20, alias="SEARCH_MAX_SOURCES_DISPLAY")
    search_snippet_length: int = Field(200, alias="SEARCH_SNIPPET_LENGTH")

    # Crawling defaults (parity with TS config)
    crawling_default_limit: int = Field(10, alias="CRAWLING_DEFAULT_LIMIT")
    crawling_cache_max_age_ms: int = Field(1_209_600_000, alias="CRAWLING_CACHE_MAX_AGE_MS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

