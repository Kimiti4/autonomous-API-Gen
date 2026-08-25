"""EvidenceSubsystem (§4.1). Stores integrity-checked evidence artifacts.

E-1 contentHash computed at write; E-2 immutable once stored; E-3 the
referencing subsystems validate existence via this subsystem before
recording their evidenceRefs.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.evidence.commands import StoreEvidence
from app.core.evidence.events import EvidenceStored
from app.core.evidence.invariants import (
    check_e1_content_hash,
    check_e2_immutability,
)


class EvidenceSubsystem:
    def __init__(self, *, store) -> None:
        self._store = store

    async def store(self, cmd: StoreEvidence) -> EvidenceStored:
        # E-2: refuse to overwrite an existing evidenceId.
        existing = await self._store.exists(cmd.evidenceId)
        check_e2_immutability(existing)

        hash_value = check_e1_content_hash(cmd.artifact)
        record = {
            "evidenceId": cmd.evidenceId,
            "evidenceType": cmd.evidenceType,
            "producedBy": cmd.producedBy,
            "subjectRef": cmd.subjectRef,
            "artifact": cmd.artifact,
            "summary": cmd.summary,
            "contentHash": hash_value,
            "storedAt": datetime.now(timezone.utc).isoformat(),
        }
        await self._store.insert(record)
        return EvidenceStored(
            evidenceId=cmd.evidenceId,
            contentHash=hash_value,
            storedAt=record["storedAt"],
        )

    async def get(self, evidence_id: str):
        return await self._store.get(evidence_id)

    async def exists(self, evidence_id: str) -> bool:
        return await self._store.exists(evidence_id)