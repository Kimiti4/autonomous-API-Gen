"""R1-W04 plan-to-ISR binding — implementation tests (IV pending)."""

from __future__ import annotations

import pytest

from certification.orchestration.plan_binding_gate import (
    assert_plan_binding_before_compile,
)
from certification.payroll.candidate_fixture import payroll_isr_revision
from compiler.core.lowering import isr_to_plan
from compiler.core.plan_binding import (
    PlanBindingError,
    PlanBindingRecord,
    build_plan_binding_record,
    compute_plan_digest,
    verify_plan_binding_record_matches,
)


def test_plan_binding_record_full_digest_on_payroll():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    binding = build_plan_binding_record(revision, plan)
    assert len(binding.isr_content_digest) == 64
    assert len(binding.plan_digest) == 64
    assert binding.plan_digest == compute_plan_digest(plan)
    assert binding.isr_revision_id == revision.revision_id


def test_execution_gate_passes_fresh_lowering():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    binding = assert_plan_binding_before_compile(revision, plan)
    assert binding.plan_digest == compute_plan_digest(plan)


def test_gate_rejects_tampered_isr_digest():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    tampered = revision.model_copy(update={"content_hash": "a" * 64})
    with pytest.raises(Exception, match="revision-integrity|digest"):
        assert_plan_binding_before_compile(tampered, plan)


def test_gate_rejects_stale_record():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    record = build_plan_binding_record(revision, plan)
    other = revision.model_copy(update={"revision_id": "rev-stale"})
    with pytest.raises(PlanBindingError, match="stale-or-tampered"):
        verify_plan_binding_record_matches(other, plan, record)


def test_gate_rejects_wrong_expected_digest():
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    with pytest.raises(PlanBindingError, match="plan-binding-digest-mismatch"):
        assert_plan_binding_before_compile(
            revision,
            plan,
            expected_plan_digest="b" * 64,
        )


def test_record_rejects_weak_prefix_only_binding_as_digest():
    """plan_id may remain a 16-char surrogate; binding must carry full plan_digest."""
    revision = payroll_isr_revision()
    plan = isr_to_plan(revision)
    assert plan.plan_id == f"plan:{revision.content_hash[:16]}"
    record = build_plan_binding_record(revision, plan)
    assert record.plan_id == plan.plan_id
    assert record.plan_digest != record.plan_id.removeprefix("plan:")
