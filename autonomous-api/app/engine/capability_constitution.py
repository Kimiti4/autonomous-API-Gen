"""Canonical senior-engineering capability constitution.

Technology-neutral vocabulary for engineering capabilities and their evidence
obligations. This module defines the contract; it does not manufacture
evidence or infer certification from code presence.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    description: str
    requirements: tuple[str, ...]
    architectural_obligations: tuple[str, ...]
    implementation_obligations: tuple[str, ...]
    verification_obligations: tuple[str, ...]
    security_obligations: tuple[str, ...]
    operational_obligations: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    backend_dependencies: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.capability_id.startswith("C"):
            raise ValueError("capability_id must use canonical Cxx form")
        if not self.description.strip():
            raise ValueError("description must not be empty")
        for name in (
            "requirements", "architectural_obligations",
            "implementation_obligations", "verification_obligations",
            "security_obligations", "operational_obligations",
            "evidence_requirements",
        ):
            values = getattr(self, name)
            if not values or any(not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty obligations")


@dataclass(frozen=True)
class CapabilityEvidence:
    capability_id: str
    requirement_results: Mapping[str, bool]
    architectural_results: Mapping[str, bool]
    implementation_results: Mapping[str, bool]
    verification_results: Mapping[str, bool]
    security_results: Mapping[str, bool]
    operational_results: Mapping[str, bool]
    evidence_results: Mapping[str, bool]

    def satisfies(self, definition: CapabilityDefinition) -> bool:
        groups = (
            (definition.requirements, self.requirement_results),
            (definition.architectural_obligations, self.architectural_results),
            (definition.implementation_obligations, self.implementation_results),
            (definition.verification_obligations, self.verification_results),
            (definition.security_obligations, self.security_results),
            (definition.operational_obligations, self.operational_results),
            (definition.evidence_requirements, self.evidence_results),
        )
        return all(
            all(results.get(item) is True for item in required)
            for required, results in groups
        )


def _cap(i: int, name: str, dep: str) -> CapabilityDefinition:
    """Create the canonical baseline contract for a capability domain."""
    return CapabilityDefinition(
        f"C{i:02d}",
        name,
        ("the capability requirement is explicit and traceable",),
        ("domain boundaries, constraints and invariants are explicit",),
        ("required behavior is implemented at the correct enforcement boundary",),
        ("required behavior is independently verified",),
        ("applicable security threats and controls are explicit",),
        ("applicable runtime behavior is observable and recoverable",),
        ("claim-to-source evidence is retained with provenance",),
        (dep,),
    )


_CAPABILITIES = (
    _cap(1, "Requirements engineering", "requirement-graph"),
    _cap(2, "Architecture", "architecture-backend"),
    _cap(3, "Backend engineering", "backend-compiler"),
    _cap(4, "API engineering", "api-compiler"),
    _cap(5, "Data engineering", "persistence-backend"),
    _cap(6, "Distributed systems", "distributed-runtime"),
    _cap(7, "Event-driven systems", "event-backend"),
    _cap(8, "Financial/transaction systems", "transaction-backend"),
    _cap(9, "Frontend engineering", "frontend-compiler"),
    _cap(10, "Security", "security-analyzer"),
    _cap(11, "Testing", "test-backend"),
    _cap(12, "Observability", "observability-backend"),
    _cap(13, "DevOps / CI/CD", "ci-backend"),
    _cap(14, "Cloud infrastructure", "cloud-backend"),
    _cap(15, "Performance engineering", "performance-harness"),
    _cap(16, "Reliability engineering", "reliability-harness"),
    _cap(17, "Production debugging", "production-observation"),
    _cap(18, "Documentation", "documentation-generator"),
    _cap(19, "System evolution", "evolution-engine"),
    _cap(20, "Engineering governance", "governance-runtime"),
)
_INDEX = {item.capability_id: item for item in _CAPABILITIES}


def capability_definitions() -> tuple[CapabilityDefinition, ...]:
    return _CAPABILITIES


def get_capability(capability_id: str) -> CapabilityDefinition:
    try:
        return _INDEX[capability_id]
    except KeyError as exc:
        raise KeyError(f"unknown capability: {capability_id}") from exc


def capability_matrix() -> dict[str, CapabilityDefinition]:
    return dict(_INDEX)


def certification_status(capability_id: str, evidence: CapabilityEvidence) -> str:
    definition = get_capability(capability_id)
    if evidence.capability_id != capability_id:
        raise ValueError("evidence capability_id does not match requested capability")
    return "CERTIFIED" if evidence.satisfies(definition) else "NOT_CERTIFIED"
