"""Family-specific canonicalization contracts (ADR-R1-02, R1-W02 Tier A)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UnknownFieldPolicy(str, Enum):
    FAIL_CLOSED = "fail_closed"
    PRESERVE = "preserve"
    STRIP = "strip"


@dataclass(frozen=True, slots=True)
class CanonicalizationContract:
    """Versioned canonicalization metadata for one ISR family."""

    isr_family_id: str
    schema_versions_supported: tuple[str, ...]
    canonicalization_id: str
    canonicalization_version: str
    hash_algorithm: str
    authority_domain: str
    determinism_rules: tuple[str, ...]
    unknown_field_policy: UnknownFieldPolicy
    description: str


# Tier A — initially authorized in CP067-R3 / R1-W02
F01_ISR_REVISION = CanonicalizationContract(
    isr_family_id="isr.core.revision",
    schema_versions_supported=("1.0", "1.1"),
    canonicalization_id="isr.core.identity",
    canonicalization_version="1.0.0",
    hash_algorithm="sha256",
    authority_domain="isr.core.certification",
    determinism_rules=(
        "sorted-json-keys",
        "sorted-node-ids",
        "sorted-edge-ids",
        "utf-8",
        "compact-separators",
    ),
    unknown_field_policy=UnknownFieldPolicy.FAIL_CLOSED,
    description="ISRRevision content_hash via schema_version + ISRGraph canonical JSON",
)

F02_ISR_GRAPH = CanonicalizationContract(
    isr_family_id="isr.core.graph",
    schema_versions_supported=("1.0", "1.1"),
    canonicalization_id="isr.core.identity",
    canonicalization_version="1.0.0",
    hash_algorithm="sha256",
    authority_domain="isr.core.certification",
    determinism_rules=F01_ISR_REVISION.determinism_rules,
    unknown_field_policy=UnknownFieldPolicy.FAIL_CLOSED,
    description="Graph payload uses same bytes as F-01 hash input (graph portion)",
)

F04_COMPILATION_PLAN = CanonicalizationContract(
    isr_family_id="compiler.core.plan",
    schema_versions_supported=("1.0",),
    canonicalization_id="compiler.core.plan.canonical",
    canonicalization_version="1.0.0",
    hash_algorithm="sha256",
    authority_domain="compiler.execution",
    determinism_rules=("pydantic-json-dump", "sorted-json-keys", "compact-separators", "utf-8"),
    unknown_field_policy=UnknownFieldPolicy.FAIL_CLOSED,
    description="Frozen CompilationPlan model_dump canonical JSON",
)

F05_API_CONTRACT = CanonicalizationContract(
    isr_family_id="compiler.core.canonical_api_contract",
    schema_versions_supported=("1.0.0",),
    canonicalization_id="compiler.core.canonical_api_contract",
    canonicalization_version="1.0.0",
    hash_algorithm="sha256",
    authority_domain="compiler.execution",
    determinism_rules=("sorted-operations", "sorted-json-keys", "compact-separators"),
    unknown_field_policy=UnknownFieldPolicy.FAIL_CLOSED,
    description="CanonicalApiContract operations list digest payload",
)

_CONTRACTS: dict[str, CanonicalizationContract] = {
    F01_ISR_REVISION.isr_family_id: F01_ISR_REVISION,
    F02_ISR_GRAPH.isr_family_id: F02_ISR_GRAPH,
    F04_COMPILATION_PLAN.isr_family_id: F04_COMPILATION_PLAN,
    F05_API_CONTRACT.isr_family_id: F05_API_CONTRACT,
}


def get_canonicalization_contract(isr_family_id: str) -> CanonicalizationContract:
    try:
        return _CONTRACTS[isr_family_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown-isr-family-no-canonicalization-contract: {isr_family_id!r}"
        ) from exc


def registered_family_ids() -> tuple[str, ...]:
    return tuple(sorted(_CONTRACTS))
