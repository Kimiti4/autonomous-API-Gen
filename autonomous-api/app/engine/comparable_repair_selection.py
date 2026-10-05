"""Comparable, evidence-complete selection among competing repairs.

Scores may rank candidates only when every candidate being compared has the
required evidence and comparable objective dimensions. Otherwise selection
fails closed instead of inventing an optimum.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .repair_candidate_selection import CandidateEvaluation, RepairSelection
from .repository_root_cause import RepairCandidate


@dataclass(frozen=True)
class ComparableSelection:
    selection: RepairSelection
    compared_candidate_ids: tuple[str, ...]
    optimality_status: str


def select_comparable_repair(
    candidates: Iterable[RepairCandidate],
    evaluations: Iterable[CandidateEvaluation],
) -> ComparableSelection:
    cs=tuple(candidates)
    es={e.candidate_id:e for e in evaluations}
    eligible=[]
    for c in cs:
        e=es.get(c.candidate_id)
        if e is None or not e.evidence or not e.passed or not e.regression_free:
            continue
        if not all(isinstance(v,(int,float)) for v in (e.verification_score,e.measurement_score)):
            continue
        eligible.append(e)
    if not eligible:
        return ComparableSelection(
            RepairSelection(None,tuple(es.values()),"no comparable evidenced candidate"),
            (), "unknown-no-comparable-candidate",
        )
    ids=tuple(sorted(e.candidate_id for e in eligible))
    winner=max(eligible,key=lambda e:(e.verification_score,e.measurement_score,e.candidate_id))
    return ComparableSelection(
        RepairSelection(
            winner.candidate_id, tuple(es.get(c.candidate_id, CandidateEvaluation(
                c.candidate_id,False,0.0,False,0.0,(),("missing-candidate-evaluation",)
            )) for c in cs),
            "selected highest-scoring candidate among comparable evidenced candidates",
        ),
        ids, "ranked-with-comparable-evidence",
    )
