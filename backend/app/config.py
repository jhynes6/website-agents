from functools import lru_cache
from typing import Optional

from .clients.agent_templates.loader import load_agent_template

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Prefer backend/.env so running from repo root still picks up backend env.
        # Keep fallbacks for existing workflows.
        env_file=[
            "backend/.env",
            "backend/.env.local",
            ".env",
            ".env.local",
            "../.env",
            "../.env.local",
        ],
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # API
    mintagent_api_key: Optional[str] = Field(default=None, alias="MINTAGENT_API_KEY")

    # Firecrawl
    firecrawl_api_key: Optional[str] = Field(None, alias="FIRECRAWL_API_KEY")
    firecrawl_base_url: HttpUrl = Field("https://api.firecrawl.dev/v2", alias="FIRECRAWL_BASE_URL")
    firecrawl_poll_interval_ms: int = Field(1000, ge=200, le=10_000, alias="FIRECRAWL_POLL_INTERVAL_MS")
    # Timeout for crawl jobs (ms). Default: 90s. Max allowed: 10m.
    firecrawl_poll_timeout_ms: int = Field(600_000, ge=5_000, le=600_000, alias="FIRECRAWL_POLL_TIMEOUT_MS")

    # Bright Data
    brightdata_api_key: Optional[str] = Field(None, alias="BRIGHTDATA_API_KEY")
    brightdata_zone: str = Field("web_unlocker1", alias="BRIGHTDATA_ZONE")

    # Upstash and DigitalOcean have been removed from this project.

    # AI providers
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(4096, alias="AI_MAX_TOKENS")

    @staticmethod
    def _default_ai_system_prompt() -> str:
        # Default to kb_chat template. Override via AI_SYSTEM_PROMPT env if desired.
        try:
            return load_agent_template("kb_chat")
        except Exception:
            # Defensive fallback: keep non-empty string so startup doesn't crash in odd envs.
            return "System Prompt: KB Chat\n\n(Template missing)"

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
    crawler_provider: str = Field("crawl4ai", alias="CRAWLER_PROVIDER")
    crawl4ai_headless: bool = Field(True, alias="CRAWL4AI_HEADLESS")
    crawl4ai_verbose: bool = Field(False, alias="CRAWL4AI_VERBOSE")
    crawl4ai_page_timeout_ms: int = Field(45_000, ge=5_000, le=180_000, alias="CRAWL4AI_PAGE_TIMEOUT_MS")
    crawl4ai_default_max_depth: int = Field(2, ge=0, le=8, alias="CRAWL4AI_DEFAULT_MAX_DEPTH")
    crawl4ai_allow_subdomains: bool = Field(False, alias="CRAWL4AI_ALLOW_SUBDOMAINS")
    crawl4ai_max_discovered_urls: int = Field(5_000, ge=100, le=50_000, alias="CRAWL4AI_MAX_DISCOVERED_URLS")

    # Supabase Storage bucket for operational reports (private by default)
    supabase_reports_bucket_name: str = Field("mintleads-reports", alias="SUPABASE_REPORTS_BUCKET")

    # Supabase Agent Project (MCP managed agents database)
    supabase_agent_url: Optional[HttpUrl] = Field(None, alias="SUPABASE_AGENT_URL")
    supabase_agent_key: Optional[str] = Field(None, alias="SUPABASE_AGENT_KEY")
    supabase_agent_publishable_key: Optional[str] = Field(None, alias="SUPABASE_AGENT_PUBLISHABLE_KEY")
    # Service role key for server-side Storage operations (preferred when present)
    supabase_agent_service_role_key: Optional[str] = Field(None, alias="SUPABASE_AGENT_SERVICE_ROLE_KEY")

    # Supabase (Email Bison workspace -> client slug mapping)
    # New (preferred): Bison-specific Supabase env vars (matches context/supabase_client.py)
    bison_supabase_project_url: Optional[HttpUrl] = Field(None, alias="BISON_SUPABASE_PROJECT_URL")
    bison_supabase_anon_key: Optional[str] = Field(None, alias="BISON_SUPABASE_ANON_KEY")
    # Optional: direct Postgres connection URL/creds (may be used later for non-PostgREST access)
    bison_supabase_bison_db_url: Optional[str] = Field(None, alias="BISON_SUPABASE_BISON_DB_URL")
    bison_user: Optional[str] = Field(None, alias="BISON_user")
    bison_password: Optional[str] = Field(None, alias="BISON_password")
    bison_host: Optional[str] = Field(None, alias="BISON_host")
    bison_port: Optional[int] = Field(None, alias="BISON_port")
    bison_dbname: Optional[str] = Field(None, alias="BISON_dbname")

    # Back-compat: generic Supabase env vars (supported, but BISON_* takes precedence)
    supabase_url: Optional[HttpUrl] = Field(None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(None, alias="SUPABASE_SERVICE_ROLE_KEY")
    # Optional schema override (default public)
    supabase_schema: str = Field("public", alias="SUPABASE_SCHEMA")

    # Supabase (mintleads-agents project) - Storage + non-vectorized data
    # These are intentionally separate from BISON_* to avoid collisions.
    # Preferred env var names for this repo:
    # - SUPABASE_AGENT_URL
    # - SUPABASE_AGENT_KEY
    # Optional:
    # - SUPABASE_AGENT_PUBLISHABLE_KEY
    supabase_agent_url: Optional[HttpUrl] = Field(None, alias="SUPABASE_AGENT_URL")
    supabase_agent_key: Optional[str] = Field(None, alias="SUPABASE_AGENT_KEY")
    supabase_agent_publishable_key: Optional[str] = Field(None, alias="SUPABASE_AGENT_PUBLISHABLE_KEY")

    # Email Bison API
    bison_api_key: Optional[str] = Field(None, alias="BISON_API_KEY")

    # Pinecone (DB + Assistant)
    pinecone_api_key: Optional[str] = Field(None, alias="PINECONE_API_KEY")
    # Optional default assistant names (Pinecone Assistant API)
    pinecone_inbox_manager_assistant_name: Optional[str] = Field(
        None, alias="PINECONE_INBOX_MANAGER_ASSISTANT_NAME"
    )
    # Defaults for migration scripts / infra
    pinecone_cloud: str = Field("aws", alias="PINECONE_CLOUD")
    pinecone_region: str = Field("us-east-1", alias="PINECONE_REGION")
    # Canonical KB index for this project (upload + retrieval).
    pinecone_kb_index_name: str = Field("sb-knowledge-bases", alias="PINECONE_KB_INDEX")
    # Optional separate index for semantic A/B runs (only used when semanticEmbeddings is enabled).
    pinecone_kb_semantic_index_name: str = Field("sb-knowledge-bases-semantic", alias="PINECONE_KB_SEMANTIC_INDEX")
    pinecone_agent_index_name: str = Field("agents", alias="PINECONE_AGENT_INDEX")
    # Report indexes (structured JSON “cards” + summaries for UI)
    # User-provided env var names:
    # - CLIENT_KB_REPORTS: Pinecone index name for client KB report docs
    # - AGENT_REPORTS: Pinecone index name for agent report docs
    pinecone_client_kb_reports_index_name: str = Field("sb-knowledge-bases", alias="CLIENT_KB_REPORTS")
    pinecone_agent_reports_index_name: str = Field("agents", alias="AGENT_REPORTS")
    # Namespaces within those report indexes
    pinecone_client_kb_reports_namespace: str = Field("REPORTING", alias="CLIENT_KB_REPORTS_NAMESPACE")
    pinecone_agent_reports_namespace: str = Field("REPORTING", alias="AGENT_REPORTS_NAMESPACE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
