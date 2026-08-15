"""
Organizational memory.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .utils import deterministic_id, utcnow


class MemoryRecord(BaseModel):
    """Record stored in organizational memory."""

    id: str

    organization_id: str

    record_type: str
    subject_id: str

    content: Dict[str, Any] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: str


class OrganizationalMemory:
    """In-memory organizational memory store."""

    def __init__(self) -> None:
        self.records: List[MemoryRecord] = []

    def add(
        self,
        organization_id: str,
        record_type: str,
        subject_id: str,
        content: Dict[str, Any],
        evidence_refs: Optional[List[str]] = None,
    ) -> MemoryRecord:
        created_at = utcnow().isoformat()

        record_id = deterministic_id(
            "memory_record",
            {
                "organization_id": organization_id,
                "record_type": record_type,
                "subject_id": subject_id,
                "created_at": created_at,
                "record_count": len(self.records),
            },
        )

        record = MemoryRecord(
            id=record_id,
            organization_id=organization_id,
            record_type=record_type,
            subject_id=subject_id,
            content=content,
            evidence_refs=evidence_refs or [],
            created_at=created_at,
        )

        self.records.append(record)

        return record

    def list_records(
        self,
        organization_id: str,
        record_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryRecord]:
        results: List[MemoryRecord] = []

        for record in reversed(self.records):
            if record.organization_id != organization_id:
                continue

            if record_type and record.record_type != record_type:
                continue

            results.append(record)

            if len(results) >= limit:
                break

        return results
