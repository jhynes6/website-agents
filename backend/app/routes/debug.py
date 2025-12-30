from fastapi import APIRouter

from ..config import get_settings

router = APIRouter()


@router.get("/debug")
async def debug_info() -> dict:
    settings = get_settings()
    return {
        "firecrawl_base_url": str(settings.firecrawl_base_url),
        "ai": {
            "openai_configured": bool(settings.openai_api_key),
            "anthropic_configured": bool(settings.anthropic_api_key),
            "groq_configured": bool(settings.groq_api_key),
        },
    }

