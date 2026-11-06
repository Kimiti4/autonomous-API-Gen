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
        "GOVERNANCE_COUNCIL_API_KEYS": {
            "council-1": "council-secret-1",
            "council-2": "council-secret-2",
        },
        "GOVERNANCE_EVALUATOR_API_KEYS": {"evaluator-1": "evaluator-secret-1"},
        "GOVERNANCE_CERTIFIER_API_KEY": "certifier-secret-1",
        "GOVERNANCE_CERTIFIER_ID": "certifier-1",
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


def test_production_configuration_requires_distinct_governance_principals():
    with pytest.raises(ValidationError, match="GOVERNANCE_COUNCIL_API_KEYS"):
        Settings(**_production_values(GOVERNANCE_COUNCIL_API_KEYS={}))

    with pytest.raises(ValidationError, match="GOVERNANCE_EVALUATOR_API_KEYS"):
        Settings(**_production_values(GOVERNANCE_EVALUATOR_API_KEYS={}))

    with pytest.raises(ValidationError, match="GOVERNANCE_CERTIFIER_API_KEY"):
        Settings(**_production_values(GOVERNANCE_CERTIFIER_API_KEY=""))

    with pytest.raises(ValidationError, match="distinct from council"):
        Settings(**_production_values(GOVERNANCE_CERTIFIER_ID="council-1"))

    with pytest.raises(ValidationError, match="must be non-empty and unique"):
        Settings(**_production_values(
            GOVERNANCE_EVALUATOR_API_KEYS={"evaluator-1": "council-secret-1"}
        ))


def test_governance_principal_roles_and_secrets_cannot_overlap_outside_production():
    with pytest.raises(ValidationError, match="identities must be distinct"):
        Settings(
            ENVIRONMENT="development",
            GOVERNANCE_COUNCIL_API_KEYS={"member-1": "council-secret"},
            GOVERNANCE_EVALUATOR_API_KEYS={"member-1": "evaluator-secret"},
        )

    with pytest.raises(ValidationError, match="must differ from ADMIN_API_KEY"):
        Settings(
            ENVIRONMENT="development",
            ADMIN_API_KEY="shared-secret",
            GOVERNANCE_COUNCIL_API_KEYS={"member-1": "shared-secret"},
        )
