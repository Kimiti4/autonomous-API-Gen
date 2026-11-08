"""Explicit bridge contracts (ADR-R1-03, R1-W06 / R1-W07)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ADR_R1_03_MINIMUM_BRIDGE_IDS: tuple[str, ...] = (
    "B-03",
    "B-04",
    "B-07",
    "B-08",
    "B-09",
)


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
    verification_method: str
    failure_behavior: str
    notes: str


B03_SYNTHESIS_TO_ISR = TransformationContract(
    bridge_id="B-03",
    source_family="reqgraph.synthesis.engineering_synthesizer",
    destination_family="isr.core.revision.ISRRevision",
    lossiness=LossinessClass.LOSSY_EXPLICIT,
    contract_version="1.0.0",
    preserved_axes=(
        "operation_ids",
        "security policy binding",
        "validation obligations",
        "synthesis provenance",
    ),
    lossy_axes=(
        "TOR-hash operation naming",
        "requirement node materialization",
        "non-synthesized graph topology",
    ),
    trusted_compile_allowed=True,
    verification_method="synthesis-obligation-preservation-v1",
    failure_behavior="FAIL_CLOSED",
    notes="Synthesized ISR digest differs from human fixtures; CP065 obligation slice required.",
)

B04_ISR_TO_PLAN = TransformationContract(
    bridge_id="B-04",
    source_family="isr.core.revision.ISRRevision",
    destination_family="compiler.core.plan.CompilationPlan",
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
    verification_method="b04-obligation-diff-verifier-v1",
    failure_behavior="FAIL_CLOSED",
    notes="Lowering is explicit; plan_binding_gate binds exact ISR digest at execution.",
)

B07_CONSTITUTIONAL_TO_CORE = TransformationContract(
    bridge_id="B-07",
    source_family="constitutional_architecture.isr.model.ISR",
    destination_family="isr.core.revision.ISRRevision",
    lossiness=LossinessClass.UNSUPPORTED_FAIL_CLOSED,
    contract_version="1.0.0",
    preserved_axes=(),
    lossy_axes=("all structural semantics",),
    trusted_compile_allowed=False,
    verification_method="cross-domain-digest-substitution-forbidden-v1",
    failure_behavior="FAIL_CLOSED",
    notes="No governed equivalence bridge; matching digests must not substitute across domains.",
)

B08_REQUIREMENTS_TO_ENGINEERING_ISR = TransformationContract(
    bridge_id="B-08",
    source_family="reqgraph.core.graph.RequirementGraph",
    destination_family="autonomous-api.app.engine.engineering_isr",
    lossiness=LossinessClass.LOSSY_EXPLICIT,
    contract_version="1.0.0",
    preserved_axes=("requirement refs", "explicit operation hints"),
    lossy_axes=("heuristic projection", "unregistered obligation carriers"),
    trusted_compile_allowed=False,
    verification_method="engineering-isr-projection-heuristic-v1",
    failure_behavior="FAIL_CLOSED",
    notes="Trusted orchestration uses Model C ImplIR path; EngISR heuristic not in certification path.",
)

B09_ENGINEERING_ISR_TO_IMPLIR = TransformationContract(
    bridge_id="B-09",
    source_family="autonomous-api.app.engine.engineering_isr",
    destination_family="autonomous-api.app.engine.implementation_ir",
    lossiness=LossinessClass.UNSUPPORTED_FAIL_CLOSED,
    contract_version="1.0.0",
    preserved_axes=(),
    lossy_axes=("authZ", "effects", "durable execution obligations"),
    trusted_compile_allowed=False,
    verification_method="implir-ingress-oracle-v1",
    failure_behavior="FAIL_CLOSED",
    notes="Parallel API path; governed production uses Model C trusted ingress guards (CP067-R4/R8).",
)


BRIDGE_REGISTRY: dict[str, TransformationContract] = {
    B03_SYNTHESIS_TO_ISR.bridge_id: B03_SYNTHESIS_TO_ISR,
    B04_ISR_TO_PLAN.bridge_id: B04_ISR_TO_PLAN,
    B07_CONSTITUTIONAL_TO_CORE.bridge_id: B07_CONSTITUTIONAL_TO_CORE,
    B08_REQUIREMENTS_TO_ENGINEERING_ISR.bridge_id: B08_REQUIREMENTS_TO_ENGINEERING_ISR,
    B09_ENGINEERING_ISR_TO_IMPLIR.bridge_id: B09_ENGINEERING_ISR_TO_IMPLIR,
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
    if contract.lossiness is LossinessClass.UNSUPPORTED_FAIL_CLOSED:
        raise ValueError(f"bridge-unsupported-fail-closed:{bridge_id}")
    return contract
