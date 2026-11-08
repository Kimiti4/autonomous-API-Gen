"""CP067 §E family inventory — registered contracts vs explicit unsupported (R1-W02)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from isr.core.canonicalization_registry import registered_family_ids

CP067_FAMILY_COUNT = 17


class InventoryStatus(str, Enum):
    REGISTERED = "REGISTERED"
    UNSUPPORTED_FAIL_CLOSED = "UNSUPPORTED_FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class FamilyCanonicalizationEntry:
    cp067_family_code: str
    isr_family_id: str
    status: InventoryStatus
    notes: str


# Authoritative CP067 F-01 … F-17 inventory (no invented finding IDs).
CP067_FAMILY_CANONICALIZATION_INVENTORY: tuple[FamilyCanonicalizationEntry, ...] = (
    FamilyCanonicalizationEntry("F-01", "isr.core.revision", InventoryStatus.REGISTERED, "Tier A F-01"),
    FamilyCanonicalizationEntry("F-02", "isr.core.graph", InventoryStatus.REGISTERED, "Tier A F-02"),
    FamilyCanonicalizationEntry(
        "F-03", "reqgraph.core.graph", InventoryStatus.UNSUPPORTED_FAIL_CLOSED, "No contract v1"
    ),
    FamilyCanonicalizationEntry("F-04", "compiler.core.plan", InventoryStatus.REGISTERED, "Tier B F-04"),
    FamilyCanonicalizationEntry(
        "F-05",
        "compiler.core.canonical_api_contract",
        InventoryStatus.REGISTERED,
        "Tier B F-05",
    ),
    FamilyCanonicalizationEntry(
        "F-06",
        "constitutional_architecture.isr.model",
        InventoryStatus.REGISTERED,
        "Constitutional serializer domain",
    ),
    FamilyCanonicalizationEntry(
        "F-07",
        "constitutional_architecture.isr.eir",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "EIR canonical contract not ratified",
    ),
    FamilyCanonicalizationEntry(
        "F-08",
        "reqgraph.adapters.tor_isr",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "TOR projection digests partial only",
    ),
    FamilyCanonicalizationEntry(
        "F-09",
        "reqgraph.synthesis.engineering_synthesizer",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Defers to F-01 for hash; semantics lossy",
    ),
    FamilyCanonicalizationEntry(
        "F-10",
        "autonomous-api.app.engine.requirement_isr",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "EngineeringISR — no trusted digest",
    ),
    FamilyCanonicalizationEntry(
        "F-11",
        "autonomous-api.app.engine.implementation_ir",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Model C blocked at trusted ingress",
    ),
    FamilyCanonicalizationEntry(
        "F-12",
        "autonomous-api.app.engine.fullstack_architecture_ir",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "No canonical contract",
    ),
    FamilyCanonicalizationEntry(
        "F-13",
        "autonomous-api.app.engine.source_bound_full_stack",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Artifact hash only",
    ),
    FamilyCanonicalizationEntry(
        "F-14",
        "certification.evidence_graph.schema",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Graph slice F-01 only",
    ),
    FamilyCanonicalizationEntry(
        "F-15",
        "compiler.core.execution_contract",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Not ISR-bound in audit",
    ),
    FamilyCanonicalizationEntry(
        "F-16",
        "tiannara.application.hash_canonical",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Local hash_canonical; ISR relationship unknown",
    ),
    FamilyCanonicalizationEntry(
        "F-17",
        "certification.orchestration.store",
        InventoryStatus.UNSUPPORTED_FAIL_CLOSED,
        "Run metadata; not ISR body",
    ),
)


def inventory_registered_ids() -> frozenset[str]:
    return frozenset(
        e.isr_family_id
        for e in CP067_FAMILY_CANONICALIZATION_INVENTORY
        if e.status is InventoryStatus.REGISTERED
    )


def assert_inventory_aligned_with_registry() -> None:
    registered = set(registered_family_ids())
    inv_registered = inventory_registered_ids()
    if inv_registered != registered:
        raise ValueError(
            f"inventory-registry-mismatch: inv={sorted(inv_registered)} reg={sorted(registered)}"
        )


def inventory_complete() -> bool:
    return len(CP067_FAMILY_CANONICALIZATION_INVENTORY) == CP067_FAMILY_COUNT


def unsupported_family_ids() -> tuple[str, ...]:
    return tuple(
        sorted(
            e.isr_family_id
            for e in CP067_FAMILY_CANONICALIZATION_INVENTORY
            if e.status is InventoryStatus.UNSUPPORTED_FAIL_CLOSED
        )
    )
