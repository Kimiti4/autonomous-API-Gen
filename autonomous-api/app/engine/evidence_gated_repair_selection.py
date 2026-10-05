"""Evidence-gated competing repair selection.

No candidate may be described as fixed, valid, optimal, or deployable without
the evidence required by its gates. Unknown measurements are never converted
into positive claims.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .repair_candidate_selection import CandidateEvaluation, RepairSelection
from .repository_root_cause import RepairCandidate


@dataclass(frozen=True)
class SelectionDecision:
    selection: RepairSelection
    epistemic_status: str
    evidence_complete: bool


def select_evidence_gated_repair(
    candidates: Iterable[RepairCandidate],
    evaluations: Iterable[CandidateEvaluation],
) -> SelectionDecision:
    candidate_list=tuple(candidates)
    evaluation_list=tuple(evaluations)
    candidate_ids={c.candidate_id for c in candidate_list}
    evaluations_by_id={e.candidate_id:e for e in evaluation_list}

    normalized=[]
    for cid,e in evaluations_by_id.items():
        if cid not in candidate_ids:
            continue
        reasons=list(e.rejection_reasons)
        if not e.evidence:
            reasons.append("missing-evaluation-evidence")
        normalized.append(CandidateEvaluation(
            e.candidate_id,
            e.passed and bool(e.evidence),
            e.verification_score,
            e.regression_free and bool(e.evidence),
            e.measurement_score,
            e.evidence,
            tuple(sorted(set(reasons))),
        ))

    selection=__import__(
        "app.engine.repair_candidate_selection",fromlist=["select_verified_repair"]
    ).select_verified_repair(candidate_list,normalized)

    if selection.selected_candidate_id is None:
        status="unknown-no-evidenced-repair-admitted"
        complete=False
    else:
        status="verified-candidate-selected"
        complete=True

    return SelectionDecision(selection,status,complete)
