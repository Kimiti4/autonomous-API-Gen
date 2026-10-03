"""Evidence-derived multi-objective fitness adapters."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EvidenceMetric:
    name: str
    value: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceFitness:
    metrics: Mapping[str, EvidenceMetric]

    def value(self, name: str) -> float:
        return self.metrics[name].value

    def evidence(self) -> tuple[str, ...]:
        return tuple(sorted({
            e for metric in self.metrics.values() for e in metric.evidence
        }))


def bounded(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError("metric-out-of-range")
    return value


def metric(name: str, value: float, evidence: tuple[str, ...]) -> EvidenceMetric:
    if not evidence:
        raise ValueError("metric-requires-evidence")
    return EvidenceMetric(name, bounded(value), evidence)


def from_observations(observations: Mapping[str, object]) -> EvidenceFitness:
    """Build metrics only from explicit observed values and evidence.

    Missing metrics remain absent; they are never silently treated as perfect.
    """
    metrics: dict[str, EvidenceMetric] = {}
    for name in (
        "correctness", "security", "performance",
        "resilience", "accessibility", "maintainability",
    ):
        raw = observations.get(name)
        evidence = tuple(observations.get(f"{name}_evidence", ()))
        if raw is not None and evidence:
            metrics[name] = metric(name, float(raw), evidence)
    return EvidenceFitness(metrics)


def require_complete_fitness(fitness: EvidenceFitness) -> None:
    required = {
        "correctness", "security", "performance",
        "resilience", "accessibility", "maintainability",
    }
    missing = sorted(required - set(fitness.metrics))
    if missing:
        raise ValueError("incomplete-evidence:" + ",".join(missing))
