"""Ordinary workload full-stack orchestration (Checkpoint 054/055)."""
from __future__ import annotations

from dataclasses import dataclass

from certification.ordinary.pipeline import OrdinaryCompileResult, compile_ordinary_candidate
from certification.ordinary.workloads import ORDINARY_WORKLOADS
from certification.product.product_acceptance import (
    ProductAcceptanceDecision,
)
from certification.proving.plan_full_stack_bridge import verify_plan_full_stack
from tiannara.application.engineering.senior_engineering_gate import (
    SeniorEngineeringVerdict,
    evaluate_senior_engineering_acceptance,
)


@dataclass(frozen=True)
class OrdinaryWorkloadReport:
    workload_id: str
    compile: OrdinaryCompileResult
    full_stack_passed: bool
    full_stack_findings: tuple[str, ...]
    senior_verdict: SeniorEngineeringVerdict
    senior_blockers: tuple[str, ...]
    product_acceptance: ProductAcceptanceDecision
    lifecycle_state: str | None
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]


def _workload_entry(workload_id: str):
    for entry in ORDINARY_WORKLOADS:
        if entry[0] == workload_id:
            return entry
    raise KeyError(f"unknown ordinary workload: {workload_id}")


def _ordinary_compile(workload_id: str) -> OrdinaryCompileResult:
    wid, cid, rev_fn, _ = _workload_entry(workload_id)
    return compile_ordinary_candidate(
        workload_id=wid,
        candidate_id=cid,
        revision_fn=rev_fn,
    )


def _report_from_canonical(workload_id: str, orch) -> OrdinaryWorkloadReport:
    compiled = _ordinary_compile(workload_id)
    limitations = tuple(
        dict.fromkeys(
            orch.limitations
            + (
                "Runtime browser E2E and live process execution are not invoked in the default orchestrator.",
            )
        )
    )
    return OrdinaryWorkloadReport(
        workload_id=workload_id,
        compile=compiled,
        full_stack_passed=orch.full_stack_passed,
        full_stack_findings=orch.full_stack_findings,
        senior_verdict=orch.senior_verdict,
        senior_blockers=orch.senior_blockers,
        product_acceptance=orch.product_acceptance,
        lifecycle_state=orch.governance_lifecycle_state,
        evidence_ids=orch.evidence_ids,
        limitations=limitations,
    )


def run_ordinary_workload(
    workload_id: str,
    *,
    evidence_registry_path: str | None = None,
    governance_store_path: str | None = None,
    orchestration_store_path: str | None = None,
) -> OrdinaryWorkloadReport:
    if evidence_registry_path and governance_store_path:
        from certification.orchestration.authority import run_canonical_full_stack

        orch = run_canonical_full_stack(
            workload_id,
            evidence_registry_path=evidence_registry_path,
            governance_store_path=governance_store_path,
            orchestration_store_path=orchestration_store_path,
        )
        return _report_from_canonical(workload_id, orch)

    wid, cid, rev_fn, _ = _workload_entry(workload_id)
    compiled = compile_ordinary_candidate(
        workload_id=wid,
        candidate_id=cid,
        revision_fn=rev_fn,
    )
    stack = verify_plan_full_stack(compiled.plan, domain_module=wid)
    findings = stack.structural_findings + stack.behavioral_findings

    senior = evaluate_senior_engineering_acceptance(
        generator_id=f"ordinary-{wid}-gen",
        reviewer_id="senior-ordinary-reviewer",
        verifier_id="independent-ordinary-verifier",
        frontend_evidence={},
        backend_evidence={},
        frontend_operations=compiled.frontend_operations,
        backend_operations=compiled.backend_operations,
        persistence_entities=compiled.persistence_entities,
        backend_persisted_entities=compiled.persistence_entities
        if compiled.backend_python
        else (),
        shared_auth_models=compiled.shared_auth_models,
        external_coherence_findings=findings,
    )
    limitations = [
        "Architecture ISR is workload-authored after TOR intake; automatic ISR synthesis from TOR alone is not proven.",
        "Governed evidence and governance paths were not configured; lifecycle staging skipped.",
    ]
    if any("FS-EFFECT-002" in f for f in findings):
        limitations.append(
            "FS-EFFECT-002: ordinary workloads lack bindable effect paths on all mutating APIs (PARTIAL full-stack evidence)."
        )
    product_acceptance = ProductAcceptanceDecision.ACCEPTANCE_BLOCKED
    if senior.verdict is SeniorEngineeringVerdict.PARTIAL_EVIDENCE:
        product_acceptance = ProductAcceptanceDecision.PARTIAL_EVIDENCE

    return OrdinaryWorkloadReport(
        workload_id=wid,
        compile=compiled,
        full_stack_passed=stack.passed,
        full_stack_findings=findings,
        senior_verdict=senior.verdict,
        senior_blockers=senior.blockers,
        product_acceptance=product_acceptance,
        lifecycle_state=None,
        evidence_ids=(),
        limitations=tuple(limitations),
    )


def run_all_ordinary_workloads(
    *,
    evidence_registry_path: str | None = None,
    governance_store_path: str | None = None,
    orchestration_store_path: str | None = None,
) -> tuple[OrdinaryWorkloadReport, ...]:
    return tuple(
        run_ordinary_workload(
            wid,
            evidence_registry_path=evidence_registry_path,
            governance_store_path=governance_store_path,
            orchestration_store_path=orchestration_store_path,
        )
        for wid, *_ in ORDINARY_WORKLOADS
    )
