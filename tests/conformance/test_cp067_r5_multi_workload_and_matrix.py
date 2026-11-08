"""CP067-R5 — multi-workload plan binding + W08 matrix catalog."""

from __future__ import annotations

from certification.isr_independent_verification.wave5_verification import (
    R5_MULTI_WORKLOAD_SLICE,
    run_multi_workload_plan_binding,
    run_wave5_independent_verification,
)
from certification.orchestration.ingress_trust_matrix import ingress_trust_matrix


def test_w08_matrix_has_governed_surfaces():
    rows = ingress_trust_matrix()
    assert len(rows) >= 3
    ids = {r.boundary_id for r in rows}
    assert "orch-api-full-stack" in ids
    assert "publication-publish" in ids


def test_multi_workload_plan_binding_payroll_orders_appointments():
    rows = run_multi_workload_plan_binding(R5_MULTI_WORKLOAD_SLICE)
    assert len(rows) == 3
    for row in rows:
        assert row.w04_passed, (row.workload_id, row.findings)


def test_wave5_integration_gate():
    report = run_wave5_independent_verification()
    assert report.w10_integration_passed
    assert report.w05_policy_passed
    assert not report.p0_closure
    assert report.cp068_admission == "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY"
    assert not report.findings
