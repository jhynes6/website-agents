from functools import lru_cache
from typing import Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local", "../.env", "../.env.local"], 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # API
    firestarter_api_key: Optional[str] = Field(default=None, alias="FIRESTARTER_API_KEY")

    # Firecrawl
    firecrawl_api_key: str = Field(..., alias="FIRECRAWL_API_KEY")
    firecrawl_base_url: HttpUrl = Field("https://api.firecrawl.dev/v2", alias="FIRECRAWL_BASE_URL")
    firecrawl_poll_interval_ms: int = Field(1000, ge=200, le=10_000, alias="FIRECRAWL_POLL_INTERVAL_MS")
    # Timeout for crawl jobs (ms). Default: 90s. Max allowed: 10m.
    firecrawl_poll_timeout_ms: int = Field(600_000, ge=5_000, le=600_000, alias="FIRECRAWL_POLL_TIMEOUT_MS")

    # Upstash Search
    upstash_search_rest_url: HttpUrl = Field(..., alias="UPSTASH_SEARCH_REST_URL")
    upstash_search_rest_token: str = Field(..., alias="UPSTASH_SEARCH_REST_TOKEN")
    upstash_search_index: str = Field("firestarter", alias="UPSTASH_SEARCH_INDEX")

    # Redis (optional, parity with TS)
    upstash_redis_rest_url: Optional[HttpUrl] = Field(None, alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: Optional[str] = Field(None, alias="UPSTASH_REDIS_REST_TOKEN")

    # Digital Ocean
    digitalocean_token: Optional[str] = Field(None, alias="DIGITALOCEAN_TOKEN")
    digitalocean_project_id: Optional[str] = Field(None, alias="DIGITALOCEAN_PROJECT_ID")
    digitalocean_spaces_key: Optional[str] = Field(None, alias="DIGITALOCEAN_SPACES_KEY")
    digitalocean_spaces_secret: Optional[str] = Field(None, alias="DIGITALOCEAN_SPACES_SECRET")
    digitalocean_spaces_region: str = Field("tor1", alias="DIGITALOCEAN_SPACES_REGION")
    digitalocean_spaces_bucket: Optional[str] = Field(None, alias="DIGITALOCEAN_SPACES_BUCKET")
    # For KB creation (default region)
    digitalocean_genai_region: str = Field("tor1", alias="DIGITALOCEAN_GENAI_REGION")
    # Shared Database ID for Knowledge Bases
    digitalocean_db_id: Optional[str] = Field("e27f23bd-d953-48c5-8923-f827868ba230", alias="DIGITALOCEAN_DB_ID") 
    # Model access key (for DO-managed foundation models)
    digitalocean_model_access_key: Optional[str] = Field(None, alias="DIGITAL_OCEAN_MODEL_ACCESS_KEY")
    # Chunking algorithm for KB data sources
    digitalocean_chunking_algorithm: str = Field(
        "CHUNKING_ALGORITHM_HIERARCHICAL",
        alias="DIGITAL_OCEAN_CHUNKING_ALGORITHM",
    )
    # Enable advanced chunking options (limited preview). If false, we omit
    # chunking_algorithm/options to avoid 403 errors from the API.
    digitalocean_enable_advanced_chunking: bool = Field(
        False, alias="DIGITAL_OCEAN_ENABLE_ADVANCED_CHUNKING"
    )
    # Agent retrieval defaults (applied via update after creation)
    digitalocean_agent_retrieval_method: str = Field(
        "RETRIEVAL_METHOD_REWRITE",
        alias="DIGITAL_OCEAN_AGENT_RETRIEVAL_METHOD",
    )
    digitalocean_agent_provide_citations: bool = Field(
        True,
        alias="DIGITAL_OCEAN_AGENT_PROVIDE_CITATIONS",
    )
    digitalocean_agent_k: int = Field(
        10,
        alias="DIGITAL_OCEAN_AGENT_K",
        ge=1,
    )
    digitalocean_agent_conversation_logs_enabled: bool = Field(
        True,
        alias="DIGITAL_OCEAN_AGENT_CONVERSATION_LOGS_ENABLED",
    )
    digitalocean_agent_log_insights_enabled: bool = Field(
        True,
        alias="DIGITAL_OCEAN_AGENT_LOG_INSIGHTS_ENABLED",
    )

    # AI providers
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(800, alias="AI_MAX_TOKENS")
    ai_system_prompt: str = Field("You are a customer support representative that handles inquiries for people that are interested in buying our services. If the potential customer engages in small talk, respond politely without referencing the website. For questions about the services or products we sell or anything else about the business, answer ONLY using information from the knowledge base. Do NOT use any other knowledge. If the context isn't sufficientg, say so expliciity.",
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
