"""
Evolutionary observability.

This module provides structured, hash-chained observability events for the
Self-Evolution Engine.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from .models import utcnow
from .utils import canonical_json, deterministic_id, sha256_hex


class EvolutionEventType(str, Enum):
    """Event types emitted by the evolution subsystem."""

    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"

    CANDIDATE_GENERATED = "CANDIDATE_GENERATED"
    CANDIDATE_EVALUATED = "CANDIDATE_EVALUATED"
    PARETO_SELECTED = "PARETO_SELECTED"

    GENOME_REFINED = "GENOME_REFINED"
    CROSSOVER_COMPLETED = "CROSSOVER_COMPLETED"

    PROMOTION_CREATED = "PROMOTION_CREATED"
    PROMOTION_SAFETY_PASSED = "PROMOTION_SAFETY_PASSED"
    PROMOTION_SAFETY_FAILED = "PROMOTION_SAFETY_FAILED"
    PROMOTION_GOVERNANCE_EVALUATED = "PROMOTION_GOVERNANCE_EVALUATED"
    PROMOTION_GOVERNANCE_DENIED = "PROMOTION_GOVERNANCE_DENIED"
    PROMOTION_PENDING_APPROVAL = "PROMOTION_PENDING_APPROVAL"
    PROMOTION_APPROVED = "PROMOTION_APPROVED"
    PROMOTION_PROMOTED = "PROMOTION_PROMOTED"
    PROMOTION_ROLLED_BACK = "PROMOTION_ROLLED_BACK"
    PROMOTION_OPERATION_FAILED = "PROMOTION_OPERATION_FAILED"


class EvolutionEvent(BaseModel):
    """A structured evolution observability event."""

    id: str

    event_type: EvolutionEventType

    campaign_id: Optional[str] = None
    proposal_id: Optional[str] = None
    candidate_id: Optional[str] = None

    actor_id: str = "system"

    payload: Dict[str, Any] = Field(default_factory=dict)

    timestamp: str

    previous_event_hash: str
    event_hash: str


class ObservabilityEmitter(Protocol):
    """Abstract observability emitter."""

    def emit(self, event: EvolutionEvent) -> None:
        ...


class LoggingObservabilityEmitter:
    """Logging-based observability emitter."""

    def __init__(self) -> None:
        import logging

        self.logger = logging.getLogger("evolution.observability")

    def emit(self, event: EvolutionEvent) -> None:
        self.logger.info(event.model_dump_json())


class ObservabilityMetrics(BaseModel):
    """Metrics derived from evolution observability events."""

    total_events: int = 0

    events_by_type: Dict[str, int] = Field(default_factory=dict)

    campaign_count: int = 0
    proposal_count: int = 0
    candidate_count: int = 0

    promoted_count: int = 0
    rolled_back_count: int = 0
    governance_denied_count: int = 0
    safety_failed_count: int = 0


class ObservabilityChainReport(BaseModel):
    """Report describing observability hash-chain integrity."""

    valid: bool
    event_count: int
    first_invalid_event_id: Optional[str] = None


class InMemoryObservabilityStore:
    """In-memory observability event store."""

    def __init__(self) -> None:
        self.events: List[EvolutionEvent] = []
        self.last_event_hash: str = "genesis"

    def add(self, event: EvolutionEvent) -> None:
        self.events.append(event)
        self.last_event_hash = event.event_hash

    def list_events(
        self,
        campaign_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvolutionEvent]:
        results: List[EvolutionEvent] = []

        for event in reversed(self.events):
            if campaign_id and event.campaign_id != campaign_id:
                continue

            if proposal_id and event.proposal_id != proposal_id:
                continue

            if candidate_id and event.candidate_id != candidate_id:
                continue

            if event_type and event.event_type.value != event_type:
                continue

            results.append(event)

            if len(results) >= limit:
                break

        return results


class EvolutionObservabilityBus:
    """Coordinates evolution observability events."""

    def __init__(
        self,
        store: Optional[InMemoryObservabilityStore] = None,
        emitters: Optional[List[ObservabilityEmitter]] = None,
    ) -> None:
        self.store = store or InMemoryObservabilityStore()
        self.emitters = emitters or [LoggingObservabilityEmitter()]

    def emit(
        self,
        event_type: EvolutionEventType,
        actor_id: str,
        campaign_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EvolutionEvent:
        timestamp = utcnow().isoformat()

        event_id = deterministic_id(
            "evolution_event",
            {
                "event_type": event_type.value,
                "campaign_id": campaign_id,
                "proposal_id": proposal_id,
                "candidate_id": candidate_id,
                "timestamp": timestamp,
                "previous_event_hash": self.store.last_event_hash,
            },
        )

        event_hash = sha256_hex(
            canonical_json(
                {
                    "event_id": event_id,
                    "event_type": event_type.value,
                    "campaign_id": campaign_id,
                    "proposal_id": proposal_id,
                    "candidate_id": candidate_id,
                    "actor_id": actor_id,
                    "payload": payload or {},
                    "timestamp": timestamp,
                    "previous_event_hash": self.store.last_event_hash,
                }
            )
        )

        event = EvolutionEvent(
            id=event_id,
            event_type=event_type,
            campaign_id=campaign_id,
            proposal_id=proposal_id,
            candidate_id=candidate_id,
            actor_id=actor_id,
            payload=payload or {},
            timestamp=timestamp,
            previous_event_hash=self.store.last_event_hash,
            event_hash=event_hash,
        )

        self.store.add(event)

        for emitter in self.emitters:
            emitter.emit(event)

        return event

    def list_events(
        self,
        campaign_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvolutionEvent]:
        return self.store.list_events(
            campaign_id=campaign_id,
            proposal_id=proposal_id,
            candidate_id=candidate_id,
            event_type=event_type,
            limit=limit,
        )

    def verify_chain(self) -> ObservabilityChainReport:
        previous_hash = "genesis"

        for event in self.store.events:
            if event.previous_event_hash != previous_hash:
                return ObservabilityChainReport(
                    valid=False,
                    event_count=len(self.store.events),
                    first_invalid_event_id=event.id,
                )

            expected_hash = sha256_hex(
                canonical_json(
                    {
                        "event_id": event.id,
                        "event_type": event.event_type.value,
                        "campaign_id": event.campaign_id,
                        "proposal_id": event.proposal_id,
                        "candidate_id": event.candidate_id,
                        "actor_id": event.actor_id,
                        "payload": event.payload,
                        "timestamp": event.timestamp,
                        "previous_event_hash": event.previous_event_hash,
                    }
                )
            )

            if event.event_hash != expected_hash:
                return ObservabilityChainReport(
                    valid=False,
                    event_count=len(self.store.events),
                    first_invalid_event_id=event.id,
                )

            previous_hash = event.event_hash

        return ObservabilityChainReport(
            valid=True,
            event_count=len(self.store.events),
        )

    def metrics(self) -> ObservabilityMetrics:
        events_by_type: Dict[str, int] = {}

        campaign_ids: set[str] = set()
        proposal_ids: set[str] = set()
        candidate_ids: set[str] = set()

        promoted_count = 0
        rolled_back_count = 0
        governance_denied_count = 0
        safety_failed_count = 0

        for event in self.store.events:
            event_type = event.event_type.value

            events_by_type[event_type] = (
                events_by_type.get(event_type, 0) + 1
            )

            if event.campaign_id:
                campaign_ids.add(event.campaign_id)

            if event.proposal_id:
                proposal_ids.add(event.proposal_id)

            if event.candidate_id:
                candidate_ids.add(event.candidate_id)

            if event.event_type == EvolutionEventType.PROMOTION_PROMOTED:
                promoted_count += 1

            if event.event_type == EvolutionEventType.PROMOTION_ROLLED_BACK:
                rolled_back_count += 1

            if event.event_type == EvolutionEventType.PROMOTION_GOVERNANCE_DENIED:
                governance_denied_count += 1

            if event.event_type == EvolutionEventType.PROMOTION_SAFETY_FAILED:
                safety_failed_count += 1

        return ObservabilityMetrics(
            total_events=len(self.store.events),
            events_by_type=events_by_type,
            campaign_count=len(campaign_ids),
            proposal_count=len(proposal_ids),
            candidate_count=len(candidate_ids),
            promoted_count=promoted_count,
            rolled_back_count=rolled_back_count,
            governance_denied_count=governance_denied_count,
            safety_failed_count=safety_failed_count,
        )
