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
        """Save chatbot index metadata to Redis."""
        if not self.redis:
            logger.warning("[Redis] Cannot save - Redis not configured")
            return
        
        namespace = index_metadata.get("namespace")
        if not namespace:
            logger.error("[Redis] Cannot save - no namespace in metadata")
            return
        
        try:
            # Save individual index with key: firestarter:index:<namespace>
            key = f"firestarter:index:{namespace}"
            logger.info(f"[Redis] Saving index for namespace '{namespace}' to key '{key}'")
            self.redis.set(key, index_metadata)
            
            # Update the indexes list
            indexes_key = "firestarter:indexes"
            indexes = self.redis.get(indexes_key) or []
            
            # Ensure indexes is a list
            if not isinstance(indexes, list):
                indexes = []
            
            # Check if this namespace already exists
            existing_idx = None
            for i, idx in enumerate(indexes):
                if isinstance(idx, dict) and idx.get("namespace") == namespace:
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                indexes[existing_idx] = index_metadata
            else:
                indexes.insert(0, index_metadata)
            
            # Keep only last 50
            indexes = indexes[:50]
            
            self.redis.set(indexes_key, indexes)
            logger.info(f"[Redis] Updated indexes list with {len(indexes)} items")
        except Exception as e:
            logger.error(f"[Redis] Failed to save index: {e}")


redis_client = RedisClient()

