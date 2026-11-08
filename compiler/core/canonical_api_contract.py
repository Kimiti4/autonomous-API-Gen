"""Authoritative API/security contract normalized from a CompilationPlan (Checkpoint 050)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from compiler.core.plan import CompilationPlan


@dataclass(frozen=True)
class CanonicalOperation:
    operation_id: str
    method: str
    path: str
    contract_id: str
    contract_version: str
    authorization_policy_ids: tuple[str, ...]
    idempotency_required: bool


@dataclass(frozen=True)
class CanonicalApiContract:
    contract_id: str
    contract_version: str
    auth_scheme: str | None
    operations: tuple[CanonicalOperation, ...]


def contract_id_for_plan(plan: CompilationPlan) -> str:
    return f"api:{plan.plan_id}"


def contract_version_for_plan(plan: CompilationPlan) -> str:
    return "1.0.0"


def build_canonical_api_contract(plan: CompilationPlan) -> CanonicalApiContract:
    """Single normalized contract identity consumed by frontend and backend emitters."""
    cid = contract_id_for_plan(plan)
    version = contract_version_for_plan(plan)
    auth_scheme = "bearer" if plan.security else None
    ops: list[CanonicalOperation] = []
    for api in plan.apis:
        if api.behavior is None:
            continue
        pol_ids = tuple(api.behavior.authorization_policy_ids)
        if api.security_policies and not pol_ids:
            pol_ids = tuple(p.policy_id for p in api.security_policies)
        idem = False
        ops.append(
            CanonicalOperation(
                operation_id=api.behavior.operation_id,
                method=api.behavior.method.upper(),
                path=api.behavior.path,
                contract_id=cid,
                contract_version=version,
                authorization_policy_ids=pol_ids,
                idempotency_required=idem,
            )
        )
    return CanonicalApiContract(
        contract_id=cid,
        contract_version=version,
        auth_scheme=auth_scheme,
        operations=tuple(sorted(ops, key=lambda item: (item.method, item.path, item.operation_id))),
    )


def contract_digest(contract: CanonicalApiContract) -> str:
    payload = {
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "auth_scheme": contract.auth_scheme,
        "operations": [
            {
                "operation_id": op.operation_id,
                "method": op.method,
                "path": op.path,
                "authorization_policy_ids": list(op.authorization_policy_ids),
                "idempotency_required": op.idempotency_required,
            }
            for op in contract.operations
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def frontend_api_invocations(plan: CompilationPlan) -> tuple[tuple[str, str], ...]:
    """Declared HTTP calls the frontend must make (method, path)."""
    keys: set[tuple[str, str]] = set()
    for route in plan.frontend_routes:
        for api in route.api_operations:
            if api.behavior is not None:
                keys.add((api.behavior.method.upper(), api.behavior.path))
        for interaction in route.interactions:
            target = interaction.target_api_operation
            if target is not None and target.behavior is not None:
                keys.add((target.behavior.method.upper(), target.behavior.path))
    return tuple(sorted(keys))


def frontend_ui_page_routes(plan: CompilationPlan) -> tuple[str, ...]:
    return tuple(
        sorted(
            route.behavior.path
            for route in plan.frontend_routes
            if route.behavior is not None
        )
    )


def _route_invokes_secured_api(route) -> bool:
    for api in route.api_operations:
        if api.behavior and api.behavior.authorization_policy_ids:
            return True
        if api.security_policies:
            return True
    for interaction in route.interactions:
        target = interaction.target_api_operation
        if target is None or target.behavior is None:
            continue
        if target.behavior.authorization_policy_ids or target.security_policies:
            return True
    return False


def apply_canonical_contract_defaults(plan: CompilationPlan) -> CompilationPlan:
    """Derive frontend security flags from the same contract that governs backend APIs."""
    if not plan.frontend_routes:
        return plan
    routes: list = []
    for route in plan.frontend_routes:
        if route.behavior is None:
            routes.append(route)
            continue
        needs_auth = _route_invokes_secured_api(route) or bool(plan.security)
        if needs_auth and not route.behavior.requires_auth:
            behavior = route.behavior.model_copy(update={"requires_auth": True})
            routes.append(route.model_copy(update={"behavior": behavior}))
        else:
            routes.append(route)
    return plan.model_copy(update={"frontend_routes": routes})


def validate_frontend_backend_invocations(
    plan: CompilationPlan,
) -> tuple[str, ...]:
    """Fail closed when frontend interactions reference operations outside the canonical contract."""
    contract = build_canonical_api_contract(plan)
    contract_keys = {(op.method, op.path) for op in contract.operations}
    problems: list[str] = []
    for method, path in frontend_api_invocations(plan):
        if (method, path) not in contract_keys:
            problems.append(
                f"contract-coherence: frontend invokes {method} {path} which is not in the canonical API contract"
            )
    return tuple(problems)


def manifest_json(contract: CanonicalApiContract) -> str:
    return json.dumps(
        {
            "schema": "tiannara.canonical-api-contract",
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "digest": contract_digest(contract),
            "auth_scheme": contract.auth_scheme,
            "operations": [
                {
                    "operation_id": op.operation_id,
                    "method": op.method,
                    "path": op.path,
                    "authorization_policy_ids": list(op.authorization_policy_ids),
                    "idempotency_required": op.idempotency_required,
                }
                for op in contract.operations
            ],
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
