"""
Meta-Evolution Engine — Top-Level Orchestrator.

Evolves the PLATFORM itself through:
1. Platform Metrics collection
2. Fitness evaluation
3. Genome mutation
4. Sandbox evaluation
5. Safety verification
6. Approval and application
7. Lineage recording

CONSTITUTIONAL CONSTRAINT: This module evolves the PLATFORM, not user software.
It NEVER modifies constitutional layers.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from constitutional_architecture.meta.benchmarking_engine import BenchmarkingEngine
from constitutional_architecture.meta.events import MetaEvent, MetaEventBus, MetaEventType
from constitutional_architecture.meta.platform_fitness import PlatformFitness, PlatformFitnessEvaluator
from constitutional_architecture.meta.platform_genome import PlatformGenome, create_default_genome
from constitutional_architecture.meta.platform_lineage import PlatformLineage
from constitutional_architecture.meta.platform_mutation import PlatformMutation, PlatformMutator
from constitutional_architecture.meta.safety_gate import SafetyGate
from constitutional_architecture.meta.sandbox_evaluator import SandboxEvaluator
from constitutional_architecture.meta.strategy_optimizer import StrategyOptimizer
from constitutional_architecture.meta.compiler_optimizer import CompilerOptimizer
from constitutional_architecture.meta.verification_optimizer import VerificationOptimizer
from constitutional_architecture.meta.scheduler_optimizer import SchedulerOptimizer
from constitutional_architecture.meta.agent_optimizer import AgentOptimizer
from constitutional_architecture.meta.knowledge_optimizer import KnowledgeOptimizer


class MetaEvolutionEngine:
    def __init__(
        self,
        genome: Optional[PlatformGenome] = None,
        event_bus: Optional[MetaEventBus] = None,
    ) -> None:
        self._genome = genome or create_default_genome()
        self._event_bus = event_bus or MetaEventBus()
        self._fitness_evaluator = PlatformFitnessEvaluator()
        self._mutator = PlatformMutator()
        self._safety_gate = SafetyGate()
        self._sandbox = SandboxEvaluator(self._fitness_evaluator)
        self._lineage = PlatformLineage()
        self._benchmarking = BenchmarkingEngine()
        self._strategy_optimizer = StrategyOptimizer(self._mutator)
        self._compiler_optimizer = CompilerOptimizer()
        self._verification_optimizer = VerificationOptimizer()
        self._scheduler_optimizer = SchedulerOptimizer()
        self._agent_optimizer = AgentOptimizer()
        self._knowledge_optimizer = KnowledgeOptimizer()

        self._lineage.record(self._genome, reasoning="Initial platform genome")
        self._safety_gate.push_rollback_point(self._genome)

        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.GENOME_CREATED,
            data={"genome_id": self._genome.genome_id, "version": self._genome.version},
        ))

    def evolve(
        self,
        platform_metrics: dict[str, Any],
        simulated_metrics: Optional[dict[str, Any]] = None,
        strategy: str = "adaptive",
    ) -> tuple[bool, str]:
        current_fitness = self._fitness_evaluator.evaluate(platform_metrics)
        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.FITNESS_EVALUATED,
            data={"composite_score": current_fitness.composite_score},
        ))

        if strategy == "auto":
            strategy = self._strategy_optimizer.recommend_strategy(self._genome)

        try:
            if strategy == "guided":
                gradient = self._compute_gradient(platform_metrics)
                new_genome, mutation = self._mutator.mutate_guided(self._genome, gradient)
            elif strategy == "adaptive":
                new_genome, mutation = self._mutator.mutate_adaptive(self._genome)
            else:
                new_genome, mutation = self._mutator.mutate_random(self._genome)
        except ValueError as e:
            return False, f"Mutation failed: {e}"

        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.GENOME_MUTATED,
            data={"parameter": mutation.parameter_name, "old_value": mutation.old_value, "new_value": mutation.new_value},
        ))

        safety_result = self._safety_gate.check_mutation_safety(self._genome, new_genome)
        if not safety_result.passed:
            self._event_bus.publish(MetaEvent(
                event_type=MetaEventType.SAFETY_CHECK_FAILED,
                data={"violations": list(safety_result.violations)},
            ))
            return False, f"Safety check failed: {'; '.join(safety_result.violations)}"

        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.SAFETY_CHECK_PASSED,
            data={"checks_passed": safety_result.checks_passed},
        ))

        if simulated_metrics is None:
            simulated_metrics = self._simulate_metrics(platform_metrics, mutation)

        sandbox_result = self._sandbox.evaluate(
            self._genome, new_genome, platform_metrics, simulated_metrics
        )

        if not sandbox_result.passed:
            self._event_bus.publish(MetaEvent(
                event_type=MetaEventType.SANDBOX_FAILED,
                data={"fitness_delta": sandbox_result.fitness_delta},
            ))
            self._mutator.record_outcome(mutation.id, success=False)
            return False, f"Sandbox evaluation failed: fitness delta = {sandbox_result.fitness_delta:.4f}"

        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.SANDBOX_COMPLETED,
            data={"fitness_delta": sandbox_result.fitness_delta},
        ))

        self._mutator.record_outcome(mutation.id, success=True)
        self._safety_gate.push_rollback_point(self._genome)
        old_genome = self._genome
        self._genome = new_genome

        if sandbox_result.fitness_before and sandbox_result.fitness_after:
            self._benchmarking.benchmark(
                old_genome.version, new_genome.version,
                sandbox_result.fitness_before, sandbox_result.fitness_after,
            )

        self._lineage.record(
            new_genome, mutation=mutation,
            fitness_score=sandbox_result.fitness_after.composite_score if sandbox_result.fitness_after else 0.0,
            sandbox_passed=True, reasoning=mutation.reasoning,
        )

        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.PLATFORM_EVOLVED,
            data={"version": new_genome.version, "parameter": mutation.parameter_name,
                  "fitness_delta": sandbox_result.fitness_delta},
        ))

        return True, (
            f"Platform evolved: {mutation.parameter_name} "
            f"{mutation.old_value} \u2192 {mutation.new_value} "
            f"(fitness delta: {sandbox_result.fitness_delta:.4f})"
        )

    def rollback(self) -> tuple[bool, str]:
        previous = self._safety_gate.rollback()
        if previous is None:
            return False, "No rollback point available"
        self._genome = previous
        self._event_bus.publish(MetaEvent(
            event_type=MetaEventType.PLATFORM_ROLLBACK,
            data={"version": previous.version},
        ))
        return True, f"Rolled back to genome version {previous.version}"

    def _compute_gradient(self, metrics: dict[str, Any]) -> dict[str, float]:
        gradient: dict[str, float] = {}
        for param in self._genome.get_mutable_parameters():
            gradient[param.id] = param.sensitivity * 0.1
        return gradient

    def _simulate_metrics(self, baseline_metrics: dict[str, Any], mutation: PlatformMutation) -> dict[str, Any]:
        simulated = dict(baseline_metrics)
        param = self._genome.get_parameter(mutation.parameter_id)
        if param:
            improvement = param.sensitivity * 0.02
            if param.category.value == "evolution":
                simulated["evolution_success_rate"] = min(1.0, simulated.get("evolution_success_rate", 0.5) + improvement)
            elif param.category.value == "compilation":
                simulated["compilation_success_rate"] = min(1.0, simulated.get("compilation_success_rate", 0.5) + improvement)
            elif param.category.value == "verification":
                simulated["verification_accuracy"] = min(1.0, simulated.get("verification_accuracy", 0.5) + improvement)
        return simulated

    @property
    def genome(self) -> PlatformGenome:
        return self._genome

    @property
    def fitness_evaluator(self) -> PlatformFitnessEvaluator:
        return self._fitness_evaluator

    @property
    def safety_gate(self) -> SafetyGate:
        return self._safety_gate

    @property
    def lineage(self) -> PlatformLineage:
        return self._lineage

    @property
    def benchmarking(self) -> BenchmarkingEngine:
        return self._benchmarking

    @property
    def can_rollback(self) -> bool:
        return self._safety_gate.can_rollback

    def get_parameter(self, param_id: str) -> Any:
        param = self._genome.get_parameter(param_id)
        return param.value if param else None

    def subscribe(self, event_type: MetaEventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)
