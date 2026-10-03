"""Evidence-backed Pareto frontier for architectural trade-offs."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from .tradeoff_experiments import TradeoffAssessment


@dataclass(frozen=True)
class Objective:
    name: str
    direction: str  # maximize|minimize

    def validate(self) -> None:
        if self.direction not in {"maximize", "minimize"}:
            raise ValueError("invalid-objective-direction")


@dataclass(frozen=True)
class ArchitectureScore:
    architecture_id: str
    values: Mapping[str, float]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ParetoResult:
    frontier: tuple[str, ...]
    dominated: tuple[str, ...]


def dominates(
    left: ArchitectureScore,
    right: ArchitectureScore,
    objectives: Sequence[Objective],
) -> bool:
    better_or_equal = True
    strictly_better = False
    for objective in objectives:
        objective.validate()
        a = left.values.get(objective.name)
        b = right.values.get(objective.name)
        if a is None or b is None:
            raise ValueError("missing-objective-value")
        if objective.direction == "maximize":
            if a < b:
                better_or_equal = False
            if a > b:
                strictly_better = True
        else:
            if a > b:
                better_or_equal = False
            if a < b:
                strictly_better = True
    return better_or_equal and strictly_better


def build_frontier(
    scores: Sequence[ArchitectureScore],
    objectives: Sequence[Objective],
) -> ParetoResult:
    if not scores:
        raise ValueError("pareto-requires-architectures")
    if not objectives:
        raise ValueError("pareto-requires-objectives")
    for score in scores:
        if not score.evidence:
            raise ValueError("pareto-score-requires-evidence")

    dominated_ids = {
        right.architecture_id
        for right in scores
        if any(
            left.architecture_id != right.architecture_id
            and dominates(left, right, objectives)
            for left in scores
        )
    }
    frontier = tuple(
        score.architecture_id
        for score in scores
        if score.architecture_id not in dominated_ids
    )
    return ParetoResult(frontier, tuple(sorted(dominated_ids)))


def scores_from_assessments(
    assessments: Sequence[TradeoffAssessment],
    metric_map: Mapping[str, str],
) -> tuple[ArchitectureScore, ...]:
    result = []
    for assessment in assessments:
        values = {}
        for objective, metric in metric_map.items():
            raw = assessment.measurements.get(metric)
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                raise ValueError("pareto-metric-not-numeric")
            values[objective] = float(raw)
        result.append(
            ArchitectureScore(
                assessment.alternative_id,
                values,
                assessment.evidence,
            )
        )
    return tuple(result)
