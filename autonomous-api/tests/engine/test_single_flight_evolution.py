"""EV-A08-003: one authoritative evolution at a time, across engines.

The control-plane lease is the single-flight boundary: a second run
(standard or elite) is rejected while a lease is live, long evaluations
renew ownership so a live run cannot be taken over mid-flight, recovery
leaves a live lease alone, and every path releases on exit.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.engine.elite_evolution import EliteEvolutionEngine
from app.engine.evolution import EvolutionEngine
from app.storage import lease


def test_standard_run_renews_lease_per_evaluation(monkeypatch):
    renewals = []
    real_heartbeat = lease.heartbeat_control_plane_lease

    def _recording_heartbeat(owner_token, **kwargs):
        renewals.append(owner_token)
        return real_heartbeat(owner_token, **kwargs)

    monkeypatch.setattr(
        "app.engine.evolution.heartbeat_control_plane_lease", _recording_heartbeat
    )

    result = EvolutionEngine().run_synchronous(generations=1, population_size=3)

    assert result["build_error"] is None
    assert len(renewals) >= 3
    assert lease.lease_is_live() is False


def test_second_standard_run_is_rejected_while_lease_is_live():
    held = lease.acquire_control_plane_lease(owner_run_id="competing-run")
    try:
        with pytest.raises(lease.ControlPlaneBusy):
            EvolutionEngine().run_synchronous(generations=1, population_size=3)
    finally:
        lease.release_control_plane_lease(held)


def test_elite_run_is_rejected_while_lease_is_live():
    held = lease.acquire_control_plane_lease(owner_run_id="competing-run")
    try:
        with pytest.raises(lease.ControlPlaneBusy):
            asyncio.run(
                EliteEvolutionEngine().run_elite_evolution(
                    generations=1, population_size=4, use_multi_population=False, seed=3
                )
            )
    finally:
        lease.release_control_plane_lease(held)


def test_elite_run_acquires_and_releases_lease(monkeypatch):
    acquisitions = []
    real_acquire = lease.acquire_control_plane_lease

    def _recording_acquire(**kwargs):
        acquisitions.append(kwargs.get("owner_run_id"))
        return real_acquire(**kwargs)

    monkeypatch.setattr(
        "app.engine.elite_evolution.acquire_control_plane_lease", _recording_acquire
    )

    asyncio.run(
        EliteEvolutionEngine().run_elite_evolution(
            generations=1, population_size=4, use_multi_population=False, seed=5
        )
    )

    assert acquisitions
    assert all(rid and rid.startswith("elite:") for rid in acquisitions)
    assert lease.lease_is_live() is False


def test_recovery_leaves_a_live_lease_untouched(monkeypatch):
    record = SimpleNamespace(
        status="running",
        completed_at=None,
        history={"schema_version": 1, "phase": "evaluating", "generation": 3},
    )

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [record]

    class DB:
        def query(self, *_args, **_kwargs):
            return Query()

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr("app.engine.evolution.SessionLocal", lambda: DB())

    held = lease.acquire_control_plane_lease(owner_run_id="live-run")
    try:
        assert EvolutionEngine.recover_interrupted_runs() == 0
        assert record.status == "running"
    finally:
        lease.release_control_plane_lease(held)
