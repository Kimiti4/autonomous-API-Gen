"""Tests for SandboxEvaluator."""

from constitutional_architecture.meta.platform_genome import create_default_genome
from constitutional_architecture.meta.platform_fitness import PlatformFitnessEvaluator
from constitutional_architecture.meta.sandbox_evaluator import SandboxEvaluator


class TestSandboxEvaluator:
    def test_evaluate_approves_improvement(self):
        evaluator = SandboxEvaluator(improvement_threshold=0.0)
        genome = create_default_genome()
        proposed = create_default_genome()
        baseline = {"evolution_success_rate": 0.5, "compilation_success_rate": 0.5,
                    "verification_accuracy": 0.5, "avg_completion_time": 100.0}
        simulated = {"evolution_success_rate": 0.9, "compilation_success_rate": 0.9,
                     "verification_accuracy": 0.9, "avg_completion_time": 50.0}
        result = evaluator.evaluate(genome, proposed, baseline, simulated)
        assert result.passed is True
        assert result.fitness_delta > 0

    def test_evaluate_rejects_degradation(self):
        evaluator = SandboxEvaluator(improvement_threshold=0.0, max_degradation=0.01)
        genome = create_default_genome()
        proposed = create_default_genome()
        baseline = {"evolution_success_rate": 0.9, "compilation_success_rate": 0.9,
                    "verification_accuracy": 0.9, "avg_completion_time": 50.0}
        simulated = {"evolution_success_rate": 0.1, "compilation_success_rate": 0.1,
                     "verification_accuracy": 0.1, "avg_completion_time": 500.0}
        result = evaluator.evaluate(genome, proposed, baseline, simulated)
        assert result.passed is False

    def test_results_history(self):
        evaluator = SandboxEvaluator()
        genome = create_default_genome()
        proposed = create_default_genome()
        baseline = {"evolution_success_rate": 0.5, "compilation_success_rate": 0.5,
                    "verification_accuracy": 0.5, "avg_completion_time": 100.0}
        simulated = {"evolution_success_rate": 0.8, "compilation_success_rate": 0.8,
                     "verification_accuracy": 0.8, "avg_completion_time": 60.0}
        evaluator.evaluate(genome, proposed, baseline, simulated)
        evaluator.evaluate(genome, proposed, baseline, simulated)
        assert len(evaluator.results) == 2
