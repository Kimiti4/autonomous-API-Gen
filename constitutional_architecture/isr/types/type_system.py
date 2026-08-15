"""
Architectural Type System.

Defines the formal type rules for the ISR. This is analogous to a
programming language's type system, but for software architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.isr.model.edges import EDGE_DEFINITIONS, EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class TypeRule:
    """A single type rule defining a valid node-edge-node combination."""

    source_type: NodeType
    edge_type: EdgeType
    target_type: NodeType
    description: str = ""

    @property
    def key(self) -> tuple[NodeType, EdgeType, NodeType]:
        return (self.source_type, self.edge_type, self.target_type)


@dataclass(frozen=True)
class TypeViolation:
    """A type system violation."""

    source_id: str
    source_type: NodeType
    edge_type: EdgeType
    target_id: str
    target_type: NodeType
    message: str
    severity: str = "error"
    suggested_fix: str = ""


class ArchitecturalTypeSystem:
    """
    The architectural type system for the ISR.

    This is the equivalent of a compiler's type system. It defines
    which node-edge-node combinations are well-formed and rejects
    those that are not.
    """

    def __init__(self) -> None:
        self._valid_rules: set[tuple[NodeType, EdgeType, NodeType]] = set()
        self._build_rules()

    def _build_rules(self) -> None:
        for edge_type, definition in EDGE_DEFINITIONS.items():
            for source in definition.valid_sources:
                for target in definition.valid_targets:
                    self._valid_rules.add((source, edge_type, target))

    def is_valid_connection(
        self,
        source_type: NodeType,
        edge_type: EdgeType,
        target_type: NodeType,
    ) -> bool:
        return (source_type, edge_type, target_type) in self._valid_rules

    def check_connection(
        self,
        source_id: str,
        source_type: NodeType,
        edge_type: EdgeType,
        target_id: str,
        target_type: NodeType,
    ) -> Optional[TypeViolation]:
        if self.is_valid_connection(source_type, edge_type, target_type):
            return None

        valid_targets = self._get_valid_targets(source_type, edge_type)
        valid_sources = self._get_valid_sources(edge_type, target_type)

        message = (
            f"Invalid edge '{edge_type.value}' from {source_type.value} "
            f"'{source_id}' to {target_type.value} '{target_id}'."
        )

        suggested_fix = ""
        if valid_targets:
            suggested_fix = (
                f"Valid targets for {source_type.value} --{edge_type.value}--> "
                f"are: {', '.join(t.value for t in valid_targets)}."
            )
        elif valid_sources:
            suggested_fix = (
                f"Valid sources for --{edge_type.value}--> {target_type.value} "
                f"are: {', '.join(s.value for s in valid_sources)}."
            )

        return TypeViolation(
            source_id=source_id,
            source_type=source_type,
            edge_type=edge_type,
            target_id=target_id,
            target_type=target_type,
            message=message,
            suggested_fix=suggested_fix,
        )

    def _get_valid_targets(
        self, source_type: NodeType, edge_type: EdgeType
    ) -> set[NodeType]:
        return {
            target
            for (src, edge, target) in self._valid_rules
            if src == source_type and edge == edge_type
        }

    def _get_valid_sources(
        self, edge_type: EdgeType, target_type: NodeType
    ) -> set[NodeType]:
        return {
            source
            for (source, edge, tgt) in self._valid_rules
            if edge == edge_type and tgt == target_type
        }

    @property
    def all_rules(self) -> frozenset[tuple[NodeType, EdgeType, NodeType]]:
        return frozenset(self._valid_rules)
