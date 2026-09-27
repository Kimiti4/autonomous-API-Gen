"""Versioned schema migrations for the evolution database.

The application must not use SQLAlchemy create_all at runtime. Schema changes
are explicit, versioned, transactional, and verified after upgrade.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

LATEST_SCHEMA_VERSION = 7

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


def _apply_v5(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_clear_audit (
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
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_memory_clear_audit_scope "
            "ON memory_clear_audit (scope, sequence)"
        ))
        # One 'requested' record per operation: enforces replay rejection at
        # the database level while the lifecycle chain (requested ->
        # backup_verified -> succeeded/failed) stays free to grow.
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_memory_clear_audit_requested "
            "ON memory_clear_audit (scope, operation_id) "
            "WHERE event_type = 'memory.clear.requested'"
        ))
        connection.execute(text("UPDATE schema_version SET version = 5"))



def _apply_v6(engine: Engine) -> None:
    """Repair the pre-release v5 memory-clear schema.

    Early v5 builds encoded UNIQUE(scope, operation_id) on the table itself.
    The lifecycle legitimately stores multiple records for one operation, so
    that constraint was too restrictive. v6 removes only that legacy table
    constraint and preserves the durable replay index introduced in v5.
    """
    with engine.begin() as connection:
        indexes = connection.execute(
            text("PRAGMA index_list('memory_clear_audit')")
        ).mappings().all()
        legacy_unique = False
        for index in indexes:
            index_name = index["name"]
            if not index["unique"] or index["partial"]:
                continue
            columns = [
                row[2]
                for row in connection.execute(
                    text(f"PRAGMA index_info('{index_name}')")
                ).all()
            ]
            if columns == ["scope", "operation_id"]:
                legacy_unique = True
                break

        if legacy_unique:
            connection.execute(text("""
                CREATE TABLE memory_clear_audit_v6 (
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
            connection.execute(text("""
                INSERT INTO memory_clear_audit_v6 (
                    id, scope, sequence, operation_id, event_type, payload,
                    previous_hash, record_hash, signature
                )
                SELECT
                    id, scope, sequence, operation_id, event_type, payload,
                    previous_hash, record_hash, signature
                FROM memory_clear_audit
            """))
            connection.execute(text("DROP TABLE memory_clear_audit"))
            connection.execute(
                text("ALTER TABLE memory_clear_audit_v6 RENAME TO memory_clear_audit")
            )

        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_memory_clear_audit_scope "
            "ON memory_clear_audit (scope, sequence)"
        ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_memory_clear_audit_requested "
            "ON memory_clear_audit (scope, operation_id) "
            "WHERE event_type = 'memory.clear.requested'"
        ))
        connection.execute(text("UPDATE schema_version SET version = 6"))




def _apply_v7(engine: Engine) -> None:
    """Add durable runtime evolution kill-switch state."""
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS runtime_kill_switch (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                reason VARCHAR NOT NULL DEFAULT '',
                activated_by VARCHAR,
                activated_at DATETIME,
                deactivated_by VARCHAR,
                deactivated_at DATETIME,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("""
            INSERT OR IGNORE INTO runtime_kill_switch (
                id, enabled, reason, updated_at
            ) VALUES (1, 0, '', CURRENT_TIMESTAMP)
        """))
        connection.execute(text("UPDATE schema_version SET version = 7"))


def _verify_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required_tables = set(_REQUIRED_COLUMNS) | {
        "schema_version", "control_plane_lease", "runtime_kill_switch", "governance_events",
        "governance_council", "governance_gates", "governance_policies", "governance_audit", "memory_clear_audit",
    }
    missing_tables = required_tables - tables
    if missing_tables:
        raise RuntimeError(
            "Database schema verification failed; missing tables: "
            + ", ".join(sorted(missing_tables))
        )

    clear_audit_columns = {column["name"] for column in inspector.get_columns("memory_clear_audit")}
    required_clear_audit_columns = {
        "id", "scope", "sequence", "operation_id", "event_type", "payload",
        "previous_hash", "record_hash", "signature",
    }
    missing_clear_audit_columns = required_clear_audit_columns - clear_audit_columns
    if missing_clear_audit_columns:
        raise RuntimeError(
            "Database schema verification failed for memory_clear_audit; missing columns: "
            + ", ".join(sorted(missing_clear_audit_columns))
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
        version = 4

    if version < 5:
        _apply_v5(engine)
        version = 5

    if version < 6:
        _apply_v6(engine)
        version = 6

    if version < 7:
        _apply_v7(engine)

    _verify_schema(engine)
    return LATEST_SCHEMA_VERSION
