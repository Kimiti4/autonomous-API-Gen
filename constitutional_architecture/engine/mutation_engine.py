"""
Mutation Engine.

Executes mutations on ISR graphs, producing new immutable ISR versions
and corresponding EIR records.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.engine.evolution_events import EventBus, EventType, EvolutionEvent
from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.mutation_registry import MutationOperatorSpec, MutationRegistry
from constitutional_architecture.engine.mutation_validator import MutationValidator, MutationValidationResult
from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class MutationResult:
    success: bool
    new_graph: Optional[TypedGraph] = None
    eir: Optional[EIR] = None
    transformation: Optional[Transformation] = None
    explanation: str = ""
    validation: Optional[MutationValidationResult] = None
    operator_id: str = ""
    target_id: str = ""


class MutationEngine:
    """
    Executes mutations on ISR graphs.

    Pipeline:
    1. Select operator (weighted by adaptive probabilities)
    2. Select target node
    3. Check preconditions
    4. Clone graph (immutability)
    5. Apply mutation
    6. Produce EIR
    7. Validate (type system + invariants)
    8. Accept or reject
    9. Record lineage
    10. Publish event
    """

    def __init__(
        self,
        registry: MutationRegistry,
        validator: MutationValidator,
        event_bus: EventBus,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._registry = registry
        self._validator = validator
        self._event_bus = event_bus
        self._rng = rng or random.Random()

    def mutate(
        self,
        graph: TypedGraph,
        operator_id: str,
        target_id: str,
        parameters: Optional[dict[str, Any]] = None,
        isr_source_hash: str = "",
        generation: int = 0,
    ) -> MutationResult:
        params = parameters or {}
        operator = self._registry.get(operator_id)
        if operator is None:
            return MutationResult(
                success=False,
                explanation=f"Unknown operator: {operator_id}",
                operator_id=operator_id,
                target_id=target_id,
            )

        if not self._validator.check_preconditions(operator, graph, target_id):
            self._event_bus.publish(EvolutionEvent(
                event_type=EventType.MUTATION_REJECTED,
                generation=generation,
                data={"operator": operator_id, "target": target_id, "reason": "precondition_failed"},
            ))
            return MutationResult(
                success=False,
                explanation=f"Preconditions not met for '{operator_id}' on '{target_id}'",
                operator_id=operator_id,
                target_id=target_id,
            )

        new_graph = graph.clone()

        transformation_data: dict[str, Any] = {}
        if operator.apply_fn is not None:
            try:
                new_graph, transformation_data = operator.apply_fn(new_graph, target_id, params)
            except Exception as e:
                return MutationResult(
                    success=False,
                    explanation=f"Mutation application failed: {str(e)}",
                    operator_id=operator_id,
                    target_id=target_id,
                )

        validation = self._validator.validate_mutation(operator, graph, new_graph, target_id)
        if not validation.is_valid:
            self._event_bus.publish(EvolutionEvent(
                event_type=EventType.MUTATION_REJECTED,
                generation=generation,
                data={
                    "operator": operator_id,
                    "target": target_id,
                    "reason": validation.rejection_reason,
                },
            ))
            return MutationResult(
                success=False,
                explanation=validation.rejection_reason,
                validation=validation,
                operator_id=operator_id,
                target_id=target_id,
            )

        transformation = Transformation(
            id=f"transform-{uuid.uuid4().hex[:12]}",
            transformation_type=operator_id,
            category=operator.category,
            mutation_class=operator.mutation_class,
            target_node_id=target_id,
            description=operator.description,
            parameters=params,
            fitness_impact=operator.expected_fitness_impact,
            reversible=operator.reversible,
            inverse_transformation=operator.inverse_operator,
            rationale=transformation_data.get("rationale", ""),
            confidence=transformation_data.get("confidence", 0.0),
        )

        eir = EIR(
            id=f"eir-{uuid.uuid4().hex[:12]}",
            source_isr_hash=isr_source_hash,
            transformations=(transformation,),
            proposed_by="mutation_engine",
            generation=generation,
        )

        explanation = operator.description
        if operator.explain_fn is not None:
            explanation = operator.explain_fn(graph, target_id, params)

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.MUTATION_APPLIED,
            generation=generation,
            data={
                "operator": operator_id,
                "target": target_id,
                "eir_id": eir.id,
                "explanation": explanation,
            },
        ))

        return MutationResult(
            success=True,
            new_graph=new_graph,
            eir=eir,
            transformation=transformation,
            explanation=explanation,
            validation=validation,
            operator_id=operator_id,
            target_id=target_id,
        )

    def select_random_target(
        self,
        graph: TypedGraph,
        operator: MutationOperatorSpec,
    ) -> Optional[str]:
        candidates = [
            node.id for node in graph.nodes()
            if node.node_type.value in operator.affected_node_types
            or not operator.affected_node_types
        ]
        if not candidates:
            return None
        return self._rng.choice(candidates)

    def random_mutation(
        self,
        graph: TypedGraph,
        operator_weights: dict[str, float],
        isr_source_hash: str = "",
        generation: int = 0,
    ) -> MutationResult:
        if not operator_weights:
            return MutationResult(success=False, explanation="No operators available")

        operators = list(operator_weights.keys())
        weights = [operator_weights[op] for op in operators]
        total = sum(weights)
        if total == 0:
            return MutationResult(success=False, explanation="All operator weights are zero")

        selected_id = self._rng.choices(operators, weights=weights, k=1)[0]
        operator = self._registry.get(selected_id)
        if operator is None:
            return MutationResult(success=False, explanation=f"Operator '{selected_id}' not found")

        target = self.select_random_target(graph, operator)
        if target is None:
            return MutationResult(
                success=False,
                explanation=f"No valid target for operator '{selected_id}'",
                operator_id=selected_id,
                target_id="",
            )

        return self.mutate(
            graph=graph,
            operator_id=selected_id,
            target_id=target,
            isr_source_hash=isr_source_hash,
            generation=generation,
        )
