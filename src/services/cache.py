"""Redis cache utilities."""

import redis
import json
from typing import Optional, Any
from decimal import Decimal

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis cache service."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
        )
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        try:
            if isinstance(value, (Decimal, float, int)):
                value = str(value)
            elif isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False
    
    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from cache."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_json(self, key: str, value: dict, ttl: int = 300) -> bool:
        """Set JSON value in cache."""
        return self.set(key, json.dumps(value), ttl)


# Global cache instance
cache_service = CacheService()

