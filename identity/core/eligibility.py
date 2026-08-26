"""Production-eligibility classification for identity adapters.

A factor/authentication implementation may be structurally complete without
being production-eligible.  Eligibility is an explicit, checkable property —
never inferred.

Reference adapters (in-memory stores) are REFERENCE.
Production adapters (durable, encrypted, fail-closed) are PRODUCTION.
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class AuthEligibility(str, Enum):
    REFERENCE = "reference"
    PRODUCTION = "production"


class EligibilityCheck(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    passed: bool
    detail: str = ""


class ProductionEligibilityReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    eligible: bool
    checks: list[EligibilityCheck] = Field(default_factory=list)


def assess_production_eligibility(
    *,
    challenge_store: object,
    secret_store: object,
    session_store: object,
    provider_verifier: object,
    mfa_enforced: bool,
    recovery_single_use: bool,
) -> ProductionEligibilityReport:
    """Evaluate whether an identity stack is production-eligible.

    Each check probes a concrete property on the adapter object.
    Reference adapters declare durable=False / encrypts_at_rest=False;
    production adapters flip these to True.
    """
    checks = [
        EligibilityCheck(
            name="durable_challenge_state",
            passed=getattr(challenge_store, "durable", False),
            detail="challenges survive process restart",
        ),
        EligibilityCheck(
            name="secrets_encrypted_at_rest",
            passed=getattr(secret_store, "encrypts_at_rest", False),
            detail="secrets encrypted at rest",
        ),
        EligibilityCheck(
            name="durable_session_store",
            passed=getattr(session_store, "durable", False),
            detail="sessions survive process restart",
        ),
        EligibilityCheck(
            name="provider_fail_closed",
            passed=getattr(provider_verifier, "fail_closed", False),
            detail="provider verification fails closed on error",
        ),
        EligibilityCheck(
            name="mfa_enforced",
            passed=mfa_enforced,
            detail="MFA is enforced for all privileged operations",
        ),
        EligibilityCheck(
            name="recovery_single_use",
            passed=recovery_single_use,
            detail="recovery codes are single-use",
        ),
    ]
    return ProductionEligibilityReport(
        eligible=all(c.passed for c in checks),
        checks=checks,
    )
