"""
Evolution history repository.

This repository maintains an append-only, hash-chained evolution audit trail.
"""

from __future__ import annotations

from typing import Any, Optional

from .models import EvolutionEvent, utcnow
from .utils import canonical_json, deterministic_id, sha256_hex


class EvolutionHistoryRepository:
    """Append-only evolution history store."""

    def __init__(self) -> None:
        self.events: list[EvolutionEvent] = []
        self.last_event_hash = "genesis"

    def record(
        self,
        proposal_id: str,
        event_type: str,
        actor_id: str,
        details: dict[str, Any],
    ) -> EvolutionEvent:
        timestamp = utcnow().isoformat()

        event_id = deterministic_id(
            "evolution_event",
            {
                "proposal_id": proposal_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "previous_event_hash": self.last_event_hash,
            },
        )

        event_hash = sha256_hex(
            canonical_json(
                {
                    "event_id": event_id,
                    "proposal_id": proposal_id,
                    "event_type": event_type,
                    "actor_id": actor_id,
                    "details": details,
                    "timestamp": timestamp,
                    "previous_event_hash": self.last_event_hash,
                }
            )
        )

        event = EvolutionEvent(
            id=event_id,
            proposal_id=proposal_id,
            event_type=event_type,
            actor_id=actor_id,
            details=details,
            timestamp=timestamp,
            previous_event_hash=self.last_event_hash,
            event_hash=event_hash,
        )

        self.events.append(event)
        self.last_event_hash = event_hash

        return event

    def list_events(
        self,
        proposal_id: Optional[str] = None,
    ) -> list[EvolutionEvent]:
        if not proposal_id:
            return list(self.events)

        return [
            event
            for event in self.events
            if event.proposal_id == proposal_id
        ]
