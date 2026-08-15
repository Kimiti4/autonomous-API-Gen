"""
Evolution Events.

Event bus for the evolution engine. All lifecycle events are published here.
Consumers (dashboards, logging, knowledge base, multi-agent coordinators)
subscribe without coupling to engine internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable, Optional

from constitutional_architecture.engine.fitness import FitnessVector


@unique
class EventType(str, Enum):
    """All evolution event types."""

    POPULATION_CREATED = "population_created"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    MUTATION_APPLIED = "mutation_applied"
    MUTATION_REJECTED = "mutation_rejected"
    CROSSOVER_APPLIED = "crossover_applied"
    NEW_ELITE_FOUND = "new_elite_found"
    PARETO_UPDATED = "pareto_updated"
    NOVEL_ARCHITECTURE_DISCOVERED = "novel_architecture_discovered"
    CONVERGENCE_DETECTED = "convergence_detected"
    PHASE_TRANSITION = "phase_transition"
    ADAPTIVE_WEIGHTS_UPDATED = "adaptive_weights_updated"
    SPECIES_CREATED = "species_created"
    SPECIES_EXTINCT = "species_extinct"
    EVOLUTION_COMPLETED = "evolution_completed"
    EVOLUTION_STOPPED = "evolution_stopped"
    FITNESS_EVALUATED = "fitness_evaluated"
    KNOWLEDGE_BASE_CONSULTED = "knowledge_base_consulted"


@dataclass(frozen=True)
class EvolutionEvent:
    """Base event published by the evolution engine."""

    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generation: int = 0
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return f"[{self.event_type.value}] gen={self.generation}"


@dataclass(frozen=True)
class MutationAppliedEvent(EvolutionEvent):
    parent_id: str = ""
    child_id: str = ""
    mutation_type: str = ""
    eir_id: str = ""
    fitness_delta: dict[str, float] = field(default_factory=dict)
    explanation: str = ""


@dataclass(frozen=True)
class MutationRejectedEvent(EvolutionEvent):
    individual_id: str = ""
    mutation_type: str = ""
    reason: str = ""


@dataclass(frozen=True)
class NewEliteFoundEvent(EvolutionEvent):
    individual_id: str = ""
    fitness: dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0


@dataclass(frozen=True)
class ConvergenceDetectedEvent(EvolutionEvent):
    metric: str = ""
    value: float = 0.0
    generations_stagnant: int = 0


@dataclass(frozen=True)
class PhaseTransitionEvent(EvolutionEvent):
    from_phase: str = ""
    to_phase: str = ""
    reason: str = ""


class EventBus:
    """
    Simple synchronous event bus for evolution lifecycle events.

    Decouples the engine from observers. Consumers subscribe to
    specific event types without coupling to engine internals.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[EvolutionEvent], None]]] = {}
        self._global_handlers: list[Callable[[EvolutionEvent], None]] = []
        self._history: list[EvolutionEvent] = []
        self._max_history: int = 10000

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[EvolutionEvent], None],
    ) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable[[EvolutionEvent], None]) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: EvolutionEvent) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[EvolutionEvent]:
        return list(self._history)

    def get_events(self, event_type: EventType) -> list[EvolutionEvent]:
        return [e for e in self._history if e.event_type == event_type]

    def clear_history(self) -> None:
        self._history.clear()
