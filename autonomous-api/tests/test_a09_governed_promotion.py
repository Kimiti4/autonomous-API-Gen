from types import SimpleNamespace

import pytest

from app.engine.evolution import EvolutionEngine


class _Settings:
    GOVERNANCE_ENFORCEMENT_REQUIRED = True


class _Governance:
    def __init__(self, state_factory):
        self.state_factory = state_factory

    async def materialize_candidate(self, candidate_id):
        return self.state_factory(candidate_id)


DIGEST = "a" * 64
ARTIFACT_REF = f"sha256:{DIGEST}"


def _approved_state(candidate_id, *, digest=ARTIFACT_REF, from_state="selected",
                    to_state="deployed", include_certification=True):
    decision = SimpleNamespace(
        candidateId=candidate_id,
        generation=1,
        verdict="approve",
        authorizesTransition=True,
        fromState=from_state,
        toState=to_state,
        evidenceRefs=[digest],
    )
    certification = SimpleNamespace(
        candidateId=candidate_id,
        revokedAt=None,
        evidenceRefs=[digest],
        validUntil="2099-01-01T00:00:00+00:00",
    )
    certifications = [certification] if include_certification else []
    return SimpleNamespace(
        candidate_id=candidate_id,
        current_state="deployed" if to_state == "deployed" else "selected",
        latest_decision=lambda: decision,
        active_certifications=lambda: certifications,
    )


def _verified_evidence(**overrides):
    evidence = {
        "build_ok": True,
        "artifact_compile_ok": True,
        "verification_status": "verified",
        "evaluation_mode": "runtime",
        "runtime_score": 1.0,
        "artifact_path": "/tmp/candidate-source",
        "output_path": "/tmp/candidate-release",
        "artifact_digest": ARTIFACT_REF,
    }
    evidence.update(overrides)
    return evidence


@pytest.mark.asyncio
async def test_governance_denies_promotion_without_authorizing_decision(monkeypatch):
    state = SimpleNamespace(
        candidate_id="candidate-denied",
        current_state="verified",
        latest_decision=lambda: None,
        active_certifications=lambda: [],
    )
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: state),
    )

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-denied")
    assert await engine._governance_allows_promotion(genome, ARTIFACT_REF) is False

    called = False

    def publisher(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("publisher must not be reached when governance denies")

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", publisher)
    with pytest.raises(ValueError, match="governance promotion gate denied"):
        await engine._publish_governed_candidate(genome, _verified_evidence())
    assert called is False


@pytest.mark.asyncio
async def test_governance_requires_deployed_transition_and_digest_bound_certification(monkeypatch):
    candidate_id = "candidate-approved"
    allowed_state = _approved_state(candidate_id)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: allowed_state),
    )
    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id=candidate_id)

    assert await engine._governance_allows_promotion(genome, ARTIFACT_REF) is True
    assert await engine._governance_allows_promotion(genome, f"sha256:{'b' * 64}") is False

    wrong_transition = _approved_state(candidate_id, from_state="proposed", to_state="evaluating")
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: wrong_transition),
    )
    assert await engine._governance_allows_promotion(genome, ARTIFACT_REF) is False

    missing_cert = _approved_state(candidate_id, include_certification=False)
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: missing_cert),
    )
    assert await engine._governance_allows_promotion(genome, ARTIFACT_REF) is False

    expired_cert_state = _approved_state(candidate_id)
    expired_cert_state.active_certifications = lambda: [
        SimpleNamespace(
            candidateId=candidate_id,
            revokedAt=None,
            evidenceRefs=[ARTIFACT_REF],
            validUntil="2000-01-01T00:00:00+00:00",
        )
    ]
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: expired_cert_state),
    )
    assert await engine._governance_allows_promotion(genome, ARTIFACT_REF) is False


@pytest.mark.asyncio
async def test_governed_publish_rejects_static_or_unverified_candidates(monkeypatch):
    candidate_id = "candidate-static"
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id=candidate_id)
    called = False

    def publisher(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", publisher)
    with pytest.raises(ValueError, match="not fully runtime-verified"):
        await engine._publish_governed_candidate(
            genome,
            _verified_evidence(evaluation_mode="static", runtime_score=None),
        )
    assert called is False


@pytest.mark.asyncio
async def test_governed_publish_passes_verified_digest_to_promoter(monkeypatch):
    candidate_id = "candidate-release"
    allowed_state = _approved_state(candidate_id)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: allowed_state),
    )

    published = []

    def publisher(*args, **kwargs):
        published.append((args, kwargs))
        return "/tmp/candidate-release"

    monkeypatch.setattr("app.engine.evolution.promote_verified_artifact", publisher)
    engine = EvolutionEngine()
    output = await engine._publish_governed_candidate(
        SimpleNamespace(genome_id=candidate_id),
        _verified_evidence(),
    )
    assert output == "/tmp/candidate-release"
    assert published[0][1]["expected_digest"] == DIGEST


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
            **_verified_evidence(),
            "artifact_path": "/tmp/candidate.bin",
        }

    denied_state = SimpleNamespace(
        candidate_id="not-the-current-candidate",
        current_state="verified",
        latest_decision=lambda: None,
        active_certifications=lambda: [],
    )

    monkeypatch.setattr("app.engine.evolution.evaluate_candidate_async", _verified)
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance",
        lambda: _Governance(lambda _candidate_id: denied_state),
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
        generations=1, population_size=2, use_docker=True, seed=3
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
            **_verified_evidence(),
            "artifact_path": "/tmp/candidate.bin",
        }

    def _state_for(candidate_id):
        return _approved_state(candidate_id)

    async def _materialize(candidate_id):
        return _state_for(candidate_id)

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
        generations=1, population_size=2, use_docker=True, seed=3
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
