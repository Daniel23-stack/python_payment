"""Idempotency service for preventing duplicate transactions."""

import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from src.db.models import IdempotencyKey, Transaction
from src.services.cache import cache_service
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class IdempotencyService:
    """Service for handling idempotency keys."""
    
    def __init__(self, db: Session):
        """Initialize idempotency service."""
        self.db = db
    
    def check_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if idempotency key exists and return cached response.
        
        Returns:
            Cached response if exists, None otherwise
        """
        # Fast path: Check Redis cache
        cache_key = f"idempotency:{idempotency_key}"
        cached_response = cache_service.get_json(cache_key)
        if cached_response:
            logger.info("Idempotency cache hit", idempotency_key=idempotency_key[:8])
            return cached_response
        
        # Slow path: Check database
        db_key = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.idempotency_key == idempotency_key,
            IdempotencyKey.expires_at > datetime.utcnow()
        ).first()
        
        if db_key and db_key.response_data:
            # Refresh cache
            cache_service.set_json(
                cache_key,
                db_key.response_data,
                ttl=settings.IDEMPOTENCY_KEY_TTL_SECONDS
            )
            logger.info("Idempotency DB hit", idempotency_key=idempotency_key[:8])
            return db_key.response_data
        
        return None
    
    def store_idempotency(
        self,
        idempotency_key: str,
        transaction_id: Optional[int],
        response_data: Dict[str, Any],
        request_hash: Optional[str] = None
    ) -> None:
        """
        Store idempotency key and response.
        
        Args:
            idempotency_key: Unique idempotency key
            transaction_id: Associated transaction ID
            response_data: Response data to cache
            request_hash: Optional hash of request for validation
        """
        expires_at = datetime.utcnow() + timedelta(seconds=settings.IDEMPOTENCY_KEY_TTL_SECONDS)
        
        # Store in database
        idempotency_record = IdempotencyKey(
            idempotency_key=idempotency_key,
            transaction_id=transaction_id,
            request_hash=request_hash,
            response_data=response_data,
            expires_at=expires_at
        )
        self.db.add(idempotency_record)
        
        # Store in cache
        cache_key = f"idempotency:{idempotency_key}"
        cache_service.set_json(
            cache_key,
            response_data,
            ttl=settings.IDEMPOTENCY_KEY_TTL_SECONDS
        )
        
        logger.info("Idempotency stored", idempotency_key=idempotency_key[:8], transaction_id=transaction_id)
    
    @staticmethod
    def generate_request_hash(request_data: Dict[str, Any]) -> str:
        """Generate hash from request data for validation."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()

