import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.storage.backup import _sha256
from app.storage.checkpoint import MANIFEST_NAME
from app.storage.cli import main
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


def _prepared_database(tmp_path: Path, value: str = "known-good"):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, value)
    engine.dispose()
    return tmp_path / "evolution.db"


def test_cli_backup_writes_verifiable_database_image(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    image = tmp_path / "backup.db"

    rc = main(["backup", "--database", str(database), "--output", str(image)])
    digest = capsys.readouterr().out.strip()

    assert rc == 0
    assert image.is_file()
    assert digest == _sha256(image)

    rc = main(["verify", "--source", str(image), "--digest", digest])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_cli_backup_image_restores_state(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    image = tmp_path / "backup.db"
    main(["backup", "--database", str(database), "--output", str(image)])
    digest = capsys.readouterr().out.strip()

    live = _engine(tmp_path)
    with live.begin() as connection:
        connection.execute(text("DELETE FROM genomes"))
    live.dispose()

    rc = main(
        ["restore", "--database", str(database), "--source", str(image), "--digest", digest]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ok"

    restored = _engine(tmp_path)
    assert _genome_state(restored)[0][0] == "known-good"
    restored.dispose()


def test_cli_verify_rejects_tampered_image(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    image = tmp_path / "backup.db"
    main(["backup", "--database", str(database), "--output", str(image)])
    digest = capsys.readouterr().out.strip()

    payload = bytearray(image.read_bytes())
    payload[len(payload) // 2] ^= 0xFF
    image.write_bytes(bytes(payload))

    with pytest.raises(ValueError, match="integrity check failed|digest mismatch"):
        main(["verify", "--source", str(image), "--digest", digest])


def test_cli_restore_rejects_wrong_digest(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    image = tmp_path / "backup.db"
    main(["backup", "--database", str(database), "--output", str(image)])
    capsys.readouterr()

    with pytest.raises(ValueError, match="digest mismatch"):
        main(
            [
                "restore",
                "--database",
                str(database),
                "--source",
                str(image),
                "--digest",
                "f" * 64,
            ]
        )


def test_cli_checkpoint_round_trip(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    artifact = tmp_path / "source"
    artifact_digest = _artifact(artifact, "known-good")
    checkpoint = tmp_path / "checkpoint"
    live_artifact = tmp_path / "live"

    rc = main(
        [
            "backup",
            "--database",
            str(database),
            "--output",
            str(checkpoint),
            "--artifact-dir",
            str(artifact),
            "--artifact-digest",
            artifact_digest,
        ]
    )
    manifest = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert (checkpoint / MANIFEST_NAME).is_file()
    assert manifest["artifact_digest"] == artifact_digest
    assert manifest["checkpoint_digest"]

    rc = main(
        [
            "verify",
            "--source",
            str(checkpoint),
            "--digest",
            manifest["checkpoint_digest"],
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ok"

    live = _engine(tmp_path)
    with live.begin() as connection:
        connection.execute(text("DELETE FROM genomes"))
    live.dispose()
    live_artifact.mkdir()
    (live_artifact / "main.py").write_text("bad-state", encoding="utf-8")

    rc = main(
        [
            "restore",
            "--database",
            str(database),
            "--source",
            str(checkpoint),
            "--digest",
            manifest["checkpoint_digest"],
            "--artifact-destination",
            str(live_artifact),
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ok"
    assert (live_artifact / "main.py").read_text(encoding="utf-8") == "known-good"

    restored = _engine(tmp_path)
    assert _genome_state(restored)[0][0] == "known-good"
    restored.dispose()


def test_cli_checkpoint_restore_requires_artifact_destination(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    artifact = tmp_path / "source"
    artifact_digest = _artifact(artifact)
    checkpoint = tmp_path / "checkpoint"
    main(
        [
            "backup",
            "--database",
            str(database),
            "--output",
            str(checkpoint),
            "--artifact-dir",
            str(artifact),
            "--artifact-digest",
            artifact_digest,
        ]
    )
    manifest = json.loads(capsys.readouterr().out)

    with pytest.raises(ValueError, match="artifact-destination is required"):
        main(
            [
                "restore",
                "--database",
                str(database),
                "--source",
                str(checkpoint),
                "--digest",
                manifest["checkpoint_digest"],
            ]
        )


def test_cli_backup_requires_matching_artifact_arguments(tmp_path, capsys):
    database = _prepared_database(tmp_path)
    artifact = tmp_path / "source"
    artifact_digest = _artifact(artifact)

    with pytest.raises(ValueError, match="must be given together"):
        main(
            [
                "backup",
                "--database",
                str(database),
                "--output",
                str(tmp_path / "checkpoint"),
                "--artifact-dir",
                str(artifact),
            ]
        )
    with pytest.raises(ValueError, match="must be given together"):
        main(
            [
                "backup",
                "--database",
                str(database),
                "--output",
                str(tmp_path / "checkpoint"),
                "--artifact-digest",
                artifact_digest,
            ]
        )
    assert not (tmp_path / "checkpoint").exists()
