import hashlib
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.storage.backup import backup_sqlite_database, restore_sqlite_database
from app.storage.migrations import migrate


def _engine(tmp_path: Path):
    return create_engine(f"sqlite:///{tmp_path / 'evolution.db'}")


def _seed(engine, value: str):
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO genomes (genome_data, fitness_score, generation) VALUES (:data, :fitness, :generation)"),
            {"data": value, "fitness": 0.9, "generation": 3},
        )
        connection.execute(
            text(
                "INSERT INTO evolution_runs "
                "(run_id, status, total_generations, best_fitness, best_genome, history) "
                "VALUES (:run_id, 'completed', 3, 0.9, :genome, :history)"
            ),
            {
                "run_id": f"run-{value}",
                "genome": value,
                "history": '{"schema_version": 1, "phase": "completed", "promotion_status": "published", "best_artifact_digest": "digest"}',
            },
        )


def _state(engine):
    with engine.connect() as connection:
        genome = connection.execute(
            text("SELECT genome_data, fitness_score, generation FROM genomes ORDER BY id")
        ).all()
        runs = connection.execute(
            text("SELECT run_id, status, total_generations, best_fitness, best_genome, history "
                 "FROM evolution_runs ORDER BY id")
        ).all()
        schema_version = connection.execute(text("SELECT version FROM schema_version")).scalar_one()
    return genome, runs, schema_version


def test_database_backup_is_restorable_known_good_state(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    backup = tmp_path / "backup.db"
    digest = backup_sqlite_database(engine, backup)

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM genomes"))
        connection.execute(text("DELETE FROM evolution_runs"))

    restored_digest = restore_sqlite_database(engine, backup, digest)

    assert restored_digest == digest
    assert _state(engine)[0][0][0] == "known-good"
    assert len(_state(engine)[1]) == 1
    assert _state(engine)[2] == 1


def test_tampered_database_backup_is_rejected(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    backup = tmp_path / "backup.db"
    digest = backup_sqlite_database(engine, backup)

    with backup.open("ab") as handle:
        handle.write(b"tamper")

    with pytest.raises(ValueError, match="SQLite integrity check failed|database backup digest mismatch"):
        restore_sqlite_database(engine, backup, digest)


def test_restore_retains_previous_database_as_rollback_point(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    backup = tmp_path / "backup.db"
    digest = backup_sqlite_database(engine, backup)

    with engine.begin() as connection:
        connection.execute(text("UPDATE genomes SET genome_data = 'changed'"))

    restore_sqlite_database(engine, backup, digest)

    rollback = tmp_path / ".evolution.db.previous"
    assert rollback.exists()
    assert "changed" in rollback.read_bytes().decode("utf-8", errors="ignore")


def test_backup_digest_is_stable_for_unchanged_state(tmp_path):
    engine = _engine(tmp_path)
    migrate(engine)
    _seed(engine, "known-good")

    first = tmp_path / "first.db"
    second = tmp_path / "second.db"
    first_digest = backup_sqlite_database(engine, first)
    second_digest = backup_sqlite_database(engine, second)

    assert first_digest == second_digest
