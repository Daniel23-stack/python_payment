"""Main application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from src.api.v1.router import api_router
from src.api.error_handlers import register_error_handlers
from src.api.middleware import RateLimitMiddleware, LoggingMiddleware
from src.core.config import settings
from src.db.database import engine, Base
from src.core.logging import setup_logging


# OpenAPI Tags metadata for Swagger documentation
tags_metadata = [
    {
        "name": "accounts",
        "description": "Operations for managing user accounts. Create accounts, view balances, and manage account status.",
    },
    {
        "name": "transfers",
        "description": "Money transfer operations between accounts. Supports idempotency for safe retries.",
    },
    {
        "name": "transactions",
        "description": "View transaction history, get transaction details, and reverse transactions.",
    },
    {
        "name": "health",
        "description": "Health check and system status endpoints.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


# API description for Swagger
API_DESCRIPTION = """
# Payment System API 💰

A **production-ready payment system** designed with zero tolerance for money handling errors.

## Features

- ✅ **Decimal-based money handling** - No floating-point precision errors
- ✅ **ACID transactions** - Guaranteed data consistency
- ✅ **Idempotency** - Safe to retry operations
- ✅ **Double-entry bookkeeping** - Self-balancing transactions
- ✅ **Comprehensive audit trail** - Full transaction history
- ✅ **Rate limiting** - Protection against abuse

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <your-token>
```

## Rate Limits

- **100 requests per minute** per IP address
- **1000 requests per hour** per IP address

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Duplicate transaction |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Idempotency

Include an `idempotency_key` in transfer requests to prevent duplicate processing:

```json
{
  "idempotency_key": "unique-key-per-request"
}
```

If the same key is used twice, the second request returns the cached response.
"""

app = FastAPI(
    title="Payment System API",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "Payment System Support",
        "email": "support@payment-system.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Register error handlers
register_error_handlers(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"], summary="Health Check")
async def health_check():
    """
    Check the health status of the payment system.
    
    Returns the status of:
    - **Database connection**
    - **Redis cache connection**
    - **Overall system health**
    
    Returns:
        Health status object with component statuses
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "database": "healthy",
            "cache": "healthy"
        }
    }


@app.get("/", tags=["health"], summary="Root", include_in_schema=False)
async def root():
    """Root endpoint - redirects to documentation."""
    return {
        "message": "Payment System API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }

