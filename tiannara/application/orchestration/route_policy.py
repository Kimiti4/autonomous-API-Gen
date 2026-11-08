"""Production entry-point routing policy (Checkpoint 056)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IngressClass(str, Enum):
    GOVERNED_FULL_STACK = "governed_full_stack"
    AUTHORIZED_SPECIALIST = "authorized_specialist"
    DEVELOPMENT_ONLY = "development_only"
    READ_ONLY = "read_only"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ProductionRoutePolicy:
    route_pattern: str
    service: str
    ingress_class: IngressClass
    canonical_authority_required: bool
    may_claim_product_lifecycle: bool
    notes: str = ""


PRODUCTION_ROUTE_POLICIES: tuple[ProductionRoutePolicy, ...] = (
    ProductionRoutePolicy(
        "POST /api/v1/orchestration/full-stack/run",
        "autonomous-api",
        IngressClass.GOVERNED_FULL_STACK,
        canonical_authority_required=True,
        may_claim_product_lifecycle=False,
        notes="Stages only; stops at AWAITING_GOVERNANCE",
    ),
    ProductionRoutePolicy(
        "GET /api/v1/orchestration/ingress-status",
        "autonomous-api",
        IngressClass.READ_ONLY,
        canonical_authority_required=False,
        may_claim_product_lifecycle=False,
    ),
    ProductionRoutePolicy(
        "POST /api/v1/evolve/*",
        "autonomous-api",
        IngressClass.DEVELOPMENT_ONLY,
        canonical_authority_required=False,
        may_claim_product_lifecycle=False,
        notes="Genetic evolution compile; subordinate to canonical full-stack",
    ),
    ProductionRoutePolicy(
        "POST /api/v1/publication/publish",
        "autonomous-api",
        IngressClass.AUTHORIZED_SPECIALIST,
        canonical_authority_required=False,
        may_claim_product_lifecycle=False,
        notes="Publication of pre-staged certified candidates only",
    ),
    ProductionRoutePolicy(
        "GET /api/v1/observation/*",
        "autonomous-api",
        IngressClass.READ_ONLY,
        canonical_authority_required=False,
        may_claim_product_lifecycle=False,
    ),
    ProductionRoutePolicy(
        "tiannara full-stack run",
        "tiannara-cli",
        IngressClass.GOVERNED_FULL_STACK,
        canonical_authority_required=True,
        may_claim_product_lifecycle=False,
    ),
    ProductionRoutePolicy(
        "tiannara create|factory",
        "tiannara-cli",
        IngressClass.DEVELOPMENT_ONLY,
        canonical_authority_required=False,
        may_claim_product_lifecycle=False,
    ),
    ProductionRoutePolicy(
        "POST /v1/product-factory/build",
        "product_factory",
        IngressClass.UNSUPPORTED,
        canonical_authority_required=False,
        may_claim_product_lifecycle=True,
        notes="Not mounted in autonomous-api main; disconnected",
    ),
)


def policies_summary() -> list[dict[str, str | bool]]:
    return [
        {
            "route": p.route_pattern,
            "service": p.service,
            "ingressClass": p.ingress_class.value,
            "canonicalAuthorityRequired": p.canonical_authority_required,
            "mayClaimProductLifecycle": p.may_claim_product_lifecycle,
            "notes": p.notes,
        }
        for p in PRODUCTION_ROUTE_POLICIES
    ]
