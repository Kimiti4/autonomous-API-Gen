"""
Core Knowledge Graph models.

These models define the normative runtime contract for entities,
relations, provenance, queries, search, and ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .ids import canonical_json, deterministic_id, sha256_hex


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


class SourceRef(BaseModel):
    """
    A reference to an authoritative source artifact.

    The Knowledge Graph must preserve source provenance.
    """

    source_type: str
    source_id: str
    source_hash: str
    uri: Optional[str] = None
    version: Optional[str] = None

    def sortable_key(self) -> tuple[str, str, str]:
        return (self.source_type, self.source_id, self.source_hash)


class Classification(BaseModel):
    """
    Sensitivity classification for knowledge entities.

    This supports security, privacy, and access-control enforcement.
    """

    sensitivity: Literal[
        "PUBLIC",
        "INTERNAL",
        "CONFIDENTIAL",
        "RESTRICTED",
    ] = "INTERNAL"
    pii: bool = False
    secret: bool = False
    tenant_id: Optional[str] = None


class EntityCreate(BaseModel):
    """Request model for creating a knowledge entity."""

    entity_type: str
    name: str
    namespace: str
    description: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    classification: Classification = Field(default_factory=Classification)
    source_refs: list[SourceRef]

    @model_validator(mode="after")
    def validate_source_refs(self) -> "EntityCreate":
        if not self.source_refs:
            raise ValueError("At least one source_ref is required.")
        return self

    def content_payload(self) -> dict[str, Any]:
        """
        Canonical payload used for content hashing.

        Labels and source refs are sorted to improve determinism.
        """
        source_refs = sorted(
            [ref.model_dump(mode="json") for ref in self.source_refs],
            key=lambda item: (
                item.get("source_type", ""),
                item.get("source_id", ""),
                item.get("source_hash", ""),
            ),
        )

        return {
            "entity_type": self.entity_type,
            "namespace": self.namespace,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "labels": sorted(self.labels),
            "classification": self.classification.model_dump(mode="json"),
            "source_refs": source_refs,
        }

    def compute_content_hash(self) -> str:
        return sha256_hex(canonical_json(self.content_payload()))

    def compute_id(self) -> str:
        return deterministic_id(
            "entity",
            {
                "content_hash": self.compute_content_hash(),
            },
        )


class Entity(EntityCreate):
    """Stored knowledge entity."""

    id: str
    content_hash: str
    status: Literal[
        "ACTIVE",
        "SUPERSEDED",
        "DEPRECATED",
        "QUARANTINED",
    ] = "ACTIVE"
    created_at: datetime


class RelationCreate(BaseModel):
    """Request model for creating a knowledge relation."""

    relation_type: str
    source_entity_id: str
    target_entity_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[SourceRef]

    @model_validator(mode="after")
    def validate_source_refs(self) -> "RelationCreate":
        if not self.source_refs:
            raise ValueError("At least one source_ref is required.")
        return self

    def content_payload(self) -> dict[str, Any]:
        source_refs = sorted(
            [ref.model_dump(mode="json") for ref in self.source_refs],
            key=lambda item: (
                item.get("source_type", ""),
                item.get("source_id", ""),
                item.get("source_hash", ""),
            ),
        )

        return {
            "relation_type": self.relation_type,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "properties": self.properties,
            "source_refs": source_refs,
        }

    def compute_content_hash(self) -> str:
        return sha256_hex(canonical_json(self.content_payload()))

    def compute_id(self) -> str:
        return deterministic_id(
            "relation",
            {
                "content_hash": self.compute_content_hash(),
            },
        )


class Relation(RelationCreate):
    """Stored knowledge relation."""

    id: str
    content_hash: str
    derived: bool = False
    inference_rule_id: Optional[str] = None
    status: Literal[
        "ACTIVE",
        "SUPERSEDED",
        "DEPRECATED",
        "QUARANTINED",
    ] = "ACTIVE"
    created_at: datetime


class GraphSlice(BaseModel):
    """A subset of the graph returned by neighbor, trace, or impact queries."""

    nodes: list[Entity]
    edges: list[Relation]


class GraphPath(BaseModel):
    """A path through the graph."""

    nodes: list[str]
    relations: list[str]


class QueryRequest(BaseModel):
    """Abstract Knowledge Graph query request."""

    query_type: Literal[
        "ENTITY",
        "NEIGHBORS",
        "PATH",
        "TRACE",
        "IMPACT",
        "SEARCH",
    ]

    entity_id: Optional[str] = None
    source_entity_id: Optional[str] = None
    target_entity_id: Optional[str] = None

    entity_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)

    direction: Literal["backward", "forward", "both"] = "both"
    depth: int = Field(default=3, ge=1, le=10)
    text: Optional[str] = None

    include_provenance: bool = False
    limit: int = Field(default=100, ge=1, le=1000)


class SearchRequest(BaseModel):
    """Search request."""

    text: str
    entity_types: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    """A single search result."""

    entity_id: str
    entity_type: str
    name: str
    score: float
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response."""

    results: list[SearchResult]


class IngestRequest(BaseModel):
    """Ingestion request."""

    source_type: str = "ISR_REVISION"
    source_id: str
    source_hash: str
    payload: dict[str, Any]


class IngestionResult(BaseModel):
    """Result of an ingestion job."""

    ingestion_job_id: str
    status: Literal[
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "PARTIALLY_SUCCEEDED",
    ]
    produced_entities: list[str]
    produced_relations: list[str]
