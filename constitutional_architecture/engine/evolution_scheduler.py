"""
Evolution Scheduler.

Manages evolution phases: exploration, exploitation, diversification, refinement.
Resolves the tension between novelty search and convergence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import Optional

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.convergence_detector import ConvergenceStatus
from constitutional_architecture.engine.evolution_events import EventBus, EventType, EvolutionEvent


@unique
class EvolutionPhase(str, Enum):
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    DIVERSIFICATION = "diversification"
    REFINEMENT = "refinement"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhaseConfig:
    mutation_rate_multiplier: float = 1.0
    crossover_rate_multiplier: float = 1.0
    selection_pressure: float = 1.0
    novelty_weight: float = 0.0
    allow_structural_mutations: bool = True
    allow_parametric_mutations: bool = True


PHASE_CONFIGS: dict[EvolutionPhase, PhaseConfig] = {
    EvolutionPhase.EXPLORATION: PhaseConfig(
        mutation_rate_multiplier=1.5,
        crossover_rate_multiplier=0.8,
        selection_pressure=0.5,
        novelty_weight=0.3,
        allow_structural_mutations=True,
        allow_parametric_mutations=True,
    ),
    EvolutionPhase.EXPLOITATION: PhaseConfig(
        mutation_rate_multiplier=0.7,
        crossover_rate_multiplier=1.2,
        selection_pressure=2.0,
        novelty_weight=0.05,
        allow_structural_mutations=False,
        allow_parametric_mutations=True,
    ),
    EvolutionPhase.DIVERSIFICATION: PhaseConfig(
        mutation_rate_multiplier=2.0,
        crossover_rate_multiplier=0.5,
        selection_pressure=0.3,
        novelty_weight=0.5,
        allow_structural_mutations=True,
        allow_parametric_mutations=True,
    ),
    EvolutionPhase.REFINEMENT: PhaseConfig(
        mutation_rate_multiplier=0.3,
        crossover_rate_multiplier=0.5,
        selection_pressure=1.5,
        novelty_weight=0.0,
        allow_structural_mutations=False,
        allow_parametric_mutations=True,
    ),
}


class EvolutionScheduler:
    """
    Manages evolution phase transitions.

    Phase logic:
    - EXPLORATION: Early generations, high diversity -> explore broadly
    - EXPLOITATION: Diversity dropping, fitness improving -> exploit best
    - DIVERSIFICATION: Convergence detected, fitness plateau -> inject novelty
    - REFINEMENT: Fitness near maximum -> fine-tune parametrically
    """

    def __init__(self, config: EvolutionConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._current_phase = EvolutionPhase.EXPLORATION
        self._generation_in_phase = 0
        self._phase_history: list[tuple[int, EvolutionPhase]] = [(0, EvolutionPhase.EXPLORATION)]

    @property
    def current_phase(self) -> EvolutionPhase:
        return self._current_phase

    @property
    def phase_config(self) -> PhaseConfig:
        return PHASE_CONFIGS[self._current_phase]

    def update(
        self,
        generation: int,
        diversity: float,
        convergence: ConvergenceStatus,
        fitness_near_max: bool = False,
    ) -> EvolutionPhase:
        self._generation_in_phase += 1
        previous_phase = self._current_phase

        if convergence.is_stagnant:
            self._transition_to(EvolutionPhase.DIVERSIFICATION, generation, "stagnation detected")
        elif convergence.is_converged and not fitness_near_max:
            self._transition_to(EvolutionPhase.DIVERSIFICATION, generation, "premature convergence")
        elif fitness_near_max:
            self._transition_to(EvolutionPhase.REFINEMENT, generation, "fitness near maximum")
        elif diversity < self._config.diversity_threshold and self._current_phase == EvolutionPhase.EXPLORATION:
            self._transition_to(EvolutionPhase.EXPLOITATION, generation, "diversity dropped")
        elif diversity > self._config.diversity_threshold * 2 and self._current_phase == EvolutionPhase.EXPLOITATION:
            self._transition_to(EvolutionPhase.EXPLORATION, generation, "diversity restored")
        elif (self._current_phase == EvolutionPhase.DIVERSIFICATION and
              self._generation_in_phase > 10 and diversity > self._config.diversity_threshold):
            self._transition_to(EvolutionPhase.EXPLOITATION, generation, "diversification successful")

        return self._current_phase

    def _transition_to(self, new_phase: EvolutionPhase, generation: int, reason: str) -> None:
        if new_phase == self._current_phase:
            return

        old_phase = self._current_phase
        self._current_phase = new_phase
        self._generation_in_phase = 0
        self._phase_history.append((generation, new_phase))

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.PHASE_TRANSITION,
            generation=generation,
            data={
                "from_phase": old_phase.value,
                "to_phase": new_phase.value,
                "reason": reason,
            },
        ))

    @property
    def effective_mutation_rate(self) -> float:
        return self._config.mutation_rate * self.phase_config.mutation_rate_multiplier

    @property
    def effective_crossover_rate(self) -> float:
        return self._config.crossover_rate * self.phase_config.crossover_rate_multiplier

    @property
    def phase_history(self) -> list[tuple[int, EvolutionPhase]]:
        return list(self._phase_history)
