"""Fail-closed evolution invariant: candidate evaluation success is not implementation-generation success.

If the selected best genome cannot be lowered by the backend, the evolution run
must not present a successful candidate. The result must report the build
error with best_genome/best_fitness/production_readiness invalidated rather
than silently degrading into apparent success.
"""

import asyncio

from app.engine.elite_evolution import EliteEvolutionEngine
from app.engine.evolution import EvolutionEngine


def _assert_fail_closed_invariant(result: dict):
    assert result["build_error"] is not None
    assert result["best_genome"] is None
    assert result["best_fitness"] == 0.0
    assert result["production_readiness"] is None
    assert result["output_path"] is None


def test_synchronous_evolution_fails_closed_when_best_not_lowerable():
    result = EvolutionEngine().run_synchronous(generations=2, population_size=4, use_docker=False)
    _assert_fail_closed_invariant(result)


def test_elite_evolution_fails_closed_when_best_not_lowerable():
    result = asyncio.run(
        EliteEvolutionEngine().run_elite_evolution(
            generations=2, population_size=4, use_multi_population=False, seed=7
        )
    )
    _assert_fail_closed_invariant(result)