"""
ASE-OS Engineering Kernel: Universal Engineering Memory (UEM).

The event-sourced "central nervous system" of the platform. Every agent
thought, mutation, simulation, and deployment is an immutable event.

Agents never communicate directly: they observe the UEM and append events.
The Coordinator reads the event stream to synthesize consensus, guaranteeing
reproducibility and auditability of every platform decision.

Constitutional Alignment:
- Axiom VII (Auditability): the UEM is append-only; every transformation is
  recorded and traceable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    INTENT_PARSED = "intent_parsed"
    AGENT_CRITIQUE = "agent_critique"
    GENOME_MUTATED = "genome_mutated"
    SIMULATION_RUN = "simulation_run"
    EXPERIMENT_STARTED = "experiment_started"
    TELEMETRY_INGESTED = "telemetry_ingested"
    CKB_UPDATED = "ckb_updated"


class UEMEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    actor_id: str  # Agent ID, Kernel ID, or System
    target_id: str  # Intent ID, Genome ID, ISR ID
    payload: Dict[str, Any] = Field(default_factory=dict)
    constitutional_proof: Optional[str] = None  # Hash proving governance approval


class UniversalEngineeringMemory:
    """The immutable, append-only memory of the ASE-OS."""

    def __init__(self) -> None:
        self._stream: List[UEMEvent] = []
        self._index: Dict[str, List[UEMEvent]] = {}  # target_id -> events

    def append(self, event: UEMEvent) -> None:
        self._stream.append(event)
        self._index.setdefault(event.target_id, []).append(event)

    def get_lineage(self, target_id: str) -> List[UEMEvent]:
        return list(self._index.get(target_id, []))

    def events_by_type(self, event_type: EventType) -> List[UEMEvent]:
        return [e for e in self._stream if e.event_type == event_type]

    @property
    def events(self) -> List[UEMEvent]:
        return list(self._stream)

    @property
    def size(self) -> int:
        return len(self._stream)
