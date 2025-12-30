import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

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


def _pinecone_fetch_report_doc(*, index_name: str, namespace: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a report doc from Pinecone by ID and parse JSON from the stored `text` field.
    Returns None if missing.
    """
    from pinecone import Pinecone

    settings = get_settings()
    if not settings.pinecone_api_key:
        return None

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)

    resp = idx.fetch(ids=[doc_id], namespace=namespace)
    vec = resp.vectors.get(doc_id) if hasattr(resp, "vectors") else None
    if not vec:
        return None
    raw = (vec.metadata or {}).get("text") or ""
    try:
        return json.loads(raw)
    except Exception:
        return None


def _build_index_payload(
    *,
    client_slug: str,
    vector_count: int,
    client_report: Optional[Dict[str, Any]],
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

    async def process_namespace(slug: str, ns_info: Dict[str, Any]) -> Dict[str, Any]:
        vector_count = int((ns_info or {}).get("vector_count") or 0)
        client_report = _pinecone_fetch_report_doc(
            index_name=settings.pinecone_client_kb_reports_index_name,
            namespace=settings.pinecone_client_kb_reports_namespace,
            doc_id=f"_client_kb_master/clients/{slug}.json",
        )
        return _build_index_payload(
            client_slug=slug,
            vector_count=vector_count,
            client_report=client_report,
        )

    results = await asyncio.gather(
        *[process_namespace(slug, ns_info) for slug, ns_info in namespaces.items()]
    )
                    
    # Sort newest first
    results.sort(key=lambda x: x.get("createdAt") or "", reverse=True)

    if target_slug:
        return {"index": results[0]}
    return {"indexes": results}
