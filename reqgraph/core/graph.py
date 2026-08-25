"""Requirement Graph: typed directed graph of problem-space knowledge."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    MUST = "must"
    SHOULD = "should"
    COULD = "could"


class RequirementKind(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    DOMAIN_CONCEPT = "domain_concept"
    STAKEHOLDER = "stakeholder"
    CONSTRAINT = "constraint"


class RequirementNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: RequirementKind
    statement: str = Field(min_length=1)
    priority: Priority
    acceptance_criteria: Sequence[str] = Field(default_factory=list)
    ambiguity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    resolution_ref: str | None = None
    source_refs: Sequence[str] = Field(default_factory=list)
    properties: Mapping[str, Any] = Field(default_factory=dict)


class RequirementEdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    REFINES = "refines"
    OWNED_BY = "owned_by"


class RequirementEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: RequirementEdgeType
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    resolution_ref: str | None = None


class RequirementGraph(BaseModel):
    """Immutable, content-addressed requirement graph."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(min_length=1)
    nodes: Mapping[str, RequirementNode] = Field(default_factory=dict)
    edges: Mapping[str, RequirementEdge] = Field(default_factory=dict)
