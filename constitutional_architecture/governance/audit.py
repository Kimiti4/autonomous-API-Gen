"""
Phase 28 — Audit Framework.

Append-only, hash-chained audit event store (Milestone 4). Every event
links to the previous event's hash, giving tamper evidence before any
external event store is introduced. Supports decision reconstruction:
the kernel records a full decision dossier at evaluation time, and
reconstruct() reassembles it with related approvals and lineage.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Protocol, runtime_checkable

from constitutional_architecture.governance.schemas import (
    Actor,
    AuditEvent,
    GovernanceDecision,
    ApprovalRecord,
)


class AuditFramework:
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
        self._by_id: Dict[str, AuditEvent] = {}
        self._decision_dossiers: Dict[str, dict] = {}
        self._approvals: Dict[str, ApprovalRecord] = {}

    def record(
        self,
        event_type: str,
        actor: Actor,
        subject_type: str,
        subject_id: str,
        action: str,
        *,
        decision_id: Optional[str] = None,
        approval_ids: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None,
        context: Optional[dict] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=f"audit_{uuid.uuid4().hex[:10]}",
            event_type=event_type,
            actor=actor,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            decision_id=decision_id,
            approval_ids=approval_ids or [],
            evidence_refs=evidence_refs or [],
            context=context or {},
        )
        previous_hash = self._events[-1].event_hash if self._events else ""
        event.recompute_hash(previous_hash)
        self._events.append(event)
        self._by_id[event.id] = event
        return event

    def record_decision_dossier(
        self,
        decision: GovernanceDecision,
        request: dict,
        approval_ids: Optional[List[str]] = None,
    ) -> None:
        """Snapshots everything needed to reconstruct a decision. Decision
        ids are content-addressed, so re-evaluating an identical request
        hits the same id; lifecycle markers (final_decision, approvals)
        from an earlier pass are preserved."""
        decision_id = decision_id_of(decision)
        dossier = {
            "request": request,
            "decision": decision.model_dump(),
            "approval_ids": approval_ids or [],
        }
        existing = self._decision_dossiers.get(decision_id)
        if existing is not None:
            for marker in ("final_decision", "approval_ids"):
                if marker in existing and existing[marker]:
                    dossier[marker] = existing[marker]
        self._decision_dossiers[decision_id] = dossier

    def attach_approval_ids(self, decision_id: str, approval_ids: List[str]) -> None:
        if decision_id in self._decision_dossiers:
            self._decision_dossiers[decision_id]["approval_ids"] = approval_ids

    def finalize_dossier_decision(self, decision_id: str, final_value: str) -> None:
        """Records the final decision (ALLOW or DENY) alongside the original
        evaluation snapshot so reconstruction shows the full lifecycle."""
        if decision_id in self._decision_dossiers:
            self._decision_dossiers[decision_id]["final_decision"] = final_value

    def record_approval(self, approval: ApprovalRecord) -> None:
        self._approvals[approval.id] = approval

    def reconstruct(self, decision_id: str) -> dict:
        """Full dossier: original request, policies evaluated, approvals,
        evidence, exceptions, final decision, related lineage."""
        if decision_id not in self._decision_dossiers:
            raise KeyError(f"Unknown decision {decision_id}")
        dossier = dict(self._decision_dossiers[decision_id])
        dossier["approvals"] = [
            self._approvals[a].model_dump()
            for a in dossier.get("approval_ids", [])
            if a in self._approvals
        ]
        dossier["lineage"] = [
            e.model_dump()
            for e in self._events
            if e.decision_id == decision_id
        ]
        return dossier

    def query(
        self,
        *,
        subject_id: Optional[str] = None,
        subject_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        event_type: Optional[str] = None,
        decision_id: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        results = self._events
        if subject_id is not None:
            results = [e for e in results if e.subject_id == subject_id]
        if subject_type is not None:
            results = [e for e in results if e.subject_type == subject_type]
        if actor_id is not None:
            results = [e for e in results if e.actor.actor_id == actor_id]
        if action is not None:
            results = [e for e in results if e.action == action]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if decision_id is not None:
            results = [e for e in results if e.decision_id == decision_id]
        if from_time is not None:
            results = [e for e in results if e.timestamp >= from_time]
        if to_time is not None:
            results = [e for e in results if e.timestamp <= to_time]
        return results

    def verify_chain(self) -> bool:
        """Tamper-evidence check: every event's hash covers its payload and
        the previous event's hash, in order."""
        valid, _ = self.verify_chain_detail()
        return valid

    def verify_chain_detail(self) -> tuple[bool, Optional[int]]:
        """(valid, first_broken_index) — the dashboard reports the first
        invalid event when the chain is tampered or missing."""
        from constitutional_architecture.governance.schemas import content_hash

        previous = ""
        for index, event in enumerate(self._events):
            if event.previous_event_hash != previous:
                return False, index
            if content_hash(event.model_dump(exclude={"event_hash"})) != event.event_hash:
                return False, index
            previous = event.event_hash
        return True, None

    def list_evaluations(
        self,
        *,
        subject_id: Optional[str] = None,
        subject_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> List[dict]:
        """Read view over recorded decision dossiers (evaluation explorer)."""
        results: List[dict] = []
        for decision_id, dossier in self._decision_dossiers.items():
            request = dossier.get("request", {})
            actor = request.get("actor", {})
            if subject_id is not None and request.get("subject_id") != subject_id:
                continue
            if subject_type is not None and request.get("subject_type") != subject_type:
                continue
            if actor_id is not None and actor.get("actor_id") != actor_id:
                continue
            if action is not None and request.get("action") != action:
                continue
            decision_dict = dossier.get("decision", {})
            if decision is not None and decision_dict.get("decision") != decision:
                continue
            results.append(
                {
                    "decision_id": decision_id,
                    "request": request,
                    "decision": decision_dict,
                    "final_decision": dossier.get("final_decision"),
                    "approval_ids": dossier.get("approval_ids", []),
                }
            )
        results.sort(key=lambda d: d["decision"]["created_at"])
        return results


def decision_id_of(decision: GovernanceDecision) -> str:
    """Stable id for a decision: first 16 hex chars of its decision hash."""
    return f"decision_{decision.decision_hash[:16]}"


# ===========================================================================
# Phase 28 additive: tamper-evident evidence ledger + compliance report log.
# Kept separate from AuditFramework above to avoid altering its contract.
# ===========================================================================

import hashlib
import json

from constitutional_architecture.governance.schemas import (
    AuditEvidenceISR,
    ComplianceReportISR,
)


def canonical_payload_hash(payload: dict) -> str:
    """SHA-256 over a canonical JSON serialization (stable across runs)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditEvidenceRecorder:
    """Append-only, hash-chained evidence ledger.

    Each record's chain_link references the previous evidence_id; the
    payload_hash covers the payload including the chain link, so reordering
    or splicing is detectable via verify_chain(). Payloads are retained
    internally for re-verification.
    """

    def __init__(self) -> None:
        self._entries: List[tuple[AuditEvidenceISR, dict]] = []

    def record(
        self,
        *,
        actor: str,
        event_kind: str,
        subject_ref: str,
        payload: dict,
        recorded_at: datetime,
    ) -> AuditEvidenceISR:
        chain_link = self._entries[-1][0].evidence_id if self._entries else None
        payload_hash = canonical_payload_hash({**payload, "chain_link": chain_link})
        evidence = AuditEvidenceISR(
            evidence_id=f"ev-{uuid.uuid4().hex[:12]}",
            recorded_at=recorded_at,
            actor=actor,
            event_kind=event_kind,
            subject_ref=subject_ref,
            payload_hash=payload_hash,
            chain_link=chain_link,
        )
        self._entries.append((evidence, payload))
        return evidence

    @property
    def entries(self) -> tuple[AuditEvidenceISR, ...]:
        return tuple(evidence for evidence, _ in self._entries)

    def verify_chain(self) -> bool:
        previous_id: str | None = None
        for evidence, payload in self._entries:
            if evidence.chain_link != previous_id:
                return False
            if canonical_payload_hash({**payload, "chain_link": previous_id}) != evidence.payload_hash:
                return False
            previous_id = evidence.evidence_id
        return True

    def verify_signatures(self) -> Optional[bool]:
        """Signature verification is N/A for the unsigned ledger (returns None).

        The signing wrapper :class:`SignedAuditEvidenceRecorder` overrides this
        to attest the authenticity of its records; the base recorder reports
        "not signed" so callers can render a signed/unsigned status.
        """
        return None


@runtime_checkable
class EvidenceLedger(Protocol):
    """Structural contract satisfied by both the unsigned
    :class:`AuditEvidenceRecorder` and the signing
    :class:`SignedAuditEvidenceRecorder`.

    A config-gated factory (``new_evidence_recorder``) chooses the concrete
    implementation at the composition root, so callers (kernel, dashboard,
    version manager) never need to know whether signing is active.
    """

    def record(
        self,
        *,
        actor: str,
        event_kind: str,
        subject_ref: str,
        payload: dict,
        recorded_at: datetime,
    ) -> AuditEvidenceISR: ...

    @property
    def entries(self) -> tuple[AuditEvidenceISR, ...]: ...

    def verify_chain(self) -> bool: ...

    def verify_signatures(self) -> Optional[bool]: ...


class ComplianceReportLog:
    """Append-only log of ComplianceReportISR; projection source for the
    governance dashboard."""

    def __init__(self) -> None:
        self._reports: List[ComplianceReportISR] = []

    def append(self, report: ComplianceReportISR) -> None:
        if any(existing.report_id == report.report_id for existing in self._reports):
            raise ValueError(f"duplicate_report_id:{report.report_id}")
        self._reports.append(report)

    def latest(self, limit: int = 20) -> tuple[ComplianceReportISR, ...]:
        return tuple(self._reports[-limit:])
