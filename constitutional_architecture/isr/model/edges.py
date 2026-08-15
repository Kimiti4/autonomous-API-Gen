"""
ISR Edge Types with full definitions and meta-model.

Defines the enumeration of all valid edge types and their constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional

from constitutional_architecture.isr.model.nodes import NodeType


@unique
class EdgeType(str, Enum):
    OWNS = "owns"
    DEPENDS_ON = "depends_on"
    EMITS = "emits"
    CONSUMES = "consumes"
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    SECURED_BY = "secured_by"
    DEPLOYS_TO = "deploys_to"
    ORCHESTRATES = "orchestrates"
    CONSTRAINS = "constrains"
    CONTAINS = "contains"
    TRANSITIONS_TO = "transitions_to"
    TRIGGERS = "triggers"
    VALIDATES = "validates"
    DOCUMENTS = "documents"
    TESTS = "tests"

    def __str__(self) -> str:
        return self.value


@unique
class CouplingStrength(str, Enum):
    TIGHT = "tight"
    MODERATE = "moderate"
    LOOSE = "loose"
    NONE = "none"


@unique
class CommunicationMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


@unique
class Criticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EdgeAttributes:
    coupling_strength: CouplingStrength = CouplingStrength.MODERATE
    communication_mode: CommunicationMode = CommunicationMode.SYNC
    criticality: Criticality = Criticality.MEDIUM
    latency_budget_ms: Optional[float] = None
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeDefinition:
    edge_type: EdgeType
    valid_sources: frozenset[NodeType]
    valid_targets: frozenset[NodeType]
    min_cardinality: int = 0
    max_cardinality: int = -1
    description: str = ""

    def is_valid_connection(self, source: NodeType, target: NodeType) -> bool:
        return source in self.valid_sources and target in self.valid_targets


EDGE_DEFINITIONS: dict[EdgeType, EdgeDefinition] = {
    EdgeType.OWNS: EdgeDefinition(
        edge_type=EdgeType.OWNS,
        valid_sources=frozenset({
            NodeType.SYSTEM, NodeType.MODULE, NodeType.ENTITY,
            NodeType.SERVICE, NodeType.WORKFLOW, NodeType.POLICY,
            NodeType.INTERFACE, NodeType.DEPLOYMENT,
        }),
        valid_targets=frozenset({
            NodeType.MODULE, NodeType.ENTITY, NodeType.SERVICE,
            NodeType.WORKFLOW, NodeType.POLICY, NodeType.INTERFACE,
            NodeType.FIELD, NodeType.OPERATION, NodeType.STATE,
            NodeType.RULE, NodeType.PERMISSION, NodeType.ENDPOINT,
            NodeType.EVENT, NodeType.CONSTRAINT, NodeType.DEPLOYMENT,
            NodeType.CONFIGURATION, NodeType.DOCUMENTATION, NodeType.TEST_STRATEGY,
        }),
        description="Containment / responsibility relationship",
    ),
    EdgeType.DEPENDS_ON: EdgeDefinition(
        edge_type=EdgeType.DEPENDS_ON,
        valid_sources=frozenset({NodeType.SERVICE, NodeType.MODULE, NodeType.WORKFLOW}),
        valid_targets=frozenset({NodeType.SERVICE, NodeType.MODULE, NodeType.INTERFACE}),
        description="Runtime or build dependency",
    ),
    EdgeType.EMITS: EdgeDefinition(
        edge_type=EdgeType.EMITS,
        valid_sources=frozenset({NodeType.SERVICE, NodeType.WORKFLOW}),
        valid_targets=frozenset({NodeType.EVENT}),
        description="Produces a domain event",
    ),
    EdgeType.CONSUMES: EdgeDefinition(
        edge_type=EdgeType.CONSUMES,
        valid_sources=frozenset({NodeType.SERVICE, NodeType.WORKFLOW}),
        valid_targets=frozenset({NodeType.EVENT}),
        description="Subscribes to a domain event",
    ),
    EdgeType.REFERENCES: EdgeDefinition(
        edge_type=EdgeType.REFERENCES,
        valid_sources=frozenset({NodeType.ENTITY, NodeType.FIELD}),
        valid_targets=frozenset({NodeType.ENTITY}),
        description="Data relationship between entities",
    ),
    EdgeType.IMPLEMENTS: EdgeDefinition(
        edge_type=EdgeType.IMPLEMENTS,
        valid_sources=frozenset({NodeType.SERVICE}),
        valid_targets=frozenset({NodeType.INTERFACE}),
        description="Realises an interface contract",
    ),
    EdgeType.SECURED_BY: EdgeDefinition(
        edge_type=EdgeType.SECURED_BY,
        valid_sources=frozenset({NodeType.INTERFACE, NodeType.ENDPOINT, NodeType.SERVICE}),
        valid_targets=frozenset({NodeType.POLICY}),
        description="Protected by a security policy",
    ),
    EdgeType.DEPLOYS_TO: EdgeDefinition(
        edge_type=EdgeType.DEPLOYS_TO,
        valid_sources=frozenset({NodeType.SERVICE, NodeType.MODULE, NodeType.SYSTEM}),
        valid_targets=frozenset({NodeType.DEPLOYMENT}),
        description="Infrastructure binding",
    ),
    EdgeType.ORCHESTRATES: EdgeDefinition(
        edge_type=EdgeType.ORCHESTRATES,
        valid_sources=frozenset({NodeType.WORKFLOW}),
        valid_targets=frozenset({NodeType.SERVICE, NodeType.OPERATION}),
        description="Workflow coordination of services",
    ),
    EdgeType.CONSTRAINS: EdgeDefinition(
        edge_type=EdgeType.CONSTRAINS,
        valid_sources=frozenset({NodeType.CONSTRAINT, NodeType.POLICY}),
        valid_targets=frozenset({
            NodeType.ENTITY, NodeType.SERVICE, NodeType.INTERFACE,
            NodeType.MODULE, NodeType.FIELD, NodeType.ENDPOINT,
        }),
        description="Applies a rule or constraint",
    ),
    EdgeType.CONTAINS: EdgeDefinition(
        edge_type=EdgeType.CONTAINS,
        valid_sources=frozenset({
            NodeType.SYSTEM, NodeType.MODULE, NodeType.ENTITY,
            NodeType.SERVICE, NodeType.WORKFLOW, NodeType.POLICY,
            NodeType.INTERFACE, NodeType.DEPLOYMENT,
        }),
        valid_targets=frozenset({
            NodeType.MODULE, NodeType.ENTITY, NodeType.SERVICE,
            NodeType.WORKFLOW, NodeType.POLICY, NodeType.INTERFACE,
            NodeType.FIELD, NodeType.OPERATION, NodeType.STATE,
            NodeType.TRANSITION, NodeType.RULE, NodeType.PERMISSION,
            NodeType.ENDPOINT, NodeType.EVENT, NodeType.CONSTRAINT,
            NodeType.CONFIGURATION, NodeType.DOCUMENTATION, NodeType.TEST_STRATEGY,
        }),
        description="Structural containment",
    ),
    EdgeType.TRANSITIONS_TO: EdgeDefinition(
        edge_type=EdgeType.TRANSITIONS_TO,
        valid_sources=frozenset({NodeType.STATE}),
        valid_targets=frozenset({NodeType.STATE}),
        description="State machine transition",
    ),
    EdgeType.TRIGGERS: EdgeDefinition(
        edge_type=EdgeType.TRIGGERS,
        valid_sources=frozenset({NodeType.TRANSITION, NodeType.EVENT}),
        valid_targets=frozenset({NodeType.OPERATION, NodeType.SERVICE, NodeType.WORKFLOW}),
        description="Triggers an action",
    ),
    EdgeType.VALIDATES: EdgeDefinition(
        edge_type=EdgeType.VALIDATES,
        valid_sources=frozenset({NodeType.CONSTRAINT, NodeType.RULE}),
        valid_targets=frozenset({NodeType.FIELD, NodeType.ENTITY, NodeType.OPERATION}),
        description="Validates a field or operation",
    ),
    EdgeType.DOCUMENTS: EdgeDefinition(
        edge_type=EdgeType.DOCUMENTS,
        valid_sources=frozenset({NodeType.DOCUMENTATION}),
        valid_targets=frozenset({
            NodeType.SYSTEM, NodeType.MODULE, NodeType.ENTITY,
            NodeType.SERVICE, NodeType.INTERFACE, NodeType.WORKFLOW,
        }),
        description="Documents an architectural element",
    ),
    EdgeType.TESTS: EdgeDefinition(
        edge_type=EdgeType.TESTS,
        valid_sources=frozenset({NodeType.TEST_STRATEGY}),
        valid_targets=frozenset({
            NodeType.SERVICE, NodeType.ENTITY, NodeType.INTERFACE,
            NodeType.WORKFLOW, NodeType.MODULE,
        }),
        description="Tests an architectural element",
    ),
}