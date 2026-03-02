"""
Resource links endpoint - generates presigned URLs for key JSON reports
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
import json
import logging
from typing import Any, Dict

from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

INDEXES_BUCKET = "client-data-sources"

def _normalize_client_slug(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "-").replace("_", "-")


def _pinecone_fetch_report_doc(*, index_name: str, namespace: str, doc_id: str) -> Dict[str, Any]:
    """
    Fetch a report doc from Pinecone by ID and parse JSON from the stored `text` field.

    Our report sync stores compact JSON in the mapped `text` field, which Pinecone returns
    inside vector metadata as `text`.
    """
    from pinecone import Pinecone

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY not configured")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)

    resp = idx.fetch(ids=[doc_id], namespace=namespace)
    vec = resp.vectors.get(doc_id) if hasattr(resp, "vectors") else None
    if not vec:
        raise HTTPException(status_code=404, detail=f"Report doc not found: {doc_id}")
    raw = (vec.metadata or {}).get("text") or ""
    return json.loads(raw)


@router.get("/resource-links")
async def get_resource_links(request: Request):
    """
    Return links to key reporting artifacts.

    Historically these were presigned URLs into DigitalOcean Spaces. Now that we’re
    Supabase + Pinecone, we expose these artifacts via API endpoints backed by
    Pinecone report indexes.
    
    Returns:
        dict: Dictionary containing presigned URLs for:
            - client_data: Summary of all clients
            - client_kb_data: Detailed KB audit results
            - agent_directory: Complete agent registry
    """
    base = str(request.base_url).rstrip("/")
    # These are API-backed links (openable in a browser tab).
    return {
        "client_data": f"{base}/api/mintagent/report/_client_kb_master/summary.json",
        "client_kb_data": f"{base}/api/mintagent/report/_client_kb_master/reports/client_audit_results.json",
        "agent_directory": f"{base}/api/mintagent/report/agent-registry.json",
    }


@router.get("/summary-warnings")
async def get_summary_warnings():
    """
    Fetch top_warnings from the summary.json file
    
    Returns:
        dict: Contains top_warnings array from summary.json
    """
    try:
        settings = get_settings()
        summary_data = _pinecone_fetch_report_doc(
            index_name=settings.pinecone_client_kb_reports_index_name,
            namespace=settings.pinecone_client_kb_reports_namespace,
            doc_id="_client_kb_master/summary.json",
        )
        
        return {
            "warnings": summary_data.get("top_warnings", []),
            "generated_at": summary_data.get("generated_at")
        }
    except HTTPException as e:
        # Missing reports are normal for fresh projects / before the report generator runs.
        if e.status_code == 404:
            return {"warnings": [], "generated_at": None, "missing": True}
        logger.error(f"Error fetching summary warnings: {e}")
        raise
    except Exception as e:
        # If Pinecone returns a non-HTTPException 404-style error, treat as missing.
        msg = str(e).lower()
        if "404" in msg and "not found" in msg:
            return {"warnings": [], "generated_at": None, "missing": True}
        logger.error(f"Error fetching summary warnings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary warnings: {str(e)}")


@router.get("/client-details/{client_slug}")
async def get_client_details(client_slug: str, request: Request):
    """
    Fetch detailed client information from both KB and agent registries
    
    Args:
        client_slug: The client identifier
        
    Returns:
        dict: Contains kb_data and agent_data for the client
    """
    try:
        slug = _normalize_client_slug(client_slug)
        settings = get_settings()
        result: Dict[str, Any] = {
            "client_slug": slug,
            # Always return objects (not None) so the UI can safely render modals/tabs.
            "kb_data": {},
            "kb_data_found": False,
            "agent_data": {},
            "agent_data_found": False,
            # UI convenience links to quickly view Supabase Storage metadata files in a new tab.
            "metadata_url": f"{str(request.base_url).rstrip('/')}/api/mintagent/client-metadata/{slug}",
            "supabase_storage_metadata_url": f"{str(request.base_url).rstrip('/')}/api/mintagent/client-metadata/{slug}?source=supabase",
            "pinecone_namespace_metadata_url": f"{str(request.base_url).rstrip('/')}/api/mintagent/client-metadata/{slug}?source=pinecone",
        }
        
        # Fetch KB/Client data
        try:
            result["kb_data"] = _pinecone_fetch_report_doc(
                index_name=settings.pinecone_client_kb_reports_index_name,
                namespace=settings.pinecone_client_kb_reports_namespace,
                doc_id=f"_client_kb_master/clients/{slug}.json",
            )
            result["kb_data_found"] = True
        except HTTPException as e:
            # Missing reports are normal for freshly ingested clients (report generator runs separately).
            if e.status_code == 404:
                logger.info(f"KB report not found for {client_slug}: {e.detail}")
            else:
                logger.warning(f"KB report fetch error for {client_slug}: {e}")
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg and "not found" in msg:
                logger.info(f"KB report not found for {client_slug}: {e}")
            else:
                logger.warning(f"KB report fetch error for {client_slug}: {e}")
        
        # Fetch Agent data
        try:
            result["agent_data"] = _pinecone_fetch_report_doc(
                index_name=settings.pinecone_agent_reports_index_name,
                namespace=settings.pinecone_agent_reports_namespace,
                doc_id=f"agents/inbox_manager_{slug}.json",
            )
            result["agent_data_found"] = True
        except HTTPException as e:
            # Agent reports are optional; missing is normal unless you run the agent pipeline.
            if e.status_code == 404:
                logger.info(f"Agent report not found for {client_slug}: {e.detail}")
            else:
                logger.warning(f"Agent report fetch error for {client_slug}: {e}")
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg and "not found" in msg:
                logger.info(f"Agent report not found for {client_slug}: {e}")
            else:
                logger.warning(f"Agent report fetch error for {client_slug}: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching client details for {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch client details: {str(e)}")


@router.get("/client-metadata/{client_slug}")
async def get_client_metadata(client_slug: str, source: str = "pinecone"):
    """
    Return the raw Supabase Storage metadata file for a client.

    Storage location:
      - bucket: client-data-sources
      - keys:
          - {client_slug}/pinecone_namespace_metadata.json
          - {client_slug}/supabase_storage_metadata.json
          - {client_slug}/metadata.json (legacy)
    """
    from ..clients.supabase_storage_client import SupabaseStorageClient

    slug = _normalize_client_slug(client_slug)
    if not slug:
        raise HTTPException(status_code=400, detail="client_slug required")

    storage = SupabaseStorageClient()
    source_norm = (source or "pinecone").strip().lower()
    candidates = []
    if source_norm in ("pinecone", "pinecone_namespace"):
        candidates = [f"{slug}/pinecone_namespace_metadata.json", f"{slug}/supabase_storage_metadata.json", f"{slug}/metadata.json"]
    elif source_norm in ("supabase", "storage", "supabase_storage"):
        candidates = [f"{slug}/supabase_storage_metadata.json", f"{slug}/metadata.json", f"{slug}/pinecone_namespace_metadata.json"]
    else:
        candidates = [f"{slug}/pinecone_namespace_metadata.json", f"{slug}/supabase_storage_metadata.json", f"{slug}/metadata.json"]

    data = None
    last_err: Exception | None = None
    for key in candidates:
        try:
            data = storage.download_json(INDEXES_BUCKET, key)
            if isinstance(data, dict):
                break
        except Exception as e:
                last_err = e
                data = None
                continue

    if not isinstance(data, dict):
        logger.warning(f"Could not fetch metadata for {slug} (source={source_norm}): {last_err}")
        raise HTTPException(status_code=404, detail="metadata not found for client")

    # Return as JSON so it renders nicely in-browser.
    return JSONResponse(content=data)


@router.get("/client-metadata-public/{client_slug}")
async def get_client_metadata_public_redirect(client_slug: str, file: str = "pinecone") -> RedirectResponse:
    """
    Redirect to canonical lowercase public storage path for client metadata JSON.

    This prevents mixed-case slug URLs from 404-ing when users manually open
    Supabase public object paths.
    """
    settings = get_settings()
    project_url = str(settings.supabase_agent_url or "").rstrip("/")
    if not project_url:
        raise HTTPException(status_code=500, detail="SUPABASE_AGENT_URL not configured")

    slug = _normalize_client_slug(client_slug)
    if not slug:
        raise HTTPException(status_code=400, detail="client_slug required")

    file_norm = (file or "pinecone").strip().lower()
    if file_norm in ("supabase", "storage", "supabase_storage"):
        key = "supabase_storage_metadata.json"
    elif file_norm in ("metadata", "legacy"):
        key = "metadata.json"
    else:
        key = "pinecone_namespace_metadata.json"

    url = f"{project_url}/storage/v1/object/public/{INDEXES_BUCKET}/{slug}/{key}"
    return RedirectResponse(url=url, status_code=307)


@router.get("/report/{doc_id:path}")
async def get_report(doc_id: str):
    """
    Fetch an arbitrary report JSON blob (by doc_id) from Pinecone report indexes.

    This replaces the old “presigned Spaces URL” model with a simple API fetch.
    """
    settings = get_settings()

    # Heuristic: agent registry and agent docs live in AGENT_REPORTS; everything else is KB_REPORTS.
    if doc_id in ("agent-registry.json", "agent-api-tokens.json") or doc_id.startswith("agents/"):
        return _pinecone_fetch_report_doc(
            index_name=settings.pinecone_agent_reports_index_name,
            namespace=settings.pinecone_agent_reports_namespace,
            doc_id=doc_id,
        )

    return _pinecone_fetch_report_doc(
        index_name=settings.pinecone_client_kb_reports_index_name,
        namespace=settings.pinecone_client_kb_reports_namespace,
        doc_id=doc_id,
    )

