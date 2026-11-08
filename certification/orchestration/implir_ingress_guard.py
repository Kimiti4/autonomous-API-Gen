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
