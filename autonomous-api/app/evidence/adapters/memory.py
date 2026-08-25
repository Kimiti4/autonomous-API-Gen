"""In-memory EvidenceStore (dev/tests).

Production backend: blob store / DB with content-hash-keyed immutable
objects. Implements the same interface the EvidenceSubsystem requires.
"""
from __future__ import annotations


class InMemoryEvidenceStore:
    def __init__(self) -> None:
        self._records: dict = {}

    async def exists(self, evidence_id: str) -> bool:
        return evidence_id in self._records

    async def insert(self, record: dict) -> None:
        self._records[record["evidenceId"]] = dict(record)

    async def get(self, evidence_id: str):
        return self._records.get(evidence_id)