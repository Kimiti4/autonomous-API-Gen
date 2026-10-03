"""Derive architecture scores strictly from execution and verification evidence."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from .dependency_reexecution import DependencyExecutionResult
from .repair_coevolution import RepairExecution
from .pareto_architecture import ArchitectureScore, Objective


@dataclass(frozen=True)
class EvidenceMeasurement:
    name: str
    value: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class DerivedArchitectureScore:
    score: ArchitectureScore
    measurements: tuple[EvidenceMeasurement, ...]


def derive_architecture_score(
    architecture_id: str,
    repairs: Sequence[RepairExecution],
    dependency_result: DependencyExecutionResult,
    objectives: Sequence[Objective],
    *,
    measurement_evidence: Mapping[str, tuple[float, tuple[str, ...]]],
) -> DerivedArchitectureScore:
    if not architecture_id:
        raise ValueError("score-requires-architecture-id")
    if not objectives:
        raise ValueError("score-requires-objectives")

    reports = [r.verification for r in repairs]
    reports.extend(x.verification for x in dependency_result.executions)
    if not reports:
        raise ValueError("score-requires-verification-reports")
    if any(not r.passed for r in reports):
        raise ValueError("score-requires-passing-verification")

    all_evidence = set()
    for report in reports:
        for gate in report.results:
            if not gate.evidence:
                raise ValueError("score-gate-requires-evidence:" + gate.property_name)
            all_evidence.update(gate.evidence)

    values = {}
    measurements = []
    for objective in objectives:
        objective.validate()
        raw = measurement_evidence.get(objective.name)
        if raw is None:
            raise ValueError("missing-measurement:" + objective.name)
        value, evidence = raw
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("measurement-not-numeric:" + objective.name)
        if not evidence:
            raise ValueError("measurement-requires-evidence:" + objective.name)
        if not set(evidence).issubset(all_evidence | set(evidence)):
            raise ValueError("measurement-evidence-invalid:" + objective.name)
        values[objective.name] = float(value)
        measurements.append(EvidenceMeasurement(objective.name, float(value), tuple(evidence)))
        all_evidence.update(evidence)

    return DerivedArchitectureScore(
        ArchitectureScore(architecture_id, values, tuple(sorted(all_evidence))),
        tuple(measurements),
    )
