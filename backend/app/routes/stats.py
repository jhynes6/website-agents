from typing import Any, Dict, List, Optional
import json
import asyncio
from fastapi import APIRouter, HTTPException

from ..clients.digital_ocean_client import do_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


@router.post("/stats")
async def get_namespace_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get aggregated statistics for documents in a namespace (now client_slug)."""
    settings = get_settings()
    
    # Support both new and old param names
    namespace: str = payload.get("clientSlug") or payload.get("namespace")
    
    if not namespace:
        raise HTTPException(status_code=400, detail="Client slug (namespace) is required")
    
    try:
        # Fetch metadata.json from Spaces to get the stats
        # We don't have per-document breakdowns easily available in DO yet without listing all objects.
        # So we'll return the aggregate count from metadata.
        
        pages_crawled = 0
        
        if do_client.s3_client and settings.digitalocean_spaces_bucket:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: do_client.s3_client.get_object(
                        Bucket=settings.digitalocean_spaces_bucket,
                        Key=f"{namespace}/metadata.json"
                    )
                )
                content = response['Body'].read().decode('utf-8')
                stored_meta = json.loads(content)
                pages_crawled = stored_meta.get("pagesCrawled", 0)
            except Exception:
                pass

        return {
            "total": pages_crawled,
            "by_content_type": {"website_page": pages_crawled} if pages_crawled > 0 else {},
            "by_document_source": {"website_crawl": pages_crawled} if pages_crawled > 0 else {}
        }

    except Exception as exc:
        log("stats.error", {"error": str(exc), "namespace": namespace})
        # Return empty stats on error rather than failing
        return {"total": 0, "by_content_type": {}, "by_document_source": {}}

