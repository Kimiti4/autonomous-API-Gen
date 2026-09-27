from types import SimpleNamespace

import pytest

from app.engine.evolution import EvolutionEngine


class _Settings:
    GOVERNANCE_ENFORCEMENT_REQUIRED = True


class _Governance:
    def __init__(self, state):
        self.state = state

    async def materialize_candidate(self, _candidate_id):
        return self.state


@pytest.mark.asyncio
async def test_governance_denies_promotion_without_authorizing_decision(monkeypatch):
    state = SimpleNamespace(
        current_state="verified",
        latest_decision=lambda: None,
    )
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance", lambda: _Governance(state)
    )

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-denied")

    assert await engine._governance_allows_promotion(genome) is False

    called = False

    def publisher(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("publisher must not be reached when governance denies")

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", publisher)
    with pytest.raises(ValueError, match="governance promotion gate denied"):
        await engine._publish_governed_candidate(
            genome,
            {
                "verification_status": "verified",
                "artifact_path": "/tmp/a",
                "artifact_digest": "sha256:x",
            },
        )
    assert called is False


@pytest.mark.asyncio
async def test_governance_allows_promotion_only_after_authorizing_decision(monkeypatch):
    decision = SimpleNamespace(verdict="approve", authorizesTransition=True)
    state = SimpleNamespace(
        current_state="certified",
        latest_decision=lambda: decision,
    )
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance", lambda: _Governance(state)
    )

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-approved")

    assert await engine._governance_allows_promotion(genome) is True

    published = []

    def publisher(*args, **kwargs):
        published.append((args, kwargs))
        return "output/generated_api"

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", publisher)
    output = await engine._publish_governed_candidate(
        genome,
        {
            "verification_status": "verified",
            "artifact_path": "/tmp/a",
            "artifact_digest": "sha256:x",
        },
    )
    assert output == "output/generated_api"
    assert published


def test_promotion_event_is_emitted_only_by_explicit_promotion_event():
    from app.engine.elite_evolution import EliteEvolutionEngine

    mapping = EvolutionEngine._EVENT_TYPE_MAP

    assert mapping["new_best"] == "evolution.stage_changed"
    assert mapping["candidate_promoted"] == "candidate.promoted"
    assert list(mapping.values()).count("candidate.promoted") == 1

    elite_mapping = EliteEvolutionEngine._EVENT_TYPE_MAP
    assert elite_mapping["new_best"] == "evolution.stage_changed"
    assert "candidate.promoted" not in elite_mapping.values()


@pytest.mark.asyncio
async def test_run_level_governance_denial_fails_closed_without_promotion(monkeypatch):
    from app.storage.db import SessionLocal
    from app.storage.models import EvolutionRun

    async def _verified(*_args, **_kwargs):
        return {
            "build_ok": True,
            "artifact_compile_ok": True,
            "verification_status": "verified",
            "artifact_digest": "sha256:test-digest",
            "artifact_path": "/tmp/candidate.bin",
            "evaluation_mode": "static",
            "static_score": 0.9,
            "runtime_score": None,
        }

    denied_state = SimpleNamespace(current_state="verified", latest_decision=lambda: None)

    async def _materialize(_candidate_id):
        return denied_state

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _verified)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: SimpleNamespace(materialize_candidate=_materialize),
    )

    publisher_reached = False

    def _publisher(*_args, **_kwargs):
        nonlocal publisher_reached
        publisher_reached = True
        return "output/generated_api"

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", _publisher)

    emitted = []
    payload_types = []

    async def _capture(*, stream_id, event_type, payload, correlation_id, generation):
        emitted.append(event_type)
        payload_types.append(payload.get("type"))

    engine = EvolutionEngine()
    engine.dispatcher = SimpleNamespace(emit=_capture)
    result = await engine.run_async(
        generations=1, population_size=2, use_docker=False, seed=3
    )

    assert publisher_reached is False
    assert result["output_path"] is None
    assert result["best_genome"] is None
    assert result["build_error"] is not None
    assert "governance promotion gate denied" in result["build_error"]
    assert "candidate.promoted" not in emitted
    assert "candidate_promoted" not in payload_types
    assert "evolution_failed" in payload_types

    db = SessionLocal()
    try:
        record = (
            db.query(EvolutionRun)
            .filter(EvolutionRun.run_id == result["run_id"])
            .first()
        )
        assert record is not None
        assert record.status == "failed"
        assert record.history["promotion_status"] == "failed"
        assert "governance promotion gate denied" in record.history["error"]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_run_level_authorized_candidate_promotes_exactly_once(monkeypatch):
    from app.storage.db import SessionLocal
    from app.storage.models import EvolutionRun

    async def _verified(*_args, **_kwargs):
        return {
            "build_ok": True,
            "artifact_compile_ok": True,
            "verification_status": "verified",
            "artifact_digest": "sha256:test-digest",
            "artifact_path": "/tmp/candidate.bin",
            "evaluation_mode": "static",
            "static_score": 0.9,
            "runtime_score": None,
        }

    decision = SimpleNamespace(verdict="approve", authorizesTransition=True)
    allowed_state = SimpleNamespace(
        current_state="certified", latest_decision=lambda: decision
    )

    async def _materialize(_candidate_id):
        return allowed_state

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _verified)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: SimpleNamespace(materialize_candidate=_materialize),
    )

    trail = []
    payload_types = []

    def _publisher(*_args, **_kwargs):
        trail.append("publisher")
        return "output/generated_api"

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", _publisher)

    async def _capture(*, stream_id, event_type, payload, correlation_id, generation):
        trail.append(event_type)
        payload_types.append(payload.get("type"))

    engine = EvolutionEngine()
    engine.dispatcher = SimpleNamespace(emit=_capture)
    result = await engine.run_async(
        generations=1, population_size=2, use_docker=False, seed=3
    )

    assert result["build_error"] is None
    assert result["output_path"] == "output/generated_api"
    assert result["best_genome"] is not None
    assert trail.count("candidate.promoted") == 1
    assert payload_types.count("candidate_promoted") == 1
    assert trail.index("publisher") < trail.index("candidate.promoted")
    assert "candidate.promoted" not in trail[: trail.index("publisher")]

    db = SessionLocal()
    try:
        record = (
            db.query(EvolutionRun)
            .filter(EvolutionRun.run_id == result["run_id"])
            .first()
        )
        assert record is not None
        assert record.status == "completed"
        assert record.history["promotion_status"] == "published"
    finally:
        db.close()
