"""
Resource links endpoint - generates presigned URLs for key JSON reports
"""
from fastapi import APIRouter, HTTPException
from app.clients.digital_ocean_client import do_client
from botocore.client import Config
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
async def get_resource_links():
    """
    Generate presigned URLs for key resource files in DigitalOcean Spaces
    
    Returns:
        dict: Dictionary containing presigned URLs for:
            - client_data: Summary of all clients
            - client_kb_data: Detailed KB audit results
            - agent_directory: Complete agent registry
    """
    try:
        # URLs expire in 1 hour (3600 seconds)
        expiration = 3600
        
        links = {}
        
        # 1. Client Data (summary.json)
        try:
            links["client_data"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-clients-kb',
                    'Key': '_client_kb_master/summary.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for client_data: {e}")
            links["client_data"] = None
        
        # 2. Client KB Data (client_audit_results.json)
        try:
            links["client_kb_data"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-clients-kb',
                    'Key': '_client_kb_master/reports/client_audit_results.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for client_kb_data: {e}")
            links["client_kb_data"] = None
        
        # 3. Agent Directory (agent_registry.json)
        try:
            links["agent_directory"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-agents-store',
                    'Key': 'agent_registry.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for agent_directory: {e}")
            links["agent_directory"] = None
        
        logger.info("Successfully generated resource links")
        return links
        
    except Exception as e:
        logger.error(f"Error generating resource links: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate resource links: {str(e)}")


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

