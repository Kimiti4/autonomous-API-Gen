"""Generic plan → verify_full_stack bridge (Checkpoint 048/049)."""
from __future__ import annotations

from dataclasses import dataclass

from compiler.core.canonical_api_contract import (
    build_canonical_api_contract,
    frontend_api_invocations,
    frontend_ui_page_routes,
)
from compiler.core.effect_projection import project_operation_effect_paths
from compiler.core.plan import CompilationPlan

import certification.orders  # noqa: F401 — autonomous-api bootstrap


@dataclass(frozen=True)
class BehavioralFullStackResult:
    structural_findings: tuple[str, ...]
    behavioral_findings: tuple[str, ...]
    passed: bool


def verify_plan_full_stack(plan: CompilationPlan, *, domain_module: str = "domain") -> BehavioralFullStackResult:
    from app.engine.api_ir import ApiContractIR, ApiOperation
    from app.engine.effect_coherence import EffectPath
    from app.engine.full_stack_verification import verify_full_stack
    from app.engine.implementation_ir import BackendIR, DataFlowIR, FrontendIR

    canonical = build_canonical_api_contract(plan)
    contract_id = canonical.contract_id
    projected_paths = project_operation_effect_paths(plan)
    operations: list[ApiOperation] = []
    idempotency_required = False
    for api in plan.apis:
        if api.behavior is None:
            continue
        pol_id = (
            api.behavior.authorization_policy_ids[0]
            if api.behavior.authorization_policy_ids
            else None
        )
        op_id = api.behavior.operation_id
        op_idem = any(
            path.operation_id == op_id and path.idempotency_required
            for path in projected_paths
        )
        idempotency_required = idempotency_required or op_idem
        operations.append(
            ApiOperation(
                operation_id=op_id,
                method=api.behavior.method,
                path=api.behavior.path,
                authorization_policy=pol_id,
                idempotency_required=op_idem,
            )
        )
    api_ir = ApiContractIR(
        schema_version="1.0.0",
        contract_id=contract_id,
        operations=tuple(operations),
        global_error_contract="problem+json",
        auth_scheme="bearer" if plan.security else None,
    )

    fe_ui = frontend_ui_page_routes(plan)
    fe_invocations = frontend_api_invocations(plan)
    fe_routes = fe_ui if fe_ui else fe_ui
    requires_fe_auth = any(
        r.behavior and r.behavior.requires_auth for r in plan.frontend_routes
    )
    secured_api = any(op.authorization_policy_ids for op in canonical.operations)
    fe_bounds: tuple[str, ...] = ()
    if requires_fe_auth or (canonical.auth_scheme and secured_api):
        fe_bounds = ("frontend-auth-required",)
    be_bounds = tuple(
        sorted(p.policy_id for p in plan.security if p.behavior is not None)
    )

    if projected_paths:
        frontend_flows = tuple(
            DataFlowIR(
                flow_id=path.frontend_flow_id,
                source=path.frontend_flow_id,
                destination=path.operation_id,
                contract=contract_id,
                failure_policy="surface-error",
            )
            for path in projected_paths
        )
    elif api_ir.operations:
        frontend_flows = (
            DataFlowIR(
                flow_id="primary-flow",
                source="frontend:primary",
                destination=api_ir.operations[0].operation_id,
                contract=contract_id,
                failure_policy="surface-error",
            ),
        )
    else:
        frontend_flows = ()

    frontend = FrontendIR(
        schema_version=canonical.contract_version,
        contract_id=f"frontend:{contract_id}",
        routes=fe_ui,
        ui_page_routes=fe_ui,
        api_invocations=fe_invocations,
        api_contract_id=contract_id,
        security_boundaries=fe_bounds,
        data_flows=frontend_flows,
    )
    persistence = tuple(m.entity_name for m in plan.data_models)
    observability: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()
    if idempotency_required:
        observability = ("durable-idempotency-store", "outbox-event-log")
        failure_modes = ("idempotency-replay-deduplication", "failure-injection-checkpoints")

    modules = tuple(
        sorted({path.domain_module for path in projected_paths} or {domain_module})
    )
    backend = BackendIR(
        schema_version="1.0.0",
        contract_id=f"backend:{contract_id}",
        domain_modules=modules,
        api_contract_id=contract_id,
        persistence_targets=persistence,
        security_boundaries=be_bounds,
        failure_modes=failure_modes,
        observability_requirements=observability,
    )

    structural: list[str] = []

    effects: tuple[EffectPath, ...] = tuple(
        EffectPath(
            operation_id=path.operation_id,
            frontend_flow_id=path.frontend_flow_id,
            domain_module=path.domain_module,
            effect_id=path.effect_id,
            authorization_boundary=path.authorization_boundary,
            consequence=path.consequence,
        )
        for path in projected_paths
    )

    report = verify_full_stack(frontend, api_ir, backend, effects, ())
    behavioral = tuple(
        f"{getattr(f, 'code', 'FS')}:{getattr(f, 'message', str(f))}"
        for f in report.findings
    )
    return BehavioralFullStackResult(
        structural_findings=tuple(structural),
        behavioral_findings=behavioral,
        passed=not structural and report.passed,
    )
