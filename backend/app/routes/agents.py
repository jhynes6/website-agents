from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..config import get_settings 
from ..logging import log
from ..services.do_agent_manager import ensure_agent as ensure_do_agent
    
router = APIRouter()


@router.post("/ensure-agent")
async def ensure_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a per-client DO inbox-manager agent exists and is ready for chat.
    Returns agent UUID + endpoint + access key for the UI to use (or cache).
    """
    settings = get_settings()
    client_slug = payload.get("clientSlug") or payload.get("client_slug") or payload.get("namespace")
    agent_type = payload.get("agentType") or payload.get("agent_type") or "inbox_manager"
    if not client_slug:
        raise HTTPException(status_code=400, detail="clientSlug is required")
    if not settings.digitalocean_token:
        raise HTTPException(status_code=500, detail="DIGITALOCEAN_TOKEN not configured")

    try:
        rec = await ensure_do_agent(client_slug, agent_type=str(agent_type))
        log("agent.ensure.ok", {"client_slug": client_slug, "agent_type": agent_type, "agent_uuid": rec.agent_uuid})
        return {
            "clientSlug": client_slug,
            "agentType": agent_type,
            "agent_uuid": rec.agent_uuid,
            "agent_endpoint": rec.endpoint_url,
            "agent_key": rec.api_key,
        }
    except PermissionError as exc:
        # Most common cause: token/team doesn't have permission to create agents (or quota hit)
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log("agent.ensure.error", {"client_slug": client_slug, "error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to ensure agent")


