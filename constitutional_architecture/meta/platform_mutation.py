"""
Platform Mutation.

Mutates platform parameters (not ISR).
Each mutation produces a new Platform Genome version.

Constitutional constraint: Locked parameters CANNOT be mutated.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.meta.platform_genome import (
    GenomeParameter, ParameterCategory, ParameterType, PlatformGenome,
)


@dataclass(frozen=True)
class PlatformMutation:
    id: str
    parameter_id: str
    parameter_name: str
    old_value: Any
    new_value: Any
    category: ParameterCategory
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reasoning: str = ""
    fitness_delta: float = 0.0
    accepted: bool = False


class PlatformMutator:
    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._history: list[PlatformMutation] = []
        self._success_rates: dict[str, float] = {}

    def mutate_random(self, genome: PlatformGenome) -> tuple[PlatformGenome, PlatformMutation]:
        mutable = genome.get_mutable_parameters()
        if not mutable:
            raise ValueError("No mutable parameters available")
        weights = [p.mutation_rate for p in mutable]
        total = sum(weights)
        if total == 0:
            param = self._rng.choice(mutable)
        else:
            param = self._rng.choices(mutable, weights=weights, k=1)[0]
        new_value = self._perturb_value(param)
        new_genome = genome.with_parameter(param.id, new_value)
        mutation = PlatformMutation(
            id=f"pmut-{uuid.uuid4().hex[:8]}",
            parameter_id=param.id, parameter_name=param.name,
            old_value=param.value, new_value=new_value, category=param.category,
            reasoning="Random perturbation",
        )
        self._history.append(mutation)
        return new_genome, mutation

    def mutate_guided(self, genome: PlatformGenome, fitness_gradient: dict[str, float]) -> tuple[PlatformGenome, PlatformMutation]:
        mutable = genome.get_mutable_parameters()
        if not mutable:
            raise ValueError("No mutable parameters available")
        best_param = None
        best_gradient = 0.0
        for param in mutable:
            gradient = fitness_gradient.get(param.id, 0.0)
            if abs(gradient) > abs(best_gradient):
                best_param = param
                best_gradient = gradient
        if best_param is None:
            return self.mutate_random(genome)
        new_value = self._move_toward(best_param, best_gradient)
        new_genome = genome.with_parameter(best_param.id, new_value)
        mutation = PlatformMutation(
            id=f"pmut-{uuid.uuid4().hex[:8]}",
            parameter_id=best_param.id, parameter_name=best_param.name,
            old_value=best_param.value, new_value=new_value, category=best_param.category,
            reasoning=f"Guided by fitness gradient: {best_gradient:.4f}",
            fitness_delta=best_gradient,
        )
        self._history.append(mutation)
        return new_genome, mutation

    def mutate_adaptive(self, genome: PlatformGenome) -> tuple[PlatformGenome, PlatformMutation]:
        mutable = genome.get_mutable_parameters()
        if not mutable:
            raise ValueError("No mutable parameters available")
        weights = [self._success_rates.get(p.id, 0.5) * p.mutation_rate for p in mutable]
        total = sum(weights)
        if total == 0:
            param = self._rng.choice(mutable)
        else:
            param = self._rng.choices(mutable, weights=weights, k=1)[0]
        new_value = self._perturb_value(param)
        new_genome = genome.with_parameter(param.id, new_value)
        mutation = PlatformMutation(
            id=f"pmut-{uuid.uuid4().hex[:8]}",
            parameter_id=param.id, parameter_name=param.name,
            old_value=param.value, new_value=new_value, category=param.category,
            reasoning=f"Adaptive (success rate: {self._success_rates.get(param.id, 0.5):.2f})",
        )
        self._history.append(mutation)
        return new_genome, mutation

    def record_outcome(self, mutation_id: str, success: bool) -> None:
        for mutation in self._history:
            if mutation.id == mutation_id:
                param_id = mutation.parameter_id
                current_rate = self._success_rates.get(param_id, 0.5)
                self._success_rates[param_id] = current_rate * 0.9 + (0.1 if success else 0.0)
                break

    def _perturb_value(self, param: GenomeParameter) -> Any:
        if param.param_type == ParameterType.FLOAT:
            scale = (param.max_value - param.min_value) * 0.1 if param.max_value and param.min_value else 0.1
            new_value = param.value + self._rng.gauss(0, scale)
            if param.min_value is not None:
                new_value = max(param.min_value, new_value)
            if param.max_value is not None:
                new_value = min(param.max_value, new_value)
            return round(new_value, 4)
        elif param.param_type == ParameterType.INT:
            scale = max(1, int((param.max_value - param.min_value) * 0.1)) if param.max_value and param.min_value else 1
            new_value = param.value + self._rng.randint(-scale, scale)
            if param.min_value is not None:
                new_value = max(int(param.min_value), new_value)
            if param.max_value is not None:
                new_value = min(int(param.max_value), new_value)
            return new_value
        elif param.param_type == ParameterType.BOOL:
            return not param.value
        elif param.param_type == ParameterType.STRING:
            if param.allowed_values:
                return self._rng.choice(param.allowed_values)
            return param.value
        return param.value

    def _move_toward(self, param: GenomeParameter, gradient: float) -> Any:
        if param.param_type in (ParameterType.FLOAT, ParameterType.INT):
            step = 0.05 * (param.max_value - param.min_value) if param.max_value and param.min_value else 0.05
            direction = 1.0 if gradient > 0 else -1.0
            new_value = param.value + direction * step
            if param.param_type == ParameterType.INT:
                new_value = int(round(new_value))
            if param.min_value is not None:
                new_value = max(param.min_value, new_value)
            if param.max_value is not None:
                new_value = min(param.max_value, new_value)
            return new_value
        return self._perturb_value(param)

    @property
    def history(self) -> list[PlatformMutation]:
        return list(self._history)

    @property
    def success_rates(self) -> dict[str, float]:
        return dict(self._success_rates)
