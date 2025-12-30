import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import boto3
import httpx
from botocore.exceptions import ClientError

from ..config import get_settings
from .do_kb_registry import KnowledgeBaseRegistry, KnowledgeBaseRecord

logger = logging.getLogger(__name__)

class DigitalOceanClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://api.digitalocean.com/v2/gen-ai"
        self.headers = {
            "Authorization": f"Bearer {self.settings.digitalocean_token}",
            "Content-Type": "application/json",
        }
        self.registry = KnowledgeBaseRegistry()
        
        # Initialize Spaces client if credentials exist
        self.s3_client = None
        if (
            self.settings.digitalocean_spaces_key
            and self.settings.digitalocean_spaces_secret
            and self.settings.digitalocean_spaces_region
        ):
            self.s3_client = boto3.client(
                "s3",
                region_name=self.settings.digitalocean_spaces_region,
                endpoint_url=f"https://{self.settings.digitalocean_spaces_region}.digitaloceanspaces.com",
                aws_access_key_id=self.settings.digitalocean_spaces_key,
                aws_secret_access_key=self.settings.digitalocean_spaces_secret,
            )

    async def get_embedding_model_uuid(self) -> Optional[str]:
        """Fetch the first available embedding model UUID."""
        async with httpx.AsyncClient() as client:
            try:
                # Try with documented parameter
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    params={"usecases": "USECASE_EMBEDDING"},
                )
                if response.status_code == 400:
                     # Fallback: try without params and filter client-side
                     logger.warning("[DO] 400 with params, retrying without params")
                     response = await client.get(
                        f"{self.base_url}/models",
                        headers=self.headers,
                    )
                
                response.raise_for_status()
                data = response.json()
                models = data.get("models", [])

                # Prefer "GTE Large" if available
                preferred_model_name = "GTE Large"
                preferred = [m for m in models if preferred_model_name in m.get("name", "")]
                if preferred:
                    return preferred[0]["uuid"]
                
                # Filter for embedding models if we fetched all
                embedding_models = [
                    m for m in models 
                    if "EMBEDDING" in m.get("usecases", []) or "USECASE_EMBEDDING" in m.get("usecases", [])
                ]
                
                if not embedding_models:
                     logger.warning(f"[DO] No explicit embedding models found via usecases. Checking names...")
                     # Fallback: look for known embedding model names
                     known_embeddings = ["GTE Large", "MiniLM", "MPNet", "Embedding", "Qwen3 Embedding"]
                     embedding_models = [
                         m for m in models
                         if any(k in m.get("name", "") for k in known_embeddings)
                     ]
                
                if embedding_models:
                    selected = embedding_models[0]
                    logger.info(f"[DO] Selected embedding model: {selected.get('name')} ({selected.get('uuid')})")
                    return selected["uuid"]

                # If still no models found, log available models for debugging
                logger.warning(f"[DO] No embedding models found. Available: {[m.get('name') for m in models]}")
                return None
            except Exception as e:
                logger.error(f"[DO] Failed to list embedding models: {e}")
                return None

    async def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """List all knowledge bases (handling pagination)."""
        if not self.settings.digitalocean_token:
            return []
            
        async with httpx.AsyncClient() as client:
            all_kbs = []
            next_url = f"{self.base_url}/knowledge_bases"
            
            while next_url:
                try:
                    response = await client.get(next_url, headers=self.headers)
                    response.raise_for_status()
                    data = response.json()
                    kbs = data.get("knowledge_bases", [])
                    all_kbs.extend(kbs)
                    
                    # Check for next page
                    links = data.get("links", {})
                    next_url = links.get("pages", {}).get("next")
                    
                    # Safety check to prevent infinite loops if API behaves unexpectedly
                    if not kbs and next_url:
                        logger.warning("[DO] Pagination returned no KBs but has next link. Breaking loop.")
                        break
                        
                except Exception as e:
                    logger.error(f"[DO] Failed to list knowledge bases: {e}")
                    # If we have some KBs, return those instead of empty
                    return all_kbs if all_kbs else []
                    
            return all_kbs

    async def get_knowledge_base(self, kb_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single knowledge base by UUID."""
        if not kb_uuid or not self.settings.digitalocean_token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/knowledge_bases/{kb_uuid}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json().get("knowledge_base")
            except Exception as e:
                logger.error(f"[DO] Failed to get knowledge base {kb_uuid}: {e}")
                return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents (handling pagination)."""
        if not self.settings.digitalocean_token:
            return []
            
        async with httpx.AsyncClient() as client:
            all_agents: List[Dict[str, Any]] = []
            next_url = f"{self.base_url}/agents"
            while next_url:
                try:
                    response = await client.get(next_url, headers=self.headers)
                    response.raise_for_status()
                    data = response.json()
                    agents = data.get("agents", [])
                    all_agents.extend(agents)

                    links = data.get("links", {})
                    next_url = links.get("pages", {}).get("next")

                    # Safety check
                    if not agents and next_url:
                        logger.warning("[DO] Pagination returned no agents but has next link. Breaking loop.")
                        break
                except Exception as e:
                    logger.error(f"[DO] Failed to list agents: {e}")
                    return all_agents if all_agents else []
            return all_agents

    async def wait_for_agent_ready(
        self, 
        agent_uuid: str, 
        max_wait_seconds: int = 120,
        poll_interval: int = 5
    ) -> bool:
        """
        Wait for a newly created agent's deployment to reach STATUS_RUNNING.
        
        Deployment statuses:
        - STATUS_UNKNOWN, STATUS_WAITING_FOR_DEPLOYMENT, STATUS_DEPLOYING, STATUS_BUILDING -> Still deploying
        - STATUS_RUNNING -> Ready!
        - STATUS_FAILED, STATUS_UNDEPLOYMENT_FAILED, STATUS_DELETED -> Failed states
        
        Args:
            agent_uuid: The agent UUID
            max_wait_seconds: Maximum time to wait (default 120s)
            poll_interval: Seconds between checks (default 5s)
            
        Returns:
            True if agent is running, False if timeout or failed
        """
        import time
        start_time = time.time()
        attempts = 0
        
        logger.info(f"[DO] Waiting for agent {agent_uuid} to deploy...")
        
        while time.time() - start_time < max_wait_seconds:
            attempts += 1
            try:
                # Get agent details
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/agents/{agent_uuid}",
                        headers=self.headers,
                    )
                    
                    if response.status_code == 200:
                        agent = response.json().get("agent", {})
                        deployment = agent.get("deployment", {})
                        status = deployment.get("status", "STATUS_UNKNOWN")
                        
                        # Check if agent is running and ready
                        if status == "STATUS_RUNNING":
                            elapsed = time.time() - start_time
                            logger.info(f"[DO] Agent deployed successfully after {elapsed:.1f}s ({attempts} checks)")
                            return True
                        elif status in ["STATUS_FAILED", "STATUS_UNDEPLOYMENT_FAILED", "STATUS_DELETED"]:
                            logger.error(f"[DO] Agent deployment failed with status: {status}")
                            return False
                        else:
                            logger.debug(f"[DO] Agent deployment status: {status}, waiting...")
                    else:
                        logger.warning(f"[DO] Failed to get agent status: {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"[DO] Error checking agent deployment status: {e}")
            
            # Wait before next check
            await asyncio.sleep(poll_interval)
        
        # Timeout
        elapsed = time.time() - start_time
        logger.warning(f"[DO] Agent deployment timeout after {elapsed:.1f}s")
        return False

    async def create_agent(
        self,
        name: str,
        knowledge_base_uuids: List[str],
        instruction: Optional[str] = None,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new Agent. Retrieval defaults are applied via update after creation."""
        if not self.settings.digitalocean_token:
            return None

        # Guard: only allow KB UUIDs we have recorded to reduce leakage risk.
        validated_kb_uuids: List[str] = []
        for kb_uuid in knowledge_base_uuids:
            rec = self.registry.find_by_uuid(kb_uuid)
            if not rec:
                logger.error("[DO] Rejecting unknown KB UUID for agent creation: %s", kb_uuid)
                continue
            if rec.region and self.settings.digitalocean_genai_region and rec.region != self.settings.digitalocean_genai_region:
                logger.error(
                    "[DO] KB region mismatch (kb=%s in %s, agent region=%s). Skipping.",
                    kb_uuid,
                    rec.region,
                    self.settings.digitalocean_genai_region,
                )
                continue
            validated_kb_uuids.append(kb_uuid)

        if knowledge_base_uuids and not validated_kb_uuids:
            logger.error("[DO] No valid KB UUIDs available for agent creation; aborting.")
            return None
            
        # Get model UUID from settings
        model_uuid = self.settings.digitalocean_agent_model_uuid


        payload = {
            "name": name,
            "model_uuid": model_uuid,
            "instruction": instruction or self.settings.ai_system_prompt,
            "region": region or self.settings.digitalocean_genai_region,
            "project_id": project_id or self.settings.digitalocean_project_id or await self.get_default_project_id(),
            # DO API expects knowledge_base_uuid (array) per docs; keep field name aligned.
            "knowledge_base_uuid": validated_kb_uuids,
            # Generation parameters
            "temperature": self.settings.digitalocean_agent_temperature,
            "top_p": self.settings.digitalocean_agent_top_p,
            "top_k": self.settings.digitalocean_agent_top_k,
            "max_tokens": self.settings.digitalocean_agent_max_tokens,
        }

        # Optional workspace/provider key wiring (some setups require these to create agents)
        if self.settings.digitalocean_workspace_uuid:
            payload["workspace_uuid"] = self.settings.digitalocean_workspace_uuid
        if self.settings.digitalocean_openai_key_uuid:
            payload["open_ai_key_uuid"] = self.settings.digitalocean_openai_key_uuid
        
        # Add optional fields only if they have values and let API default if possible
        if self.settings.digitalocean_project_id:
             payload["project_id"] = str(self.settings.digitalocean_project_id)
        
        # Re-enabling fields but strictly checking them
        if self.settings.digitalocean_genai_region:
           # payload["region"] = self.settings.digitalocean_genai_region
           # If we are attaching KBs, we must be in the SAME region as the KBs.
           # The KB "integrity-professionals" is in "sfo2".
           # My config says "tor1".
           # Mismatch! Agent region must match KB region? Or at least compatible?
           # Let's try to infer region from KB if available.
           if knowledge_base_uuids:
               # We need to look up the KB to check its region.
               # This is expensive but necessary if we have mixed regions.
               # For now, let's just HARDCODE sfo2 to test.
               # payload["region"] = "sfo2" 
               # Revert to tor1 (default) to test agent creation there
               payload["region"] = self.settings.digitalocean_genai_region
           else:
               payload["region"] = self.settings.digitalocean_genai_region
            
        # Log payload before request (needs json import if not present, but logger usually handles dicts)
        import json
        logger.info(f"[DO] Creating agent with payload: {json.dumps(payload)}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/agents", headers=self.headers, json=payload)
                response.raise_for_status()
                agent = response.json().get("agent")

                # Apply retrieval defaults via update call (some fields may not be accepted on create)
                if agent and agent.get("uuid"):
                    try:
                        update_payload = {
                            "retrieval_method": self.settings.digitalocean_agent_retrieval_method,
                            "provide_citations": self.settings.digitalocean_agent_provide_citations,
                            "k": self.settings.digitalocean_agent_k,
                            "conversation_logs_enabled": self.settings.digitalocean_agent_conversation_logs_enabled,
                            "agent_log_insights_enabled": self.settings.digitalocean_agent_log_insights_enabled,
                        }
                        update_resp = await client.put(
                            f"{self.base_url}/agents/{agent['uuid']}",
                            headers=self.headers,
                            json=update_payload,
                        )
                        update_resp.raise_for_status()
                        agent = update_resp.json().get("agent", agent)
                    except httpx.HTTPStatusError as e:
                        logger.error(f"[DO] HTTP Error updating agent retrieval defaults: {e.response.status_code} - {e.response.text}")
                    except Exception as e:
                        logger.error(f"[DO] Failed to update agent retrieval defaults: {e}")

                return agent
            except httpx.HTTPStatusError as e:
                logger.error(f"[DO] HTTP Error creating agent: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 403:
                    # Bubble up a clear error so callers can surface it to the UI
                    raise PermissionError(f"DigitalOcean denied agent creation: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"[DO] Failed to create agent: {e}")
                return None

    async def attach_client_kb_to_agent(self, agent_uuid: str, client_slug: str) -> bool:
        """
        Attach the client's KB to an agent, enforcing registry and region consistency.
        """
        rec = self.registry.get(client_slug)
        if not rec:
            logger.error("[DO] No KB registry entry for client '%s'; cannot attach.", client_slug)
            return False

        kb = await self.get_knowledge_base(rec.kb_uuid)
        kb_region = (kb or {}).get("region") or rec.region
        agent_region = self.settings.digitalocean_genai_region
        if kb_region and agent_region and kb_region != agent_region:
            logger.error(
                "[DO] Region mismatch when attaching KB. kb=%s region=%s agent_region=%s",
                rec.kb_uuid,
                kb_region,
                agent_region,
            )
            return False

        payload = {"knowledge_base_uuids": [rec.kb_uuid]}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/agents/{agent_uuid}/knowledge_bases",
                    headers=self.headers,
                    json=payload,
                )
                resp.raise_for_status()
                logger.info("[DO] Attached KB %s to agent %s", rec.kb_uuid, agent_uuid)
                return True
            except httpx.HTTPStatusError as e:
                logger.error(
                    "[DO] HTTP Error attaching KB %s to agent %s: %s - %s",
                    rec.kb_uuid,
                    agent_uuid,
                    e.response.status_code,
                    e.response.text,
                )
                return False
            except Exception as e:
                logger.error("[DO] Failed to attach KB %s to agent %s: %s", rec.kb_uuid, agent_uuid, e)
                return False

    async def get_agent_chat_endpoint(self, agent_uuid: str, max_retries: int = 3) -> Optional[str]:
        """
        Get the endpoint URL for an agent (ensuring it's public/accessible).
        Includes retry logic for newly created agents.
        
        Args:
            agent_uuid: The agent UUID
            max_retries: Number of retry attempts (default 3)
        """
        for attempt in range(1, max_retries + 1):
            async with httpx.AsyncClient() as client:
                try:
                    payload = {"uuid": agent_uuid, "visibility": "VISIBILITY_PUBLIC"}
                    response = await client.put(
                        f"{self.base_url}/agents/{agent_uuid}/deployment_visibility",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json() or {}
                    # Observed DO response shape: {"agent": {"deployment": {"url": "..."} } }
                    url = data.get("url")
                    if not url and isinstance(data.get("agent"), dict):
                        url = (data.get("agent", {}).get("deployment") or {}).get("url")
                    
                    if url:
                        return url
                    elif attempt < max_retries:
                        logger.warning(f"[DO] No URL in response (attempt {attempt}/{max_retries}), waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        return None

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 400 and attempt < max_retries:
                        logger.warning(f"[DO] Endpoint request failed (attempt {attempt}/{max_retries}), waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        logger.error(f"[DO] Failed to get agent endpoint: {e}")
                        if attempt == max_retries:
                            return None
                except Exception as e:
                    logger.error(f"[DO] Error getting agent endpoint (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(5)
                    else:
                        return None
        return None

    async def get_agent(self, agent_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single agent by UUID."""
        if not agent_uuid or not self.settings.digitalocean_token:
            return None
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/agents/{agent_uuid}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json().get("agent") or response.json().get("agent_info") or response.json()
            except httpx.HTTPStatusError as e:
                # Some DO responses may not expose a direct GET-by-UUID in all contexts;
                # fallback to list + match so callers can still validate UUID existence.
                if e.response is not None and e.response.status_code == 404:
                    try:
                        agents = await self.list_agents()
                        for a in agents:
                            if a.get("uuid") == agent_uuid:
                                return a
                    except Exception:
                        pass
                logger.error(f"[DO] Failed to get agent {agent_uuid}: {e}")
                return None
            except Exception as e:
                logger.error(f"[DO] Failed to get agent {agent_uuid}: {e}")
                return None

    async def create_agent_api_key(self, agent_uuid: str, max_retries: int = 3) -> Optional[str]:
        """
        Create an API key for the agent.
        Includes retry logic for newly created agents.
        
        Args:
            agent_uuid: The agent UUID
            max_retries: Number of retry attempts (default 3)
        """
        for attempt in range(1, max_retries + 1):
            async with httpx.AsyncClient() as client:
                try:
                    payload = {"agent_uuid": agent_uuid, "name": f"key-{int(asyncio.get_event_loop().time())}"}
                    response = await client.post(
                        f"{self.base_url}/agents/{agent_uuid}/api_keys",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json() or {}
                    # Observed DO response shape: {"api_key_info": {"secret_key": "..."}}
                    api_key_info = data.get("api_key_info") if isinstance(data.get("api_key_info"), dict) else {}
                    api_key = (
                        api_key_info.get("secret_key")
                        or data.get("access_key")
                        or data.get("key")
                    )
                    
                    if api_key:
                        return api_key
                    elif attempt < max_retries:
                        logger.warning(f"[DO] No API key in response (attempt {attempt}/{max_retries}), waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        return None
                        
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [400, 404] and attempt < max_retries:
                        logger.warning(f"[DO] API key creation failed (attempt {attempt}/{max_retries}), waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        logger.error(f"[DO] Failed to create agent API key: {e}")
                        if attempt == max_retries:
                            return None
                except Exception as e:
                    logger.error(f"[DO] Failed to create agent API key (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(5)
                    else:
                        return None
        return None


    async def get_knowledge_base_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a KB by name."""
        kbs = await self.list_knowledge_bases()
        for kb in kbs:
            if kb.get("name") == name:
                return kb
        return None

    async def get_default_project_id(self) -> Optional[str]:
        """Fetch the default project ID."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.digitalocean.com/v2/projects",
                    headers=self.headers,
                )
                if response.status_code == 200:
                    projects = response.json().get("projects", [])
                    default = next((p for p in projects if p.get("is_default")), projects[0] if projects else None)
                    return default.get("id") if default else None
            except Exception as e:
                logger.error(f"[DO] Failed to list projects: {e}")
        return None

    def _record_kb(self, slug: str, kb: Dict[str, Any]) -> Optional[KnowledgeBaseRecord]:
        """Persist KB metadata in the local registry."""
        if not kb:
            return None
        kb_uuid = kb.get("uuid")
        if not kb_uuid:
            return None

        region = kb.get("region") or kb.get("datacenter") or self.settings.digitalocean_genai_region
        tags = kb.get("tags", [])
        data_sources = kb.get("knowledge_base_data_sources") or kb.get("data_sources") or []
        created_at = kb.get("created_at")

        rec = self.registry.upsert(
            slug=slug,
            kb_uuid=kb_uuid,
            region=region,
            tags=tags,
            data_sources=data_sources,
            created_at=created_at,
        )
        logger.info("[DO] Recorded KB mapping: slug=%s uuid=%s region=%s", slug, kb_uuid, region)
        return rec

    async def ensure_client_kb(self, slug: str, data_sources: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """
        Resolve or create the KB for a client slug and record it in the registry.
        """
        existing = self.registry.get(slug)
        if existing:
            kb = await self.get_knowledge_base(existing.kb_uuid)
            if kb:
                return kb

        kb = await self.create_knowledge_base(name=slug, data_sources=data_sources)
        if kb:
            self._record_kb(slug, kb)
        return kb

    async def create_knowledge_base(self, name: str, data_sources: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Create a new Knowledge Base."""
        if not self.settings.digitalocean_token:
            logger.warning("[DO] Token not configured, skipping KB creation.")
            return None

        # Check if exists first
        existing = await self.get_knowledge_base_by_name(name)
        if existing:
            self._record_kb(name, existing)
            return existing

        embedding_model_uuid = await self.get_embedding_model_uuid()
        if not embedding_model_uuid:
            logger.error("[DO] No embedding model found.")
            return None

        payload = {
            "name": name,
            "embedding_model_uuid": embedding_model_uuid,
            "region": self.settings.digitalocean_genai_region,
            # Tag with generic label plus the specific client slug for filtering
            "tags": ["client-docs", name]
        }
        
        # Use configured shared Database ID
        if self.settings.digitalocean_db_id:
             payload["database_id"] = self.settings.digitalocean_db_id
        
        # Project ID Logic
        pid = self.settings.digitalocean_project_id
        if not pid or len(str(pid)) < 10:
            pid = await self.get_default_project_id()
        
        if pid:
            payload["project_id"] = str(pid)
            
        # Data Sources (required by API)
        # If caller didn't provide datasources, default to this client's folder in Spaces so KB creation succeeds.
        if not data_sources:
            if self.settings.digitalocean_spaces_bucket:
                default_prefix = f"{name.strip().strip('/')}/"
                data_sources = [
                    {
                        "spaces_data_source": {
                            "bucket_name": self.settings.digitalocean_spaces_bucket,
                            "region": self.settings.digitalocean_spaces_region,
                            "item_path": default_prefix,
                        }
                    }
                ]
                logger.info("[DO] No datasources provided; defaulting KB '%s' to Spaces %s/%s",
                            name, self.settings.digitalocean_spaces_bucket, default_prefix)
            else:
                logger.error("[DO] datasources are required but DIGITALOCEAN_SPACES_BUCKET is not configured.")
                return None

        # API requires datasources; when provided, inject chunking fields if enabled.
        if data_sources:
            processed_sources: List[Dict[str, Any]] = []
            for ds in data_sources:
                # Shallow copy to avoid mutating caller
                new_ds = dict(ds)
                if (
                    self.settings.digitalocean_enable_advanced_chunking
                    and "chunking_algorithm" not in new_ds
                ):
                    new_ds["chunking_algorithm"] = self.settings.digitalocean_chunking_algorithm
                if (
                    self.settings.digitalocean_enable_advanced_chunking
                    and "chunking_options" not in new_ds
                ):
                    new_ds["chunking_options"] = {
                        "child_chunk_size": 400,
                        "max_chunk_size": 800,
                        "parent_chunk_size": 1500,
                        "semantic_threshold": 0.5,
                    }
                processed_sources.append(new_ds)
            payload["datasources"] = processed_sources
        
        payload["chunking_algorithm"] = self.settings.digitalocean_chunking_algorithm
        payload["chunking_options"] = {
                "child_chunk_size": 400,
                "max_chunk_size": 800,
                "parent_chunk_size": 1500,
                "semantic_threshold": 0.5,
            }

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/knowledge_bases",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                kb = response.json().get("knowledge_base")
                if kb:
                    self._record_kb(name, kb)
                
                # Poll until KB is ready (or at least created successfully)
                if kb:
                    uuid = kb.get("uuid")
                    logger.info(f"[DO] Waiting for KB {uuid} to be ready...")
                    for _ in range(10):  # Poll for up to 20 seconds
                        await asyncio.sleep(2)
                        check_resp = await client.get(
                            f"{self.base_url}/knowledge_bases/{uuid}",
                            headers=self.headers
                        )
                        if check_resp.status_code == 200:
                            status = check_resp.json().get("database_status", "UNKNOWN")
                            logger.info(f"[DO] KB {uuid} status: {status}")
                            # According to docs, 'CREATING' -> 'DEPLOYING' -> 'READY'
                            # We can return once it exists and is readable, 
                            # but waiting for READY ensures subsequent calls (add source) don't fail.
                            if status == "ONLINE":
                                return check_resp.json().get("knowledge_base")
                            if status != "ONLINE":
                                logger.error(f"[DO] KB creation failed with status {status}")
                                return None
                
                return kb
            except httpx.HTTPStatusError as e:
                logger.error(f"[DO] HTTP Error creating KB: {e.response.text}")
                
                # If conflict (409) or "already exists" in message, try to fetch it again
                if e.response.status_code == 409 or "already exists" in e.response.text.lower():
                    logger.info(f"[DO] KB '{name}' likely already exists. Attempting to fetch...")
                    return await self.get_knowledge_base_by_name(name)
                    
                return None
            except Exception as e:
                logger.error(f"[DO] Error creating KB: {e}")
                return None

    async def list_data_sources(self, kb_uuid: str) -> List[Dict[str, Any]]:
        """List data sources for a KB."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/knowledge_bases/{kb_uuid}/data_sources",
                    headers=self.headers,
                )
                response.raise_for_status()
                # API returns 'knowledge_base_data_sources', not 'data_sources'
                return response.json().get("knowledge_base_data_sources", [])
            except Exception as e:
                logger.error(f"[DO] Error listing data sources: {e}")
                return []

    async def delete_data_source(self, kb_uuid: str, source_uuid: str) -> bool:
        """Delete a data source from a KB."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/knowledge_bases/{kb_uuid}/data_sources/{source_uuid}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"[DO] Error deleting data source: {e}")
                return False

    async def ensure_correct_spaces_source(self, kb_uuid: str, bucket: str, expected_prefix: str) -> Tuple[bool, bool]:
        """
        Ensures that the KB has the correct Spaces source (bucket + prefix).
        Removes any sources pointing to the same bucket with a DIFFERENT prefix (e.g. root).
        Adds the correct source if missing.
        Returns (is_valid, is_newly_created).
        """
        logger.info(f"[DO] Verifying sources for KB {kb_uuid}. Expecting {bucket}/{expected_prefix}")
        sources = await self.list_data_sources(kb_uuid)
        correct_source_exists = False
        
        for s in sources:
            s_details = s.get("spaces_data_source", {})
            existing_bucket = s_details.get("bucket_name")
            # API uses 'item_path', but we check both just in case
            existing_prefix = s_details.get("item_path") or s_details.get("prefix", "")
            
            logger.info(f"[DO] Found source: uuid={s.get('uuid')}, bucket={existing_bucket}, prefix='{existing_prefix}'")

            if existing_bucket == bucket:
                # Check if this is the correct source
                if existing_prefix.rstrip("/") == expected_prefix.rstrip("/"):
                    correct_source_exists = True
                    logger.info("[DO] Correct source already exists.")
                else:
                    # Found a source with same bucket but wrong prefix -> DELETE IT
                    logger.warning(f"[DO] Deleting incorrect source {s.get('uuid')} with prefix '{existing_prefix}' (expected '{expected_prefix}')")
                    deleted = await self.delete_data_source(kb_uuid, s.get("uuid"))
                    if deleted:
                        logger.info("[DO] Incorrect source deleted.")
                        # Small delay to ensure deletion propagates/doesn't conflict with add
                        await asyncio.sleep(1)
        
        if not correct_source_exists:
            logger.info(f"[DO] Adding correct source for {bucket}/{expected_prefix}")
            success = await self.add_spaces_source(kb_uuid, bucket, expected_prefix)
            return success, True # is_valid=success, is_new=True
            
        return True, False # is_valid=True, is_new=False

    async def add_spaces_source(self, kb_uuid: str, bucket: str, prefix: str = "") -> bool:
        """Add a Spaces bucket/folder as a data source."""
        # Check if already exists to avoid duplicates
        existing_sources = await self.list_data_sources(kb_uuid)
        for source in existing_sources:
            s_details = source.get("spaces_data_source", {})
            if s_details.get("bucket_name") == bucket:
                 existing_prefix = s_details.get("item_path") or s_details.get("prefix", "")
                 if prefix.rstrip("/") == existing_prefix.rstrip("/"):
                     logger.info(f"[DO] Data source for bucket {bucket} prefix {prefix} already exists.")
                     return True

        payload = {
            "knowledge_base_uuid": kb_uuid,
            "spaces_data_source": {
                "bucket_name": bucket,
                "region": self.settings.digitalocean_spaces_region,
            }
        }
        if self.settings.digitalocean_enable_advanced_chunking:
            payload["chunking_algorithm"] = self.settings.digitalocean_chunking_algorithm
            payload["chunking_options"] = {
                "child_chunk_size": 400,
                "max_chunk_size": 800,
                "parent_chunk_size": 1500,
                "semantic_threshold": 0.5,
            }
        if prefix:
             # Use item_path instead of prefix as per API observation
             payload["spaces_data_source"]["item_path"] = prefix

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/knowledge_bases/{kb_uuid}/data_sources",
                    headers=self.headers,
                    json=payload,
                )
                try:
                    resp.raise_for_status()
                    return True
                except httpx.HTTPStatusError as e:
                    # If advanced chunking is rejected, retry once without it
                    if (
                        self.settings.digitalocean_enable_advanced_chunking
                        and resp.status_code == 403
                        and "Advanced chunking algorithms" in resp.text
                    ):
                        logger.warning("[DO] Advanced chunking rejected; retrying without chunking fields.")
                        fallback_payload = {
                            "knowledge_base_uuid": kb_uuid,
                            "spaces_data_source": payload["spaces_data_source"],
                        }
                        resp2 = await client.post(
                            f"{self.base_url}/knowledge_bases/{kb_uuid}/data_sources",
                            headers=self.headers,
                            json=fallback_payload,
                        )
                        resp2.raise_for_status()
                        return True
                    logger.error(f"[DO] HTTP Error adding spaces source: {resp.text}")
                    return False
            except Exception as e:
                logger.error(f"[DO] Error adding spaces source: {e}")
                return False

    async def trigger_reindexing(self, kb_uuid: str, bucket: str, prefix: str = "") -> bool:
        """
        Trigger re-indexing by deleting and re-adding the data source.
        The dedicated indexing_jobs endpoint appears to be unavailable or undocumented for Spaces.
        """
        logger.info(f"[DO] Triggering re-index for KB {kb_uuid} bucket {bucket} prefix '{prefix}' via replace.")
        
        sources = await self.list_data_sources(kb_uuid)
        target_uuids = []
        
        # Identify all sources matching this bucket/prefix (handling duplicates if any)
        for source in sources:
            s_details = source.get("spaces_data_source", {})
            if s_details.get("bucket_name") == bucket:
                 existing_prefix = s_details.get("item_path") or s_details.get("prefix", "")
                 if prefix.rstrip("/") == existing_prefix.rstrip("/"):
                     target_uuids.append(source.get("uuid"))
        
        if not target_uuids:
            logger.warning(f"[DO] No source found to reindex for {bucket}/{prefix}. Adding it now.")
            return await self.add_spaces_source(kb_uuid, bucket, prefix)

        # Delete existing sources
        for uuid in target_uuids:
            logger.info(f"[DO] Deleting old source {uuid} for re-indexing...")
            await self.delete_data_source(kb_uuid, uuid)
        
        # Wait for deletion to propagate
        await asyncio.sleep(2)
        
        # Add fresh source
        logger.info(f"[DO] Adding fresh source for {bucket}/{prefix}")
        return await self.add_spaces_source(kb_uuid, bucket, prefix)

    def upload_file_content(self, content: str | bytes, key: str, content_type: str = "text/markdown") -> bool:
        """Upload content to Spaces."""
        if not self.s3_client or not self.settings.digitalocean_spaces_bucket:
            logger.warning("[DO] Spaces not configured, skipping upload.")
            return False

        try:
            # Ensure content is bytes
            body = content.encode("utf-8") if isinstance(content, str) else content
            
            self.s3_client.put_object(
                Bucket=self.settings.digitalocean_spaces_bucket,
                Key=key,
                Body=body,
                ACL="private", 
                ContentType=content_type,
            )
            return True
        except ClientError as e:
            logger.error(f"[DO] Failed to upload to Spaces: {e}")
            return False
        except Exception as e:
            logger.error(f"[DO] Error uploading to Spaces: {e}")
            return False

# Singleton instance
do_client = DigitalOceanClient()
