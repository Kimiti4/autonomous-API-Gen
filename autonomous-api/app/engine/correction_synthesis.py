"""Counterexample-driven architectural correction synthesis."""
from __future__ import annotations
from dataclasses import dataclass
from .counterexample_analysis import MinimizedCounterexample


@dataclass(frozen=True)
class CorrectionCandidate:
    correction_id: str
    strategy: str
    changed_assumptions: tuple[str, ...]
    preserved_invariants: tuple[str, ...]
    new_risks: tuple[str, ...]
    rationale: tuple[str, ...]


def synthesize_corrections(
    counterexample: MinimizedCounterexample,
    assumptions: tuple[str, ...] = (),
) -> tuple[CorrectionCandidate, ...]:
    violations = counterexample.violated_invariants
    return (
        CorrectionCandidate(
            f"{counterexample.scenario_id}:guard",
            "strengthen-transition-guards",
            assumptions,
            violations,
            ("guard complexity",),
            ("prevent the minimal failing sequence at its transition boundary",),
        ),
        CorrectionCandidate(
            f"{counterexample.scenario_id}:serialize",
            "serialize-conflicting-effects",
            assumptions,
            violations,
            ("reduced concurrency",),
            ("prevent conflicting effects from racing",),
        ),
        CorrectionCandidate(
            f"{counterexample.scenario_id}:compensate",
            "add-compensation-or-recovery",
            assumptions,
            violations,
            ("recovery complexity",),
            ("restore invariants after the observed failure",),
        ),
    )


def classify_failure_scope(
    counterexample: MinimizedCounterexample,
    architectural_assumptions: tuple[str, ...],
) -> str:
    if not counterexample.violated_invariants:
        return "implementation-or-observation"
    if architectural_assumptions:
        return "architecture-or-implementation"
    return "implementation"
