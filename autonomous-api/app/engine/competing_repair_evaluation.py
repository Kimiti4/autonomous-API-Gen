"""Evidence-based evaluation and selection of competing repair strategies.

This layer is deliberately decision-bounded: it never declares a globally
optimal repair, never treats incomplete evidence as comparable, and never
mutates or admits a candidate. It produces a selection recommendation only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .repair_candidate_selection import CandidateEvaluation
from .repository_root_cause import RepairCandidate


@dataclass(frozen=True)
class RepairEvaluation:
    """Evaluation of one candidate against the same repair obligation."""

    candidate_id: str
    evaluation: CandidateEvaluation
    evidence_complete: bool
    evidence_current: bool
    objective_dimensions: tuple[str, ...]
    findings: tuple[str, ...] = ()

    @property
    def comparable(self) -> bool:
        e = self.evaluation
        return (
            self.evidence_complete
            and self.evidence_current
            and e.passed
            and e.regression_free
            and isinstance(e.verification_score, (int, float))
            and not isinstance(e.verification_score, bool)
            and isinstance(e.measurement_score, (int, float))
            and not isinstance(e.measurement_score, bool)
            and bool(self.objective_dimensions)
            and not self.findings
        )


@dataclass(frozen=True)
class CompetingRepairSelection:
    selected_candidate_id: str | None
    evaluations: tuple[RepairEvaluation, ...]
    compared_candidate_ids: tuple[str, ...]
    status: str
    rationale: str


def evaluate_competing_repairs(
    candidates: Iterable[RepairCandidate],
    evaluations: Iterable[CandidateEvaluation],
    *,
    current_evidence: Mapping[str, tuple[str, ...]],
    objective_dimensions: Mapping[str, tuple[str, ...]],
) -> tuple[RepairEvaluation, ...]:
    """Build bounded, current-evidence evaluations for all supplied candidates.

    Missing evaluations/evidence are represented as findings rather than
    silently dropped. This preserves an auditable explanation of why a
    candidate was not comparable.
    """
    if isinstance(evaluations, CandidateEvaluation):
        evaluations = (evaluations,)
    by_id = {e.candidate_id: e for e in evaluations}
    result: list[RepairEvaluation] = []

    for candidate in candidates:
        evaluation = by_id.get(candidate.candidate_id)
        evidence = tuple(sorted(set(current_evidence.get(candidate.candidate_id, ()))))
        dimensions = tuple(sorted(set(objective_dimensions.get(candidate.candidate_id, ()))))
        findings: list[str] = []

        if evaluation is None:
            evaluation = CandidateEvaluation(
                candidate.candidate_id, False, 0.0, False, 0.0, (),
                ("missing-candidate-evaluation",),
            )
            findings.append("missing-candidate-evaluation")

        if not evaluation.evidence:
            findings.append("missing-evaluation-evidence")
        if not evidence:
            findings.append("missing-current-evidence")
        if evaluation.evidence and evidence and not set(evaluation.evidence).issubset(set(evidence)):
            findings.append("evaluation-evidence-not-current")
        if not dimensions:
            findings.append("missing-objective-dimensions")

        result.append(
            RepairEvaluation(
                candidate.candidate_id,
                evaluation,
                not any(x.startswith("missing-evaluation-evidence") for x in findings)
                and "evaluation-evidence-not-current" not in findings
                and "missing-candidate-evaluation" not in findings,
                bool(evidence),
                dimensions,
                tuple(sorted(set(findings))),
            )
        )

    return tuple(result)


def select_competing_repair(
    evaluations: Iterable[RepairEvaluation],
) -> CompetingRepairSelection:
    """Select the highest-scoring *comparable* repair, or fail closed.

    A tie on both scoring dimensions is intentionally not resolved by
    candidate ID. The system must request additional evidence or a governing
    tie-break rule instead of inventing a preference.
    """
    checked = tuple(evaluations)
    eligible = tuple(e for e in checked if e.comparable)

    if not eligible:
        return CompetingRepairSelection(
            None,
            checked,
            (),
            "unknown-no-comparable-repair",
            "no candidate has complete current evidence and passing regression-free verification",
        )

    max_pair = max(
        (float(e.evaluation.verification_score), float(e.evaluation.measurement_score))
        for e in eligible
    )
    winners = tuple(
        e for e in eligible
        if (float(e.evaluation.verification_score), float(e.evaluation.measurement_score)) == max_pair
    )

    if len(winners) != 1:
        return CompetingRepairSelection(
            None,
            checked,
            tuple(sorted(e.candidate_id for e in eligible)),
            "unknown-insufficient-discrimination",
            "comparable candidates tie on all current selection dimensions; no arbitrary tie-break is permitted",
        )

    winner = winners[0]
    return CompetingRepairSelection(
        winner.candidate_id,
        checked,
        tuple(sorted(e.candidate_id for e in eligible)),
        "selected-evidenced-candidate",
        "selected highest-scoring candidate among comparable candidates with current evidence; not a global optimum",
    )
