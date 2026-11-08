"""Bridge CompilationPlan IR to autonomous-api ``verify_full_stack`` (Checkpoint 045/050)."""
from __future__ import annotations

from compiler.core.plan import CompilationPlan
from certification.proving.plan_full_stack_bridge import (
    BehavioralFullStackResult,
    verify_plan_full_stack,
)

import certification.payroll  # noqa: F401 — autonomous-api path bootstrap


def verify_payroll_plan_full_stack(plan: CompilationPlan) -> BehavioralFullStackResult:
    return verify_plan_full_stack(plan, domain_module="payroll")


def merged_coherence_findings(plan: CompilationPlan) -> tuple[str, ...]:
    result = verify_payroll_plan_full_stack(plan)
    return result.structural_findings + result.behavioral_findings
