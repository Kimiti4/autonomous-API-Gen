"""
Models for Knowledge Graph learning synchronization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Protocol, Set

from pydantic import BaseModel, Field

from ..utils import utcnow


class KGEntityType(str, Enum):
    TELEMETRY_SIGNAL = "TELEMETRY_SIGNAL"
    ANOMALY = "ANOMALY"
    INCIDENT_CLUSTER = "INCIDENT_CLUSTER"
    LEARNING_INSIGHT = "LEARNING_INSIGHT"
    FITNESS_OBJECTIVE = "FITNESS_OBJECTIVE"


class KGRelationType(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    GROUPED_INTO = "GROUPED_INTO"
    SUPPORTS = "SUPPORTS"
    AFFECTS = "AFFECTS"
    ROOT_CAUSE_OF = "ROOT_CAUSE_OF"


class KGEntityPayload(BaseModel):
    """Payload for upserting a Knowledge Graph entity."""

    id: str
    entity_type: str
    name: str

    namespace: str = "learning"

    properties: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[str] = Field(default_factory=list)


class KGRelationPayload(BaseModel):
    """Payload for upserting a Knowledge Graph relation."""

    id: str
    relation_type: str

    source_entity_id: str
    target_entity_id: str

    properties: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[str] = Field(default_factory=list)


class KnowledgeGraphGateway(Protocol):
    """Abstract Knowledge Graph gateway."""

    def upsert_entity(self, entity: KGEntityPayload) -> Dict:
        ...

    def upsert_relation(self, relation: KGRelationPayload) -> Dict:
        ...


class SyncRegistry(BaseModel):
    """Tracks synchronized learning artifacts to ensure idempotency."""

    synced_signal_ids: Set[str] = Field(default_factory=set)
    synced_anomaly_ids: Set[str] = Field(default_factory=set)
    synced_cluster_ids: Set[str] = Field(default_factory=set)
    synced_insight_ids: Set[str] = Field(default_factory=set)
    synced_objectives: Set[str] = Field(default_factory=set)


class LearningSyncReport(BaseModel):
    """Report produced by a synchronization run."""

    signals_synced: int = 0
    anomalies_synced: int = 0
    clusters_synced: int = 0
    insights_synced: int = 0

    entities_upserted: int = 0
    relations_upserted: int = 0

    synced_at: str = Field(default_factory=lambda: utcnow().isoformat())
