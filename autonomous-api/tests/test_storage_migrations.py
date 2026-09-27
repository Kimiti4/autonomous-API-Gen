from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.storage.migrations import LATEST_SCHEMA_VERSION, migrate


def _engine(tmp_path: Path):
    return create_engine(f"sqlite:///{tmp_path / 'evolution.db'}")


def test_fresh_database_is_migrated_and_verified(tmp_path):
    engine = _engine(tmp_path)

    assert migrate(engine) == LATEST_SCHEMA_VERSION

    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        version = connection.execute(text("SELECT version FROM schema_version")).scalar_one()

    assert {"schema_version", "genomes", "evolution_runs"} <= tables
    assert version == LATEST_SCHEMA_VERSION
    assert migrate(engine) == LATEST_SCHEMA_VERSION


def test_schema_drift_fails_closed(tmp_path):
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        connection.execute(text("INSERT INTO schema_version(version) VALUES (1)"))
        connection.execute(text("""
            CREATE TABLE genomes (
                id INTEGER PRIMARY KEY,
                genome_data JSON,
                fitness_score FLOAT,
                generation INTEGER,
                created_at DATETIME
            )
        """))
        connection.execute(text("""
            CREATE TABLE evolution_runs (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR UNIQUE,
                status VARCHAR,
                total_generations INTEGER,
                best_fitness FLOAT,
                best_genome JSON,
                started_at DATETIME,
                completed_at DATETIME
            )
        """))

    with pytest.raises(RuntimeError, match="missing columns: history"):
        migrate(engine)


def test_database_newer_than_application_fails_closed(tmp_path):
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        connection.execute(text("INSERT INTO schema_version(version) VALUES (999)"))

    with pytest.raises(RuntimeError, match="newer than supported"):
        migrate(engine)


def test_legacy_v5_memory_clear_schema_is_forward_repaired(tmp_path):
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE schema_version (version INTEGER NOT NULL)"
        ))
        connection.execute(text("INSERT INTO schema_version(version) VALUES (5)"))
        connection.execute(text("""
            CREATE TABLE memory_clear_audit (
                id INTEGER PRIMARY KEY,
                scope VARCHAR NOT NULL,
                sequence INTEGER NOT NULL,
                operation_id VARCHAR NOT NULL,
                event_type VARCHAR NOT NULL,
                payload TEXT NOT NULL,
                previous_hash VARCHAR NOT NULL,
                record_hash VARCHAR NOT NULL,
                signature VARCHAR NOT NULL,
                UNIQUE(scope, sequence),
                UNIQUE(scope, operation_id)
            )
        """))
        connection.execute(text("""
            INSERT INTO memory_clear_audit
            (id, scope, sequence, operation_id, event_type, payload,
             previous_hash, record_hash, signature)
            VALUES
            (1, 'elite-memory', 1, 'op-1', 'memory.clear.requested',
             '{}', '', 'hash-1', 'sig-1')
        """))

    assert migrate(engine) == LATEST_SCHEMA_VERSION

    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO memory_clear_audit
            (id, scope, sequence, operation_id, event_type, payload,
             previous_hash, record_hash, signature)
            VALUES
            (2, 'elite-memory', 2, 'op-1', 'memory.clear.backup_verified',
             '{}', 'hash-1', 'hash-2', 'sig-2')
        """))
        connection.execute(text("""
            INSERT INTO memory_clear_audit
            (id, scope, sequence, operation_id, event_type, payload,
             previous_hash, record_hash, signature)
            VALUES
            (3, 'elite-memory', 3, 'op-1', 'memory.clear.succeeded',
             '{}', 'hash-2', 'hash-3', 'sig-3')
        """))
        version = connection.execute(
            text("SELECT version FROM schema_version")
        ).scalar_one()
        count = connection.execute(
            text("SELECT COUNT(*) FROM memory_clear_audit")
        ).scalar_one()

    assert version == LATEST_SCHEMA_VERSION
    assert count == 3
    assert migrate(engine) == LATEST_SCHEMA_VERSION


def test_v0_database_upgrades_through_every_migration(tmp_path):
    engine = _engine(tmp_path)

    assert migrate(engine) == LATEST_SCHEMA_VERSION

    with engine.connect() as connection:
        version = connection.execute(text("SELECT version FROM schema_version")).scalar_one()
        assert version == LATEST_SCHEMA_VERSION
