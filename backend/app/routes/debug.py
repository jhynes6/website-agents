from fastapi import APIRouter

from ..config import get_settings

router = APIRouter()


@router.get("/debug")
async def debug_info() -> dict:
    settings = get_settings()
    return {
        "firecrawl_base_url": str(settings.firecrawl_base_url),
        # Upstash deprecated (DO-only path). Kept for visibility if still configured.
        "upstash_search_rest_url": str(settings.upstash_search_rest_url) if settings.upstash_search_rest_url else None,
        "upstash_search_index": settings.upstash_search_index if settings.upstash_search_rest_url else None,
        "ai": {
            "openai_configured": bool(settings.openai_api_key),
            "anthropic_configured": bool(settings.anthropic_api_key),
            "groq_configured": bool(settings.groq_api_key),
        },
    }

