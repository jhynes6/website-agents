import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from ..clients.digital_ocean_client import do_client
from ..config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


def _open_pinecone_index(index_name: str):
    """
    Return a Pinecone Index handle for the KB index (Records API + stats).
    """
    from pinecone import Pinecone  # local dependency pinned in backend/requirements.txt

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY not configured")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    return pc.Index(host=desc.host)


async def _try_get_spaces_client_report(bucket: str, client_slug: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort: load our canonical UI/KB report from Spaces.
    """
    if not do_client.s3_client:
        return None
    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: do_client.s3_client.get_object(
                Bucket=bucket,
                Key=f"REPORTING/clients/{client_slug}.json",
            ),
        )
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception:
        return None


async def _try_get_spaces_metadata_json(bucket: str, client_slug: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort: load legacy metadata.json from Spaces (written by create flow).
    """
    if not do_client.s3_client:
        return None
    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: do_client.s3_client.get_object(
                Bucket=bucket,
                Key=f"{client_slug}/metadata.json",
            ),
        )
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception:
        return None


def _build_index_payload(
    *,
    client_slug: str,
    vector_count: int,
    client_report: Optional[Dict[str, Any]],
    legacy_meta: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    # Metadata defaults
    metadata: Dict[str, Any] = {
        "title": client_slug,
        "description": f"Pinecone namespace: {client_slug}",
        "favicon": None,
        "indexName": client_slug,
    }

    created_at = None
    pages_crawled = 0

    # Prefer the canonical report
    if isinstance(client_report, dict):
        ui = client_report.get("ui") or {}
        if ui.get("title"):
            metadata["title"] = ui["title"]
        if ui.get("description"):
            metadata["description"] = ui["description"]
        if ui.get("favicon"):
            metadata["favicon"] = ui["favicon"]
        if ui.get("ogImage"):
            metadata["ogImage"] = ui["ogImage"]
        if ui.get("indexName"):
            metadata["indexName"] = ui["indexName"]

        spaces_info = client_report.get("spaces") or {}
        pages_crawled = int(spaces_info.get("total_files") or 0)

        ts = client_report.get("timestamps") or {}
        created_at = ts.get("createdAt") or ts.get("created_at") or created_at

    # Fallback to legacy metadata.json written by create flow
    if isinstance(legacy_meta, dict):
        pages_crawled = int(legacy_meta.get("pagesCrawled") or pages_crawled or 0)
        created_at = legacy_meta.get("createdAt") or created_at
        m = legacy_meta.get("metadata") or {}
        if m.get("title"):
            metadata["title"] = m["title"]
        if m.get("description"):
            metadata["description"] = m["description"]
        if m.get("favicon"):
            metadata["favicon"] = m["favicon"]
        if m.get("ogImage"):
            metadata["ogImage"] = m["ogImage"]
        if m.get("indexName"):
            metadata["indexName"] = m["indexName"]

    # Reasonable fallback
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    # NOTE: This product is now Pinecone-backed; "chunks" maps to vectors in the namespace.
    return {
        "url": f"https://{client_slug}.com",
        "clientSlug": client_slug,
        "namespace": client_slug,  # back-compat
        "pagesCrawled": pages_crawled,
        "pages": pages_crawled,
        "chunks": int(vector_count),
        "createdAt": created_at,
        "metadata": metadata,
        # DO agent fields (deprecated for this Pinecone-first UI path)
        "agent": None,
        "agents": {},
    }


@router.get("/indexes")
async def list_indexes(
    client_slug: Optional[str] = None, 
    clientSlug: Optional[str] = None,
    namespace: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all indexes (Pinecone namespaces) that have content.
    Accepts client_slug (preferred), clientSlug (JS compat), or namespace (deprecated).
    """
    settings = get_settings()
    
    # Handle aliases
    target_slug = client_slug or clientSlug or namespace
    # Pinecone-backed listing
    kb_index_name = settings.pinecone_kb_index_name
    idx = _open_pinecone_index(kb_index_name)
    stats = idx.describe_index_stats()
    namespaces: Dict[str, Any] = (stats or {}).get("namespaces") or {}

    # Determine which namespaces to return
    if target_slug:
        if target_slug not in namespaces:
            raise HTTPException(status_code=404, detail="Namespace not found")
        namespaces = {target_slug: namespaces[target_slug]}

    # Spaces bucket for UI metadata (optional but recommended)
    bucket = settings.digitalocean_spaces_bucket

    async def process_namespace(slug: str, ns_info: Dict[str, Any]) -> Dict[str, Any]:
        vector_count = int((ns_info or {}).get("vector_count") or 0)
        client_report = await _try_get_spaces_client_report(bucket, slug) if bucket else None
        legacy_meta = await _try_get_spaces_metadata_json(bucket, slug) if bucket else None
        return _build_index_payload(
            client_slug=slug,
            vector_count=vector_count,
            client_report=client_report,
            legacy_meta=legacy_meta,
        )

    results = await asyncio.gather(
        *[process_namespace(slug, ns_info) for slug, ns_info in namespaces.items()]
    )
                    
    # Sort newest first
    results.sort(key=lambda x: x.get("createdAt") or "", reverse=True)

    if target_slug:
        return {"index": results[0]}
    return {"indexes": results}
