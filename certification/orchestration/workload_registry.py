"""Registered full-stack workloads (Checkpoint 055)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from compiler.core.plan import CompilationPlan
from isr.core.revision import ISRRevision
from reqgraph.core.graph import RequirementGraph

from certification.orchestration.contract import IsrProvenance
from certification.ordinary.pipeline import OrdinaryCompileResult, compile_ordinary_candidate
from certification.ordinary.workloads import ORDINARY_WORKLOADS
from certification.orders.artifact_extraction import OrdersCompileResult, compile_orders_candidate
from certification.payroll.artifact_extraction import PayrollCompileResult, compile_payroll_candidate
from certification.payroll.candidate_fixture import approved_payroll_requirements
from certification.payroll.full_stack_bridge import verify_payroll_plan_full_stack
from certification.proving.plan_full_stack_bridge import verify_plan_full_stack
from certification.orders.candidate_fixture import approved_orders_requirements


@dataclass(frozen=True)
class NormalizedCompile:
    candidate_id: str
    revision_id: str
    revision: ISRRevision
    plan: CompilationPlan
    artifact_sha256: str
    artifact_manifest_digest: str
    artifact_bytes: bytes
    frontend_operations: tuple[str, ...]
    backend_operations: tuple[str, ...]
    persistence_entities: tuple[str, ...]
    shared_auth_models: bool
    backend_present: bool
    frontend: object
    backend: object | None


@dataclass(frozen=True)
class VerifyOutcome:
    passed: bool
    findings: tuple[str, ...]


@dataclass(frozen=True)
class WorkloadSpec:
    workload_id: str
    isr_provenance: IsrProvenance
    revision_fn: Callable[[], ISRRevision]
    requirements_fn: Callable[[], RequirementGraph]
    compile_fn: Callable[[], NormalizedCompile]
    verify_fn: Callable[[CompilationPlan], VerifyOutcome]


def _norm_payroll() -> NormalizedCompile:
    r = compile_payroll_candidate()
    return _from_payroll(r)


def _norm_orders() -> NormalizedCompile:
    r = compile_orders_candidate()
    return _from_orders(r)


def _from_payroll(r: PayrollCompileResult) -> NormalizedCompile:
    return NormalizedCompile(
        candidate_id=r.candidate_id,
        revision_id=r.revision_id,
        revision=r.revision,
        plan=r.plan,
        artifact_sha256=r.artifact_sha256,
        artifact_manifest_digest=r.artifact_manifest_digest,
        artifact_bytes=r.artifact_bytes,
        frontend_operations=r.frontend_operations,
        backend_operations=r.backend_operations,
        persistence_entities=r.persistence_entities,
        shared_auth_models=r.shared_auth_models,
        backend_present=r.backend is not None,
        frontend=r.frontend,
        backend=r.backend,
    )


def _from_orders(r: OrdersCompileResult) -> NormalizedCompile:
    return NormalizedCompile(
        candidate_id=r.candidate_id,
        revision_id=r.revision_id,
        revision=r.revision,
        plan=r.plan,
        artifact_sha256=r.artifact_sha256,
        artifact_manifest_digest=r.artifact_manifest_digest,
        artifact_bytes=r.artifact_bytes,
        frontend_operations=r.frontend_operations,
        backend_operations=r.backend_operations,
        persistence_entities=r.persistence_entities,
        shared_auth_models=r.shared_auth_models,
        backend_present=r.backend is not None,
        frontend=r.frontend,
        backend=r.backend,
    )


def _from_ordinary(r: OrdinaryCompileResult) -> NormalizedCompile:
    return NormalizedCompile(
        candidate_id=r.candidate_id,
        revision_id=r.revision_id,
        revision=r.revision,
        plan=r.plan,
        artifact_sha256=r.artifact_sha256,
        artifact_manifest_digest=r.artifact_manifest_digest,
        artifact_bytes=r.artifact_bytes,
        frontend_operations=r.frontend_operations,
        backend_operations=r.backend_operations,
        persistence_entities=r.persistence_entities,
        shared_auth_models=r.shared_auth_models,
        backend_present=r.backend_python is not None,
        frontend=r.frontend,
        backend=r.backend_python,
    )


def _ordinary_factory(wid: str, cid: str, rev_fn):
    def _compile() -> NormalizedCompile:
        return _from_ordinary(
            compile_ordinary_candidate(workload_id=wid, candidate_id=cid, revision_fn=rev_fn)
        )
    return _compile


WORKLOAD_SPECS: dict[str, WorkloadSpec] = {
    "payroll": WorkloadSpec(
        workload_id="payroll",
        isr_provenance=IsrProvenance.HUMAN_AUTHORED_IMPORTED,
        revision_fn=__import__(
            "certification.payroll.candidate_fixture", fromlist=["payroll_isr_revision"]
        ).payroll_isr_revision,
        requirements_fn=approved_payroll_requirements,
        compile_fn=_norm_payroll,
        verify_fn=lambda plan: _verify_outcome(verify_payroll_plan_full_stack(plan)),
    ),
    "orders": WorkloadSpec(
        workload_id="orders",
        isr_provenance=IsrProvenance.HUMAN_AUTHORED_IMPORTED,
        revision_fn=__import__(
            "certification.orders.candidate_fixture", fromlist=["orders_isr_revision"]
        ).orders_isr_revision,
        requirements_fn=approved_orders_requirements,
        compile_fn=_norm_orders,
        verify_fn=lambda plan: _verify_outcome(verify_plan_full_stack(plan, domain_module="order")),
    ),
}

for _wid, _cid, _rev, _req in ORDINARY_WORKLOADS:
    WORKLOAD_SPECS[_wid] = WorkloadSpec(
        workload_id=_wid,
        isr_provenance=IsrProvenance.HUMAN_AUTHORED_IMPORTED,
        revision_fn=_rev,
        requirements_fn=_req,
        compile_fn=_ordinary_factory(_wid, _cid, _rev),
        verify_fn=lambda plan, w=_wid: _verify_outcome(
            verify_plan_full_stack(plan, domain_module=w)
        ),
    )


def _verify_outcome(stack) -> VerifyOutcome:
    findings = stack.structural_findings + stack.behavioral_findings
    return VerifyOutcome(passed=stack.passed, findings=findings)


ALL_WORKLOAD_IDS = tuple(WORKLOAD_SPECS.keys())


def get_workload_spec(workload_id: str) -> WorkloadSpec:
    if workload_id not in WORKLOAD_SPECS:
        raise KeyError(f"orchestration-unknown-workload:{workload_id}")
    return WORKLOAD_SPECS[workload_id]
