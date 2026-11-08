"""Execution-time plan-to-ISR gate (R1-W04)."""

from __future__ import annotations

from compiler.core.plan import CompilationPlan
from compiler.core.plan_binding import (
    PlanBindingRecord,
    PlanBindingError,
    build_plan_binding_record,
    verify_plan_binding_record_matches,
)
from isr.core.revision import ISRRevision
from isr.core.revision_integrity import assert_revision_integrity_at_boundary


def assert_plan_binding_before_compile(
    revision: ISRRevision,
    plan: CompilationPlan,
    *,
    expected_plan_digest: str = "",
    recorded_binding: PlanBindingRecord | None = None,
    backend_id: str | None = None,
) -> PlanBindingRecord:
    """Mandatory gate immediately before compile on governed orchestration paths."""
    assert_revision_integrity_at_boundary(revision)
    binding = build_plan_binding_record(
        revision,
        plan,
        backend_id=backend_id or "python-fastapi",
    )
    if recorded_binding is not None:
        verify_plan_binding_record_matches(revision, plan, recorded_binding)
    if expected_plan_digest and expected_plan_digest != binding.plan_digest:
        raise PlanBindingError("plan-binding-digest-mismatch")
    return binding
