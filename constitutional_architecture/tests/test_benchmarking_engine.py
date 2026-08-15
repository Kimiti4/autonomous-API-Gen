"""Tests for BenchmarkingEngine."""

from constitutional_architecture.meta.benchmarking_engine import BenchmarkingEngine
from constitutional_architecture.meta.platform_fitness import PlatformFitness


class TestBenchmarkingEngine:
    def test_benchmark_improvement(self):
        engine = BenchmarkingEngine()
        fb = PlatformFitness(evolution_success_rate=0.5, compilation_success_rate=0.5,
                             verification_accuracy=0.5, deployment_success_rate=0.5)
        fa = PlatformFitness(evolution_success_rate=0.9, compilation_success_rate=0.9,
                             verification_accuracy=0.9, deployment_success_rate=0.9)
        result = engine.benchmark(1, 2, fb, fa)
        assert result.improvement > 0
        assert len(result.dimensions_improved) > 0

    def test_benchmark_degradation(self):
        engine = BenchmarkingEngine()
        fb = PlatformFitness(evolution_success_rate=0.9, compilation_success_rate=0.9,
                             verification_accuracy=0.9, deployment_success_rate=0.9)
        fa = PlatformFitness(evolution_success_rate=0.1, compilation_success_rate=0.1,
                             verification_accuracy=0.1, deployment_success_rate=0.1)
        result = engine.benchmark(1, 2, fb, fa)
        assert result.improvement < 0
        assert len(result.dimensions_degraded) > 0

    def test_average_improvement(self):
        engine = BenchmarkingEngine()
        fb = PlatformFitness(evolution_success_rate=0.5, compilation_success_rate=0.5,
                             verification_accuracy=0.5, deployment_success_rate=0.5)
        fa = PlatformFitness(evolution_success_rate=0.7, compilation_success_rate=0.7,
                             verification_accuracy=0.7, deployment_success_rate=0.7)
        engine.benchmark(1, 2, fb, fa)
        engine.benchmark(2, 3, fa, fb)
        assert engine.average_improvement == 0.0

    def test_get_best_mutation(self):
        engine = BenchmarkingEngine()
        fb = PlatformFitness(evolution_success_rate=0.5, compilation_success_rate=0.5,
                             verification_accuracy=0.5, deployment_success_rate=0.5)
        fa_good = PlatformFitness(evolution_success_rate=0.9, compilation_success_rate=0.9,
                                  verification_accuracy=0.9, deployment_success_rate=0.9)
        fa_bad = PlatformFitness(evolution_success_rate=0.1, compilation_success_rate=0.1,
                                 verification_accuracy=0.1, deployment_success_rate=0.1)
        engine.benchmark(1, 2, fb, fa_good)
        engine.benchmark(2, 3, fa_good, fa_bad)
        best = engine.get_best_mutation()
        assert best is not None
        assert best.genome_version_after == 2
