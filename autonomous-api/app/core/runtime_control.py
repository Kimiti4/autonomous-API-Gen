"""Durable runtime controls for emergency evolution shutdown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import text

from app.storage.db import SessionLocal


@dataclass(frozen=True)
class KillSwitchState:
    enabled: bool
    reason: str
    activated_by: str | None
    activated_at: str | None
    deactivated_by: str | None
    deactivated_at: str | None


def _row(db):
    return db.execute(
        text(
            "SELECT enabled, reason, activated_by, activated_at, "
            "deactivated_by, deactivated_at "
            "FROM runtime_kill_switch WHERE id = 1"
        )
    ).mappings().one()


def get_kill_switch() -> KillSwitchState:
    db = SessionLocal()
    try:
        row = _row(db)
        return KillSwitchState(
            enabled=bool(row["enabled"]),
            reason=row["reason"] or "",
            activated_by=row["activated_by"],
            activated_at=str(row["activated_at"]) if row["activated_at"] else None,
            deactivated_by=row["deactivated_by"],
            deactivated_at=str(row["deactivated_at"]) if row["deactivated_at"] else None,
        )
    finally:
        db.close()


def assert_evolution_enabled() -> None:
    state = get_kill_switch()
    if state.enabled:
        raise RuntimeError(
            "runtime evolution kill switch is active"
            + (f": {state.reason}" if state.reason else "")
        )


def activate_kill_switch(*, reason: str, actor: str) -> KillSwitchState:
    now = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE runtime_kill_switch SET enabled = 1, reason = :reason, "
                "activated_by = :actor, activated_at = :now, "
                "deactivated_by = NULL, deactivated_at = NULL, updated_at = :now "
                "WHERE id = 1"
            ),
            {"reason": reason, "actor": actor, "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return get_kill_switch()


def deactivate_kill_switch(*, actor: str, reason: str = "") -> KillSwitchState:
    now = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE runtime_kill_switch SET enabled = 0, "
                "reason = CASE WHEN :reason != '' THEN :reason ELSE reason END, "
                "deactivated_by = :actor, deactivated_at = :now, updated_at = :now "
                "WHERE id = 1"
            ),
            {"reason": reason, "actor": actor, "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return get_kill_switch()
