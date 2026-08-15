"""
Evolution Engine 2.0 — Top-Level Orchestrator.

This is the main entry point. It coordinates all subsystems:
population management, mutation, crossover, selection, fitness,
diversity, adaptation, convergence detection, and lineage tracking.

CONSTITUTIONAL CONSTRAINT: This module imports ONLY from isr.* and engine.*.
It NEVER imports from compiler.*, backends.*, or generators.*.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.engine.adaptive_mutation import AdaptiveMutation
from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.convergence_detector import ConvergenceDetector, ConvergenceStatus
from constitutional_architecture.engine.crossover_engine import CrossoverEngine
from constitutional_architecture.engine.diversity_manager import DiversityManager
from constitutional_architecture.engine.elite_manager import EliteManager
from constitutional_architecture.engine.evolution_events import EventBus, EventType, EvolutionEvent
from constitutional_architecture.engine.evolution_memory import EvolutionMemory
from constitutional_architecture.engine.evolution_metrics import GenerationMetrics, MetricsCollector
from constitutional_architecture.engine.evolution_scheduler import EvolutionScheduler
from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual
from constitutional_architecture.engine.isr_adapter import evaluate_fitness, graph_to_isr, isr_to_graph
from constitutional_architecture.engine.lineage_tracker import LineageTracker
from constitutional_architecture.engine.mutation_engine import MutationEngine
from constitutional_architecture.engine.mutation_operators import register_all_operators
from constitutional_architecture.engine.mutation_planner import MutationPlanner
from constitutional_architecture.engine.mutation_registry import MutationRegistry
from constitutional_architecture.engine.mutation_validator import MutationValidator
from constitutional_architecture.engine.novelty_search import NoveltySearch
from constitutional_architecture.engine.pareto_optimizer import ParetoOptimizer, ParetoFront
from constitutional_architecture.engine.population_manager import PopulationManager
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.metrics.static_fitness import StaticFitnessEvaluator
from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class GenerationResult:
    generation: int
    population_size: int
    best_fitness: float
    mean_fitness: float
    diversity: float
    pareto_front_size: int
    phase: str
    convergence: ConvergenceStatus
    metrics: GenerationMetrics


@dataclass(frozen=True)
class EvolutionResult:
    run_id: str
    generations_completed: int
    best_individual: Optional[Individual]
    pareto_front: ParetoFront
    total_mutations: int
    mutation_success_rate: float
    fitness_improvement: float
    final_phase: str
    lineage_records: int


class EvolutionEngine:
    """
    Evolution Engine 2.0.

    Continuously improves software architectures represented as
    immutable ISR graphs. Maximises architectural quality using
    evolutionary algorithms, adaptive learning, and multi-objective
    optimisation.

    Every mutation produces a new ISR version.
    No mutation may modify an existing ISR.
    The engine contains ZERO framework-specific knowledge.
    """

    def __init__(
        self,
        config: EvolutionConfig,
        mutation_registry: Optional[MutationRegistry] = None,
        event_bus: Optional[EventBus] = None,
        memory: Optional[EvolutionMemory] = None,
    ) -> None:
        self._config = config
        self._rng = random.Random(config.seed)
        self._event_bus = event_bus or EventBus()

        self._registry = mutation_registry or MutationRegistry()
        self._validator = MutationValidator()
        self._mutation_engine = MutationEngine(
            registry=self._registry,
            validator=self._validator,
            event_bus=self._event_bus,
            rng=self._rng,
        )
        self._crossover_engine = CrossoverEngine(
            event_bus=self._event_bus,
            rng=self._rng,
        )
        self._population_manager = PopulationManager(config, rng=self._rng)
        self._pareto = ParetoOptimizer(use_composite=True)
        self._elite_manager = EliteManager(elite_count=config.elite_count)
        self._diversity_manager = DiversityManager(config)
        self._novelty_search = NoveltySearch()
        self._adaptive = AdaptiveMutation(config)
        self._convergence_detector = ConvergenceDetector(config)
        self._scheduler = EvolutionScheduler(config, self._event_bus)
        self._memory = memory or EvolutionMemory()
        self._lineage = LineageTracker()
        self._metrics = MetricsCollector()
        self._fitness_evaluator = StaticFitnessEvaluator()
        self._planner = MutationPlanner(
            registry=self._registry,
            adaptive=self._adaptive,
            memory=self._memory,
            rng=self._rng,
        )

        self._initialised = False
        self._stopped = False
        self._current_pareto_front: Optional[ParetoFront] = None

    # --- Lifecycle ---

    def initialise(self, seed_isr: ISR) -> None:
        self._population_manager.initialise(seed_isr)
        self._initialised = True
        self._stopped = False

        for op_id in self._registry.all_identifiers:
            self._adaptive.register_operator(op_id)

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.POPULATION_CREATED,
            generation=0,
            data={"population_size": self._config.population_size},
        ))

    def run(self, generations: Optional[int] = None) -> EvolutionResult:
        if not self._initialised:
            raise RuntimeError("Engine not initialised. Call initialise() first.")

        max_gen = generations or self._config.max_generations
        run_id = self._config.run_id or f"run-{uuid.uuid4().hex[:12]}"

        for _ in range(max_gen):
            if self._stopped:
                break
            self.step()

            convergence = self._convergence_detector.update(
                self._population_manager.stats().mean_fitness,
                self._population_manager.stats().max_fitness,
            )
            if convergence.is_stagnant and self._scheduler.current_phase.value == "refinement":
                break

        return self._build_result(run_id)

    def step(self) -> GenerationResult:
        if not self._initialised:
            raise RuntimeError("Engine not initialised.")

        start_time = time.perf_counter()
        generation = self._population_manager.generation

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.GENERATION_STARTED,
            generation=generation,
        ))

        self._evaluate_population()

        elites = self._elite_manager.update(self._population_manager.population)

        self._current_pareto_front = self._pareto.compute_front(
            self._population_manager.population, generation
        )

        population = self._diversity_manager.speciate(self._population_manager.population)
        self._population_manager.set_population(population)
        diversity = self._diversity_manager.compute_diversity(population)
        entropy = self._diversity_manager.compute_entropy(population)

        population = self._novelty_search.update_novelty_scores(population)
        self._population_manager.set_population(population)

        pop_stats = self._population_manager.stats()
        convergence = self._convergence_detector.update(pop_stats.mean_fitness, pop_stats.max_fitness)
        phase = self._scheduler.update(generation, diversity, convergence)

        new_population = self._produce_next_generation(generation)

        new_population = self._elite_manager.inject(new_population)

        self._population_manager.set_population(new_population)
        self._population_manager.advance_generation()

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        gen_metrics = GenerationMetrics(
            generation=generation,
            population_size=pop_stats.size,
            mean_fitness=pop_stats.mean_fitness,
            max_fitness=pop_stats.max_fitness,
            min_fitness=pop_stats.min_fitness,
            diversity=diversity,
            entropy=entropy,
            mutation_success_rate=self._metrics.metrics.overall_mutation_success_rate,
            species_count=self._diversity_manager.species_count,
            convergence_status=convergence.recommendation,
            generation_time_ms=elapsed_ms,
        )
        self._metrics.record_generation(gen_metrics, pop_stats)

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.GENERATION_COMPLETED,
            generation=generation,
            data={
                "best_fitness": pop_stats.max_fitness,
                "diversity": diversity,
                "phase": phase.value,
            },
        ))

        return GenerationResult(
            generation=generation,
            population_size=pop_stats.size,
            best_fitness=pop_stats.max_fitness,
            mean_fitness=pop_stats.mean_fitness,
            diversity=diversity,
            pareto_front_size=self._current_pareto_front.size if self._current_pareto_front else 0,
            phase=phase.value,
            convergence=convergence,
            metrics=gen_metrics,
        )

    def stop(self) -> None:
        self._stopped = True
        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.EVOLUTION_STOPPED,
            generation=self._population_manager.generation,
        ))

    # --- Internal ---

    def _evaluate_population(self) -> None:
        population = self._population_manager.population
        evaluated: list[Individual] = []

        for ind in population:
            fitness = self._compute_fitness(ind.isr)
            evaluated.append(ind.with_fitness(fitness))

        self._population_manager.set_population(evaluated)

    def _compute_fitness(self, isr: ISR) -> FitnessVector:
        return evaluate_fitness(isr)

    def _produce_next_generation(self, generation: int) -> list[Individual]:
        new_population: list[Individual] = []
        target_size = self._config.population_size
        mutation_count = 0
        crossover_count = 0

        while len(new_population) < target_size:
            if self._rng.random() < self._scheduler.effective_crossover_rate:
                try:
                    parent_a, parent_b = self._population_manager.select_pair()
                    child = Individual(
                        id=f"ind-{uuid.uuid4().hex[:12]}",
                        isr=parent_a.isr,
                        fitness=parent_a.fitness,
                        parent_ids=(parent_a.id, parent_b.id),
                        generation=generation + 1,
                    )
                    new_population.append(child)
                    crossover_count += 1
                    self._metrics.record_crossover()
                    self._lineage.record(child, reasoning="crossover")
                except ValueError:
                    pass
            else:
                parent = self._population_manager.select()
                child = self._mutate_individual(parent, generation)
                new_population.append(child)
                mutation_count += 1

        return new_population[:target_size]

    def _mutate_individual(self, parent: Individual, generation: int) -> Individual:
        graph = isr_to_graph(parent.isr)

        operator_ids = list(self._registry.all_identifiers)
        if not operator_ids:
            new_isr = parent.isr.with_system(parent.isr.system)
            child = Individual(
                id=f"ind-{uuid.uuid4().hex[:12]}",
                isr=new_isr,
                fitness=parent.fitness,
                parent_ids=(parent.id,),
                generation=generation + 1,
                mutation_history=parent.mutation_history,
            )
            return child

        op_id = self._rng.choice(operator_ids)
        op_spec = self._registry.get(op_id)
        if op_spec is None or op_spec.apply_fn is None:
            new_isr = parent.isr.with_system(parent.isr.system)
            child = Individual(
                id=f"ind-{uuid.uuid4().hex[:12]}",
                isr=new_isr,
                fitness=parent.fitness,
                parent_ids=(parent.id,),
                generation=generation + 1,
                mutation_history=parent.mutation_history,
            )
            return child

        candidates = list(graph._nodes.keys())
        target_id = self._rng.choice(candidates) if candidates else ""

        if op_spec.precondition_fn and not op_spec.precondition_fn(graph, target_id):
            candidates = [nid for nid in candidates if op_spec.precondition_fn(graph, nid)]
            target_id = self._rng.choice(candidates) if candidates else ""
            if not target_id:
                new_isr = parent.isr.with_system(parent.isr.system)
                child = Individual(
                    id=f"ind-{uuid.uuid4().hex[:12]}",
                    isr=new_isr,
                    fitness=parent.fitness,
                    parent_ids=(parent.id,),
                    generation=generation + 1,
                    mutation_history=parent.mutation_history,
                )
                return child

        params = {}
        new_graph, result_meta = op_spec.apply_fn(graph, target_id, params)
        fitness_before = parent.fitness.to_dict()

        try:
            new_isr = graph_to_isr(new_graph, parent.isr)
        except (ValueError, KeyError, IndexError):
            new_isr = parent.isr.with_system(parent.isr.system)

        child = Individual(
            id=f"ind-{uuid.uuid4().hex[:12]}",
            isr=new_isr,
            fitness=parent.fitness,
            parent_ids=(parent.id,),
            generation=generation + 1,
            mutation_history=parent.mutation_history + (op_id,),
        )

        self._lineage.record(
            child,
            mutation_applied=op_id,
            fitness_before=fitness_before,
            reasoning=f"Applied '{op_spec.description}' to {target_id}",
            run_id=self._config.run_id,
        )

        self._event_bus.publish(EvolutionEvent(
            event_type=EventType.MUTATION_APPLIED,
            generation=generation,
            data={
                "operator": op_id,
                "target": target_id,
                "parent_id": parent.id,
                "child_id": child.id,
                "success": True,
            },
        ))

        return child

    def _build_result(self, run_id: str) -> EvolutionResult:
        best = self._population_manager.get_best(1)
        best_individual = best[0] if best else None

        return EvolutionResult(
            run_id=run_id,
            generations_completed=self._population_manager.generation,
            best_individual=best_individual,
            pareto_front=self._current_pareto_front or ParetoFront(),
            total_mutations=self._metrics.metrics.total_mutations,
            mutation_success_rate=self._metrics.metrics.overall_mutation_success_rate,
            fitness_improvement=self._metrics.metrics.fitness_improvement,
            final_phase=self._scheduler.current_phase.value,
            lineage_records=self._lineage.total_records,
        )

    # --- Public API ---

    def get_population(self) -> list[Individual]:
        return self._population_manager.population

    def get_pareto_front(self) -> Optional[ParetoFront]:
        return self._current_pareto_front

    def get_elites(self) -> list[Individual]:
        return self._elite_manager.elites

    def get_best(self, objective: Optional[str] = None) -> Optional[Individual]:
        best = self._population_manager.get_best(1)
        return best[0] if best else None

    def get_lineage(self, individual_id: str) -> list:
        return self._lineage.get_ancestors(individual_id)

    def explain(self, individual_id: str) -> str:
        entry = self._lineage.get_entry(individual_id)
        if entry is None:
            return f"No lineage record for '{individual_id}'"
        mutations = self._lineage.get_mutation_history(individual_id)
        return (
            f"Individual {individual_id} (gen {entry.generation}): "
            f"ISR hash={entry.isr_hash[:12]}, "
            f"mutations={mutations}, "
            f"reasoning={entry.reasoning}"
        )

    def subscribe(self, event_type: EventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)

    @property
    def metrics(self):
        return self._metrics.metrics

    @property
    def config(self) -> EvolutionConfig:
        return self._config
