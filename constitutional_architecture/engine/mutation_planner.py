"""
Mutation Planner.

Plans mutation sequences by composing operators whose preconditions
chain correctly. Consults the Knowledge Base for successful sequences.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.engine.adaptive_mutation import AdaptiveMutation
from constitutional_architecture.engine.evolution_memory import EvolutionMemory
from constitutional_architecture.engine.mutation_registry import MutationRegistry
from constitutional_architecture.isr.eir.taxonomy import MutationClass
from constitutional_architecture.isr.graph.typed_graph import TypedGraph


@dataclass(frozen=True)
class MutationStep:
    operator_id: str
    target_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MutationPlan:
    steps: tuple[MutationStep, ...] = ()
    rationale: str = ""
    expected_impact: dict[str, float] = field(default_factory=dict)
    intermediate_validation: bool = True
    source: str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)


class MutationPlanner:
    """
    Plans mutation sequences.

    Strategies:
    1. Query memory for successful sequences in similar contexts
    2. Compose operators whose preconditions chain correctly
    3. Fall back to random single mutations

    The planner makes evolution increasingly informed rather than
    purely stochastic.
    """

    def __init__(
        self,
        registry: MutationRegistry,
        adaptive: AdaptiveMutation,
        memory: EvolutionMemory,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._registry = registry
        self._adaptive = adaptive
        self._memory = memory
        self._rng = rng or random.Random()

    def plan(
        self,
        graph: TypedGraph,
        max_steps: int = 3,
        allowed_classes: Optional[set[MutationClass]] = None,
    ) -> MutationPlan:
        plan = self._plan_from_memory(graph, max_steps)
        if plan and plan.step_count > 0:
            return plan

        return self._plan_random(graph, max_steps, allowed_classes)

    def _plan_from_memory(self, graph: TypedGraph, max_steps: int) -> Optional[MutationPlan]:
        successful = self._memory.query_successful(limit=20)
        if not successful:
            return None

        entry = self._rng.choice(successful)
        mutation_type = entry.content.get("mutation_type", "")
        if not mutation_type or mutation_type not in self._registry:
            return None

        operator = self._registry.get(mutation_type)
        if operator is None:
            return None

        target = self._find_target(graph, operator)
        if target is None:
            return None

        return MutationPlan(
            steps=(MutationStep(operator_id=mutation_type, target_id=target),),
            rationale=f"From memory: '{mutation_type}' succeeded with delta={entry.fitness_impact:.3f}",
            expected_impact={"composite": entry.fitness_impact},
            source="memory",
        )

    def _plan_random(
        self,
        graph: TypedGraph,
        max_steps: int,
        allowed_classes: Optional[set[MutationClass]] = None,
    ) -> MutationPlan:
        weights = self._adaptive.get_weights()
        if not weights:
            all_ops = self._registry.all_identifiers
            if not all_ops:
                return MutationPlan()
            weights = {op: 1.0 for op in all_ops}

        if allowed_classes:
            weights = {
                op: w for op, w in weights.items()
                if (self._registry.get(op) and self._registry.get(op).mutation_class in allowed_classes)
            }

        if not weights:
            return MutationPlan()

        steps: list[MutationStep] = []
        for _ in range(max_steps):
            operators = list(weights.keys())
            w = [weights[op] for op in operators]
            selected = self._rng.choices(operators, weights=w, k=1)[0]
            operator = self._registry.get(selected)
            if operator is None:
                continue

            target = self._find_target(graph, operator)
            if target is None:
                continue

            steps.append(MutationStep(operator_id=selected, target_id=target))

        return MutationPlan(
            steps=tuple(steps),
            rationale="Adaptive-weighted random selection",
            source="planner",
        )

    def _find_target(self, graph: TypedGraph, operator: Any) -> Optional[str]:
        candidates = [
            node.id for node in graph.nodes()
            if not operator.affected_node_types
            or node.node_type.value in operator.affected_node_types
        ]
        if not candidates:
            return None
        return self._rng.choice(candidates)
