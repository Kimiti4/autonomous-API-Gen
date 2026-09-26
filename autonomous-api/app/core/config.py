"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    APP_NAME: str = "Autonomous Evolution Engine"
    APP_VERSION: str = "3.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "sqlite:///./evolution.db"

    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    SECRET_KEY: str = ""
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_API_KEY: str = ""

    RATE_LIMIT_GENERAL: int = 100
    RATE_LIMIT_EVOLUTION: int = 20
    RATE_LIMIT_WINDOW: int = 60

    GOVERNANCE_CERTIFIERS: str = ""
    GOVERNANCE_QUORUM_THRESHOLD: float = 1.0
    GOVERNANCE_EXECUTIVE_WEIGHT: float = 0.6
    GOVERNANCE_ENFORCEMENT_REQUIRED: bool = False
    GOVERNANCE_AUDIT_SIGNING_KEY: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _coerce_debug(cls, v):
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return v

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, v):
        value = str(v).strip().lower()
        if value not in {"development", "test", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, staging, or production")
        return value

    @field_validator("GOVERNANCE_QUORUM_THRESHOLD", "GOVERNANCE_EXECUTIVE_WEIGHT")
    @classmethod
    def _non_negative_governance_weights(cls, v):
        if v < 0:
            raise ValueError("governance quorum and executive weight must be non-negative")
        return v

    @field_validator("RATE_LIMIT_GENERAL", "RATE_LIMIT_EVOLUTION", "RATE_LIMIT_WINDOW")
    @classmethod
    def _positive_limits(cls, v):
        if v <= 0:
            raise ValueError("rate-limit settings must be positive")
        return v

    @model_validator(mode="after")
    def _validate_production_security(self):
        if self.ENVIRONMENT == "production":
            if not self.ADMIN_API_KEY:
                raise ValueError("ADMIN_API_KEY is required in production")
            if not self.SECRET_KEY or self.SECRET_KEY == "change-this-in-production":
                raise ValueError("SECRET_KEY must be explicitly configured in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must be configured in production")
            if not self.GOVERNANCE_CERTIFIERS.strip():
                raise ValueError("GOVERNANCE_CERTIFIERS is required in production")
            if self.GOVERNANCE_QUORUM_THRESHOLD <= 0:
                raise ValueError("GOVERNANCE_QUORUM_THRESHOLD must be positive in production")
            if not self.GOVERNANCE_ENFORCEMENT_REQUIRED:
                raise ValueError("GOVERNANCE_ENFORCEMENT_REQUIRED must be true in production")
            if not self.GOVERNANCE_AUDIT_SIGNING_KEY:
                raise ValueError("GOVERNANCE_AUDIT_SIGNING_KEY is required in production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
