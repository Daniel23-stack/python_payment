"""API middleware."""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from src.core.config import settings
from src.core.logging import get_logger
from src.services.cache import cache_service
from src.core.exceptions import RateLimitExceededError

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (IP address or user ID)
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        response = await call_next(request)
        return response
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        minute_key = f"rate_limit:minute:{client_id}"
        hour_key = f"rate_limit:hour:{client_id}"
        
        # Check minute limit
        minute_count = cache_service.get(minute_key)
        if minute_count and int(minute_count) >= settings.RATE_LIMIT_PER_MINUTE:
            return False
        
        # Check hour limit
        hour_count = cache_service.get(hour_key)
        if hour_count and int(hour_count) >= settings.RATE_LIMIT_PER_HOUR:
            return False
        
        # Increment counters
        cache_service.set(minute_key, str(int(minute_count or 0) + 1), ttl=60)
        cache_service.set(hour_key, str(int(hour_count or 0) + 1), ttl=3600)
        
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response."""
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time
        )
        
        return response

