"""R2.6 -- multi-objective fitness for candidate evaluation.

Fitness is a vector of named objectives, never collapsed to a scalar. Objectives
are lifted from the R2.5 CandidateGate verdict so gate-derived signals and
evolutionary signals (e.g. complexity) compose into one Pareto front.
"""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.evolution.candidate_gate import CandidateVerdict
from tiannara.application.evolution.mutation_operators import MutationCandidate


@dataclass(frozen=True)
class FitnessVector:
    objectives: tuple[tuple[str, float], ...]

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> "FitnessVector":
        return cls(tuple(sorted(values.items())))

    def get(self, name: str) -> float:
        return dict(self.objectives).get(name, 0.0)

    def dominates(self, other: "FitnessVector") -> bool:
        keys = set(self.objectives) | set(other.objectives)
        a = dict(self.objectives)
        b = dict(other.objectives)
        ge = all(a.get(k, 0.0) >= b.get(k, 0.0) for k in keys)
        gt = any(a.get(k, 0.0) > b.get(k, 0.0) for k in keys)
        return ge and gt


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: MutationCandidate
    verdict: CandidateVerdict
    fitness: FitnessVector
    feasible: bool

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate.candidate_id,
            "operator_id": self.candidate.operator_id,
            "feasible": self.feasible,
            "fitness": dict(self.fitness.objectives),
            "gate_results": [
                {"gate": r.gate_id, "passed": r.passed, "reason": r.reason}
                for r in self.verdict.gate_results
            ],
        }


def _gate_passed(verdict: CandidateVerdict, gate_id: str) -> float:
    return 1.0 if any(
        r.gate_id == gate_id and r.passed for r in verdict.gate_results
    ) else 0.0


def compute_fitness(verdict: CandidateVerdict, candidate: MutationCandidate) -> FitnessVector:
    structural = 1.0 if (
        _gate_passed(verdict, "compile") and _gate_passed(verdict, "isr_validity")
    ) else 0.0
    complexity_efficiency = 1.0 / (1.0 + candidate.mutation_delta.size)
    return FitnessVector.from_dict(
        {
            "correctness": _gate_passed(verdict, "target_failure"),
            "regression_safety": _gate_passed(verdict, "regression"),
            "structural_validity": structural,
            "causal_validity": _gate_passed(verdict, "causal"),
            "invariant_compliance": _gate_passed(verdict, "invariant"),
            "complexity_efficiency": round(complexity_efficiency, 6),
        }
    )
