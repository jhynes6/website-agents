import logging
from typing import Optional

from ..clients.digital_ocean_client import do_client
from ..clients.do_agent_registry import AgentRecord, AgentRegistry
from ..clients.agent_templates.loader import load_agent_template

logger = logging.getLogger(__name__)

GLOBAL_AGENT_TYPES = {"inbox_manager_qa"}


def _normalize_agent_type(agent_type: str) -> str:
    """
    Normalizes agent type to the template filename convention.
    - accepts 'inbox-manager' or 'inbox_manager' -> 'inbox_manager'
    """
    t = (agent_type or "").strip().lower()
    if not t:
        return "inbox_manager"
    return t.replace("-", "_")


def _agent_name_prefix(agent_type: str) -> str:
    # DO agent naming convention uses dashes (e.g. inbox-manager-<slug>)
    return _normalize_agent_type(agent_type).replace("_", "-")


def _instruction_for(agent_type: str) -> str:
    # Source of truth: backend/app/clients/agent_templates/<agent_type>.md
    return load_agent_template(_normalize_agent_type(agent_type))

async def ensure_agent(
    client_slug: str,
    *,
    agent_type: str = "inbox_manager",
    registry: Optional[AgentRegistry] = None,
) -> AgentRecord:
    """
    Ensure a per-client DO agent exists and is usable.
    - One agent per (client_slug, agent_type)
    - Permanently attached to that client's KB (no dynamic attach/detach)
    - Persist endpoint + key in an on-disk registry (no Upstash)
    """
    normalized_type = _normalize_agent_type(agent_type)

    # Global agents (one shared agent for all clients)
    # Example: inbox_manager_qa should NOT be per-client and should NOT include client slug in the DO name.
    if normalized_type in GLOBAL_AGENT_TYPES:
        return await ensure_global_agent(agent_type=normalized_type, registry=registry)

    if not client_slug:
        raise ValueError("client_slug is required")
    reg = registry or AgentRegistry()
    rec = reg.get_for(client_slug, normalized_type)

    # Resolve KB (must exist); also record it in KB registry so create_agent validation passes.
    kb = await do_client.get_knowledge_base_by_name(client_slug)
    if not kb:
        raise ValueError(f"Knowledge Base '{client_slug}' not found")
    do_client._record_kb(client_slug, kb)  # internal helper; ensures registry is populated
    kb_uuid = kb.get("uuid")
    if not kb_uuid:
        raise ValueError(f"Knowledge Base '{client_slug}' has no uuid")
    kb_project_id = kb.get("project_id")
    kb_region = kb.get("region")

    agent_name = f"{_agent_name_prefix(normalized_type)}-{client_slug}"

    # Validate cached registry entries. It's possible the agent was deleted in DO while the
    # local registry still has UUID/endpoint/key. In that case, recreate.
    if rec and rec.agent_uuid:
        try:
            # This call is also how we ensure visibility is PUBLIC; if it fails, agent likely doesn't exist.
            validated_url = await do_client.get_agent_chat_endpoint(rec.agent_uuid)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed validating agent from registry (%s): %s", rec.agent_uuid, exc)
            validated_url = None

        if not validated_url:
            logger.warning(
                "Registry entry appears stale (agent missing). Will recreate. key=%s",
                AgentRegistry.make_key(client_slug, normalized_type),
            )
            rec = None
        else:
            # Keep registry endpoint fresh (in case DO rotated it / visibility changed).
            if rec.endpoint_url != validated_url:
                rec = reg.upsert_for(
                    client_slug,
                    normalized_type,
                    agent_uuid=rec.agent_uuid,
                    endpoint_url=validated_url,
                    api_key=rec.api_key,
                )

    # If we have a registry record, try to fill in missing pieces without recreating agent.
    if rec and rec.agent_uuid:
        agent_uuid = rec.agent_uuid
    else:
        # Fallback: scan agents once to find by name (handles registry loss).
        agent_uuid = ""
        try:
            agents = await do_client.list_agents()
            for a in agents:
                if a.get("name") == agent_name and a.get("uuid"):
                    agent_uuid = a["uuid"]
                    break
        except Exception as exc:
            logger.warning("Failed to list agents while ensuring '%s': %s", agent_name, exc)

        if not agent_uuid:
            # Create agent with KB attached
            instruction = _instruction_for(normalized_type) or do_client.settings.ai_system_prompt
            created = await do_client.create_agent(
                agent_name,
                [kb_uuid],
                instruction=instruction,
                project_id=str(kb_project_id) if kb_project_id else None,
                region=str(kb_region) if kb_region else None,
            )
            if not created or not created.get("uuid"):
                raise RuntimeError("Failed to create agent")
            agent_uuid = created["uuid"]

        rec = reg.upsert_for(client_slug, normalized_type, agent_uuid=agent_uuid)

    # Ensure endpoint url exists
    if not rec.endpoint_url:
        # Newly created agents can take time to deploy; endpoint visibility calls may 400 until running.
        # Wait briefly for deployment readiness before attempting to fetch the public endpoint URL.
        try:
            await do_client.wait_for_agent_ready(rec.agent_uuid, max_wait_seconds=180, poll_interval=5)
        except Exception as exc:  # pragma: no cover
            logger.warning("[DO] Error while waiting for agent readiness (%s): %s", rec.agent_uuid, exc)
        endpoint = await do_client.get_agent_chat_endpoint(rec.agent_uuid)
        if not endpoint:
            raise RuntimeError("Failed to retrieve agent endpoint")
        rec = reg.upsert_for(client_slug, normalized_type, agent_uuid=rec.agent_uuid, endpoint_url=endpoint)

    # Ensure API key exists
    if not rec.api_key:
        # API key creation may also fail for agents that aren't fully deployed yet.
        try:
            await do_client.wait_for_agent_ready(rec.agent_uuid, max_wait_seconds=180, poll_interval=5)
        except Exception as exc:  # pragma: no cover
            logger.warning("[DO] Error while waiting for agent readiness (%s): %s", rec.agent_uuid, exc)
        key = await do_client.create_agent_api_key(rec.agent_uuid)
        if not key:
            raise RuntimeError("Failed to create agent API key")
        rec = reg.upsert_for(client_slug, normalized_type, agent_uuid=rec.agent_uuid, api_key=key)

    return rec


async def ensure_inbox_manager_agent(
    client_slug: str,
    *,
    registry: Optional[AgentRegistry] = None,
) -> AgentRecord:
    # Back-compat wrapper
    return await ensure_agent(client_slug, agent_type="inbox_manager", registry=registry)


async def ensure_global_agent(
    *,
    agent_type: str,
    registry: Optional[AgentRegistry] = None,
) -> AgentRecord:
    """
    Ensure a global DigitalOcean agent exists (shared across all clients).
    - No client slug in the agent name
    - No per-client KB requirement/attachment
    """
    normalized_type = _normalize_agent_type(agent_type)
    reg = registry or AgentRegistry()

    # Store under a reserved "global" client slug key so we can reuse AgentRegistry infra.
    global_client_slug = "__global__"
    rec = reg.get_for(global_client_slug, normalized_type)

    agent_name = _agent_name_prefix(normalized_type)  # e.g. inbox-manager-qa

    # Validate cached registry entries
    if rec and rec.agent_uuid:
        try:
            validated_url = await do_client.get_agent_chat_endpoint(rec.agent_uuid)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed validating global agent from registry (%s): %s", rec.agent_uuid, exc)
            validated_url = None

        if not validated_url:
            logger.warning(
                "Global registry entry appears stale (agent missing). Will recreate. key=%s",
                AgentRegistry.make_key(global_client_slug, normalized_type),
            )
            rec = None
        else:
            if rec.endpoint_url != validated_url:
                rec = reg.upsert_for(
                    global_client_slug,
                    normalized_type,
                    agent_uuid=rec.agent_uuid,
                    endpoint_url=validated_url,
                    api_key=rec.api_key,
                )

    # Resolve agent UUID (registry or scan by name)
    if rec and rec.agent_uuid:
        agent_uuid = rec.agent_uuid
    else:
        agent_uuid = ""
        try:
            agents = await do_client.list_agents()
            for a in agents:
                if a.get("name") == agent_name and a.get("uuid"):
                    agent_uuid = a["uuid"]
                    break
        except Exception as exc:
            logger.warning("Failed to list agents while ensuring global '%s': %s", agent_name, exc)

        if not agent_uuid:
            instruction = _instruction_for(normalized_type) or do_client.settings.ai_system_prompt
            created = await do_client.create_agent(
                agent_name,
                [],  # global QA agent should not be tied to any client KB
                instruction=instruction,
            )
            if not created or not created.get("uuid"):
                raise RuntimeError("Failed to create global agent")
            agent_uuid = created["uuid"]

        rec = reg.upsert_for(global_client_slug, normalized_type, agent_uuid=agent_uuid)

    # Ensure endpoint url exists
    if not rec.endpoint_url:
        try:
            await do_client.wait_for_agent_ready(rec.agent_uuid, max_wait_seconds=180, poll_interval=5)
        except Exception as exc:  # pragma: no cover
            logger.warning("[DO] Error while waiting for global agent readiness (%s): %s", rec.agent_uuid, exc)
        endpoint = await do_client.get_agent_chat_endpoint(rec.agent_uuid)
        if not endpoint:
            raise RuntimeError("Failed to retrieve global agent endpoint")
        rec = reg.upsert_for(global_client_slug, normalized_type, agent_uuid=rec.agent_uuid, endpoint_url=endpoint)

    # Ensure API key exists
    if not rec.api_key:
        try:
            await do_client.wait_for_agent_ready(rec.agent_uuid, max_wait_seconds=180, poll_interval=5)
        except Exception as exc:  # pragma: no cover
            logger.warning("[DO] Error while waiting for global agent readiness (%s): %s", rec.agent_uuid, exc)
        key = await do_client.create_agent_api_key(rec.agent_uuid)
        if not key:
            raise RuntimeError("Failed to create global agent API key")
        rec = reg.upsert_for(global_client_slug, normalized_type, agent_uuid=rec.agent_uuid, api_key=key)

    return rec


