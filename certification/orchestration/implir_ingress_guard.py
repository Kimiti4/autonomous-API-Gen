"""Model C — block trusted ingress for ImplementationIR-only sources (ADR-R1-05)."""

from __future__ import annotations

from enum import Enum


class IsrIngressAuthority(str, Enum):
    ISR_REVISION = "isr.core.revision"
    ENGINEERING_ISR = "engineering.isr"
    IMPLEMENTATION_IR = "autonomous-api.implementation_ir"


NON_AUTHORITATIVE_PROVENANCE_KEY = "non_authoritative"
NON_AUTHORITATIVE_IMPLIR_MARKER = "implementation_ir.non_authoritative.v1"


class ImplirIngressBlocked(ValueError):
    """Trusted orchestration/publication must not consume ImplIR-only authority."""


def mark_non_authoritative_provenance(provenance: dict) -> dict:
    """Tag isolated / ImplIR paths so they cannot impersonate certification authority."""
    out = dict(provenance)
    out[NON_AUTHORITATIVE_PROVENANCE_KEY] = True
    out["authority_marker"] = NON_AUTHORITATIVE_IMPLIR_MARKER
    return out


def assert_trusted_orchestration_ingress(
    ingress_authority: str,
    *,
    governed_lineage_ref: str = "",
) -> None:
    """Fail closed before governed full-stack orchestration."""
    try:
        authority = IsrIngressAuthority(ingress_authority)
    except ValueError as exc:
        raise ImplirIngressBlocked(
            f"trusted-orchestration-unknown-ingress:{ingress_authority!r}"
        ) from exc
    if authority is IsrIngressAuthority.IMPLEMENTATION_IR:
        raise ImplirIngressBlocked("trusted-orchestration-implir-blocked")
    if authority is IsrIngressAuthority.ENGINEERING_ISR and not governed_lineage_ref.strip():
        raise ImplirIngressBlocked(
            "trusted-orchestration-engineering-isr-missing-governed-lineage"
        )


def assert_trusted_publication_ingress(
    ingress_authority: str,
    *,
    governed_lineage_ref: str = "",
) -> None:
    """Fail closed before governed publication / promotion."""
    assert_trusted_orchestration_ingress(
        ingress_authority,
        governed_lineage_ref=governed_lineage_ref,
    )
    if ingress_authority != IsrIngressAuthority.ISR_REVISION.value:
        raise ImplirIngressBlocked(
            "trusted-publication-requires-isr-revision-authority"
        )


def assert_trusted_maintenance_ingress(
    ingress_authority: str,
    *,
    governed_lineage_ref: str,
    production_write_requested: bool,
) -> None:
    """Maintenance may record observations; production writes bind ISR revision only."""
    if not production_write_requested:
        return
    if ingress_authority == IsrIngressAuthority.IMPLEMENTATION_IR.value:
        raise ImplirIngressBlocked("trusted-maintenance-implir-blocked")
    if ingress_authority != IsrIngressAuthority.ISR_REVISION.value:
        raise ImplirIngressBlocked("trusted-maintenance-requires-isr-revision")
    if not governed_lineage_ref.strip():
        raise ImplirIngressBlocked("trusted-maintenance-missing-lineage-ref")


def assert_trusted_marketplace_ingress(
    ingress_authority: str,
    *,
    governed_lineage_ref: str = "",
) -> None:
    """Marketplace listing requires certification-grade ISR authority."""
    assert_trusted_publication_ingress(
        ingress_authority,
        governed_lineage_ref=governed_lineage_ref,
    )


def assert_trusted_evolution_ingress(
    *,
    ingress_authority: str = "",
    claim_governed_product_lifecycle: bool = False,
) -> None:
    """Evolution is subordinate; cannot claim full-stack lifecycle or ImplIR authority."""
    if claim_governed_product_lifecycle:
        raise ImplirIngressBlocked("evolution-cannot-claim-governed-full-stack-lifecycle")
    auth = ingress_authority.strip()
    if auth == IsrIngressAuthority.IMPLEMENTATION_IR.value:
        raise ImplirIngressBlocked("evolution-implir-authority-blocked")


def assert_trusted_factory_ingress(
    *,
    governed_production: bool,
    dev_subordinate_override: bool = False,
) -> None:
    """Factory/create CLI must not substitute for orchestration authority."""
    if dev_subordinate_override or not governed_production:
        return
    raise ImplirIngressBlocked("factory-create-blocked-under-governed-production")


W09_EXPANDED_BOUNDARIES: tuple[str, ...] = (
    "orchestration",
    "publication",
    "maintenance",
    "marketplace",
    "evolution",
    "factory_cli",
)
