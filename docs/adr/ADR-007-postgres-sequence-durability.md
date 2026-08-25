# ADR-007: Postgres Sequence Durability Under Concurrency

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-24 |
| Relates to | ADR-001 (POC v1.1 event envelope), ADR-004 (gap-detection sync) |
| Scope | `observation/sequences/sql_binding.py`, `schema.sql`, `tests/integration/test_sequence_concurrency.py` (V1-07), CI Gate 3 |

## Context

The observation event stream's entire recovery model rests on `(streamId, sequence)` being **strictly monotonic with no gaps and no duplicates**: `LiveProjection`'s gap detector, duplicate guard, replay coordinator, and resync logic all assume it. This is a *constitutional correctness property*, not a performance convenience — the Phase B audit classified it as release-blocking (V1-07), and the remediation specified `ON CONFLICT ... RETURNING` with `UNIQUE(stream_id, sequence)`.

## Problem

Guarantee sequence integrity **under concurrent writers** with the following constraints:

1. Corruption is **unrecoverable**: a gap permanently breaks gap detection for that stream; a duplicate breaks idempotency. Theoretical arguments are insufficient — the constitution requires evidence-based verification.
2. Streams are created dynamically (per campaign), so any mechanism requiring pre-provisioning per stream is unsuitable.
3. The platform core must not depend on Postgres (plugin-first): the durability mechanism must sit behind the `SequencePersistence` port.
4. Development uses SQLite/in-memory stores; the concurrency guarantee must never be silently "verified" against a backend that cannot provide it.

## Decision

Three-part design:

1. **Atomic allocation via a single statement** — `observation_stream_counters` keyed by `stream_id`; `atomic_next` executes `INSERT ... ON CONFLICT (stream_id) DO UPDATE SET current_sequence = current_sequence + 1 RETURNING current_sequence`. Allocation and read are one atomic statement; the row lock serializes writers on the same stream.
2. **Structural second line of defense** — `observation_events` with `PRIMARY KEY (stream_id, sequence)`. Even if allocation logic were ever buggy, a double-persist is rejected by the database, converting silent corruption into a loud `IntegrityError`.
3. **Empirical release gate (V1-07)** — integration test: 20 concurrent writers × 500 increments ⇒ exactly 10,000 sequences, asserted contiguous and unique; plus a double-persist rejection test. Runs in CI Gate 3 against a **real `postgres:16-alpine` service container** — never SQLite. The test is wired into `v1.1-release-gate.yml` behind `pytest -m integration`.

All of it lives in `SqlSequencePersistence`, one implementation of the `SequencePersistence` protocol — Postgres is a backend, not a foundation.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| `CREATE SEQUENCE` per stream | Cannot be created dynamically at emit time without DDL in the hot path; unbounded catalog growth; awkward cleanup |
| Application-level lock (single writer process) | Single point of failure; forbids horizontal scaling; moves a durability guarantee into app memory where restarts break it |
| Redis `INCR` | Fast, but introduces a second system of record with weaker durability semantics than the store holding the envelopes; split-brain risk between counter and events |
| UUIDv7 timestamp ordering alone | Already used for `eventId`, but time-ordering is not dense: it cannot support gap detection (`104 → 107` must be detectable), which is the core recovery invariant |
| A dedicated event store (e.g., EventStoreDB) | Viable in principle; rejected for v1.1 as unnecessary infrastructure coupling when Postgres already stores the envelopes — revisit if event volume outgrows it |

## Trade-offs

- **Row-lock serialization per stream** — writers on the *same* stream serialize on one row. Accepted: one stream = one logical campaign; contention is bounded, and cross-stream writers never contend.
- **Two tables instead of one** — counters and events separated. Slight extra bookkeeping for clean semantics: allocation never depends on event-table state, and replay reads never touch the counter.
- **Postgres in CI** — a service container adds startup time and flake surface. Mitigated with healthcheck retries and an explicit readiness loop; acceptable price for empirical proof.
- **SQLite remains for dev/unit work** — but V1-07 is marker-gated (`-m integration`) so it can never run against SQLite by accident.

## Benefits

1. Atomicity guaranteed by the database engine, not by application code paths that could be refactored away.
2. Two independent mechanisms (counter atomicity + PK uniqueness) defend the same invariant — defense in depth, per the constitution's security-by-design ethos applied to data integrity.
3. The guarantee is **proven empirically on every merge**, not assumed.
4. The port preserves replaceability: CockroachDB, Spanner-class stores, or a dedicated event store can be substituted without touching the dispatcher, materializer, or client.

## Risks

| Risk | Mitigation |
|---|---|
| Extreme single-stream writer counts increase lock wait time | Monitor allocation latency (OTel metric candidate); partition hot streams if observed; batching of emissions is available without contract change |
| CI service-container flakiness | Healthcheck retries + readiness loop; failure is loud and blocks release (fail-closed, as intended) |
| Future backend substitution (e.g., CockroachDB) may differ subtly in `ON CONFLICT ... RETURNING` semantics | V1-07 is backend-agnostic in intent: any new `SequencePersistence` must pass the same 20×500 gate before acceptance |
| Replay-window growth on long-lived streams | Retention pruning exists in the binding; checkpointing strategy is tracked as future work below |

## Future evolution considerations

- **Sustained-load benchmark harness** complementing the correctness test (throughput/latency percentiles under hours-long load).
- **Partitioning or sharding** of `observation_events` by `(stream_id, sequence)` range for very long-lived streams.
- **Compaction/checkpointing**: periodically materialize `sequence N` snapshots so replay never scans from zero — pairs with the read-model checkpoint store.
- **Alternative backends**: CockroachDB binding for geo-distributed deployments, validated against the identical V1-07 gate.
