import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.storage.backup import _sha256, backup_sqlite_database
from app.storage.checkpoint import (
    ARTIFACT_DIR_NAME,
    DATABASE_IMAGE_NAME,
    MANIFEST_NAME,
    create_system_checkpoint,
    restore_system_checkpoint,
    verify_system_checkpoint,
)
from app.storage.migrations import migrate


def _engine(tmp_path: Path):
    return create_engine(f"sqlite:///{tmp_path / 'evolution.db'}")


def _seed(engine, value: str):
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO genomes (genome_data, fitness_score, generation) VALUES (:data, :fitness, :generation)"),
            {"data": value, "fitness": 0.9, "generation": 3},
        )


def _genome_state(engine):
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT genome_data FROM genomes ORDER BY id")
        ).all()


def _artifact(root: Path, payload: str = "known-good") -> str:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text(payload, encoding="utf-8")
    file_digest = hashlib.sha256((root / "main.py").read_bytes()).hexdigest()
    digest_payload = {
        "manifest_version": 1,
        "backend_id": "test",
        "architecture_hash": "arch-test",
        "files": {"main.py": file_digest},
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (root / "artifact-manifest.json").write_text(
        json.dumps({**digest_payload, "artifact_digest": digest}, sort_keys=True),
        encoding="utf-8",
    )
    return digest


def test_checkpoint_round_trip_restores_both_halves(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source, "known-good")
    checkpoint = tmp_path / "checkpoint"

    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(checkpoint),
    )

    assert manifest["checkpoint_digest"]
    assert manifest["artifact_digest"] == artifact_digest
    assert (checkpoint / MANIFEST_NAME).is_file()
    assert (checkpoint / DATABASE_IMAGE_NAME).is_file()
    assert (checkpoint / ARTIFACT_DIR_NAME / "main.py").is_file()

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM genomes"))
    live = tmp_path / "live"
    live.mkdir()
    (live / "main.py").write_text("bad-state", encoding="utf-8")

    restored = restore_system_checkpoint(
        engine,
        str(checkpoint),
        expected_checkpoint_digest=manifest["checkpoint_digest"],
        artifact_destination=str(live),
    )

    assert restored["checkpoint_digest"] == manifest["checkpoint_digest"]
    assert _genome_state(engine)[0][0] == "known-good"
    assert (live / "main.py").read_text(encoding="utf-8") == "known-good"


def test_checkpoint_binds_both_digests_into_one(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    standalone_db_digest = backup_sqlite_database(engine, tmp_path / "standalone.db")

    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(tmp_path / "checkpoint"),
    )

    assert manifest["artifact_digest"] == artifact_digest
    assert manifest["database_digest"] == standalone_db_digest
    assert manifest["checkpoint_digest"] != manifest["artifact_digest"]
    assert manifest["checkpoint_digest"] != manifest["database_digest"]

    payload = {
        "schema": manifest["schema"],
        "schema_version": manifest["schema_version"],
        "artifact_digest": manifest["artifact_digest"],
        "database_digest": manifest["database_digest"],
    }
    recomputed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert manifest["checkpoint_digest"] == recomputed


def test_verify_passes_on_untouched_checkpoint(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(tmp_path / "checkpoint"),
    )

    verified = verify_system_checkpoint(
        str(tmp_path / "checkpoint"),
        expected_checkpoint_digest=manifest["checkpoint_digest"],
    )
    assert verified["checkpoint_digest"] == manifest["checkpoint_digest"]


def test_tampered_manifest_binding_is_refused(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    checkpoint = tmp_path / "checkpoint"
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(checkpoint),
    )

    manifest_path = checkpoint / MANIFEST_NAME
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["database_digest"] = "0" * 64
    manifest_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="binding digest does not match"):
        verify_system_checkpoint(
            str(checkpoint),
            expected_checkpoint_digest=manifest["checkpoint_digest"],
        )


def test_wrong_expected_checkpoint_digest_is_refused(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(tmp_path / "checkpoint"),
    )

    with pytest.raises(ValueError, match="checkpoint digest mismatch"):
        verify_system_checkpoint(
            str(tmp_path / "checkpoint"),
            expected_checkpoint_digest="f" * 64,
        )


def test_tampered_database_image_is_refused(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    checkpoint = tmp_path / "checkpoint"
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(checkpoint),
    )

    image = checkpoint / DATABASE_IMAGE_NAME
    payload = bytearray(image.read_bytes())
    payload[len(payload) // 2] ^= 0xFF
    image.write_bytes(bytes(payload))

    with pytest.raises(ValueError, match="integrity check failed|database digest mismatch"):
        verify_system_checkpoint(
            str(checkpoint),
            expected_checkpoint_digest=manifest["checkpoint_digest"],
        )


def test_tampered_artifact_half_is_refused(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    checkpoint = tmp_path / "checkpoint"
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(checkpoint),
    )

    (checkpoint / ARTIFACT_DIR_NAME / "main.py").write_text(
        "tampered", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="artifact file digest mismatch"):
        verify_system_checkpoint(
            str(checkpoint),
            expected_checkpoint_digest=manifest["checkpoint_digest"],
        )


def test_create_refuses_unverified_artifact(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    _artifact(artifact_source)

    with pytest.raises(ValueError, match="digest does not match expected digest"):
        create_system_checkpoint(
            engine,
            artifact_dir=str(artifact_source),
            artifact_digest="a" * 64,
            checkpoint_dir=str(tmp_path / "checkpoint"),
        )
    assert not (tmp_path / "checkpoint").exists()


def test_artifact_restore_failure_rolls_database_back(tmp_path, monkeypatch):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source, "known-good")
    checkpoint = tmp_path / "checkpoint"
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(checkpoint),
    )

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM genomes"))
        connection.execute(
            text("INSERT INTO genomes (genome_data, fitness_score, generation) VALUES ('pre-restore', 0.1, 1)")
        )

    def _boom(*args, **kwargs):
        raise RuntimeError("artifact restore exploded")

    monkeypatch.setattr(
        "app.storage.checkpoint.restore_verified_artifact", _boom
    )
    live = tmp_path / "live"
    live.mkdir()

    with pytest.raises(RuntimeError, match="artifact restore exploded"):
        restore_system_checkpoint(
            engine,
            str(checkpoint),
            expected_checkpoint_digest=manifest["checkpoint_digest"],
            artifact_destination=str(live),
        )

    assert _genome_state(engine)[0][0] == "pre-restore"


def test_checkpoint_database_image_matches_standalone_backup_digest(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    artifact_source = tmp_path / "source"
    artifact_digest = _artifact(artifact_source)
    manifest = create_system_checkpoint(
        engine,
        artifact_dir=str(artifact_source),
        artifact_digest=artifact_digest,
        checkpoint_dir=str(tmp_path / "checkpoint"),
    )

    image = tmp_path / "checkpoint" / DATABASE_IMAGE_NAME
    assert _sha256(image) == manifest["database_digest"]
