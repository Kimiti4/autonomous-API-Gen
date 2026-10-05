"""Evidence/truth gate for autonomous ESAP decisions.

The gate prevents unsupported claims from becoming executable repair or
admission facts. Unknowns stay unknown; evidence must be attributable to the
current candidate and verification run.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class EpistemicStatus(str, Enum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


@dataclass(frozen=True)
class EvidenceClaim:
    claim_id: str
    subject_id: str
    status: EpistemicStatus
    evidence_ids: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class TruthGateResult:
    admissible: bool
    status: EpistemicStatus
    reasons: tuple[str, ...]


def evaluate_claim(
    claim: EvidenceClaim,
    available_evidence: Mapping[str, object],
    *,
    expected_subject_id: str | None = None,
) -> TruthGateResult:
    reasons=[]
    if not claim.claim_id or not claim.subject_id:
        reasons.append("missing-claim-identity")
    if expected_subject_id is not None and claim.subject_id != expected_subject_id:
        reasons.append("claim-subject-mismatch")
    if not claim.source:
        reasons.append("missing-claim-source")
    if claim.status is EpistemicStatus.VERIFIED:
        if not claim.evidence_ids:
            reasons.append("verified-claim-requires-evidence")
        for eid in claim.evidence_ids:
            if eid not in available_evidence:
                reasons.append(f"missing-evidence:{eid}")
    elif claim.status is EpistemicStatus.UNKNOWN:
        reasons.append("claim-is-unknown")
    elif claim.status is EpistemicStatus.CONTRADICTED:
        reasons.append("claim-is-contradicted")
    if reasons:
        return TruthGateResult(False, claim.status, tuple(reasons))
    return TruthGateResult(True, EpistemicStatus.VERIFIED, ())
