from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

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
        # Pinecone-backed stats: use namespace vector_count as the primary signal.
        if not settings.pinecone_api_key:
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not configured")

        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.pinecone_api_key)
        desc = pc.describe_index(settings.pinecone_kb_index_name)
        idx = pc.Index(host=desc.host)
        stats = idx.describe_index_stats()
        ns_info = (stats or {}).get("namespaces") or {}
        vector_count = int((ns_info.get(namespace) or {}).get("vector_count") or 0)

        return {
            "total": vector_count,
            "by_content_type": {},
            "by_document_source": {},
        }

    except Exception as exc:
        log("stats.error", {"error": str(exc), "namespace": namespace})
        # Return empty stats on error rather than failing
        return {"total": 0, "by_content_type": {}, "by_document_source": {}}

