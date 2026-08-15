"""
Application configuration.
Auto-generated from ISR.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    app_name: str = "MonolithShop"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./app.db"
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    cors_origins: List[str] = ["*"]

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
