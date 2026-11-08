"""W08 — ingress trust-boundary matrix (CP067-R5, planning + audit)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EnforcementStatus(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    PLANNED = "planned"


@dataclass(frozen=True, slots=True)
class IngressTrustRow:
    boundary_id: str
    entry_point: str
    mandatory_checks: tuple[str, ...]
    enforcement_module: str
    status: EnforcementStatus
    bypass_risk: str


def ingress_trust_matrix() -> tuple[IngressTrustRow, ...]:
    """Catalog of governed ingress surfaces (not exhaustive universal ISR)."""
    return (
        IngressTrustRow(
            "orch-api-full-stack",
            "POST /api/v1/orchestration/full-stack/run",
            (
                "identity",
                "isr_revision_digest",
                "plan_binding",
                "implir_model_c",
            ),
            "autonomous-api/app/api/orchestration_routes.py",
            EnforcementStatus.IMPLEMENTED,
            "dashboard parallel route",
        ),
        IngressTrustRow(
            "orch-dashboard-full-stack",
            "POST /api/v1/dashboard/orchestration/full-stack/run",
            ("identity", "isr_revision_digest", "plan_binding", "implir_model_c"),
            "autonomous-api/app/api/dashboard_orchestration_routes.py",
            EnforcementStatus.PARTIAL,
            "same gateway as API route",
        ),
        IngressTrustRow(
            "publication-publish",
            "POST /api/v1/publication/publish",
            ("identity", "isr_revision_authority_only", "implir_model_c"),
            "autonomous-api/app/api/publication_routes.py",
            EnforcementStatus.IMPLEMENTED,
            "503 if governed stores absent",
        ),
        IngressTrustRow(
            "orchestration-authority",
            "FullStackOrchestrationAuthority.run",
            (
                "digest_envelope",
                "plan_binding",
                "implir_model_c",
            ),
            "certification/orchestration/authority.py",
            EnforcementStatus.IMPLEMENTED,
            "CLI/programmatic bypass if caller skips authority",
        ),
    )


def matrix_boundary_ids() -> tuple[str, ...]:
    return tuple(row.boundary_id for row in ingress_trust_matrix())
