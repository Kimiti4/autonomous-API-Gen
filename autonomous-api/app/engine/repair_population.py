"""Feed verified repair candidates back into evolutionary architecture populations."""
from __future__ import annotations
from dataclasses import dataclass
from .verification_to_repair import VerificationRepairCandidate
from .evolution_population import EvolutionMember, ArchitectureLineage
from .pareto_architecture import ArchitectureScore, build_frontier


@dataclass(frozen=True)
class RepairLineage:
    repair_id: str
    source_architecture_id: str
    failed_gate_id: str
    counterexample_id: str


@dataclass(frozen=True)
class RepairPromotion:
    member: EvolutionMember
    lineage: RepairLineage


def promote_repair(
    source: EvolutionMember,
    candidate: VerificationRepairCandidate,
    repair_id: str,
    score: ArchitectureScore,
    generation: int,
) -> RepairPromotion:
    if generation <= source.lineage.generation:
        raise ValueError("repair-generation-must-increase")
    if not score.evidence:
        raise ValueError("repair-score-requires-evidence")
    if score.architecture_id != repair_id:
        raise ValueError("repair-score-id-mismatch")
    lineage = ArchitectureLineage(
        repair_id,
        (source.lineage.architecture_id,),
        generation,
        score.evidence,
    )
    return RepairPromotion(
        EvolutionMember(lineage, score),
        RepairLineage(
            repair_id,
            source.lineage.architecture_id,
            candidate.regression_gate_id,
            candidate.counterexample.counterexample.counterexample_id,
        ),
    )


def reintegrate_population(
    existing: tuple[EvolutionMember, ...],
    repair: EvolutionMember,
    objectives,
) -> tuple[EvolutionMember, ...]:
    if not existing:
        raise ValueError("population-requires-members")
    candidates = existing + (repair,)
    frontier = build_frontier(tuple(m.score for m in candidates), objectives)
    return tuple(
        m for m in candidates
        if m.lineage.architecture_id in frontier.frontier
    )
