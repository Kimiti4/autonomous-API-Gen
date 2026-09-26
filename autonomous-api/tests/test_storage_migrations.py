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
