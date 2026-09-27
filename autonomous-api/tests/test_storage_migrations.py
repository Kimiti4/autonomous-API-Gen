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

    # Start from a complete current schema, then emulate the pre-main v5
    # window: schema stamped at 5 with the incorrect operation-wide UNIQUE.
    assert migrate(engine) == LATEST_SCHEMA_VERSION
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ux_memory_clear_audit_requested"))
        connection.execute(text("CREATE UNIQUE INDEX legacy_memory_clear_operation_id ON memory_clear_audit (scope, operation_id)"))
        connection.execute(text("UPDATE schema_version SET version = 5"))
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


def test_legacy_v5_schema_is_repaired_without_data_loss(tmp_path):
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
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
            VALUES
            (1, 'elite-memory', 1, 'op-1', 'memory.clear.requested', '{}', '', 'h1', 's1'),
            (2, 'elite-memory', 2, 'op-1', 'memory.clear.backup_verified', '{}', 'h1', 'h2', 's2'),
            (3, 'elite-memory', 3, 'op-1', 'memory.clear.succeeded', '{}', 'h2', 'h3', 's3')
        """))

    assert migrate(engine) == LATEST_SCHEMA_VERSION

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                "SELECT sequence, operation_id, event_type "
                "FROM memory_clear_audit ORDER BY sequence"
            )
        ).all()
        assert len(rows) == 3
        assert [row[2] for row in rows] == [
            "memory.clear.requested",
            "memory.clear.backup_verified",
            "memory.clear.succeeded",
        ]

        connection.execute(text("""
            INSERT INTO memory_clear_audit
            VALUES
            (4, 'elite-memory', 4, 'op-1', 'memory.clear.failed', '{}', 'h3', 'h4', 's4')
        """))

        with pytest.raises(Exception):
            connection.execute(text("""
                INSERT INTO memory_clear_audit
                VALUES
                (5, 'elite-memory', 5, 'op-1', 'memory.clear.requested', '{}', 'h4', 'h5', 's5')
            """))

    assert migrate(engine) == LATEST_SCHEMA_VERSION


def test_migration_upgrade_path_reaches_latest_from_v5(tmp_path):
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
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
                UNIQUE(scope, sequence)
            )
        """))

    assert migrate(engine) == 6

    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT version FROM schema_version"
        )).scalar_one() == 6
