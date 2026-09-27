import pytest
from pathlib import Path

from app.core.runtime_control import (
    KillSwitchState,
    activate_kill_switch,
    assert_evolution_enabled,
    deactivate_kill_switch,
)
from app.storage.migrations import migrate
from sqlalchemy import create_engine


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "autonomous-api"


def test_kill_switch_is_durable_across_process_restart(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'control.db'}")
    migrate(engine)

    import app.core.runtime_control as control

    session_factory = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        bind=engine
    )
    monkeypatch.setattr(control, "SessionLocal", session_factory)

    state = activate_kill_switch(reason="incident", actor="operator")
    assert state.enabled is True
    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        assert_evolution_enabled()

    # A fresh engine/session observes the persisted state rather than a process-local flag.
    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'control.db'}")
    fresh_factory = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        bind=fresh_engine
    )
    monkeypatch.setattr(control, "SessionLocal", fresh_factory)
    persisted = control.get_kill_switch()
    assert persisted.enabled is True
    assert persisted.reason == "incident"
    assert persisted.activated_by == "operator"

    disabled = deactivate_kill_switch(actor="operator", reason="incident resolved")
    assert disabled.enabled is False
    assert disabled.deactivated_by == "operator"

    assert_evolution_enabled()


def test_kill_switch_schema_is_migrated_to_latest_version(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'schema.db'}")
    assert migrate(engine) == 7


def test_kill_switch_blocks_engine_before_work(monkeypatch):
    from app.engine.evolution import EvolutionEngine

    monkeypatch.setattr(
        "app.engine.evolution.assert_evolution_enabled",
        lambda: (_ for _ in ()).throw(
            RuntimeError("runtime evolution kill switch is active: test")
        ),
    )

    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        import asyncio
        asyncio.run(EvolutionEngine().run_async(generations=1, population_size=2, use_docker=False))


def test_elite_kill_switch_blocks_before_work(monkeypatch):
    from app.engine.elite_evolution import EliteEvolutionEngine

    monkeypatch.setattr(
        "app.engine.elite_evolution.assert_evolution_enabled",
        lambda: (_ for _ in ()).throw(
            RuntimeError("runtime evolution kill switch is active: test")
        ),
    )

    with pytest.raises(RuntimeError, match="runtime evolution kill switch is active"):
        import asyncio
        asyncio.run(
            EliteEvolutionEngine().run_elite_evolution(
                generations=1, population_size=2, use_multi_population=False
            )
        )


def test_kill_switch_routes_require_auth():
    from app.api.routes import router
    from app.middleware.security import require_auth

    protected_paths = {
        "/evolution/kill-switch",
        "/evolution/kill-switch/activate",
        "/evolution/kill-switch/deactivate",
    }
    routes = {
        route.path: route
        for route in router.routes
        if route.path in protected_paths
    }

    assert set(routes) == protected_paths
    for route in routes.values():
        assert any(dependency.call is require_auth for dependency in route.dependencies)
