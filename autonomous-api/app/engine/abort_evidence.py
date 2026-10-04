"""Durable, deterministic evidence for aborted ESAP evolution transactions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AbortEvidenceRecord:
    transaction_id: str
    source_architecture_id: str
    candidate_architecture_id: str
    stage: str
    reason: str
    attempted_mutations: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    residuals: tuple[str, ...]
    successor_admitted: bool = False

    def canonical_payload(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def evidence_digest(self) -> str:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest()


def build_abort_evidence(
    *,
    transaction_id: str,
    source_architecture_id: str,
    candidate_architecture_id: str,
    stage: str,
    reason: str,
    attempted_mutations: Sequence[str] = (),
    verification_evidence: Sequence[str] = (),
    residuals: Sequence[str] = (),
) -> AbortEvidenceRecord:
    if not transaction_id:
        raise ValueError("missing-transaction-id")
    if not source_architecture_id:
        raise ValueError("missing-source-architecture-id")
    if not candidate_architecture_id:
        raise ValueError("missing-candidate-architecture-id")
    if not stage:
        raise ValueError("missing-abort-stage")
    if not reason:
        raise ValueError("missing-abort-reason")
    return AbortEvidenceRecord(
        transaction_id=transaction_id,
        source_architecture_id=source_architecture_id,
        candidate_architecture_id=candidate_architecture_id,
        stage=stage,
        reason=reason,
        attempted_mutations=tuple(attempted_mutations),
        verification_evidence=tuple(verification_evidence),
        residuals=tuple(residuals),
    )
