from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..config import get_settings 
from ..logging import log
    
router = APIRouter()


@router.post("/ensure-agent")
async def ensure_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Back-compat endpoint.

    This project no longer provisions DigitalOcean agents. Chat is grounded using
    Pinecone retrieval (and optionally Pinecone Assistant) plus an LLM.

    The frontend may still call this endpoint; we return a non-fatal stub response.
    """
    client_slug = payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace")
    agent_type = payload.get("agentType") or payload.get("agent_type") or "inbox_manager"
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    log("agent.ensure.noop", {"client_slug": client_slug, "agent_type": agent_type})
    return {
        "clientSlug": client_slug,
        "agentType": agent_type,
        "agent_uuid": None,
        "agent_endpoint": None,
        "agent_key": None,
        "status": "ok",
        "reason": "No agent provisioning required; chat is Pinecone-grounded.",
    }   


