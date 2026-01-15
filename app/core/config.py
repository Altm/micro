from pydantic_settings import BaseSettings
from typing import Optional, List, Union


class Settings(BaseSettings):
    PROJECT_NAME: str = "Catalog and Inventory Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/inventory_db"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # HMAC settings for terminals
    TERMINAL_SECRET_KEY: str = "terminal-secret-key-here-change-in-production"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = []
    
    # Audit settings
    AUDIT_ENABLED: bool = True
    REQUEST_LOG_MAX_LENGTH: int = 1000  # Maximum length of request body to log
    
    # Business logic settings
    RECONCILIATION_INTERVAL_HOURS: int = 1  # How often to reconcile pending transactions
    TERMINAL_TIME_WINDOW_MINUTES: int = 5  # Time window for terminal requests (for replay protection)
    
    class Config:
        env_file = ".env"


settings = Settings()