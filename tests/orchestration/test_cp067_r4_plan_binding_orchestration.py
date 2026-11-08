"""Plan binding wired into canonical orchestration authority."""

from __future__ import annotations

from certification.orchestration.authority import run_canonical_full_stack
from certification.orchestration.contract import OrchestrationLifecycleState
from certification.orchestration.implir_ingress_guard import ImplirIngressBlocked
from certification.payroll.candidate_fixture import payroll_isr_revision
from compiler.core.lowering import isr_to_plan
from compiler.core.plan_binding import compute_plan_digest
import pytest


def test_orchestration_emits_plan_binding_digest(tmp_path):
    report = run_canonical_full_stack(
        "payroll",
        evidence_registry_path=str(tmp_path / "tev.jsonl"),
        governance_store_path=str(tmp_path / "gov"),
        orchestration_store_path=str(tmp_path / "orun"),
    )
    revision = payroll_isr_revision()
    expected = compute_plan_digest(isr_to_plan(revision))
    assert report.state is OrchestrationLifecycleState.AWAITING_GOVERNANCE
    assert report.plan_binding_digest == expected
    assert any("plan binding digest" in x.lower() for x in report.limitations)


def test_orchestration_rejects_implir_ingress_authority(tmp_path):
    with pytest.raises(ImplirIngressBlocked):
        run_canonical_full_stack(
            "payroll",
            evidence_registry_path=str(tmp_path / "tev.jsonl"),
            governance_store_path=str(tmp_path / "gov"),
            isr_ingress_authority="autonomous-api.implementation_ir",
        )
