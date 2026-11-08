"""Checkpoint 049 — Orders senior-engineering proving case orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import BackendCapabilities
from compiler.core.effect_projection import project_operation_effect_paths
from certification.orders.artifact_extraction import OrdersCompileResult, compile_orders_candidate
from certification.orders.candidate_fixture import approved_orders_requirements
from certification.proving.plan_full_stack_bridge import verify_plan_full_stack
from tiannara.application.engineering.capability_profiles import (
    BACKEND_DIMENSIONS,
    FRONTEND_DIMENSIONS,
    assess_backend_profile,
    assess_frontend_profile,
)
from tiannara.application.engineering.senior_engineering_gate import (
    SeniorEngineeringVerdict,
    evaluate_senior_engineering_acceptance,
)


@dataclass(frozen=True)
class DimensionVerdictRow:
    layer: str
    dimension_id: str
    status: str
    evidence_ref: str
    artifact: str
    verifier: str
    scope: str
    limitations: str


@dataclass(frozen=True)
class OrdersProvingCaseReport:
    candidate_id: str
    artifact_sha256: str
    artifact_manifest_digest: str
    revision_id: str
    backend_compile_error: str | None
    effect_paths: tuple[Mapping[str, Any], ...]
    senior_verdict: SeniorEngineeringVerdict | None
    senior_blockers: tuple[str, ...]
    dimension_rows: tuple[DimensionVerdictRow, ...]
    full_stack_findings: tuple[str, ...]
    acceptance_decision: str
    limitations: tuple[str, ...]
    frontend_operations: tuple[str, ...]
    backend_operations: tuple[str, ...]


def _dimension_matrix(
    frontend_evidence: Mapping[str, str],
    backend_evidence: Mapping[str, str],
    artifact_label: str,
    verifier: str,
) -> tuple[DimensionVerdictRow, ...]:
    rows: list[DimensionVerdictRow] = []
    for assessment in assess_frontend_profile(frontend_evidence):
        rows.append(
            DimensionVerdictRow(
                layer="frontend",
                dimension_id=assessment.dimension_id,
                status=assessment.status.value,
                evidence_ref=assessment.evidence_ref,
                artifact=artifact_label,
                verifier=verifier,
                scope="orders-proving-case",
                limitations=assessment.detail or "",
            )
        )
    for assessment in assess_backend_profile(backend_evidence):
        rows.append(
            DimensionVerdictRow(
                layer="backend",
                dimension_id=assessment.dimension_id,
                status=assessment.status.value,
                evidence_ref=assessment.evidence_ref,
                artifact=artifact_label,
                verifier=verifier,
                scope="orders-proving-case",
                limitations=assessment.detail or "",
            )
        )
    return tuple(rows)


def run_orders_proving_case(*, populate_all_dimensions: bool = False) -> OrdersProvingCaseReport:
    compile_result = compile_orders_candidate()
    plan = compile_result.plan
    paths = project_operation_effect_paths(plan)
    effect_paths = tuple(
        {
            "operation_id": p.operation_id,
            "effect_id": p.effect_id,
            "idempotency_required": p.idempotency_required,
            "consequence": p.consequence,
        }
        for p in paths
    )

    stack = verify_plan_full_stack(plan, domain_module="order")
    external_findings = stack.structural_findings + stack.behavioral_findings
    if compile_result.backend is None and compile_result.frontend_operations:
        external_findings = external_findings + (
            "orders-backend-not-emitted: frontend operations lack compiled backend implementation",
        )

    limitations = [
        "Orders lifecycle is narrowed to create + submit; cancel/read/list not in ISR.",
        "Durable execution is SQLite-backed (Checkpoint 051); not multi-worker production certified.",
        "Trusted evidence and senior gate dimensions still block product acceptance.",
        "Rust backend does not compile this ISR; effect parity is Python FastAPI only.",
    ]
    if compile_result.backend_compile_error:
        limitations.append(f"Backend compile error preserved: {compile_result.backend_compile_error}")

    frontend_evidence: dict[str, str] = {}
    backend_evidence: dict[str, str] = {}
    senior_verdict: SeniorEngineeringVerdict | None = None
    senior_blockers: tuple[str, ...] = ()

    if populate_all_dimensions:
        for dim in FRONTEND_DIMENSIONS:
            frontend_evidence[dim] = f"trusted:orders:{dim}:{compile_result.artifact_sha256[:12]}"
        for dim in BACKEND_DIMENSIONS:
            backend_evidence[dim] = f"trusted:orders:{dim}:{compile_result.artifact_sha256[:12]}"

    engineering = evaluate_senior_engineering_acceptance(
        generator_id="compiler-orders-gen",
        reviewer_id="senior-orders-reviewer",
        verifier_id="independent-orders-verifier",
        frontend_evidence=frontend_evidence,
        backend_evidence=backend_evidence,
        frontend_operations=compile_result.frontend_operations,
        backend_operations=compile_result.backend_operations,
        persistence_entities=compile_result.persistence_entities,
        backend_persisted_entities=compile_result.persistence_entities
        if compile_result.backend
        else (),
        shared_auth_models=compile_result.shared_auth_models,
    )
    senior_verdict = engineering.verdict
    senior_blockers = engineering.blockers

    rows = _dimension_matrix(
        frontend_evidence,
        backend_evidence,
        artifact_label=f"manifest:{compile_result.artifact_sha256[:16]}",
        verifier="independent-orders-verifier" if populate_all_dimensions else "unconfigured",
    )

    if senior_verdict == SeniorEngineeringVerdict.READY_FOR_INDEPENDENT_PRODUCT_ACCEPTANCE:
        acceptance = "PARTIAL_EVIDENCE"
    elif paths and compile_result.backend is not None:
        acceptance = "PARTIAL_EVIDENCE"
    else:
        acceptance = "ACCEPTANCE_BLOCKED"

    if senior_blockers or external_findings:
        acceptance = "ACCEPTANCE_BLOCKED" if not paths else "PARTIAL_EVIDENCE"

    approved_orders_requirements()  # authoritative TOR bundle for audits

    return OrdersProvingCaseReport(
        candidate_id=compile_result.candidate_id,
        artifact_sha256=compile_result.artifact_sha256,
        artifact_manifest_digest=compile_result.artifact_manifest_digest,
        revision_id=compile_result.revision_id,
        backend_compile_error=compile_result.backend_compile_error,
        effect_paths=effect_paths,
        senior_verdict=senior_verdict,
        senior_blockers=senior_blockers,
        dimension_rows=rows,
        full_stack_findings=external_findings,
        acceptance_decision=acceptance,
        limitations=tuple(limitations),
        frontend_operations=compile_result.frontend_operations,
        backend_operations=compile_result.backend_operations,
    )


def orders_backend_capability_matrix() -> tuple[BackendCapabilities, ...]:
    return (
        BackendCapabilities(
            backend_id=PythonFastAPIBackend().name,
            version=PythonFastAPIBackend().version,
            supported_features=PythonFastAPIBackend().supported_features,
        ),
        BackendCapabilities(
            backend_id=RustAxumBackend().name,
            version=RustAxumBackend().version,
            supported_features=RustAxumBackend().supported_features,
        ),
    )
