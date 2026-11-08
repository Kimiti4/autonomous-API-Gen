"""FS00-FS-041 — Durable two-phase governance promotion lifecycle.

Phase A (evaluation/staging) ends in ``AWAITING_GOVERNANCE`` with immutable staged
bytes and trusted evidence bound to the candidate. Phase B (governance) requires
fresh evidence re-resolution at approve, certify, and promote boundaries.

Restart safety: candidate state is persisted under ``store_root``; a service
restart reloads pending candidates from disk without regenerating artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from constitutional_architecture.governance.trusted_evidence_registry import (
    GENESIS_HASH,
    _canonical,
    _sha256_hex,
)
from constitutional_architecture.governance.trusted_evidence_resolution import (
    EvidenceBinding,
    GovernedProductCertification,
    GovernedPromotionRequest,
    GovernedTrustedEvidenceService,
)

SCHEMA_ID = "tiannara.governance.candidate_lifecycle"
SCHEMA_VERSION = "1.0.0"
GOVERNANCE_CANDIDATE_STORE_ENV = "ESAP_GOVERNANCE_CANDIDATE_STORE"


class CandidateLifecycleState(str, Enum):
    GENERATED = "GENERATED"
    BUILDING = "BUILDING"
    VERIFYING = "VERIFYING"
    STAGED = "STAGED"
    AWAITING_GOVERNANCE = "AWAITING_GOVERNANCE"
    APPROVED = "APPROVED"
    CERTIFIED = "CERTIFIED"
    PROMOTING = "PROMOTING"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


TERMINAL_STATES = frozenset({
    CandidateLifecycleState.PROMOTED,
    CandidateLifecycleState.REJECTED,
    CandidateLifecycleState.EXPIRED,
    CandidateLifecycleState.REVOKED,
    CandidateLifecycleState.FAILED,
    CandidateLifecycleState.QUARANTINED,
})

_PENDING_GOVERNANCE = frozenset({
    CandidateLifecycleState.AWAITING_GOVERNANCE,
    CandidateLifecycleState.APPROVED,
    CandidateLifecycleState.CERTIFIED,
    CandidateLifecycleState.PROMOTING,
})

VALID_TRANSITIONS: dict[CandidateLifecycleState, frozenset[CandidateLifecycleState]] = {
    CandidateLifecycleState.GENERATED: frozenset({
        CandidateLifecycleState.BUILDING,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.BUILDING: frozenset({
        CandidateLifecycleState.VERIFYING,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.VERIFYING: frozenset({
        CandidateLifecycleState.STAGED,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.STAGED: frozenset({
        CandidateLifecycleState.AWAITING_GOVERNANCE,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.AWAITING_GOVERNANCE: frozenset({
        CandidateLifecycleState.APPROVED,
        CandidateLifecycleState.REJECTED,
        CandidateLifecycleState.EXPIRED,
        CandidateLifecycleState.FAILED,
        CandidateLifecycleState.QUARANTINED,
    }),
    CandidateLifecycleState.APPROVED: frozenset({
        CandidateLifecycleState.CERTIFIED,
        CandidateLifecycleState.REJECTED,
        CandidateLifecycleState.EXPIRED,
        CandidateLifecycleState.REVOKED,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.CERTIFIED: frozenset({
        CandidateLifecycleState.PROMOTING,
        CandidateLifecycleState.REVOKED,
        CandidateLifecycleState.EXPIRED,
        CandidateLifecycleState.FAILED,
    }),
    CandidateLifecycleState.PROMOTING: frozenset({
        CandidateLifecycleState.PROMOTED,
        CandidateLifecycleState.FAILED,
        CandidateLifecycleState.QUARANTINED,
    }),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class GovernanceCandidateRecord:
    candidate_id: str
    state: CandidateLifecycleState
    artifact_sha256: str
    artifact_manifest_digest: str
    source_revision: str
    evidence_ids: tuple[str, ...]
    certification_id: str = ""
    staged_artifact_path: str = ""
    approval_ref: str = ""
    approval_expires_at: str = ""
    council_decision_digest: str = ""
    promotion_target: str = ""
    promotion_history: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    failure_reason: str = ""
    schema_id: str = SCHEMA_ID
    schema_version: str = SCHEMA_VERSION

    def binding(self) -> EvidenceBinding:
        return EvidenceBinding(
            candidate_id=self.candidate_id,
            artifact_sha256=self.artifact_sha256,
            source_revision=self.source_revision,
            artifact_manifest_digest=self.artifact_manifest_digest,
        )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


class GovernanceCandidateStore:
    """Durable candidate staging and append-only promotion events."""

    def __init__(self, store_root: str | Path) -> None:
        self.root = Path(store_root)
        self.candidates_dir = self.root / "candidates"
        self.staging_dir = self.root / "staging"
        self.promoted_dir = self.root / "promoted"
        self.events_path = self.root / "governance-candidate-events.jsonl"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.promoted_dir.mkdir(parents=True, exist_ok=True)

    def _candidate_path(self, candidate_id: str) -> Path:
        safe = candidate_id.replace("/", "_").replace("\\", "_")
        return self.candidates_dir / f"{safe}.json"

    def save(self, record: GovernanceCandidateRecord) -> None:
        record.updated_at = _utcnow_iso()
        _atomic_write_json(self._candidate_path(record.candidate_id), asdict(record))

    def load(self, candidate_id: str) -> GovernanceCandidateRecord | None:
        path = self._candidate_path(candidate_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        state = CandidateLifecycleState(data["state"])
        return GovernanceCandidateRecord(
            candidate_id=str(data["candidate_id"]),
            state=state,
            artifact_sha256=str(data["artifact_sha256"]),
            artifact_manifest_digest=str(data["artifact_manifest_digest"]),
            source_revision=str(data["source_revision"]),
            evidence_ids=tuple(data.get("evidence_ids", ())),
            certification_id=str(data.get("certification_id", "")),
            staged_artifact_path=str(data.get("staged_artifact_path", "")),
            approval_ref=str(data.get("approval_ref", "")),
            approval_expires_at=str(data.get("approval_expires_at", "")),
            council_decision_digest=str(data.get("council_decision_digest", "")),
            promotion_target=str(data.get("promotion_target", "")),
            promotion_history=tuple(data.get("promotion_history", ())),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            failure_reason=str(data.get("failure_reason", "")),
        )

    def list_all(self) -> list[GovernanceCandidateRecord]:
        out: list[GovernanceCandidateRecord] = []
        for path in sorted(self.candidates_dir.glob("*.json")):
            cid = json.loads(path.read_text(encoding="utf-8")).get("candidate_id")
            if isinstance(cid, str):
                rec = self.load(cid)
                if rec is not None:
                    out.append(rec)
        return out

    def list_pending(self) -> list[GovernanceCandidateRecord]:
        return [r for r in self.list_all() if r.state in _PENDING_GOVERNANCE]

    def stage_bytes(self, candidate_id: str, artifact_bytes: bytes) -> tuple[Path, str]:
        cdir = self.staging_dir / candidate_id.replace("/", "_")
        cdir.mkdir(parents=True, exist_ok=True)
        path = cdir / "artifact.bin"
        digest = hashlib.sha256(artifact_bytes).hexdigest()
        fd, tmp = tempfile.mkstemp(dir=str(cdir), suffix=".part")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(artifact_bytes)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        return path, digest

    def read_staged_bytes(self, record: GovernanceCandidateRecord) -> bytes:
        path = Path(record.staged_artifact_path)
        if not path.is_file():
            raise ValueError("governance-candidate-staged-artifact-missing")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.artifact_sha256:
            raise ValueError("governance-candidate-staged-artifact-digest-mismatch")
        return data

    def append_event(self, event_type: str, candidate_id: str, payload: Mapping[str, Any]) -> str:
        prev = GENESIS_HASH
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        prev = str(json.loads(line).get("record_hash", prev))
                    except json.JSONDecodeError:
                        pass
        body = {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "event_type": event_type,
            "candidate_id": candidate_id,
            "recorded_at": _utcnow_iso(),
            "payload": dict(payload),
            "prev_hash": prev,
        }
        rhash = _sha256_hex(_canonical(body).encode("utf-8"))
        entry = {**body, "record_hash": rhash}
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(_canonical(entry) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return rhash

    def promote_artifact_atomically(self, record: GovernanceCandidateRecord) -> Path:
        data = self.read_staged_bytes(record)
        out_dir = self.promoted_dir / record.candidate_id.replace("/", "_")
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "artifact.bin"
        fd, tmp = tempfile.mkstemp(dir=str(out_dir), suffix=".part")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        if hashlib.sha256(target.read_bytes()).hexdigest() != record.artifact_sha256:
            raise ValueError("governance-candidate-promotion-digest-mismatch")
        return target


@dataclass(frozen=True)
class CouncilApproval:
    """Council decision binding candidate identity and staged artifact digest."""

    candidate_id: str
    artifact_sha256: str
    approval_ref: str
    decision_digest: str
    expires_at: str
    council_member_id: str = ""

    def verify_binding(self, record: GovernanceCandidateRecord) -> None:
        if self.candidate_id != record.candidate_id:
            raise ValueError("governance-council-candidate-mismatch")
        if self.artifact_sha256 != record.artifact_sha256:
            raise ValueError("governance-council-artifact-mismatch")
        payload = {
            "candidate_id": self.candidate_id,
            "artifact_sha256": self.artifact_sha256,
            "approval_ref": self.approval_ref,
            "expires_at": self.expires_at,
            "council_member_id": self.council_member_id,
        }
        if self.decision_digest != _digest(payload):
            raise ValueError("governance-council-decision-digest-invalid")


class GovernedCandidatePromotionService:
    """Two-phase candidate staging and promotion with mandatory trusted evidence."""

    def __init__(
        self,
        store: GovernanceCandidateStore,
        evidence_service: GovernedTrustedEvidenceService,
        *,
        require_runtime: bool = True,
    ) -> None:
        self._store = store
        self._evidence = evidence_service
        self._require_runtime = require_runtime

    def recover_pending(self) -> list[GovernanceCandidateRecord]:
        return self._store.list_pending()

    def _transition(
        self,
        record: GovernanceCandidateRecord,
        new_state: CandidateLifecycleState,
        *,
        reason: str = "",
    ) -> GovernanceCandidateRecord:
        if record.state in TERMINAL_STATES:
            raise ValueError(f"governance-candidate-terminal:{record.state.value}")
        allowed = VALID_TRANSITIONS.get(record.state, frozenset())
        if new_state not in allowed:
            raise ValueError(
                f"governance-candidate-invalid-transition:"
                f"{record.state.value}->{new_state.value}"
            )
        prior = record.state
        record.state = new_state
        if reason:
            record.failure_reason = reason
        self._store.save(record)
        self._store.append_event(
            "state_transition",
            record.candidate_id,
            {"from": prior.value, "to": new_state.value, "reason": reason},
        )
        return record

    def evaluate_and_stage(
        self,
        *,
        candidate_id: str,
        artifact_bytes: bytes,
        artifact_manifest_digest: str,
        source_revision: str,
        evidence_ids: Iterable[str],
    ) -> GovernanceCandidateRecord:
        staged_path, digest = self._store.stage_bytes(candidate_id, artifact_bytes)
        binding = EvidenceBinding(
            candidate_id=candidate_id,
            artifact_sha256=digest,
            source_revision=source_revision,
            artifact_manifest_digest=artifact_manifest_digest,
        )
        self._evidence.resolve_evidence(
            evidence_ids,
            binding=binding,
            require_runtime=self._require_runtime,
        )
        now = _utcnow_iso()
        record = GovernanceCandidateRecord(
            candidate_id=candidate_id,
            state=CandidateLifecycleState.GENERATED,
            artifact_sha256=digest,
            artifact_manifest_digest=artifact_manifest_digest,
            source_revision=source_revision,
            evidence_ids=tuple(str(x) for x in evidence_ids),
            staged_artifact_path=str(staged_path),
            created_at=now,
            updated_at=now,
        )
        self._store.save(record)
        for s in (
            CandidateLifecycleState.BUILDING,
            CandidateLifecycleState.VERIFYING,
            CandidateLifecycleState.STAGED,
            CandidateLifecycleState.AWAITING_GOVERNANCE,
        ):
            record = self._transition(record, s)
        self._store.append_event(
            "staged",
            candidate_id,
            {
                "artifact_sha256": digest,
                "evidence_ids": list(record.evidence_ids),
                "manifest_digest": artifact_manifest_digest,
            },
        )
        return record

    def get_candidate(self, candidate_id: str) -> GovernanceCandidateRecord:
        rec = self._store.load(candidate_id)
        if rec is None:
            raise ValueError(f"governance-candidate-unknown:{candidate_id}")
        return rec

    def get_resolved_evidence(self, candidate_id: str) -> tuple[Any, ...]:
        rec = self.get_candidate(candidate_id)
        return self._evidence.resolve_evidence(
            rec.evidence_ids,
            binding=rec.binding(),
            require_runtime=self._require_runtime,
        )

    def approve(self, candidate_id: str, approval: CouncilApproval) -> GovernanceCandidateRecord:
        rec = self.get_candidate(candidate_id)
        if rec.state is not CandidateLifecycleState.AWAITING_GOVERNANCE:
            raise ValueError("governance-candidate-not-awaiting-approval")
        approval.verify_binding(rec)
        self._evidence.resolve_evidence(
            rec.evidence_ids,
            binding=rec.binding(),
            require_runtime=self._require_runtime,
        )
        rec.approval_ref = approval.approval_ref
        rec.approval_expires_at = approval.expires_at
        rec.council_decision_digest = approval.decision_digest
        self._store.save(rec)
        return self._transition(rec, CandidateLifecycleState.APPROVED)

    def reject(self, candidate_id: str, *, reason: str) -> GovernanceCandidateRecord:
        rec = self.get_candidate(candidate_id)
        if rec.state not in {
            CandidateLifecycleState.AWAITING_GOVERNANCE,
            CandidateLifecycleState.APPROVED,
        }:
            raise ValueError("governance-candidate-not-rejectable")
        return self._transition(rec, CandidateLifecycleState.REJECTED, reason=reason)

    def certify(
        self,
        candidate_id: str,
        *,
        verifier_identity: str,
        verification_environment: str,
        issued_at: str,
        expires_at: str,
    ) -> tuple[GovernanceCandidateRecord, GovernedProductCertification]:
        rec = self.get_candidate(candidate_id)
        if rec.state is not CandidateLifecycleState.APPROVED:
            raise ValueError("governance-candidate-not-approved")
        if rec.approval_expires_at:
            exp = datetime.fromisoformat(rec.approval_expires_at.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                self._transition(rec, CandidateLifecycleState.EXPIRED, reason="approval-expired")
                raise ValueError("governance-candidate-approval-expired")
        cert = self._evidence.issue_product_certification(
            binding=rec.binding(),
            evidence_ids=rec.evidence_ids,
            verifier_identity=verifier_identity,
            verification_environment=verification_environment,
            verification_scope="product",
            issued_at=issued_at,
            expires_at=expires_at,
            require_runtime=self._require_runtime,
        )
        rec.certification_id = cert.certification_id
        self._store.save(rec)
        rec = self._transition(rec, CandidateLifecycleState.CERTIFIED)
        return rec, cert

    def promote(
        self,
        candidate_id: str,
        *,
        from_environment: str,
        to_environment: str,
    ) -> GovernanceCandidateRecord:
        rec = self.get_candidate(candidate_id)
        if rec.state is not CandidateLifecycleState.CERTIFIED:
            raise ValueError("governance-candidate-not-certified")
        if not rec.certification_id:
            raise ValueError("governance-candidate-missing-certification-id")
        self._store.read_staged_bytes(rec)
        self._evidence.authorize_promotion(
            GovernedPromotionRequest(
                candidate_id=rec.candidate_id,
                artifact_sha256=rec.artifact_sha256,
                source_revision=rec.source_revision,
                evidence_ids=rec.evidence_ids,
                certification_id=rec.certification_id,
                from_environment=from_environment,
                to_environment=to_environment,
            ),
            require_runtime=self._require_runtime,
        )
        rec = self._transition(rec, CandidateLifecycleState.PROMOTING)
        try:
            promoted_path = self._store.promote_artifact_atomically(rec)
        except ValueError as exc:
            self._transition(rec, CandidateLifecycleState.QUARANTINED, reason=str(exc))
            raise
        rec.promotion_target = str(promoted_path.parent)
        rec.promotion_history = rec.promotion_history + (f"{from_environment}->{to_environment}",)
        self._store.save(rec)
        rec = self._transition(rec, CandidateLifecycleState.PROMOTED)
        self._store.append_event(
            "promoted",
            candidate_id,
            {
                "artifact_sha256": rec.artifact_sha256,
                "certification_id": rec.certification_id,
                "path": rec.promotion_target,
            },
        )
        return rec


def open_governed_promotion_service(
    *,
    candidate_store: str | Path | None = None,
    evidence_ledger: str | Path | None = None,
) -> GovernedCandidatePromotionService:
    """Composition root for governed promotion (requires both stores configured)."""
    from constitutional_architecture.governance.trusted_evidence_registry import (
        TrustedEvidenceRegistry,
    )
    from constitutional_architecture.governance.trusted_evidence_resolution import (
        GovernedTrustedEvidenceService,
        TrustBoundary,
    )

    store_path = (
        str(candidate_store).strip()
        if candidate_store is not None
        else os.getenv(GOVERNANCE_CANDIDATE_STORE_ENV, "").strip()
    )
    if not store_path:
        raise ValueError("governance-candidate-store-unconfigured")
    evidence = GovernedTrustedEvidenceService.require_for_boundary(
        TrustBoundary.PRODUCTION,
        ledger_path=str(evidence_ledger) if evidence_ledger else None,
    )
    if evidence is None:
        raise ValueError("governance-trusted-evidence-required")
    return GovernedCandidatePromotionService(
        GovernanceCandidateStore(store_path),
        evidence,
    )
