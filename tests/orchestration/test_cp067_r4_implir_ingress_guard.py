"""R1-W05 Model C — trusted ingress blocks ImplementationIR (IV pending)."""

from __future__ import annotations

import pytest

from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    IsrIngressAuthority,
    assert_trusted_orchestration_ingress,
    assert_trusted_publication_ingress,
    mark_non_authoritative_provenance,
)


def test_isr_revision_allowed_on_trusted_orchestration():
    assert_trusted_orchestration_ingress(IsrIngressAuthority.ISR_REVISION.value)


def test_implir_blocked_on_trusted_orchestration():
    with pytest.raises(ImplirIngressBlocked, match="implir-blocked"):
        assert_trusted_orchestration_ingress(
            IsrIngressAuthority.IMPLEMENTATION_IR.value,
        )


def test_engineering_isr_requires_governed_lineage():
    with pytest.raises(ImplirIngressBlocked, match="missing-governed-lineage"):
        assert_trusted_orchestration_ingress(
            IsrIngressAuthority.ENGINEERING_ISR.value,
        )
    assert_trusted_orchestration_ingress(
        IsrIngressAuthority.ENGINEERING_ISR.value,
        governed_lineage_ref="isr.core.revision:payroll-human",
    )


def test_publication_requires_isr_revision_even_with_lineage():
    with pytest.raises(ImplirIngressBlocked, match="requires-isr-revision"):
        assert_trusted_publication_ingress(
            IsrIngressAuthority.ENGINEERING_ISR.value,
            governed_lineage_ref="isr.core.revision:payroll-human",
        )


def test_non_authoritative_provenance_marker():
    marked = mark_non_authoritative_provenance({"source_refs": ["req-1"]})
    assert marked["non_authoritative"] is True
    assert "implementation_ir" in marked["authority_marker"]
