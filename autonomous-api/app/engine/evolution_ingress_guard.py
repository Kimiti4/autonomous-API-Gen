"""Evolution ingress enforcement (Checkpoint 057 / CP067-W09)."""
from __future__ import annotations

from fastapi import HTTPException

from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    assert_trusted_evolution_ingress,
)
from tiannara.application.governance.production_boundary import governed_production_enabled


class EvolutionIngressDenied(ValueError):
    """Raised when evolution attempts a forbidden governed-product action."""


def enforce_evolution_request_scope(*, claim_governed_product_lifecycle: bool) -> None:
    try:
        assert_trusted_evolution_ingress(
            claim_governed_product_lifecycle=claim_governed_product_lifecycle,
        )
    except ImplirIngressBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def assert_evolution_promotion_allowed() -> None:
    """Block evolution-driven promotion when governed production is active."""
    if governed_production_enabled():
        raise EvolutionIngressDenied(
            "evolution-promotion-blocked-in-governed-production-use-orchestration-authority"
        )


def evolution_response_metadata() -> dict[str, str | bool]:
    return {
        "governedFullStackLifecycle": False,
        "orchestrationAuthorityRequiredForProduct": governed_production_enabled(),
        "ingressClass": "subordinate_evolution",
    }
