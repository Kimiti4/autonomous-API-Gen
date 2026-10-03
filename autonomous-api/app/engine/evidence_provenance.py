"""Evidence provenance and fail-closed verification verdicts."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from .verification_artifacts import VerificationExecution


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    artifact_id: str
    status: str
    executor: str
    runtime_identity: str
    assertions: tuple[str, ...]
    content_hash: str
    predecessor_hash: str = ""


@dataclass(frozen=True)
class VerificationVerdict:
    obligation_id: str
    verdict: str
    evidence_ids: tuple[str, ...]
    reason: str


def _hash_payload(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_evidence_record(
    execution: VerificationExecution,
    artifact_id: str,
    obligation_id: str,
    runtime_identity: str,
    assertions: tuple[str, ...] = (),
    predecessor_hash: str = "",
) -> EvidenceRecord:
    if execution.artifact_id != artifact_id:
        raise ValueError("execution does not match artifact")
    if execution.status not in {"passed", "failed", "blocked"}:
        raise ValueError("invalid execution status")
    if not runtime_identity:
        raise ValueError("runtime_identity is required")
    payload = {
        "artifact_id": artifact_id,
        "obligation_id": obligation_id,
        "status": execution.status,
        "executor": execution.executor,
        "runtime_identity": runtime_identity,
        "assertions": list(assertions),
        "predecessor_hash": predecessor_hash,
    }
    return EvidenceRecord(
        evidence_id=_hash_payload(payload),
        artifact_id=artifact_id,
        status=execution.status,
        executor=execution.executor,
        runtime_identity=runtime_identity,
        assertions=assertions,
        content_hash=_hash_payload(payload),
        predecessor_hash=predecessor_hash,
    )


def verify_evidence_chain(records: tuple[EvidenceRecord, ...]) -> bool:
    previous = ""
    for record in records:
        if record.predecessor_hash != previous:
            return False
        payload = {
            "artifact_id": record.artifact_id,
            "obligation_id": record.artifact_id.split(":", 1)[-1],
            "status": record.status,
            "executor": record.executor,
            "runtime_identity": record.runtime_identity,
            "assertions": list(record.assertions),
            "predecessor_hash": record.predecessor_hash,
        }
        if _hash_payload(payload) != record.content_hash:
            return False
        previous = record.content_hash
    return True


def derive_verdict(
    obligation_id: str,
    records: tuple[EvidenceRecord, ...],
) -> VerificationVerdict:
    matching = tuple(r for r in records if r.artifact_id.endswith(f":{obligation_id}"))
    if not matching:
        return VerificationVerdict(obligation_id, "INCONCLUSIVE", (), "no execution evidence")
    if any(r.status == "failed" for r in matching):
        return VerificationVerdict(obligation_id, "FAIL", tuple(r.evidence_id for r in matching), "execution failure")
    if any(r.status == "blocked" for r in matching):
        return VerificationVerdict(obligation_id, "BLOCKED", tuple(r.evidence_id for r in matching), "execution was blocked")
    if not all(r.runtime_identity for r in matching):
        return VerificationVerdict(obligation_id, "INCONCLUSIVE", tuple(r.evidence_id for r in matching), "missing runtime identity")
    return VerificationVerdict(obligation_id, "PASS", tuple(r.evidence_id for r in matching), "all available executions passed")
