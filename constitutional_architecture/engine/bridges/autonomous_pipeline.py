from typing import Any

from constitutional_architecture.engine.bridges.compiler_bridge import CompilerBridge
from constitutional_architecture.engine.bridges.fitness_bridge import FitnessBridge
from constitutional_architecture.engine.bridges.verification_bridge import VerificationBridge
from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.evolution_loop import EvolutionLoop
from constitutional_architecture.engine.mutation_operators import register_all_operators
from constitutional_architecture.engine.mutation_registry import MutationRegistry
from constitutional_architecture.isr.eir.model import EIR
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.verification.verification_result import VerificationLevel
from constitutional_architecture.verification.verification_report import VerificationReport


class AutonomousPipeline:
    def __init__(
        self,
        config: EvolutionConfig,
        verification_level: VerificationLevel = VerificationLevel.L2_BEHAVIOURAL,
    ) -> None:
        self._config = config
        self._registry = MutationRegistry()
        register_all_operators(self._registry)
        self._loop = EvolutionLoop(config=config, registry=self._registry)
        self._compiler = CompilerBridge()
        self._verifier = VerificationBridge(minimum_level=verification_level)
        self._fitness = FitnessBridge()
        self._history: list[dict[str, Any]] = []

    def run(self, seed_isr: ISR, generations: int | None = None) -> ISR:
        evolved_isr, eirs = self._loop.evolve(seed_isr)

        compiled = self._compiler.compile(evolved_isr)
        vresult = self._verifier.verify(evolved_isr)
        vfitness = self._verifier.to_fitness(vresult, static_fitness=self._fitness.evaluate(evolved_isr))

        self._history.append({
            "generations": generations or self._config.max_generations,
            "seed_hash": seed_isr.content_hash[:12],
            "evolved_hash": evolved_isr.content_hash[:12],
            "eir_count": len(eirs),
            "compilation_passed": compiled.success if hasattr(compiled, "success") else True,
            "verification_passed": vresult.approved_for_deployment,
            "verification_fitness": vfitness.to_dict(),
        })

        return evolved_isr

    def run_with_feedback(
        self,
        seed_isr: ISR,
        fitness_feedback: dict[str, float] | None = None,
        generations: int | None = None,
    ) -> ISR:
        evolved_isr, eirs = self._loop.evolve_with_feedback(seed_isr, fitness_feedback)

        compiled = self._compiler.compile(evolved_isr)
        vresult = self._verifier.verify(evolved_isr)
        vfitness = self._verifier.to_fitness(vresult, static_fitness=self._fitness.evaluate(evolved_isr))

        self._history.append({
            "generations": generations or self._config.max_generations,
            "seed_hash": seed_isr.content_hash[:12],
            "evolved_hash": evolved_isr.content_hash[:12],
            "eir_count": len(eirs),
            "compilation_passed": compiled.success if hasattr(compiled, "success") else True,
            "verification_passed": vresult.approved_for_deployment,
            "verification_fitness": vfitness.to_dict(),
        })

        return evolved_isr

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    @property
    def loop(self) -> EvolutionLoop:
        return self._loop

    @property
    def registry(self) -> MutationRegistry:
        return self._registry
