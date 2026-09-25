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


def test_synchronous_evolution_fails_closed_when_best_not_lowerable(monkeypatch):
    async def _fail_evaluation(*args, **kwargs):
        return {
            "build_ok": False,
            "artifact_compile_ok": False,
            "verification_status": "unverified",
            "artifact_digest": None,
            "evaluation_mode": "static_failed",
            "static_score": 0.0,
            "runtime_score": None,
            "error": "cannot lower unmapped capabilities: backends",
        }

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _fail_evaluation)
    result = EvolutionEngine().run_synchronous(generations=2, population_size=4, use_docker=False)
    _assert_fail_closed_invariant(result)


def test_elite_evolution_fails_closed_when_best_not_lowerable(monkeypatch):
    def _fail_lowering(*args, **kwargs):
        raise ValueError("cannot lower unmapped capabilities: backends")

    monkeypatch.setattr("app.engine.elite_evolution.build_genome_output", _fail_lowering)
    result = asyncio.run(
        EliteEvolutionEngine().run_elite_evolution(
            generations=2, population_size=4, use_multi_population=False, seed=7
        )
    )
    _assert_fail_closed_invariant(result)


def test_synchronous_evolution_can_complete_when_random_genomes_are_lowerable():
    result = EvolutionEngine().run_synchronous(generations=1, population_size=3)
    assert result["build_error"] is None
    assert result["best_genome"] is not None
    assert result["best_fitness"] > 0.0
    assert result["production_readiness"] is not None
    assert result["output_path"] is not None

def test_async_evolution_fails_closed_when_runtime_evaluation_fails(monkeypatch):
    async def _runtime_failed(*args, **kwargs):
        return {
            "build_ok": True,
            "evaluation_mode": "runtime_failed",
            "runtime_score": None,
            "static_score": None,
            "error": "container exited non-zero",
        }

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _runtime_failed)
    result = asyncio.run(
        EvolutionEngine().run_async(generations=1, population_size=2, use_docker=True, seed=7)
    )
    _assert_fail_closed_invariant(result)


def test_runtime_failed_candidate_is_never_promoted(monkeypatch):
    async def _runtime_failed(*args, **kwargs):
        return {
            "build_ok": True,
            "evaluation_mode": "runtime_failed",
            "runtime_score": None,
            "static_score": None,
            "error": "container exited non-zero",
        }

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _runtime_failed)
    result = asyncio.run(
        EvolutionEngine().run_async(generations=1, population_size=2, use_docker=True, seed=11)
    )

    assert result["best_genome"] is None
    assert result["best_fitness"] == 0.0
    assert result["production_readiness"] is None
    assert result["output_path"] is None
    assert result["build_error"] is not None



def test_production_promotion_requires_governance_decision(monkeypatch):
    from types import SimpleNamespace

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-1")
    denied_state = SimpleNamespace(current_state="verified", latest_decision=lambda: None)
    governance = SimpleNamespace(
        materialize_candidate=lambda _candidate_id: denied_state
    )
    settings = SimpleNamespace(GOVERNANCE_ENFORCEMENT_REQUIRED=True)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: settings)
    monkeypatch.setattr("app.engine.evolution.get_governance", lambda: governance)

    assert asyncio.run(engine._governance_allows_promotion(genome)) is False


def test_production_promotion_accepts_certified_governance_decision(monkeypatch):
    from types import SimpleNamespace

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-2")
    decision = SimpleNamespace(verdict="approve", authorizesTransition=True)
    allowed_state = SimpleNamespace(
        current_state="certified", latest_decision=lambda: decision
    )
    governance = SimpleNamespace(
        materialize_candidate=lambda _candidate_id: allowed_state
    )
    settings = SimpleNamespace(GOVERNANCE_ENFORCEMENT_REQUIRED=True)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: settings)
    monkeypatch.setattr("app.engine.evolution.get_governance", lambda: governance)

    assert asyncio.run(engine._governance_allows_promotion(genome)) is True
