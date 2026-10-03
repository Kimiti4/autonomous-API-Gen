"""Technology-neutral full-stack flow IR: control, data, async and failure semantics."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FlowNode:
    node_id: str
    layer: str
    operation: str


@dataclass(frozen=True)
class FlowEdge:
    source: str
    target: str
    mode: str  # sync, async, stream, event
    ordering: str = "unordered"
    delivery: str = "at-most-once"


@dataclass(frozen=True)
class FailureRecovery:
    failure_id: str
    trigger: str
    recovery: str
    retry_limit: int = 0
    idempotency_required: bool = False
    compensation: str | None = None


@dataclass(frozen=True)
class FlowIR:
    architecture_id: str
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    recoveries: tuple[FailureRecovery, ...] = ()
    consistency_boundaries: tuple[str, ...] = ()
    cancellation_rules: tuple[str, ...] = ()


def validate_flow(ir: FlowIR) -> tuple[str, ...]:
    errors = []
    ids = {n.node_id for n in ir.nodes}
    for e in ir.edges:
        if e.source not in ids:
            errors.append(f"missing-source:{e.source}")
        if e.target not in ids:
            errors.append(f"missing-target:{e.target}")
        if e.mode not in {"sync", "async", "stream", "event"}:
            errors.append(f"invalid-mode:{e.source}->{e.target}")
        if e.mode in {"async", "event"} and e.delivery != "at-most-once" and e.delivery not in {
            "at-least-once", "exactly-once"
        }:
            errors.append(f"invalid-delivery:{e.source}->{e.target}")
    for r in ir.recoveries:
        if r.retry_limit < 0:
            errors.append(f"negative-retry-limit:{r.failure_id}")
        if r.retry_limit > 0 and not r.idempotency_required:
            errors.append(f"retry-without-idempotency:{r.failure_id}")
    return tuple(errors)


def verify_flow_references(
    flow: FlowIR,
    architecture_id: str,
) -> tuple[str, ...]:
    return () if flow.architecture_id == architecture_id else ("architecture-id-mismatch",)
