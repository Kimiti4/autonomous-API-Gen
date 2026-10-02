"""CAP-001 technology-neutral engineering ISR projection.

Only normalized engineering semantics are projected downstream. No framework,
database, cloud provider, language or deployment product may enter this layer.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .requirement_ir import RequirementGraph, RequirementKind


@dataclass(frozen=True)
class EngineeringEntity:
    entity_id: str
    source_requirements: tuple[str, ...]
    kind: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"entity_id": self.entity_id, "source_requirements": list(self.source_requirements),
                "kind": self.kind, "name": self.name}


@dataclass(frozen=True)
class EngineeringInvariant:
    invariant_id: str
    statement: str
    source_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"invariant_id": self.invariant_id, "statement": self.statement,
                "source_requirements": list(self.source_requirements)}


@dataclass(frozen=True)
class EngineeringPolicy:
    policy_id: str
    statement: str
    source_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "statement": self.statement,
                "source_requirements": list(self.source_requirements)}


@dataclass(frozen=True)
class EngineeringInterface:
    interface_id: str
    statement: str
    source_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"interface_id": self.interface_id, "statement": self.statement,
                "source_requirements": list(self.source_requirements)}


@dataclass(frozen=True)
class EngineeringISR:
    schema_version: str
    source_requirement_ids: tuple[str, ...]
    entities: tuple[EngineeringEntity, ...]
    invariants: tuple[EngineeringInvariant, ...]
    policies: tuple[EngineeringPolicy, ...]
    interfaces: tuple[EngineeringInterface, ...]
    traceability: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "authority": "requirements-derived-engineering-isr",
            "source_requirement_ids": list(self.source_requirement_ids),
            "entities": [x.to_dict() for x in self.entities],
            "invariants": [x.to_dict() for x in self.invariants],
            "policies": [x.to_dict() for x in self.policies],
            "interfaces": [x.to_dict() for x in self.interfaces],
            "traceability": self.traceability,
        }


def project_to_isr(graph: RequirementGraph) -> EngineeringISR:
    """Project a validated requirement graph into neutral engineering semantics.

    Blocking errors make projection impossible. Warnings are retained in the
    source graph and never converted into certainty.
    """
    issues = graph.validate()
    if any(i.severity == "error" for i in issues):
        raise ValueError("cannot project invalid requirements into ISR")

    entities: list[EngineeringEntity] = []
    invariants: list[EngineeringInvariant] = []
    policies: list[EngineeringPolicy] = []
    interfaces: list[EngineeringInterface] = []

    for req in graph.requirements.values():
        rid = req.requirement_id
        statement = req.statement.strip()
        lower = statement.lower()

        # Entity extraction is conservative: only explicit domain nouns are
        # accepted through tags such as entity:Wallet; no guessed entities.
        for tag in req.tags:
            if tag.startswith("entity:") and tag[7:].strip():
                name = tag[7:].strip()
                entities.append(EngineeringEntity(f"E-{rid}-{name}", (rid,), "entity", name))

        if req.kind in (RequirementKind.SECURITY, RequirementKind.CONSTRAINT):
            policies.append(EngineeringPolicy(f"P-{rid}", statement, (rid,)))

        if any(token in lower for token in ("must not", "cannot", "exactly once", "only once", "never")):
            invariants.append(EngineeringInvariant(f"I-{rid}", statement, (rid,)))

        if any(token in lower for token in ("api", "endpoint", "request", "response", "interface")):
            interfaces.append(EngineeringInterface(f"IF-{rid}", statement, (rid,)))

    return EngineeringISR(
        "CAP-001-ISR.v1",
        tuple(graph.topological_order()),
        tuple(entities),
        tuple(invariants),
        tuple(policies),
        tuple(interfaces),
        graph.traceability(),
    )
