from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..logging import log

router = APIRouter()


@router.get("/agent-debug/{agent_uuid}")
async def agent_debug(agent_uuid: str) -> Dict[str, Any]:
    """
    Deprecated endpoint.

    DigitalOcean agent provisioning was removed. This endpoint remains for back-compat
    but always returns 410 Gone.
    """
    log("agent.debug.deprecated", {"agent_uuid": agent_uuid})
    raise HTTPException(status_code=410, detail="DigitalOcean agent debug removed; this project is Supabase + Pinecone.")


