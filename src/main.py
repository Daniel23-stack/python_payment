"""Main application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.v1.router import api_router
from src.api.error_handlers import register_error_handlers
from src.api.middleware import RateLimitMiddleware, LoggingMiddleware
from src.core.config import settings
from src.db.database import engine, Base
from src.core.logging import setup_logging


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


app = FastAPI(
    title="Payment System API",
    description="A production-ready payment system with zero tolerance for errors",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Payment System API",
        "version": "1.0.0",
        "docs": "/docs",
    }

