"""
Traceability and impact explanation models.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RelationHop(BaseModel):
    """One hop in a trace or impact path."""

    relation_id: str
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    propagation: Literal["forward", "reverse", "both", "unknown"] = "unknown"
    weight: float = 1.0
    reason: Optional[str] = None


class ImpactRequest(BaseModel):
    """Request to compute impact from or toward an entity."""

    entity_id: str

    mode: Literal[
        "forward",
        "backward",
    ] = "forward"

    depth: int = Field(default=3, ge=1, le=6)
    min_score: float = Field(default=0.05, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=1000)

    relation_types: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)

    include_explanations: bool = True
    redact_sensitive: bool = True


class ImpactEntry(BaseModel):
    """A single impacted entity."""

    entity_id: str
    name: str
    entity_type: str

    score: float
    depth: int

    direct: bool
    transitive: bool

    hops: list[RelationHop] = Field(default_factory=list)
    path_entity_ids: list[str] = Field(default_factory=list)

    explanation: Optional[str] = None


class ImpactMetadata(BaseModel):
    """Metadata for an impact result."""

    root_entity_id: str
    mode: str
    depth: int
    min_score: float
    node_count: int
    excluded_sensitive_count: int
    generated_at: str


class ImpactResult(BaseModel):
    """Impact analysis result."""

    metadata: ImpactMetadata
    entries: list[ImpactEntry] = Field(default_factory=list)


class PathExplanationRequest(BaseModel):
    """Request to explain paths between two entities."""

    source_entity_id: str
    target_entity_id: str

    depth: int = Field(default=5, ge=1, le=8)
    max_paths: int = Field(default=3, ge=1, le=10)

    relation_types: list[str] = Field(default_factory=list)

    include_provenance: bool = False
    redact_sensitive: bool = True


class PathExplanation(BaseModel):
    """An explained path between two entities."""

    path_id: str

    source_entity_id: str
    target_entity_id: str

    entity_ids: list[str] = Field(default_factory=list)
    relation_ids: list[str] = Field(default_factory=list)

    hops: list[RelationHop] = Field(default_factory=list)

    confidence: float = 0.0
    human_summary: str = ""

    evidence_refs: list[Any] = Field(default_factory=list)


class PathExplanationMetadata(BaseModel):
    """Metadata for path explanation."""

    source_entity_id: str
    target_entity_id: str
    path_count: int
    excluded_sensitive_count: int
    generated_at: str


class PathExplanationResult(BaseModel):
    """Path explanation result."""

    metadata: PathExplanationMetadata
    paths: list[PathExplanation] = Field(default_factory=list)
