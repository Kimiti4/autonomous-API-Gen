"""Causal/differential evaluation for counterexample-guided evolution."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class GenomeChange:
    path: str
    before: str
    after: str


@dataclass(frozen=True)
class DifferentialRun:
    baseline_id: str
    candidate_id: str
    changes: tuple[GenomeChange, ...]
    baseline_observations: Mapping[str, object]
    candidate_observations: Mapping[str, object]


@dataclass(frozen=True)
class CausalAssessment:
    counterexample_id: str
    resolved: bool
    regressions: tuple[str, ...]
    improved_properties: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    causal_confidence: str


def _failed_properties(obs: Mapping[str, object]) -> set[str]:
    return set(obs.get("failed_properties", ()))


def _resolved_properties(obs: Mapping[str, object]) -> set[str]:
    return set(obs.get("resolved_properties", ()))


def assess_differential(
    counterexample_id: str,
    violated_property: str,
    run: DifferentialRun,
) -> CausalAssessment:
    before_failures = _failed_properties(run.baseline_observations)
    after_failures = _failed_properties(run.candidate_observations)
    regressions = tuple(sorted(after_failures - before_failures))
    resolved = (
        violated_property in _resolved_properties(run.candidate_observations)
        and violated_property not in after_failures
    )

    improved = tuple(sorted(
        _resolved_properties(run.candidate_observations)
        - _resolved_properties(run.baseline_observations)
    ))
    evidence = tuple(sorted(set(
        run.candidate_observations.get("evidence", ())
    )))

    if not run.changes:
        confidence = "insufficient"
    elif resolved and not regressions and evidence:
        confidence = "supported"
    else:
        confidence = "insufficient"

    return CausalAssessment(
        counterexample_id=counterexample_id,
        resolved=resolved and not regressions,
        regressions=regressions,
        improved_properties=improved,
        supporting_evidence=evidence,
        causal_confidence=confidence,
    )


def require_generalization(
    related_runs: tuple[DifferentialRun, ...],
    violated_property: str,
) -> tuple[str, ...]:
    if not related_runs:
        raise ValueError("generalization-requires-related-runs")

    evidence: set[str] = set()
    for run in related_runs:
        failures = _failed_properties(run.candidate_observations)
        resolved = _resolved_properties(run.candidate_observations)
        if violated_property in failures or violated_property not in resolved:
            raise ValueError("generalization-not-demonstrated")
        evidence.update(run.candidate_observations.get("evidence", ()))

    if not evidence:
        raise ValueError("generalization-requires-evidence")
    return tuple(sorted(evidence))
