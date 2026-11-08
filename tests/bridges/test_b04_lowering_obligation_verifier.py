from __future__ import annotations

from certification.bridges.b04_lowering_obligation_verifier import (
    verify_b04_lowering_for_revision,
    verify_b04_lowering_obligations,
)
from certification.isr_independent_verification.b04_lowering_oracle import (
    INDEPENDENT_VERIFIER_B04,
    run_b04_lowering_oracle,
)
import pytest

from certification.isr_independent_verification.wave5_verification import R5_MULTI_WORKLOAD_SLICE
from certification.orchestration.workload_registry import get_workload_spec
from certification.payroll.candidate_fixture import payroll_isr_revision
from compiler.core.lowering import isr_to_plan


def test_payroll_b04_obligation_verifier_passes():
    revision = payroll_isr_revision()
    report = verify_b04_lowering_for_revision(revision)
    assert report.passed, report.findings
    assert "relowering-digest-stable" in report.preserved_evidence


def test_oracle_matches_verifier():
    revision = payroll_isr_revision()
    oracle = run_b04_lowering_oracle(revision)
    assert oracle.verifier_id == INDEPENDENT_VERIFIER_B04
    assert oracle.passed


@pytest.mark.parametrize("workload_id", R5_MULTI_WORKLOAD_SLICE)
def test_b04_multi_workload_obligations(workload_id: str):
    revision = get_workload_spec(workload_id).revision_fn()
    assert verify_b04_lowering_for_revision(revision).passed


def test_tampered_plan_fails_obligation_diff():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    tampered = plan.model_copy(update={"plan_id": "plan:deadbeefdeadbeef"})
    report = verify_b04_lowering_obligations(revision, tampered)
    assert not report.passed
    assert any("plan_id" in f for f in report.findings)
