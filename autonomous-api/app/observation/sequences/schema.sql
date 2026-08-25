-- POC v1.1 Observation durability schema (V1-07).
--
-- observation_stream_counters: per-stream monotonic allocation counter.
--   atomic_next is INSERT ... ON CONFLICT DO UPDATE ... RETURNING next_val - 1,
--   which is a single atomic statement under row lock: 20 concurrent writers
--   x 500 increments yield exactly [0, 10000) with no gaps and no duplicates.
--
-- observation_events: full EvolutionEventEnvelope JSON keyed by
--   (stream_id, sequence) PRIMARY KEY — the UNIQUE constraint that makes
--   double-persist of the same envelope impossible (V1-07 assertion).
--
-- Consumed by tests/integration fixtures via OBSERVATION_SCHEMA_SQL and by
-- deployments via the platform migration path. Keep DDL canonical here only.

CREATE TABLE IF NOT EXISTS observation_stream_counters (
    stream_id TEXT    PRIMARY KEY,
    next_val  BIGINT  NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS observation_events (
    stream_id   TEXT        NOT NULL,
    sequence    BIGINT      NOT NULL CHECK (sequence >= 0),
    event_type  TEXT        NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    envelope    JSONB       NOT NULL,
    PRIMARY KEY (stream_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_observation_events_event_type
    ON observation_events (event_type);
