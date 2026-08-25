"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Autonomous Evolution Engine"
    APP_VERSION: str = "3.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # "development" | "production"
    
    # Database
    DATABASE_URL: str = "sqlite:///./evolution.db"
    
    # Ollama Configuration
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Security
    SECRET_KEY: str = "change-this-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_API_KEY: str = ""
    
    # Rate Limiting
    RATE_LIMIT_GENERAL: int = 100
    RATE_LIMIT_EVOLUTION: int = 20
    RATE_LIMIT_WINDOW: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _coerce_debug(cls, v):
        """Tolerate non-boolean DEBUG values from the environment
        (e.g. DEBUG=release) instead of refusing to start."""
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings