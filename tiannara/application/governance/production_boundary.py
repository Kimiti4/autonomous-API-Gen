"""Production vs legacy development trust boundary selection."""

from __future__ import annotations

import os

from constitutional_architecture.governance.candidate_promotion_lifecycle import (
    GOVERNANCE_CANDIDATE_STORE_ENV,
    GovernedCandidatePromotionService,
    open_governed_promotion_service,
)
from constitutional_architecture.governance.trusted_evidence_resolution import (
    GovernedTrustedEvidenceService,
    TrustBoundary,
    TRUSTED_EVIDENCE_LEDGER_ENV,
)

ESAP_GOVERNED_PRODUCTION_ENV = "ESAP_GOVERNED_PRODUCTION"


def governed_production_enabled() -> bool:
    explicit = os.getenv(ESAP_GOVERNED_PRODUCTION_ENV, "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    return bool(
        os.getenv(TRUSTED_EVIDENCE_LEDGER_ENV, "").strip()
        and os.getenv(GOVERNANCE_CANDIDATE_STORE_ENV, "").strip()
    )


def default_trust_boundary() -> TrustBoundary:
    return (
        TrustBoundary.PRODUCTION
        if governed_production_enabled()
        else TrustBoundary.LEGACY_DEVELOPMENT
    )


def open_production_evidence_service() -> GovernedTrustedEvidenceService:
    svc = GovernedTrustedEvidenceService.require_for_boundary(TrustBoundary.PRODUCTION)
    if svc is None:
        raise ValueError("trusted-evidence-ledger-unconfigured")
    return svc


def open_production_promotion_service() -> GovernedCandidatePromotionService:
    return open_governed_promotion_service()
