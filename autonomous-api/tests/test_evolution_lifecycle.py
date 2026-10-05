from types import SimpleNamespace

from app.engine.evolution import EvolutionEngine


def test_completed_run_requires_verified_published_artifact():
    base = {
        "status": "completed",
        "completed_at": "2026-09-24T00:00:00",
        "best_genome": {"genome_id": "g1"},
    }
    missing_digest = SimpleNamespace(**base, history={
        "schema_version": 1,
        "phase": "completed",
        "promotion_status": "published",
    })
    failed_promotion = SimpleNamespace(**base, history={
        "schema_version": 1,
        "phase": "completed",
        "promotion_status": "failed",
        "best_artifact_digest": "sha256:abc",
    })
    valid = SimpleNamespace(**base, history={
        "schema_version": 1,
        "phase": "completed",
        "promotion_status": "published",
        "best_artifact_digest": "sha256:abc",
    })

    assert not EvolutionEngine._is_authoritative(missing_digest)
    assert not EvolutionEngine._is_authoritative(failed_promotion)
    assert EvolutionEngine._is_authoritative(valid)


def test_running_run_is_recovered_as_abandoned(monkeypatch):
    record = SimpleNamespace(
        status="running",
        completed_at=None,
        history={
            "schema_version": 1,
            "phase": "evaluating",
            "generation": 3,
            "best_artifact_digest": "sha256:abc",
        },
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

    assert EvolutionEngine.recover_interrupted_runs() == 1
    assert record.status == "abandoned"
    assert record.completed_at is not None
    assert record.history["phase"] == "abandoned"
    assert record.history["best_artifact_digest"] == "sha256:abc"


def test_failed_run_never_becomes_authoritative():
    failed = SimpleNamespace(
        status="failed",
        completed_at="2026-09-24T00:00:00",
        best_genome={"genome_id": "g1"},
        history={
            "schema_version": 1,
            "phase": "failed",
            "promotion_status": "failed",
            "best_artifact_digest": "sha256:abc",
        },
    )
    abandoned = SimpleNamespace(
        status="abandoned",
        completed_at="2026-09-24T00:00:00",
        best_genome={"genome_id": "g1"},
        history={
            "schema_version": 1,
            "phase": "abandoned",
            "promotion_status": "published",
            "best_artifact_digest": "sha256:abc",
        },
    )

    assert not EvolutionEngine._is_authoritative(failed)
    assert not EvolutionEngine._is_authoritative(abandoned)
