from functools import lru_cache
from typing import Optional

from .clients.agent_templates.loader import load_agent_template

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

    # Upstash (deprecated - DO-only path). Keep optional for backwards compatibility.
    upstash_search_rest_url: Optional[HttpUrl] = Field(None, alias="UPSTASH_SEARCH_REST_URL")
    upstash_search_rest_token: Optional[str] = Field(None, alias="UPSTASH_SEARCH_REST_TOKEN")
    upstash_search_index: str = Field("firestarter", alias="UPSTASH_SEARCH_INDEX")

    # Redis (deprecated - DO-only path). Keep optional for backwards compatibility.
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
    # Optional: workspace/provider key IDs used by some org setups for agent creation
    digitalocean_workspace_uuid: Optional[str] = Field(None, alias="DIGITALOCEAN_WORKSPACE_UUID")
    digitalocean_openai_key_uuid: Optional[str] = Field(None, alias="DIGITALOCEAN_OPENAI_KEY_UUID")
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
    digitalocean_agent_model_uuid: str = Field(
        "1b07e52b-73c5-11f0-b074-4e013e2ddde4",
        alias="DIGITALOCEAN_AGENT_MODEL_UUID"
    )
    
    # Agent generation parameters
    digitalocean_agent_temperature: float = Field(
        0.3,
        alias="DIGITALOCEAN_AGENT_TEMPERATURE",
        ge=0.0,
        le=2.0
    )
    digitalocean_agent_top_p: float = Field(
        0.8,
        alias="DIGITALOCEAN_AGENT_TOP_P",
        ge=0.0,
        le=1.0
    )
    digitalocean_agent_top_k: int = Field(
        40,
        alias="DIGITALOCEAN_AGENT_TOP_K",
        ge=1,
        le=100
    )
    digitalocean_agent_max_tokens: int = Field(
        1024,
        alias="DIGITALOCEAN_AGENT_MAX_TOKENS",
        ge=1,
        le=4096
    )

    # AI providers
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(4096, alias="AI_MAX_TOKENS")

    @staticmethod
    def _default_ai_system_prompt() -> str:
        # Default to inbox manager template. Override via AI_SYSTEM_PROMPT env if desired.
        try:
            return load_agent_template("inbox_manager")
        except Exception:
            # Defensive fallback: keep non-empty string so startup doesn't crash in odd envs.
            return "System Prompt: Inbox Manager\n\n(Template missing)"

    ai_system_prompt: str = Field(default_factory=_default_ai_system_prompt, alias="AI_SYSTEM_PROMPT")

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
