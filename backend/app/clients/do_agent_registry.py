import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import boto3

logger = logging.getLogger(__name__)


@dataclass
class AgentRecord:
    slug: str
    agent_uuid: str
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    agent_name: Optional[str] = None
    region: Optional[str] = None
    model: Optional[str] = None
    knowledge_base_uuids: Optional[list] = None
    retrieval_method: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "agent_uuid": self.agent_uuid,
            "agent_name": self.agent_name,
            "endpoint_url": self.endpoint_url,
            "api_key": self.api_key,
            "region": self.region,
            "model": self.model,
            "knowledge_base_uuids": self.knowledge_base_uuids or [],
            "retrieval_method": self.retrieval_method,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AgentRegistry:
    """
    Registry for DigitalOcean agent metadata, stored in mintleads-agents-store Space.
    Reads from Spaces on initialization and caches locally.
    """

    def __init__(self) -> None:
        from app.config import get_settings
        
        self.settings = get_settings()
        self.bucket = 'mintleads-agents-store'
        self.registry_key = 'agent_registry.json'
        self._data: Dict[str, AgentRecord] = {}
        self._cache_ttl = 300  # 5 minutes cache
        self._last_load = 0
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3',
                region_name=self.settings.digitalocean_spaces_region,
                endpoint_url=f"https://{self.settings.digitalocean_spaces_region}.digitaloceanspaces.com",
                aws_access_key_id=self.settings.digitalocean_spaces_key,
                aws_secret_access_key=self.settings.digitalocean_spaces_secret
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
        
        self._load()

    def _load(self) -> None:
        """Load registry from Spaces."""
        if not self.s3_client:
            logger.warning("S3 client not initialized, cannot load registry from Spaces")
            return
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=self.registry_key)
            raw = json.loads(response['Body'].read().decode('utf-8'))
            
            if not isinstance(raw, dict):
                logger.warning("Invalid registry format in Spaces")
                return
            
            self._data.clear()
            for slug, payload in raw.items():
                if not isinstance(payload, dict):
                    continue
                self._data[slug] = AgentRecord(
                    slug=slug,
                    agent_uuid=payload.get("agent_uuid", ""),
                    agent_name=payload.get("agent_name"),
                    endpoint_url=payload.get("endpoint_url"),
                    api_key=payload.get("api_key"),
                    region=payload.get("region"),
                    model=payload.get("model"),
                    knowledge_base_uuids=payload.get("knowledge_base_uuids", []),
                    retrieval_method=payload.get("retrieval_method"),
                    created_at=payload.get("created_at"),
                    updated_at=payload.get("updated_at"),
                )
            
            self._last_load = datetime.now(timezone.utc).timestamp()
            logger.info(f"Loaded {len(self._data)} agents from Spaces registry")
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Registry file not found in Spaces: {self.bucket}/{self.registry_key}")
        except Exception as exc:
            logger.error(f"Failed to load agent registry from Spaces: {exc}")

    def _maybe_refresh(self) -> None:
        """Refresh cache if TTL expired."""
        now = datetime.now(timezone.utc).timestamp()
        if now - self._last_load > self._cache_ttl:
            logger.info("Registry cache expired, refreshing from Spaces")
            self._load()

    def _persist(self) -> None:
        """Persist registry to Spaces."""
        if not self.s3_client:
            logger.warning("S3 client not initialized, cannot persist registry to Spaces")
            return
        
        try:
            serializable = {slug: rec.to_dict() for slug, rec in self._data.items()}
            self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=self.registry_key,
                    Body=json.dumps(serializable, indent=2, sort_keys=True).encode('utf-8'),
                    ContentType='application/json'
                )
            logger.info(f"Persisted {len(self._data)} agents to Spaces registry")
        except Exception as exc:
            logger.error(f"Failed to persist agent registry to Spaces: {exc}")

    @staticmethod
    def make_key(client_slug: str, agent_type: str) -> str:
        """
        Registry key format:
          <agent_type>:<client_slug>
        This prevents collisions when a client has multiple agent types (e.g. inbox_manager + copywriter).
        """
        slug = (client_slug or "").strip()
        a_type = (agent_type or "").strip()
        if not slug:
            raise ValueError("client_slug is required")
        if not a_type:
            raise ValueError("agent_type is required")
        return f"{a_type}:{slug}"

    def get(self, slug: str) -> Optional[AgentRecord]:
        """Get agent record by slug."""
        self._maybe_refresh()
        return self._data.get(slug)

    def get_for(self, client_slug: str, agent_type: str) -> Optional[AgentRecord]:
        """
        Get registry entry for a (client_slug, agent_type) pair.
        Back-compat: if agent_type is inbox_manager and a legacy entry exists keyed by client_slug,
        return it and migrate it to the new key.
        """
        self._maybe_refresh()
        key = self.make_key(client_slug, agent_type)
        rec = self._data.get(key)
        if rec:
            return rec

        # Backwards compatibility migration (older registry keyed only by client_slug)
        if agent_type == "inbox_manager":
            legacy = self._data.get(client_slug)
            if legacy:
                migrated = self.upsert(
                    slug=key,
                    agent_uuid=legacy.agent_uuid,
                    endpoint_url=legacy.endpoint_url,
                    api_key=legacy.api_key,
                )
                return migrated

        return None

    def upsert(
        self,
        slug: str,
        agent_uuid: str,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        agent_name: Optional[str] = None,
        region: Optional[str] = None,
        model: Optional[str] = None,
        knowledge_base_uuids: Optional[list] = None,
        retrieval_method: Optional[str] = None,
    ) -> AgentRecord:
        """Upsert agent record."""
        self._maybe_refresh()
        now = datetime.now(timezone.utc).isoformat()
        existing = self._data.get(slug)
        created_ts = (existing.created_at if existing and existing.created_at else now)
        rec = AgentRecord(
            slug=slug,
            agent_uuid=agent_uuid,
            agent_name=agent_name if agent_name is not None else (existing.agent_name if existing else None),
            endpoint_url=endpoint_url if endpoint_url is not None else (existing.endpoint_url if existing else None),
            api_key=api_key if api_key is not None else (existing.api_key if existing else None),
            region=region if region is not None else (existing.region if existing else None),
            model=model if model is not None else (existing.model if existing else None),
            knowledge_base_uuids=knowledge_base_uuids if knowledge_base_uuids is not None else (existing.knowledge_base_uuids if existing else []),
            retrieval_method=retrieval_method if retrieval_method is not None else (existing.retrieval_method if existing else None),
            created_at=created_ts,
            updated_at=now,
        )
        self._data[slug] = rec
        self._persist()
        return rec

    def upsert_for(
        self,
        client_slug: str,
        agent_type: str,
        *,
        agent_uuid: str,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        agent_name: Optional[str] = None,
        region: Optional[str] = None,
        model: Optional[str] = None,
        knowledge_base_uuids: Optional[list] = None,
        retrieval_method: Optional[str] = None,
    ) -> AgentRecord:
        """Upsert agent record for a specific client and agent type."""
        key = self.make_key(client_slug, agent_type)
        return self.upsert(
            slug=key,
            agent_uuid=agent_uuid,
            agent_name=agent_name,
            endpoint_url=endpoint_url,
            api_key=api_key,
            region=region,
            model=model,
            knowledge_base_uuids=knowledge_base_uuids,
            retrieval_method=retrieval_method,
        )

    def list_all(self) -> Dict[str, AgentRecord]:
        """List all agents in the registry."""
        self._maybe_refresh()
        return self._data.copy()
