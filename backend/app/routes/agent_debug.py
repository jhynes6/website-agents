from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..clients.digital_ocean_client import do_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


@router.get("/agent-debug/{agent_uuid}")
async def agent_debug(agent_uuid: str) -> Dict[str, Any]:
    """
    Debug endpoint: verifies whether an agent UUID exists in DigitalOcean and returns minimal metadata.
    """
    settings = get_settings()
    if not settings.digitalocean_token:
        raise HTTPException(status_code=500, detail="DIGITALOCEAN_TOKEN not configured")

    agent = await do_client.get_agent(agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    payload = {
        "uuid": agent.get("uuid"),
        "name": agent.get("name"),
        "region": agent.get("region"),
        "project_id": agent.get("project_id"),
        "deployment": agent.get("deployment"),
        "knowledge_bases": agent.get("knowledge_bases"),
        "retrieval_method": agent.get("retrieval_method"),
        "provide_citations": agent.get("provide_citations"),
        "k": agent.get("k"),
        "created_at": agent.get("created_at"),
        "updated_at": agent.get("updated_at"),
    }
    log("agent.debug.ok", {"agent_uuid": agent_uuid, "name": payload.get("name")})
    return payload


