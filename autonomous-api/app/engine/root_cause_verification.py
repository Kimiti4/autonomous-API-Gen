"""Root-cause verification gate for repository repair.

A hypothesis is not a fact. Repair execution requires explicit current
verification tying the selected hypothesis to the observed defect.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from .repository_root_cause import RootCauseHypothesis


@dataclass(frozen=True)
class RootCauseVerification:
    hypothesis_id: str
    confirmed: bool
    evidence_ids: tuple[str, ...]
    reason: str


def verify_root_cause(
    hypothesis: RootCauseHypothesis,
    current_observations: Mapping[str, object],
    evidence_ids: tuple[str, ...],
) -> RootCauseVerification:
    if not evidence_ids:
        return RootCauseVerification(
            hypothesis.hypothesis_id, False, (), "missing-current-root-cause-evidence"
        )
    marker = current_observations.get(hypothesis.finding_id)
    if marker is not True:
        return RootCauseVerification(
            hypothesis.hypothesis_id, False, tuple(sorted(set(evidence_ids))),
            "root-cause-not-confirmed-by-current-observation",
        )
    return RootCauseVerification(
        hypothesis.hypothesis_id, True, tuple(sorted(set(evidence_ids))),
        "confirmed-by-current-observation",
    )


def require_verified_root_cause(result: RootCauseVerification) -> None:
    if not result.confirmed:
        raise ValueError("root-cause-not-verified:"+result.reason)
