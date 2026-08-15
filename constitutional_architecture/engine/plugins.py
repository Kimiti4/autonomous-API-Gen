"""
Plugin System.

Supports plugins for mutation operators, fitness evaluators,
crossover strategies, diversity algorithms, selection algorithms,
and optimisation algorithms. No engine modification required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Protocol

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual
from constitutional_architecture.engine.mutation_registry import MutationOperatorSpec, MutationRegistry
from constitutional_architecture.isr.graph.typed_graph import TypedGraph


class EvolutionPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def register(self, registry: "PluginRegistry") -> None:
        ...

    def capabilities(self) -> set[str]:
        return set()


class FitnessEvaluatorPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def evaluate(self, graph: TypedGraph) -> dict[str, float]:
        ...


class SelectionAlgorithmPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def select(self, population: list[Individual], **kwargs: Any) -> Individual:
        ...


class CrossoverStrategyPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def crossover(
        self, parent_a: TypedGraph, parent_b: TypedGraph, **kwargs: Any
    ) -> Optional[TypedGraph]:
        ...


class PluginRegistry:
    """
    Central plugin registry.

    All extension points are registered here. No engine modification
    is required to add new capabilities.
    """

    def __init__(self) -> None:
        self._mutation_registry: Optional[MutationRegistry] = None
        self._fitness_evaluators: dict[str, FitnessEvaluatorPlugin] = {}
        self._selection_algorithms: dict[str, SelectionAlgorithmPlugin] = {}
        self._crossover_strategies: dict[str, CrossoverStrategyPlugin] = {}
        self._plugins: dict[str, EvolutionPlugin] = {}

    def set_mutation_registry(self, registry: MutationRegistry) -> None:
        self._mutation_registry = registry

    def register_mutation_operator(self, operator: MutationOperatorSpec) -> None:
        if self._mutation_registry:
            self._mutation_registry.register(operator)

    def register_fitness_evaluator(self, evaluator: FitnessEvaluatorPlugin) -> None:
        self._fitness_evaluators[evaluator.name] = evaluator

    def register_selection_algorithm(self, algorithm: SelectionAlgorithmPlugin) -> None:
        self._selection_algorithms[algorithm.name] = algorithm

    def register_crossover_strategy(self, strategy: CrossoverStrategyPlugin) -> None:
        self._crossover_strategies[strategy.name] = strategy

    def register_plugin(self, plugin: EvolutionPlugin) -> None:
        self._plugins[plugin.name] = plugin
        plugin.register(self)

    def get_fitness_evaluator(self, name: str) -> Optional[FitnessEvaluatorPlugin]:
        return self._fitness_evaluators.get(name)

    def get_selection_algorithm(self, name: str) -> Optional[SelectionAlgorithmPlugin]:
        return self._selection_algorithms.get(name)

    def get_crossover_strategy(self, name: str) -> Optional[CrossoverStrategyPlugin]:
        return self._crossover_strategies.get(name)

    @property
    def registered_plugins(self) -> list[str]:
        return list(self._plugins.keys())
