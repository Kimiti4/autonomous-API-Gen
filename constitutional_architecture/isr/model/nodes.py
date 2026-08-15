"""
ISR Node Types.

Defines the enumeration of all valid node types in the ISR graph.
Each node type represents a technology-neutral architectural concept.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class NodeType(str, Enum):
    """All valid node types in the ISR typed graph."""

    SYSTEM = "system"
    MODULE = "module"
    ENTITY = "entity"
    SERVICE = "service"
    WORKFLOW = "workflow"
    POLICY = "policy"
    INTERFACE = "interface"
    EVENT = "event"
    DEPLOYMENT = "deployment"
    CONSTRAINT = "constraint"
    FIELD = "field"
    OPERATION = "operation"
    STATE = "state"
    TRANSITION = "transition"
    RULE = "rule"
    PERMISSION = "permission"
    ENDPOINT = "endpoint"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    TEST_STRATEGY = "test_strategy"

    def __str__(self) -> str:
        return self.value

    @property
    def is_container(self) -> bool:
        """Whether this node type can contain child nodes."""
        return self in {
            NodeType.SYSTEM, NodeType.MODULE, NodeType.ENTITY,
            NodeType.SERVICE, NodeType.WORKFLOW, NodeType.POLICY,
            NodeType.INTERFACE, NodeType.DEPLOYMENT,
        }

    @property
    def is_leaf(self) -> bool:
        """Whether this node type is a terminal node."""
        return self in {
            NodeType.FIELD, NodeType.OPERATION, NodeType.STATE,
            NodeType.RULE, NodeType.PERMISSION, NodeType.ENDPOINT,
            NodeType.CONFIGURATION,
        }