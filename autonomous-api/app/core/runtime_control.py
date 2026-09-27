"""Durable, signed runtime emergency controls for evolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.config import get_settings
from app.core.governance.audit import AuditRecord, GovernanceAuditSigner, verify_chain
from app.storage.db import SessionLocal


RUNTIME_SCOPE = "__runtime__"
ACTIVATE_EVENT = "RuntimeKillSwitchActivated"
DEACTIVATE_EVENT = "RuntimeKillSwitchDeactivated"


@dataclass(frozen=True)
class KillSwitchState:
    enabled: bool
    reason: str
    activated_by: str | None
    activated_at: str | None
    deactivated_by: str | None
    deactivated_at: str | None


def _signer() -> GovernanceAuditSigner:
    settings = get_settings()
    return GovernanceAuditSigner(settings.GOVERNANCE_AUDIT_SIGNING_KEY)


def _records(db) -> list[AuditRecord]:
    rows = db.execute(
        text(
            "SELECT candidate_id, sequence, event_type, payload, previous_hash, "
            "record_hash, signature FROM governance_audit "
            "WHERE candidate_id = :scope ORDER BY sequence ASC"
        ),
        {"scope": RUNTIME_SCOPE},
    ).all()
    records = [AuditRecord(*row) for row in rows]
    verify_chain(records, _signer())
    return records


def get_kill_switch() -> KillSwitchState:
    db = SessionLocal()
    try:
        records = _records(db)
        if not records:
            return KillSwitchState(False, "", None, None, None, None)
        latest = json.loads(records[-1].payload)
        if records[-1].event_type == ACTIVATE_EVENT:
            return KillSwitchState(
                True,
                latest.get("reason", ""),
                latest.get("actor"),
                latest.get("at"),
                None,
                None,
            )
        if records[-1].event_type == DEACTIVATE_EVENT:
            return KillSwitchState(
                False,
                latest.get("reason", ""),
                latest.get("previous_activated_by"),
                latest.get("previous_activated_at"),
                latest.get("actor"),
                latest.get("at"),
            )
        raise RuntimeError("unknown runtime kill-switch event; refusing to infer state")
    finally:
        db.close()


def assert_evolution_enabled() -> None:
    state = get_kill_switch()
    if state.enabled:
        raise RuntimeError(
            "runtime evolution kill switch is active"
            + (f": {state.reason}" if state.reason else "")
        )


def _append(event_type: str, payload: dict) -> None:
    payload_text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signer = _signer()
    db = SessionLocal()
    try:
        with db.begin():
            previous = db.execute(
                text(
                    "SELECT sequence, record_hash FROM governance_audit "
                    "WHERE candidate_id = :scope ORDER BY sequence DESC LIMIT 1"
                ),
                {"scope": RUNTIME_SCOPE},
            ).first()
            sequence = (previous[0] + 1) if previous else 1
            previous_hash = previous[1] if previous else ""
            record_hash, signature = signer.sign(
                candidate_id=RUNTIME_SCOPE,
                sequence=sequence,
                event_type=event_type,
                payload=payload_text,
                previous_hash=previous_hash,
            )
            db.execute(
                text(
                    "INSERT INTO governance_events "
                    "(candidate_id, event_type, payload) "
                    "VALUES (:candidate_id, :event_type, :payload)"
                ),
                {
                    "candidate_id": RUNTIME_SCOPE,
                    "event_type": event_type,
                    "payload": payload_text,
                },
            )
            db.execute(
                text(
                    "INSERT INTO governance_audit "
                    "(candidate_id, sequence, event_type, payload, previous_hash, record_hash, signature) "
                    "VALUES (:candidate_id, :sequence, :event_type, :payload, "
                    ":previous_hash, :record_hash, :signature)"
                ),
                {
                    "candidate_id": RUNTIME_SCOPE,
                    "sequence": sequence,
                    "event_type": event_type,
                    "payload": payload_text,
                    "previous_hash": previous_hash,
                    "record_hash": record_hash,
                    "signature": signature,
                },
            )
    finally:
        db.close()


def activate_kill_switch(*, reason: str, actor: str) -> KillSwitchState:
    current = get_kill_switch()
    if current.enabled:
        return current
    now = datetime.now(timezone.utc).isoformat()
    _append(ACTIVATE_EVENT, {"reason": reason, "actor": actor, "at": now})
    return get_kill_switch()


def deactivate_kill_switch(*, actor: str, reason: str = "") -> KillSwitchState:
    current = get_kill_switch()
    if not current.enabled:
        return current
    now = datetime.now(timezone.utc).isoformat()
    _append(
        DEACTIVATE_EVENT,
        {
            "reason": reason or current.reason,
            "actor": actor,
            "at": now,
            "previous_activated_by": current.activated_by,
            "previous_activated_at": current.activated_at,
        },
    )
    return get_kill_switch()
