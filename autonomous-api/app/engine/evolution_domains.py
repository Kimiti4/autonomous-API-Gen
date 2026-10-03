"""Domain-specific engineering evolution candidates.

Candidates are proposals only: selection/authorization remains outside this module.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Domain = Literal["frontend", "backend", "data", "security", "fullstack"]


@dataclass(frozen=True)
class EvolutionObservation:
    observation_id: str
    domain: Domain
    symptom: str
    evidence: tuple[str, ...]
    constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngineeringCandidate:
    candidate_id: str
    domain: Domain
    hypothesis: str
    changes: tuple[str, ...]
    expected_properties: tuple[str, ...]
    risks: tuple[str, ...]
    evidence_basis: tuple[str, ...]


def generate_candidates(
    observation: EvolutionObservation,
) -> tuple[EngineeringCandidate, ...]:
    base = observation.observation_id
    common = {
        "frontend": (
            ("FE-RESILIENCE", "Improve client recovery/state synchronization.",
             ("state-flow", "recovery", "cache")),
            ("FE-UX", "Reduce unnecessary interaction complexity.",
             ("interaction-flow", "accessibility", "error-recovery")),
        ),
        "backend": (
            ("BE-RESILIENCE", "Improve failure isolation and recovery.",
             ("timeouts", "retry-policy", "idempotency")),
            ("BE-CORRECTNESS", "Strengthen domain invariants.",
             ("transaction-boundary", "state-machine", "contract")),
        ),
        "data": (
            ("DATA-INTEGRITY", "Strengthen persistence correctness.",
             ("constraints", "migration", "reconciliation")),
            ("DATA-PERF", "Improve data access efficiency.",
             ("query-plan", "indexing", "batching")),
        ),
        "security": (
            ("SEC-AUTHZ", "Strengthen authorization and trust-boundary enforcement.",
             ("authorization", "object-boundary", "negative-tests")),
            ("SEC-REDUCE-ATTACK", "Reduce an evidenced attack surface.",
             ("input-validation", "boundary-analysis", "abuse-case-tests")),
        ),
        "fullstack": (
            ("FS-CONSISTENCY", "Improve cross-layer behavioral consistency.",
             ("api-contract", "state-flow", "e2e")),
        ),
    }[observation.domain]

    return tuple(
        EngineeringCandidate(
            f"{base}:{suffix}",
            observation.domain,
            hypothesis,
            changes,
            props,
            observation.constraints,
            observation.evidence,
        )
        for suffix, hypothesis, props in common
        for changes in (props,)
    )


def candidate_is_evidence_backed(candidate: EngineeringCandidate) -> bool:
    return bool(candidate.evidence_basis)
