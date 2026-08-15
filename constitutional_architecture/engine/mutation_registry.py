"""
Mutation Registry.

Central registry for all typed mutation operators.
Supports plugin registration without engine modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass
from constitutional_architecture.isr.graph.typed_graph import TypedGraph


@dataclass(frozen=True)
class MutationOperatorSpec:
    identifier: str
    category: MutationCategory
    mutation_class: MutationClass
    description: str
    risk_level: str = "medium"
    affected_node_types: tuple[str, ...] = ()
    affected_edge_types: tuple[str, ...] = ()
    estimated_complexity: float = 0.5
    expected_fitness_impact: dict[str, float] = field(default_factory=dict)
    reversible: bool = True
    inverse_operator: Optional[str] = None
    required_capabilities: tuple[str, ...] = ()

    precondition_fn: Optional[Callable[[TypedGraph, str], bool]] = None
    apply_fn: Optional[Callable[[TypedGraph, str, dict[str, Any]], tuple[TypedGraph, dict]]] = None
    postcondition_fn: Optional[Callable[[TypedGraph], bool]] = None
    explain_fn: Optional[Callable[[TypedGraph, str, dict[str, Any]], str]] = None


class MutationRegistry:
    """
    Central registry for mutation operators.

    Supports:
    - Registration of new operators (plugin architecture)
    - Query by category, class, risk level
    - Lookup by identifier
    - Enumeration for adaptive weight management

    No engine modification is required to add new operators.
    """

    def __init__(self) -> None:
        self._operators: dict[str, MutationOperatorSpec] = {}
        self._by_category: dict[MutationCategory, list[str]] = {}
        self._by_class: dict[MutationClass, list[str]] = {}

    def register(self, operator: MutationOperatorSpec) -> None:
        if operator.identifier in self._operators:
            raise ValueError(f"Operator '{operator.identifier}' already registered")
        self._operators[operator.identifier] = operator
        self._by_category.setdefault(operator.category, []).append(operator.identifier)
        self._by_class.setdefault(operator.mutation_class, []).append(operator.identifier)

    def unregister(self, identifier: str) -> None:
        if identifier not in self._operators:
            raise ValueError(f"Operator '{identifier}' not found")
        op = self._operators[identifier]
        del self._operators[identifier]
        if identifier in self._by_category.get(op.category, []):
            self._by_category[op.category].remove(identifier)
        if identifier in self._by_class.get(op.mutation_class, []):
            self._by_class[op.mutation_class].remove(identifier)

    def get(self, identifier: str) -> Optional[MutationOperatorSpec]:
        return self._operators.get(identifier)

    def get_by_category(self, category: MutationCategory) -> list[MutationOperatorSpec]:
        ids = self._by_category.get(category, [])
        return [self._operators[i] for i in ids]

    def get_by_class(self, mutation_class: MutationClass) -> list[MutationOperatorSpec]:
        ids = self._by_class.get(mutation_class, [])
        return [self._operators[i] for i in ids]

    def get_by_risk(self, max_risk: str) -> list[MutationOperatorSpec]:
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_level = risk_order.get(max_risk, 3)
        return [
            op for op in self._operators.values()
            if risk_order.get(op.risk_level, 1) <= max_level
        ]

    @property
    def all_identifiers(self) -> list[str]:
        return list(self._operators.keys())

    @property
    def count(self) -> int:
        return len(self._operators)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._operators

    def __len__(self) -> int:
        return len(self._operators)
