"""Independent W05 Model C ingress matrix (trusted path policy)."""

from __future__ import annotations

from dataclasses import dataclass

from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    IsrIngressAuthority,
    assert_trusted_orchestration_ingress,
    assert_trusted_publication_ingress,
    mark_non_authoritative_provenance,
)

INDEPENDENT_VERIFIER_W05 = "certification.isr_independent_verification.implir_ingress_oracle.v1"


@dataclass(frozen=True)
class ImplirIngressOracleReport:
    verifier_id: str
    isr_revision_orchestration_ok: bool
    implir_orchestration_blocked: bool
    engisr_without_lineage_blocked: bool
    engisr_with_lineage_orchestration_ok: bool
    publication_implir_blocked: bool
    publication_engisr_blocked: bool
    non_authoritative_marker_ok: bool
    findings: tuple[str, ...]


def run_implir_ingress_oracle() -> ImplirIngressOracleReport:
    findings: list[str] = []
    flags = {k: False for k in (
        "isr_revision_orchestration_ok",
        "implir_orchestration_blocked",
        "engisr_without_lineage_blocked",
        "engisr_with_lineage_orchestration_ok",
        "publication_implir_blocked",
        "publication_engisr_blocked",
        "non_authoritative_marker_ok",
    )}

    try:
        assert_trusted_orchestration_ingress(IsrIngressAuthority.ISR_REVISION.value)
        flags["isr_revision_orchestration_ok"] = True
    except Exception as exc:
        findings.append(f"isr-rev-orch:{exc}")

    try:
        try:
            assert_trusted_orchestration_ingress(
                IsrIngressAuthority.IMPLEMENTATION_IR.value,
            )
            findings.append("implir-should-be-blocked")
        except ImplirIngressBlocked:
            flags["implir_orchestration_blocked"] = True
    except Exception as exc:
        findings.append(f"implir-orch:{exc}")

    try:
        try:
            assert_trusted_orchestration_ingress(
                IsrIngressAuthority.ENGINEERING_ISR.value,
            )
            findings.append("engisr-without-lineage-should-fail")
        except ImplirIngressBlocked:
            flags["engisr_without_lineage_blocked"] = True
    except Exception as exc:
        findings.append(f"engisr-no-lineage:{exc}")

    try:
        assert_trusted_orchestration_ingress(
            IsrIngressAuthority.ENGINEERING_ISR.value,
            governed_lineage_ref="isr.core.revision:test",
        )
        flags["engisr_with_lineage_orchestration_ok"] = True
    except Exception as exc:
        findings.append(f"engisr-lineage:{exc}")

    for auth, key in (
        (IsrIngressAuthority.IMPLEMENTATION_IR.value, "publication_implir_blocked"),
        (IsrIngressAuthority.ENGINEERING_ISR.value, "publication_engisr_blocked"),
    ):
        try:
            try:
                assert_trusted_publication_ingress(
                    auth,
                    governed_lineage_ref="isr.core.revision:test",
                )
                findings.append(f"publication-{auth}-should-fail")
            except ImplirIngressBlocked:
                flags[key] = True
        except Exception as exc:
            findings.append(f"pub-{auth}:{exc}")

    marked = mark_non_authoritative_provenance({})
    if marked.get("non_authoritative") is True:
        flags["non_authoritative_marker_ok"] = True
    else:
        findings.append("non-authoritative-marker-missing")

    return ImplirIngressOracleReport(
        verifier_id=INDEPENDENT_VERIFIER_W05,
        findings=tuple(findings),
        **flags,
    )
