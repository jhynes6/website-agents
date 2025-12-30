from typing import Any, Dict, Optional

from upstash_redis import Redis

from ..config import get_settings
from ..logging import logger


class RedisClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis: Optional[Redis] = None
        
        # Only initialize if Redis credentials are configured
        if self.settings.upstash_redis_rest_url and self.settings.upstash_redis_rest_token:
            self.redis = Redis(
                url=str(self.settings.upstash_redis_rest_url),
                token=self.settings.upstash_redis_rest_token,
            )
            logger.info(f"[Redis] Initialized with URL: {self.settings.upstash_redis_rest_url}")
            # Test connection
            try:
                result = self.redis.ping()
                logger.info(f"[Redis] PING response: {result}")
            except Exception as e:
                logger.error(f"[Redis] PING failed: {e}")
        else:
            logger.warning("[Redis] Not configured - metadata will not be persisted")

    def save_index(self, index_metadata: Dict[str, Any]) -> None:
        """Save chatbot index metadata to Redis using stable client-slug keys."""
        if not self.redis:
            logger.warning("[Redis] Cannot save - Redis not configured")
            return
        
        client_slug = (
            index_metadata.get("clientSlug")
            or index_metadata.get("index")
            or index_metadata.get("namespace")
        )
        if not client_slug:
            logger.error("[Redis] Cannot save - no clientSlug/index/namespace in metadata")
            return
        
        # Ensure metadata uses the canonical slug for namespace/index
        index_metadata = {**index_metadata}
        index_metadata["namespace"] = client_slug
        index_metadata["index"] = client_slug
        index_metadata["clientSlug"] = client_slug
        
        try:
            key = f"mintagent:index:{client_slug}"
            logger.info(f"[Redis] Saving index for client '{client_slug}' to key '{key}'")
            self.redis.set(key, index_metadata)
            
            indexes_key = "mintagent:indexes"
            indexes = self.redis.get(indexes_key) or []
            if not isinstance(indexes, list):
                indexes = []
            
            existing_idx = None
            for i, idx in enumerate(indexes):
                if isinstance(idx, dict) and (
                    idx.get("clientSlug") == client_slug
                    or idx.get("index") == client_slug
                    or idx.get("namespace") == client_slug
                ):
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                indexes[existing_idx] = index_metadata
            else:
                indexes.insert(0, index_metadata)
            
            self.redis.set(indexes_key, indexes)
            logger.info(f"[Redis] Updated indexes list with {len(indexes)} items")
        except Exception as e:
            logger.error(f"[Redis] Failed to save index: {e}")


redis_client = RedisClient()

