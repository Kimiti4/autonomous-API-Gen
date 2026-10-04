"""Evidence-driven selection among competing repository repair candidates."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping

from .repository_root_cause import RepairCandidate

@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    passed: bool
    verification_score: float
    regression_free: bool
    measurement_score: float
    evidence: tuple[str, ...]
    rejection_reasons: tuple[str, ...] = ()

@dataclass(frozen=True)
class RepairSelection:
    selected_candidate_id: str | None
    evaluations: tuple[CandidateEvaluation, ...]
    rationale: str

def select_verified_repair(
    candidates: Iterable[RepairCandidate],
    evaluations: Iterable[CandidateEvaluation],
) -> RepairSelection:
    by_id={e.candidate_id:e for e in evaluations}
    checked=[]
    for c in candidates:
        e=by_id.get(c.candidate_id)
        if e is None:
            checked.append(CandidateEvaluation(
                c.candidate_id,False,0.0,False,0.0,(),
                ("missing-candidate-evaluation",)))
        else:
            checked.append(e)
    eligible=[e for e in checked if e.passed and e.regression_free]
    if not eligible:
        return RepairSelection(None,tuple(checked),"no candidate passed verification and regression gates")
    winner=max(eligible,key=lambda e:(e.verification_score,e.measurement_score,e.candidate_id))
    return RepairSelection(
        winner.candidate_id,
        tuple(checked),
        "selected highest-scoring candidate among verified regression-free candidates",
    )
