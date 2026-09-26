"""Versioned schema migrations for the evolution database.

The application must not use SQLAlchemy create_all at runtime. Schema changes
are explicit, versioned, transactional, and verified after upgrade.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

LATEST_SCHEMA_VERSION = 4

_REQUIRED_COLUMNS = {
    "genomes": {"id", "genome_data", "fitness_score", "generation", "created_at"},
    "evolution_runs": {
        "id", "run_id", "status", "total_generations", "best_fitness",
        "best_genome", "history", "started_at", "completed_at",
    },
}


def _ensure_version_table(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)
        """))
        count = connection.execute(text("SELECT COUNT(*) FROM schema_version")).scalar_one()
        if count == 0:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (0)"))
        elif count != 1:
            raise RuntimeError("Database schema_version must contain exactly one row")


def _apply_v1(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS genomes (
                id INTEGER PRIMARY KEY,
                genome_data JSON,
                fitness_score FLOAT DEFAULT 0.0,
                generation INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS evolution_runs (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR UNIQUE,
                status VARCHAR DEFAULT 'running',
                total_generations INTEGER DEFAULT 0,
                best_fitness FLOAT DEFAULT 0.0,
                best_genome JSON,
                history JSON,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_genomes_id ON genomes (id)"))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_evolution_runs_run_id ON evolution_runs (run_id)"
        ))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_evolution_runs_id ON evolution_runs (id)"))
        connection.execute(text("UPDATE schema_version SET version = 1"))


def _apply_v2(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS control_plane_lease (
                lease_key VARCHAR PRIMARY KEY,
                owner_token VARCHAR NOT NULL,
                owner_run_id VARCHAR NOT NULL,
                acquired_at DATETIME NOT NULL,
                heartbeat_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL
            )
        """))
        connection.execute(text("UPDATE schema_version SET version = 2"))


def _apply_v3(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_events (
                id INTEGER PRIMARY KEY,
                candidate_id VARCHAR NOT NULL,
                event_type VARCHAR NOT NULL,
                payload TEXT NOT NULL
            )
        """))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_governance_events_candidate_id "
            "ON governance_events (candidate_id, id)"
        ))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_council (
                registry_key VARCHAR PRIMARY KEY,
                payload TEXT NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_gates (
                gate_id VARCHAR PRIMARY KEY,
                payload TEXT NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_policies (
                policy_id VARCHAR PRIMARY KEY,
                payload TEXT NOT NULL
            )
        """))
        connection.execute(text("UPDATE schema_version SET version = 3"))



def _apply_v4(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_audit (
                id INTEGER PRIMARY KEY,
                candidate_id VARCHAR NOT NULL,
                sequence INTEGER NOT NULL,
                event_type VARCHAR NOT NULL,
                payload TEXT NOT NULL,
                previous_hash VARCHAR NOT NULL,
                record_hash VARCHAR NOT NULL,
                signature VARCHAR NOT NULL,
                UNIQUE(candidate_id, sequence)
            )
        """))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_governance_audit_candidate_id "
            "ON governance_audit (candidate_id, sequence)"
        ))
        connection.execute(text("UPDATE schema_version SET version = 4"))


def _verify_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required_tables = set(_REQUIRED_COLUMNS) | {
        "schema_version", "control_plane_lease", "governance_events",
        "governance_council", "governance_gates", "governance_policies", "governance_audit",
    }
    missing_tables = required_tables - tables
    if missing_tables:
        raise RuntimeError(
            "Database schema verification failed; missing tables: "
            + ", ".join(sorted(missing_tables))
        )

    audit_columns = {column["name"] for column in inspector.get_columns("governance_audit")}
    required_audit_columns = {
        "id", "candidate_id", "sequence", "event_type", "payload",
        "previous_hash", "record_hash", "signature",
    }
    missing_audit_columns = required_audit_columns - audit_columns
    if missing_audit_columns:
        raise RuntimeError(
            "Database schema verification failed for governance_audit; missing columns: "
            + ", ".join(sorted(missing_audit_columns))
        )

    lease_columns = {column["name"] for column in inspector.get_columns("control_plane_lease")}
    required_lease_columns = {
        "lease_key", "owner_token", "owner_run_id", "acquired_at",
        "heartbeat_at", "expires_at",
    }
    missing_lease_columns = required_lease_columns - lease_columns
    if missing_lease_columns:
        raise RuntimeError(
            "Database schema verification failed for control_plane_lease; missing columns: "
            + ", ".join(sorted(missing_lease_columns))
        )

    for table, required_columns in _REQUIRED_COLUMNS.items():
        columns = {column["name"] for column in inspector.get_columns(table)}
        missing_columns = required_columns - columns
        if missing_columns:
            raise RuntimeError(
                f"Database schema verification failed for {table}; "
                f"missing columns: {', '.join(sorted(missing_columns))}"
            )


def migrate(engine: Engine) -> int:
    """Apply all known migrations and verify the resulting schema."""
    _ensure_version_table(engine)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version FROM schema_version")).scalar_one()

    if version > LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than supported "
            f"version {LATEST_SCHEMA_VERSION}"
        )

    if version < 1:
        _apply_v1(engine)
        version = 1

    if version < 2:
        _apply_v2(engine)
        version = 2

    if version < 3:
        _apply_v3(engine)
        version = 3

    if version < 4:
        _apply_v4(engine)

    _verify_schema(engine)
    return LATEST_SCHEMA_VERSION
