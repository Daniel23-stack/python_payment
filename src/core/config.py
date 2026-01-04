"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/payment_system"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Application
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Idempotency
    IDEMPOTENCY_KEY_TTL_SECONDS: int = 86400  # 24 hours
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

