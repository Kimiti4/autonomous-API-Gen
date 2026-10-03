"""Specialized engineering mutation operators with verification requirements."""
from __future__ import annotations
from dataclasses import dataclass
from .architecture_mutation import ArchitectureMutation, domain_operator


@dataclass(frozen=True)
class EngineeringMutationSpec:
    mutation: ArchitectureMutation
    verification_properties: tuple[str, ...]
    risk_class: str


def _spec(mutation, properties, risk):
    if not properties:
        raise ValueError("mutation-requires-verification-properties")
    if risk not in {"low", "medium", "high", "critical"}:
        raise ValueError("invalid-risk-class")
    return EngineeringMutationSpec(mutation, properties, risk)


def frontend_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "frontend", paths, rationale, evidence, operator),
        ("accessibility", "interaction-consistency", "state-integrity"),
        "medium",
    )


def backend_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "backend", paths, rationale, evidence, operator),
        ("api-contract", "effect-safety", "failure-recovery"),
        "high",
    )


def data_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "data", paths, rationale, evidence, operator),
        ("data-integrity", "migration-safety", "traceability"),
        "high",
    )


def security_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "security", paths, rationale, evidence, operator),
        ("authorization", "trust-boundary", "auditability"),
        "critical",
    )


def operations_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "operations", paths, rationale, evidence, operator),
        ("observability", "recoverability", "failure-isolation"),
        "high",
    )


def fullstack_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "fullstack", paths, rationale, evidence, operator),
        ("cross-domain-contracts", "security", "operability", "end-to-end-flow"),
        "critical",
    )
