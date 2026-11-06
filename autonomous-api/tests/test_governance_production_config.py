import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_values(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "ADMIN_API_KEY": "admin-key-with-sufficient-entropy",
        "SECRET_KEY": "production-secret-with-sufficient-entropy",
        "GOVERNANCE_AUDIT_SIGNING_KEY": "governance-signing-key-with-sufficient-entropy",
        "CORS_ORIGINS": ["https://example.invalid"],
        "GOVERNANCE_ENFORCEMENT_REQUIRED": True,
    }
    values.update(overrides)
    return values


def test_production_configuration_requires_governance_enforcement():
    with pytest.raises(ValidationError, match="GOVERNANCE_ENFORCEMENT_REQUIRED"):
        Settings(**_production_values(GOVERNANCE_ENFORCEMENT_REQUIRED=False))


def test_production_configuration_accepts_explicit_governance_enforcement():
    settings = Settings(**_production_values())
    assert settings.ENVIRONMENT == "production"
    assert settings.GOVERNANCE_ENFORCEMENT_REQUIRED is True


def test_nonproduction_configuration_can_remain_in_staging_mode():
    settings = Settings(
        ENVIRONMENT="development",
        GOVERNANCE_ENFORCEMENT_REQUIRED=False,
    )
    assert settings.GOVERNANCE_ENFORCEMENT_REQUIRED is False
