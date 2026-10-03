"""Counterexample-guided mutation for full-stack evolution."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any, Callable
from .fullstack_genome import FullStackGenome
from .fullstack_mutation import compatibility_errors


@dataclass(frozen=True)
class Counterexample:
    counterexample_id: str
    domain: str
    violated_property: str
    evidence: tuple[str, ...]
    observations: Mapping[str, Any]


@dataclass(frozen=True)
class MutationHypothesis:
    hypothesis_id: str
    counterexample_id: str
    domain: str
    rationale: str
    target_properties: tuple[str, ...]


@dataclass(frozen=True)
class GuidedMutation:
    hypothesis: MutationHypothesis
    genome: FullStackGenome
    parent_id: str


def infer_mutation_hypothesis(
    counterexample: Counterexample,
) -> MutationHypothesis:
    return MutationHypothesis(
        hypothesis_id=f"repair:{counterexample.counterexample_id}",
        counterexample_id=counterexample.counterexample_id,
        domain=counterexample.domain,
        rationale=(
            f"Change {counterexample.domain} architecture to address "
            f"{counterexample.violated_property} using observed evidence."
        ),
        target_properties=(counterexample.violated_property,),
    )


def apply_guided_mutation(
    parent_id: str,
    genome: FullStackGenome,
    hypothesis: MutationHypothesis,
    mutator: Callable[[FullStackGenome], FullStackGenome],
) -> GuidedMutation:
    candidate = mutator(genome)
    errors = compatibility_errors(candidate)
    if errors:
        raise ValueError("invalid-guided-mutation:" + ";".join(errors))
    return GuidedMutation(hypothesis, candidate, parent_id)


def counterexample_resolved(
    counterexample: Counterexample,
    observations: Mapping[str, Any],
) -> bool:
    resolved = observations.get("resolved_properties", ())
    return counterexample.violated_property in set(resolved)


def require_resolution_evidence(
    counterexample: Counterexample,
    observations: Mapping[str, Any],
) -> tuple[str, ...]:
    if not counterexample_resolved(counterexample, observations):
        raise ValueError("counterexample-not-resolved")
    evidence = tuple(observations.get("evidence", ()))
    if not evidence:
        raise ValueError("resolution-requires-evidence")
    return evidence
