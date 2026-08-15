from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.isr_adapter import evaluate_fitness as _evaluate_static
from constitutional_architecture.isr.metrics.static_fitness import StaticFitnessEvaluator
from constitutional_architecture.isr.model.isr import ISR


class FitnessBridge:
    def __init__(self) -> None:
        self._evaluator = StaticFitnessEvaluator()

    def evaluate(self, isr: ISR) -> FitnessVector:
        return _evaluate_static(isr)

    def dimension_names(self) -> list[str]:
        return [
            "complexity", "coupling", "cohesion", "security_coverage",
            "scalability", "reliability", "deployment_completeness",
            "observability", "documentation", "maintainability",
            "extensibility", "architecture_quality",
        ]
