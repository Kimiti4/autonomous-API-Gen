"""
Evolutionary memory.
"""

from __future__ import annotations

from typing import Dict, List

from .models import EvolutionaryMemoryRecord


class EvolutionaryMemory:
    """In-memory evolutionary memory store."""

    def __init__(self) -> None:
        self.records: List[EvolutionaryMemoryRecord] = []

    def add_record(
        self,
        campaign_id: str,
        record_type: str,
        payload: Dict,
        generation_index: int | None = None,
    ) -> EvolutionaryMemoryRecord:
        record = EvolutionaryMemoryRecord(
            campaign_id=campaign_id,
            generation_index=generation_index,
            record_type=record_type,
            payload=payload,
        )

        self.records.append(record)

        return record

    def campaign_records(
        self,
        campaign_id: str,
    ) -> List[EvolutionaryMemoryRecord]:
        return [
            record
            for record in self.records
            if record.campaign_id == campaign_id
        ]
