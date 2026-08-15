"""
Explicit Type Rules.

Documents all valid and explicitly invalid type combinations
for reference and testing.
"""

from __future__ import annotations

from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType

INVALID_COMBINATIONS: list[tuple[NodeType, EdgeType, NodeType, str]] = [
    (
        NodeType.ENTITY, EdgeType.DEPENDS_ON, NodeType.SERVICE,
        "Entities cannot depend on services; services depend on entities",
    ),
    (
        NodeType.INTERFACE, EdgeType.IMPLEMENTS, NodeType.POLICY,
        "Interfaces are secured-by policies, not implementing them",
    ),
    (
        NodeType.EVENT, EdgeType.EMITS, NodeType.SERVICE,
        "Events do not emit services; services emit events",
    ),
    (
        NodeType.FIELD, EdgeType.DEPENDS_ON, NodeType.SERVICE,
        "Fields cannot have service dependencies",
    ),
    (
        NodeType.POLICY, EdgeType.SECURED_BY, NodeType.INTERFACE,
        "Policies do not get secured by interfaces; interfaces are secured by policies",
    ),
    (
        NodeType.SERVICE, EdgeType.ORCHESTRATES, NodeType.WORKFLOW,
        "Services do not orchestrate workflows; workflows orchestrate services",
    ),
    (
        NodeType.DEPLOYMENT, EdgeType.DEPENDS_ON, NodeType.SERVICE,
        "Deployment does not depend on services; services deploy to deployment",
    ),
]

VALID_COMBINATIONS: list[tuple[NodeType, EdgeType, NodeType, str]] = [
    (
        NodeType.SERVICE, EdgeType.DEPENDS_ON, NodeType.SERVICE,
        "Services can depend on other services",
    ),
    (
        NodeType.MODULE, EdgeType.OWNS, NodeType.ENTITY,
        "Modules own entities",
    ),
    (
        NodeType.SERVICE, EdgeType.EMITS, NodeType.EVENT,
        "Services emit events",
    ),
    (
        NodeType.SERVICE, EdgeType.CONSUMES, NodeType.EVENT,
        "Services consume events",
    ),
    (
        NodeType.INTERFACE, EdgeType.SECURED_BY, NodeType.POLICY,
        "Interfaces are secured by policies",
    ),
    (
        NodeType.WORKFLOW, EdgeType.ORCHESTRATES, NodeType.SERVICE,
        "Workflows orchestrate services",
    ),
    (
        NodeType.SERVICE, EdgeType.IMPLEMENTS, NodeType.INTERFACE,
        "Services implement interfaces",
    ),
    (
        NodeType.SERVICE, EdgeType.DEPLOYS_TO, NodeType.DEPLOYMENT,
        "Services deploy to infrastructure",
    ),
    (
        NodeType.ENTITY, EdgeType.REFERENCES, NodeType.ENTITY,
        "Entities reference other entities",
    ),
]
