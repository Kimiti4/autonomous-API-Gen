"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    APP_NAME: str = "Autonomous Evolution Engine"
    APP_VERSION: str = "3.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "sqlite:///./evolution.db"
    MAINTENANCE_OUTBOX_DB_PATH: str = ""

    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    SECRET_KEY: str = ""
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_API_KEY: str = ""
    GOVERNANCE_AUDIT_SIGNING_KEY: str = ""
    GOVERNANCE_ENFORCEMENT_REQUIRED: bool = False
    GOVERNANCE_COUNCIL_API_KEYS: dict[str, str] = Field(default_factory=dict)
    GOVERNANCE_EVALUATOR_API_KEYS: dict[str, str] = Field(default_factory=dict)
    GOVERNANCE_CERTIFIER_API_KEY: str = ""
    GOVERNANCE_CERTIFIER_ID: str = "certifier-1"

    RATE_LIMIT_GENERAL: int = 100
    RATE_LIMIT_EVOLUTION: int = 20
    RATE_LIMIT_WINDOW: int = 60

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

    @field_validator("RATE_LIMIT_GENERAL", "RATE_LIMIT_EVOLUTION", "RATE_LIMIT_WINDOW")
    @classmethod
    def _positive_limits(cls, v):
        if v <= 0:
            raise ValueError("rate-limit settings must be positive")
        return v

    @model_validator(mode="after")
    def _validate_production_security(self):
        council_ids = set(self.GOVERNANCE_COUNCIL_API_KEYS)
        evaluator_ids = set(self.GOVERNANCE_EVALUATOR_API_KEYS)
        if council_ids & evaluator_ids:
            raise ValueError("governance council and evaluator identities must be distinct")
        if self.GOVERNANCE_CERTIFIER_ID and self.GOVERNANCE_CERTIFIER_ID in council_ids | evaluator_ids:
            raise ValueError("governance certifier identity must be distinct from council and evaluator identities")
        role_keys = (
            list(self.GOVERNANCE_COUNCIL_API_KEYS.values())
            + list(self.GOVERNANCE_EVALUATOR_API_KEYS.values())
            + ([self.GOVERNANCE_CERTIFIER_API_KEY] if self.GOVERNANCE_CERTIFIER_API_KEY else [])
        )
        if any(not key for key in role_keys) or len(set(role_keys)) != len(role_keys):
            raise ValueError("governance principal API keys must be non-empty and unique")
        if self.ADMIN_API_KEY and self.ADMIN_API_KEY in role_keys:
            raise ValueError("governance principal API keys must differ from ADMIN_API_KEY")

        if self.ENVIRONMENT == "production":
            if not self.ADMIN_API_KEY:
                raise ValueError("ADMIN_API_KEY is required in production")
            if not self.SECRET_KEY or self.SECRET_KEY == "change-this-in-production":
                raise ValueError("SECRET_KEY must be explicitly configured in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must be configured in production")
            if not self.GOVERNANCE_AUDIT_SIGNING_KEY:
                raise ValueError("GOVERNANCE_AUDIT_SIGNING_KEY is required in production")
            if not self.GOVERNANCE_ENFORCEMENT_REQUIRED:
                raise ValueError(
                    "GOVERNANCE_ENFORCEMENT_REQUIRED must be true in production; "
                    "ungoverned candidate promotion is prohibited"
                )
            if not self.GOVERNANCE_COUNCIL_API_KEYS:
                raise ValueError("GOVERNANCE_COUNCIL_API_KEYS is required in production")
            if not self.GOVERNANCE_EVALUATOR_API_KEYS:
                raise ValueError("GOVERNANCE_EVALUATOR_API_KEYS is required in production")
            if not self.GOVERNANCE_CERTIFIER_API_KEY:
                raise ValueError("GOVERNANCE_CERTIFIER_API_KEY is required in production")
            if not self.GOVERNANCE_CERTIFIER_ID:
                raise ValueError("GOVERNANCE_CERTIFIER_ID is required in production")
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
