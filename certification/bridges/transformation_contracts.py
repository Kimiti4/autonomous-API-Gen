"""Explicit bridge contracts (ADR-R1-03, W06)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LossinessClass(str, Enum):
    LOSSLESS_VERIFIED = "LOSSLESS_VERIFIED"
    LOSSY_EXPLICIT = "LOSSY_EXPLICIT"
    UNSUPPORTED_FAIL_CLOSED = "UNSUPPORTED_FAIL_CLOSED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class TransformationContract:
    bridge_id: str
    source_family: str
    destination_family: str
    lossiness: LossinessClass
    contract_version: str
    preserved_axes: tuple[str, ...]
    lossy_axes: tuple[str, ...]
    trusted_compile_allowed: bool
    notes: str


B04_ISR_TO_PLAN = TransformationContract(
    bridge_id="B-04",
    source_family="isr.core.revision",
    destination_family="compiler.core.plan",
    lossiness=LossinessClass.LOSSY_EXPLICIT,
    contract_version="1.0.0",
    preserved_axes=(
        "revision_id",
        "content_hash",
        "behavior payloads",
        "security policy ids (lowered)",
    ),
    lossy_axes=(
        "graph topology detail",
        "requirement_ref materialization",
        "non-lowered node types",
    ),
    trusted_compile_allowed=True,
    notes="Lowering is explicit; plan_binding_gate binds exact ISR digest at execution.",
)


BRIDGE_REGISTRY: dict[str, TransformationContract] = {
    B04_ISR_TO_PLAN.bridge_id: B04_ISR_TO_PLAN,
}


def get_bridge_contract(bridge_id: str) -> TransformationContract:
    try:
        return BRIDGE_REGISTRY[bridge_id]
    except KeyError as exc:
        raise ValueError(f"unknown-bridge-contract:{bridge_id!r}") from exc


def assert_trusted_bridge_allowed(bridge_id: str) -> TransformationContract:
    contract = get_bridge_contract(bridge_id)
    if not contract.trusted_compile_allowed:
        raise ValueError(f"bridge-not-trusted:{bridge_id}")
    if contract.lossiness is LossinessClass.UNKNOWN:
        raise ValueError(f"bridge-lossiness-unknown:{bridge_id}")
    return contract
