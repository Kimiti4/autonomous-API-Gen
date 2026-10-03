"""Rich technology-neutral frontend/backend architecture IRs."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FrontendState:
    state_id: str
    owner: str
    source: str
    consistency: str = "local"


@dataclass(frozen=True)
class FrontendInteraction:
    interaction_id: str
    trigger: str
    outcome: str
    states: tuple[str, ...] = ()
    accessibility_obligations: tuple[str, ...] = ()
    performance_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackendBoundary:
    boundary_id: str
    component: str
    authority: str
    trust_level: str
    concurrency_policy: str
    failure_policy: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataContract:
    contract_id: str
    direction: str
    schema_ref: str
    idempotency: str = "not_required"


@dataclass(frozen=True)
class FrontendIR:
    architecture_id: str
    components: tuple[str, ...]
    states: tuple[FrontendState, ...]
    interactions: tuple[FrontendInteraction, ...]
    consumed_contracts: tuple[DataContract, ...]
    invariants: tuple[str, ...]
    security_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackendIR:
    architecture_id: str
    boundaries: tuple[BackendBoundary, ...]
    contracts: tuple[DataContract, ...]
    invariants: tuple[str, ...]
    security_obligations: tuple[str, ...] = ()
    observability_obligations: tuple[str, ...] = ()


def validate_frontend_ir(ir: FrontendIR) -> tuple[str, ...]:
    errors = []
    ids = {c.contract_id for c in ir.consumed_contracts}
    for interaction in ir.interactions:
        if not interaction.outcome:
            errors.append(f"{interaction.interaction_id}:missing-outcome")
    if len(ids) != len(ir.consumed_contracts):
        errors.append("duplicate-contract-id")
    return tuple(errors)


def validate_backend_ir(ir: BackendIR) -> tuple[str, ...]:
    errors = []
    ids = {c.contract_id for c in ir.contracts}
    if len(ids) != len(ir.contracts):
        errors.append("duplicate-contract-id")
    for b in ir.boundaries:
        if not b.authority:
            errors.append(f"{b.boundary_id}:missing-authority")
        if not b.concurrency_policy:
            errors.append(f"{b.boundary_id}:missing-concurrency-policy")
    return tuple(errors)


def verify_cross_layer_contracts(
    frontend: FrontendIR,
    backend: BackendIR,
) -> tuple[str, ...]:
    errors = []
    if frontend.architecture_id != backend.architecture_id:
        errors.append("architecture-id-mismatch")
    backend_ids = {c.contract_id for c in backend.contracts}
    for c in frontend.consumed_contracts:
        if c.contract_id not in backend_ids:
            errors.append(f"missing-backend-contract:{c.contract_id}")
    for invariant in frontend.invariants:
        if invariant not in backend.invariants:
            errors.append(f"invariant-not-shared:{invariant}")
    return tuple(errors)
