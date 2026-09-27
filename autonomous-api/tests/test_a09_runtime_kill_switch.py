import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.governance.audit import AuditIntegrityError
from app.core.runtime_control import (
    RUNTIME_SCOPE,
    activate_kill_switch,
    assert_evolution_enabled,
    deactivate_kill_switch,
    get_kill_switch,
)
from app.storage.migrations import migrate


def _bind_control_store(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'evolution.db'}")
    migrate(engine)
    import app.core.runtime_control as control
    monkeypatch.setattr(control, "SessionLocal", sessionmaker(bind=engine))
    return engine


def test_kill_switch_is_durable_signed_and_tamper_evident(monkeypatch, tmp_path):
    engine = _bind_control_store(monkeypatch, tmp_path)

    state = activate_kill_switch(reason="incident", actor="operator")
    assert state.enabled is True
    assert state.activated_by == "operator"

    # Reconstruct through a fresh SQLAlchemy session: no process-local state is used.
    import app.core.runtime_control as control
    monkeypatch.setattr(control, "SessionLocal", sessionmaker(bind=create_engine(f"sqlite:///{tmp_path / 'evolution.db'}")))
    assert get_kill_switch().enabled is True
    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        assert_evolution_enabled()

    with engine.begin() as db:
        db.execute(
            __import__("sqlalchemy").text(
                "UPDATE governance_audit SET payload = :payload "
                "WHERE candidate_id = :scope AND sequence = 1"
            ),
            {"payload": '{"actor":"tampered"}', "scope": RUNTIME_SCOPE},
        )

    with pytest.raises(AuditIntegrityError):
        get_kill_switch()


def test_kill_switch_deactivation_is_signed_and_durable(monkeypatch, tmp_path):
    _bind_control_store(monkeypatch, tmp_path)
    activate_kill_switch(reason="maintenance", actor="operator")
    state = deactivate_kill_switch(actor="operator", reason="maintenance complete")
    assert state.enabled is False
    assert state.deactivated_by == "operator"
    assert_evolution_enabled()


def test_kill_switch_engine_guards(monkeypatch):
    from app.engine.evolution import EvolutionEngine
    from app.engine.elite_evolution import EliteEvolutionEngine

    error = lambda: (_ for _ in ()).throw(
        RuntimeError("runtime evolution kill switch is active: test")
    )
    monkeypatch.setattr("app.engine.evolution.assert_evolution_enabled", error)
    monkeypatch.setattr("app.engine.elite_evolution.assert_evolution_enabled", error)

    import asyncio
    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        asyncio.run(EvolutionEngine().run_async(generations=1, population_size=2, use_docker=False))
    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        asyncio.run(EliteEvolutionEngine().run_elite_evolution(generations=1, population_size=2, use_multi_population=False))


def test_kill_switch_routes_require_auth():
    from app.api.routes import router
    from app.middleware.security import require_auth

    protected_paths = {
        "/evolution/kill-switch",
        "/evolution/kill-switch/activate",
        "/evolution/kill-switch/deactivate",
    }
    routes = {route.path: route for route in router.routes if route.path in protected_paths}
    assert set(routes) == protected_paths
    assert all(any(dep.call is require_auth for dep in route.dependant.dependencies) for route in routes.values())
