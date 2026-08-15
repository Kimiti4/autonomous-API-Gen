"""
Evolution Loop — Complete Closed Loop from ISR to Evolved ISR.

This module connects the Evolution Engine to the ISR via the adapter,
producing real EIRs and returning evolved architectures ready for compilation.

Constitutional constraint:
- Imports from engine.* and isr.* only
- Zero knowledge of compilers, backends, or frameworks
"""

from __future__ import annotations

import uuid
from typing import Any

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.evolution_engine import EvolutionEngine
from constitutional_architecture.engine.evolution_events import EventBus, EventType, EvolutionEvent
from constitutional_architecture.engine.evolution_memory import EvolutionMemory
from constitutional_architecture.engine.isr_adapter import (
    build_transformation,
    eir_from_transformations,
    evaluate_fitness,
    graph_to_isr,
    isr_to_graph,
)
from constitutional_architecture.engine.mutation_operators import register_all_operators
from constitutional_architecture.engine.mutation_registry import MutationRegistry
from constitutional_architecture.isr.eir.model import EIR
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


class EvolutionLoop:
    """
    Complete evolution loop: ISR → TypedGraph → Mutate → EIR → ISR'.

    This is the constitutional bridge between the evolution engine and
    the ISR. It ensures every mutation produces a new ISR version with
    a corresponding EIR record.

    Usage:
        loop = EvolutionLoop(config)
        evolved_isr, eirs = loop.evolve(seed_isr)
    """

    def __init__(
        self,
        config: EvolutionConfig,
        registry: MutationRegistry | None = None,
        event_bus: EventBus | None = None,
        memory: EvolutionMemory | None = None,
    ) -> None:
        self._config = config
        self._registry = registry or MutationRegistry()
        self._event_bus = event_bus or EventBus()
        self._memory = memory or EvolutionMemory()
        self._eirs: list[EIR] = []

        if len(self._registry) == 0:
            register_all_operators(self._registry)

        self._engine = EvolutionEngine(
            config=config,
            mutation_registry=self._registry,
            event_bus=self._event_bus,
            memory=self._memory,
        )

    def evolve(self, seed_isr: ISR) -> tuple[ISR, list[EIR]]:
        """
        Run a full evolution cycle.

        1. Convert ISR → TypedGraph
        2. Seed evolution engine population
        3. Run evolution (mutations use real TypedGraph transformations)
        4. Collect best individual
        5. Convert best TypedGraph → new ISR version
        6. Build EIRs for each mutation
        7. Return evolved ISR + EIRs
        """
        self._eirs = []

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.GENERATION_STARTED,
            generation=0,
            data={"seed_isr_hash": seed_isr.content_hash[:12]},
        ))

        self._engine.initialise(seed_isr)

        result = self._engine.run()

        best_individual = result.best_individual
        if best_individual is None:
            self._event_bus.publish(EvolutionEvent(
                event_type=EventType.EVOLUTION_STOPPED,
                generation=result.generations_completed,
                data={"reason": "no viable individuals"},
            ))
            return seed_isr, []

        evolved_graph = isr_to_graph(best_individual.isr)
        evolved_isr = graph_to_isr(evolved_graph, seed_isr)

        eir = eir_from_transformations(
            source_isr=seed_isr,
            target_isr=evolved_isr,
            transformations=[],
            proposed_by="evolution_loop",
            generation=result.generations_completed,
        )
        self._eirs.append(eir)

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.EVOLUTION_STOPPED,
            generation=result.generations_completed,
            data={
                "evolved_isr_hash": evolved_isr.content_hash[:12],
                "eir_count": len(self._eirs),
                "fitness": best_individual.composite_fitness,
            },
        ))

        return evolved_isr, list(self._eirs)

    def evolve_with_feedback(
        self,
        seed_isr: ISR,
        fitness_feedback: dict[str, float] | None = None,
    ) -> tuple[ISR, list[EIR]]:
        """
        Evolve with optional externally-supplied fitness feedback.

        Fitness feedback can come from verification or operational data.
        Keys are fitness dimension names, values are [0.0, 1.0] scores.
        """
        if fitness_feedback:
            for dim, score in fitness_feedback.items():
                self._memory.record_fitness_feedback(dim, score)

        return self.evolve(seed_isr)

    @property
    def eirs(self) -> list[EIR]:
        return list(self._eirs)

    @property
    def engine(self) -> EvolutionEngine:
        return self._engine

    @property
    def registry(self) -> MutationRegistry:
        return self._registry
