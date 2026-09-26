"""Fail-closed, auditable destructive clearing of elite evolution memory."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.core.config import get_settings
from app.core.governance.audit import AuditRecord, GovernanceAuditSigner, verify_chain
from app.core.ids import uuid7
from app.storage.db import engine
from app.storage.lease import acquire_control_plane_lease, release_control_plane_lease

CONFIRMATION = "CLEAR_ELITE_MEMORY"
SCOPE = "elite-memory"
_CLEAR_LOCK = threading.Lock()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json_backup(source: Path, destination: Path) -> str:
    if not source.is_file():
        raise RuntimeError(
            "elite evolution memory file does not exist; refusing destructive clear"
        )
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "elite evolution memory is unreadable; refusing destructive clear"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            "elite evolution memory is not a JSON object; refusing destructive clear"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        shutil.copy2(source, temporary)
        if json.loads(temporary.read_text(encoding="utf-8")) != data:
            raise RuntimeError("memory backup verification failed")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        return _sha256(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


class MemoryClearAuditStore:
    """Durable HMAC-chained audit for destructive memory operations."""

    def __init__(self, signing_key: str):
        self._signer = GovernanceAuditSigner(signing_key)

    def append(self, event_type: str, payload: dict) -> AuditRecord:
        payload_text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with engine.begin() as connection:
            previous = connection.execute(
                text(
                    "SELECT sequence, record_hash FROM memory_clear_audit "
                    "WHERE scope = :scope ORDER BY sequence DESC LIMIT 1"
                ),
                {"scope": SCOPE},
            ).first()
            sequence = previous[0] + 1 if previous else 1
            previous_hash = previous[1] if previous else ""
            record_hash, signature = self._signer.sign(
                candidate_id=SCOPE,
                sequence=sequence,
                event_type=event_type,
                payload=payload_text,
                previous_hash=previous_hash,
            )
            connection.execute(
                text(
                    "INSERT INTO memory_clear_audit "
                    "(scope, sequence, operation_id, event_type, payload, previous_hash, record_hash, signature) "
                    "VALUES (:scope, :sequence, :operation_id, :event_type, :payload, "
                    ":previous_hash, :record_hash, :signature)"
                ),
                {
                    "scope": SCOPE,
                    "sequence": sequence,
                    "operation_id": payload["operation_id"],
                    "event_type": event_type,
                    "payload": payload_text,
                    "previous_hash": previous_hash,
                    "record_hash": record_hash,
                    "signature": signature,
                },
            )
        return AuditRecord(
            candidate_id=SCOPE,
            sequence=sequence,
            event_type=event_type,
            payload=payload_text,
            previous_hash=previous_hash,
            record_hash=record_hash,
            signature=signature,
        )

    def verify(self) -> list[AuditRecord]:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT scope, sequence, event_type, payload, previous_hash, "
                    "record_hash, signature FROM memory_clear_audit "
                    "WHERE scope = :scope ORDER BY sequence ASC"
                ),
                {"scope": SCOPE},
            ).all()
        records = [AuditRecord(*row) for row in rows]
        verify_chain(records, self._signer)
        return records


def clear_elite_memory(
    *,
    memory,
    adaptive_mutator,
    actor: str,
    confirmation: str,
    operation_id: str | None = None,
) -> dict:
    """Clear elite memory only after authentication, confirmation and recovery setup."""
    if confirmation != CONFIRMATION:
        raise PermissionError("explicit clear-memory confirmation required")
    if not actor:
        raise PermissionError("authenticated actor required")
    try:
        operation = str(UUID(operation_id)) if operation_id else str(uuid7())
    except ValueError as exc:
        raise ValueError("operation_id must be a valid UUID") from exc

    memory_path = Path(memory.path).resolve()
    backup_path = memory_path.parent / "memory-backups" / f"{operation}.json"
    audit = MemoryClearAuditStore(get_settings().GOVERNANCE_AUDIT_SIGNING_KEY)

    existing = audit.verify()
    if any(
        json.loads(record.payload).get("operation_id") == operation
        for record in existing
    ):
        raise ValueError("operation_id has already been used")

    audit.append(
        "memory.clear.requested",
        {"operation_id": operation, "actor": actor, "target": SCOPE},
    )

    lease_token = None
    with _CLEAR_LOCK:
        try:
            lease_token = acquire_control_plane_lease(
                owner_run_id=f"memory-clear:{operation}"
            )
        except Exception as exc:
            audit.append(
                "memory.clear.failed",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "error": type(exc).__name__,
                },
            )
            raise

        try:
            digest = _atomic_json_backup(memory_path, backup_path)
            audit.append(
                "memory.clear.backup_verified",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "backup_path": str(backup_path),
                    "backup_digest": digest,
                },
            )

            adaptive_bias = adaptive_mutator.success_bias.copy()
            adaptive_history = list(adaptive_mutator.mutation_history)
            try:
                memory.clear()
                adaptive_mutator.reset()
            except Exception:
                adaptive_mutator.success_bias = adaptive_bias
                adaptive_mutator.mutation_history = adaptive_history
                raise

            audit.append(
                "memory.clear.succeeded",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "backup_path": str(backup_path),
                    "backup_digest": digest,
                },
            )
            return {
                "operation_id": operation,
                "status": "cleared",
                "backup_path": str(backup_path),
                "backup_digest": digest,
            }
        except Exception as exc:
            audit.append(
                "memory.clear.failed",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "error": type(exc).__name__,
                },
            )
            raise
        finally:
            if lease_token is not None:
                release_control_plane_lease(lease_token)
