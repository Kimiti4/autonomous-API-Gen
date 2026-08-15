"""
Transformation Operators.

Defines the typed transformation operators that produce EIRs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass
from constitutional_architecture.isr.graph.typed_graph import TypedGraph


@dataclass(frozen=True)
class TransformationExplanation:
    """Human-readable explanation of a transformation."""

    summary: str
    rationale: str
    expected_impact: dict[str, float]
    risk_assessment: str
    confidence: float
    alternatives_considered: tuple[str, ...] = ()


class TransformationOperator(ABC):
    """
    Base class for all transformation operators.

    Each operator:
    - Checks preconditions
    - Applies the transformation (producing a new graph)
    - Produces an EIR recording what was done
    - Generates an explanation
    """

    @property
    @abstractmethod
    def identifier(self) -> str:
        ...

    @property
    @abstractmethod
    def category(self) -> MutationCategory:
        ...

    @property
    @abstractmethod
    def mutation_class(self) -> MutationClass:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def check_preconditions(self, graph: TypedGraph, target_id: str) -> bool:
        ...

    @abstractmethod
    def apply(
        self, graph: TypedGraph, target_id: str, parameters: dict[str, Any]
    ) -> tuple[TypedGraph, Transformation]:
        ...

    @abstractmethod
    def check_postconditions(self, graph: TypedGraph) -> bool:
        ...

    @abstractmethod
    def explain(
        self, graph: TypedGraph, target_id: str, parameters: dict[str, Any]
    ) -> TransformationExplanation:
        ...

    @property
    def reversible(self) -> bool:
        return True

    @property
    def risk_level(self) -> str:
        return "medium"

    @property
    def expected_fitness_impact(self) -> dict[str, float]:
        return {}
