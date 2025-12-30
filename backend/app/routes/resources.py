"""
Resource links endpoint - generates presigned URLs for key JSON reports
"""
from fastapi import APIRouter, HTTPException, Request
import json
import logging
from typing import Any, Dict

from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


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
    except Exception as e:
        logger.error(f"Error fetching summary warnings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary warnings: {str(e)}")


@router.get("/client-details/{client_slug}")
async def get_client_details(client_slug: str):
    """
    Fetch detailed client information from both KB and agent registries
    
    Args:
        client_slug: The client identifier
        
    Returns:
        dict: Contains kb_data and agent_data for the client
    """
    try:
        settings = get_settings()
        result = {
            "client_slug": client_slug,
            "kb_data": None,
            "agent_data": None
        }
        
        # Fetch KB/Client data
        try:
            result["kb_data"] = _pinecone_fetch_report_doc(
                index_name=settings.pinecone_client_kb_reports_index_name,
                namespace=settings.pinecone_client_kb_reports_namespace,
                doc_id=f"_client_kb_master/clients/{client_slug}.json",
            )
        except Exception as e:
            logger.warning(f"Could not fetch KB data for {client_slug}: {e}")
        
        # Fetch Agent data
        try:
            result["agent_data"] = _pinecone_fetch_report_doc(
                index_name=settings.pinecone_agent_reports_index_name,
                namespace=settings.pinecone_agent_reports_namespace,
                doc_id=f"agents/inbox_manager_{client_slug}.json",
            )
        except Exception as e:
            logger.warning(f"Could not fetch agent data for {client_slug}: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching client details for {client_slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch client details: {str(e)}")


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

