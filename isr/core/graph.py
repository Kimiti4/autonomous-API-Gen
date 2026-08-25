"""Graph semantics: the typed directed graph taxonomy of the ISR."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


class NodeType(str, Enum):
    DOMAIN = "domain"
    CAPABILITY = "capability"
    SERVICE = "service"
    API = "api"
    DATA_MODEL = "data_model"
    EVENT = "event"
    SECURITY_POLICY = "security_policy"
    INFRASTRUCTURE_TARGET = "infrastructure_target"
    REQUIREMENT_REF = "requirement_ref"


class EdgeType(str, Enum):
    SATISFIES = "satisfies"  # capability -> requirement_ref
    IMPLEMENTED_BY = "implemented_by"  # capability -> service
    EXPOSES = "exposes"  # service -> api
    PERSISTS = "persists"  # service -> data_model
    PUBLISHES = "publishes"  # service -> event
    CONSUMED_BY = "consumed_by"  # event -> service
    DEPENDS_ON = "depends_on"  # service -> service
    SECURED_BY = "secured_by"  # service|api -> security_policy


class Node(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: NodeType
    properties: Mapping[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: EdgeType
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    properties: Mapping[str, Any] = Field(default_factory=dict)


class ISRGraph(BaseModel):
    """The typed directed graph representing the software architecture."""

    model_config = ConfigDict(frozen=True)

    nodes: Mapping[str, Node] = Field(default_factory=dict)
    edges: Mapping[str, Edge] = Field(default_factory=dict)


EDGE_TYPE_COMPATIBILITY: dict[EdgeType, tuple[frozenset[NodeType], frozenset[NodeType]]] = {
    EdgeType.SATISFIES: (
        frozenset({NodeType.CAPABILITY}),
        frozenset({NodeType.REQUIREMENT_REF}),
    ),
    EdgeType.IMPLEMENTED_BY: (
        frozenset({NodeType.CAPABILITY}),
        frozenset({NodeType.SERVICE}),
    ),
    EdgeType.EXPOSES: (
        frozenset({NodeType.SERVICE}),
        frozenset({NodeType.API}),
    ),
    EdgeType.PERSISTS: (
        frozenset({NodeType.SERVICE}),
        frozenset({NodeType.DATA_MODEL}),
    ),
    EdgeType.PUBLISHES: (
        frozenset({NodeType.SERVICE}),
        frozenset({NodeType.EVENT}),
    ),
    EdgeType.CONSUMED_BY: (
        frozenset({NodeType.EVENT}),
        frozenset({NodeType.SERVICE}),
    ),
    EdgeType.DEPENDS_ON: (
        frozenset({NodeType.SERVICE, NodeType.CAPABILITY}),
        frozenset({NodeType.SERVICE, NodeType.CAPABILITY}),
    ),
    EdgeType.SECURED_BY: (
        frozenset({NodeType.SERVICE, NodeType.API}),
        frozenset({NodeType.SECURITY_POLICY}),
    ),
}
