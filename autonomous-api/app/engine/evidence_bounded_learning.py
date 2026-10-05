"""Evidence-bounded learning memory for ESAP.

Historical observations are retained with provenance and epistemic status.
Memory can inform future planning, but cannot by itself certify current code.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class LearningRecord:
    record_id: str
    project_id: str
    kind: str
    statement: str
    outcome: str
    evidence_ids: tuple[str, ...]
    source_digest: str
    confidence: str = "observed"

@dataclass(frozen=True)
class MemoryQueryResult:
    records: tuple[LearningRecord, ...]
    advisory_only: bool = True

def record_learning(*, record_id: str, project_id: str, kind: str, statement: str,
                    outcome: str, evidence_ids: tuple[str, ...], source_digest: str) -> LearningRecord:
    if not all((record_id, project_id, kind, statement, outcome, source_digest)):
        raise ValueError("learning-record-missing-identity")
    if not evidence_ids:
        raise ValueError("learning-record-requires-evidence")
    return LearningRecord(record_id, project_id, kind, statement, outcome,
                          tuple(sorted(set(evidence_ids))), source_digest)

def query_learning(records: tuple[LearningRecord, ...], project_id: str, kind: str | None = None) -> MemoryQueryResult:
    matches=tuple(r for r in records if r.project_id == project_id and (kind is None or r.kind == kind))
    return MemoryQueryResult(matches)

def authorize_learning_as_fact(record: LearningRecord, current_evidence_ids: tuple[str, ...]) -> None:
    if not current_evidence_ids:
        raise ValueError("historical-memory-cannot-certify-current-state")
