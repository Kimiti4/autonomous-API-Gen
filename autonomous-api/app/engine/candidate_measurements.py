"""Execute measurable candidate experiments and return observed metrics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Any, Sequence
from .fullstack_genome import FullStackGenome
from .pareto_architecture import Objective


MeasurementRunner = Callable[[FullStackGenome, Mapping[str, Any]], Mapping[str, float | int | bool | str]]


@dataclass(frozen=True)
class ObservedMeasurement:
    objective: str
    value: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CandidateMeasurementResult:
    architecture_id: str
    measurements: tuple[ObservedMeasurement, ...]
    evidence: tuple[str, ...]


def execute_candidate_measurements(
    architecture_id: str,
    genome: FullStackGenome,
    objectives: Sequence[Objective],
    runners: Mapping[str, MeasurementRunner],
    context: Mapping[str, Any],
) -> CandidateMeasurementResult:
    if not architecture_id:
        raise ValueError("measurement-requires-architecture-id")
    if not objectives:
        raise ValueError("measurement-requires-objectives")

    observations = []
    evidence = set()
    for objective in objectives:
        objective.validate()
        runner = runners.get(objective.name)
        if runner is None:
            raise ValueError("missing-measurement-runner:" + objective.name)
        raw = runner(genome, context)
        value = raw.get(objective.name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("measurement-runner-nonnumeric:" + objective.name)
        runner_evidence = raw.get("_evidence")
        if not isinstance(runner_evidence, (tuple, list)) or not runner_evidence:
            raise ValueError("measurement-runner-missing-evidence:" + objective.name)
        ev = tuple(str(x) for x in runner_evidence)
        observations.append(ObservedMeasurement(objective.name, float(value), ev))
        evidence.update(ev)

    return CandidateMeasurementResult(
        architecture_id,
        tuple(observations),
        tuple(sorted(evidence)),
    )


def measurement_evidence_map(
    result: CandidateMeasurementResult,
) -> dict[str, tuple[float, tuple[str, ...]]]:
    return {
        m.objective: (m.value, m.evidence)
        for m in result.measurements
    }
