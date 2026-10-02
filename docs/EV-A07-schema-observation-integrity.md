# EV-A07 — Schema / Observation Integrity

**Audit:** evidence-first production readiness, sequence EV-A01 → … → EV-A06 → **EV-A07 (this)** → EV-A08 → EV-A09
**Canonical audited state:** `6e1aa1a` (PR #1 head; main `1f26e42`)
**Scope:** contract layer (`app/core/contracts/*`), identity/hashing (`ids.py`), observation pipeline (dispatcher, sequence stores, projectors, reducer, routes), storage models/serialization, schema surface (pydantic request/response), contract-version negotiation, evidence/governance/lineage subsystem integrity, and the observation test suite. Read-only.
**Taxonomy:** `IMPLEMENTED_REAL / IMPLEMENTED_BOUNDED / IMPLEMENTED_SIMULATED / PARTIAL / UNIMPLEMENTED / UNKNOWN` · Confidence `CONFIRMED / INFERRED / UNVERIFIED`.

---

## STATUS: **FAIL**

The contract *kernel* is genuinely strong — frozen framework-agnostic models, total error taxonomy, RFC-9562 UUIDv7, canonical-JSON content hashes, lock-correct sequence allocation, bounded replay with honest `SYNC_REPLAY_EXHAUSTED` recovery, fail-closed auth on every observation route, and a real 63-test acceptance suite (green in 2.34 s). But the layer around it fails production reality: **the declared production durability path is non-functional on three stacked faults** (sync engine handed to an async Postgres binding, observation tables never created by `init_db`, `schema.sql` never executed by any migration path), **capabilities advertise schema contracts and event types that have no server and no emitter**, **two components are dead/broken while their tests stay green by mocking the broken interface**, and **allocate-then-persist can burn sequence numbers permanently with no reconcile path**.

Register: **EV-A07-001 … EV-A07-012**.

---

## 1. Surface inventory

| Layer | Files | Verdict |
|---|---|---|
| Error contract | `core/contracts/errors.py` — 23-code `ERROR_TAXONOMY`, `build_error_envelope`, frozen models, contentHash over error body | `[IMPLEMENTED_REAL]` (totality tested) |
| Event contract | `core/contracts/events.py` — `EvolutionEventEnvelope` generic, `make_envelope`, UUIDv7, payload-only hash | `[IMPLEMENTED_REAL]` |
| Provenance | `core/contracts/provenance.py` — `ContractMetadata`, `ObservationProvenance` (64-hex) | `[IMPLEMENTED_REAL]` |
| Observation contracts | `core/contracts/observations.py` — ISR/Fitness/Candidates/Recovery/Snapshot/Capability | `[IMPLEMENTED_REAL]` (Fitness typing soft — EV-A07-009) |
| Governance / lineage / evidence contracts | `core/contracts/{governance,lineage,evidence}.py` — lifecycle gates, immutable decisions, minimal evidence record | `[IMPLEMENTED_REAL]` models; write-side enforcement partial (006) |
| IDs / hashing | `core/ids.py` — RFC-9562 uuid7, `canonical_json` (sorted, ASCII, `default=str`), sha-256 | `[IMPLEMENTED_REAL]` |
| Sequence stores | `sequences/{store,memory,persisted,sql_binding,schema}.py` | memory REAL; persisted `[UNIMPLEMENTED]` in shipped runtime (001) |
| Dispatcher | `gateway/dispatcher.py` — allocate+persist under lock, per-subscriber failure isolation | `[PARTIAL]` (005) |
| Projectors | `projectors/{fitness,isr,governance,lineage}.py` + `base.py` `ProjectionContract` | fitness/ISR REAL; governance/lineage unrouted (002) |
| Reducer / aggregator | `readmodel/reducer.py`, `snapshot_aggregator.py` | reducer PARTIAL (009); aggregator dead (004) |
| Routes | `api/observation_routes.py` — capabilities/fitness/isr/snapshot/state, all `require_auth` | `[IMPLEMENTED_REAL]` for served set (probe 401/200/500) |
| Heartbeat | `gateway/heartbeat.py` | `[UNIMPLEMENTED]` broken import (003) |
| Storage models | `storage/{db,models}.py` — genomes + evolution_runs only | `[IMPLEMENTED_BOUNDED]` (009) |
| Legacy errors | `core/error_handler.py` (AppError/ErrorResponse/CircuitBreaker) | dead-in-routes, still tested/exported (007) |
| Test suite | `tests/observation/` — 16 files; 63 pass, 3 integration-deselect in 2.34 s | REAL but CI-scheduled only (010) |

---

## 2. Production durability — the declared path cannot run

### EV-A07-001 — `ENVIRONMENT=production` observation store fails on three stacked faults; `/observation/state` and `/snapshot` return 500
`[UNIMPLEMENTED]` · Confidence **CONFIRMED** (live probe + static)

Composition root (`main.py:68-71`): production swaps `InMemorySequenceStore` → `PersistedSequenceStore(SqlSequencePersistence(db_engine))`. Probed with `ENVIRONMENT=production`, valid `ADMIN_API_KEY` + `SECRET_KEY` (server boots — the production validator itself works ✓):

1. **Sync engine → async binding (first failure, TypeError):** `db_engine` is a *synchronous* `create_engine(...)` (`storage/db.py:12`), but `SqlSequencePersistence` issues `async with self._engine.begin()` (`sql_binding.py:51,56,62,77`). Probe: `prod_store_next: FAIL TypeError: 'contextlib._GeneratorContextManager' object does not support the asynchronous context manager protocol`. Every store operation dies before touching SQL.
2. **Tables never exist:** `init_db()` creates only `GenomeRecord` + `EvolutionRun` — probe `tables_after_init_db=['evolution_runs', 'genomes']`, `observation_tables_present=False`. Nothing in `app/` ever executes `sequences/schema.sql`.
3. **`schema.sql` is Postgres-only and has no runtime consumer:** `TIMESTAMPTZ`/`JSONB` columns (`schema.sql:24-25`); the header claims consumption "by deployments via the platform migration path" — **no migration path exists** (no Alembic, no `create_all` for these tables, no startup DDL). The only consumer is the *test* fixture `_bootstrap_schema` against a real Postgres (`tests/conftest`).

Live result: `GET /observation/state` → **500 `PLATFORM_INTERNAL`** (correct envelope shape, `traceId` present — and per EV-A06-001 that id never reaches a log). `GET /observation/snapshot` same store path. `GET /observation/fitness` still 200 (it reads genomes through legacy sync sessions, not the sequence store) — so production observation is *half* alive, masking the breakage.

Latent only because EV-A05-001 showed no doc sets `ENVIRONMENT=production` — but the moment anyone does (the correct move per EV-A05), recovery/snapshot/capabilities-streams break while fitness keeps answering.

---

## 3. Capabilities vs reality

### EV-A07-002 — Capabilities over-advertise: unserved schema contracts, phantom event types, empty production stream list
`[PARTIAL]` · Confidence **CONFIRMED**

`GET /observation/capabilities` (probe 200, auth-gated ✓) returns:

- **`observationSchemas` lists `platform.observation.lineage` and `platform.observation.candidates`** — `LineageProjector` and `GovernanceProjector` exist (`projectors/lineage.py`, `governance.py`) but **zero routes import them** (grep: definitions + tests only). No HTTP surface serves either contract. Negotiation says "supported"; the router says 404.
- **`eventTypes` = full `EventType.__args__`**, including `event.dropped` and `observation.error` — **no emitter anywhere** constructs those types (only the `Literal` definition matches). Likewise `observation.heartbeat` is advertised but its emitter cannot import (EV-A07-003).
- **`supportedStreamIds` enumerates `store._counter`** (`capabilities.py:20-23`) — a *private attribute of the in-memory store only*. `PersistedSequenceStore` has no `_counter` (probe: `persisted_has_counter False`) → **production always advertises `[]`** while still claiming the `stream_replay` feature. Leaky abstraction inverted: the dev store works, the production store cannot answer.

### EV-A07-003 — `HeartbeatEmitter` is unimportable dead code; advertised heartbeat path does not exist
`[UNIMPLEMENTED]` · Confidence **CONFIRMED**

`gateway/heartbeat.py:3` — `from core.contracts.events import EventTypes`. Probe: **`ModuleNotFoundError: No module named 'core'`** (correct root is `app.core`). Second defect: the module `app.core.contracts.events` exports `EventType` (a `Literal`), not an `EventTypes` class with `.HEARTBEAT` — even a fixed import would `AttributeError`. Nothing in `main.py` starts an emitter; grep shows the class referenced only by its own file. The V1-04 liveness contract is advertised (002) and unimplementable as shipped.

---

## 4. Dead component, green test — interface mocked into agreement

### EV-A07-004 — `SnapshotAggregator` calls a method the real projector does not have; its tests mock that nonexistent name
`[IMPLEMENTED_SIMULATED]` · Confidence **CONFIRMED**

- `snapshot_aggregator.py:11` calls `await self._governance.project_generation(...)`.
- Real `GovernanceProjector` methods: **`get_generation`, `get_candidate`** (probe: `MATCH=False`).
- `tests/observation/test_snapshot_data_aggregator.py:13,29` stubs **`gov_proj.project_generation.return_value...`** — the test constructs the fantasy interface the aggregator expects. Both tests pass (in the 63) while the aggregator wired to a real projector would `AttributeError` (then be swallowed — see below).
- Not routed anywhere (grep: self + test only) — dead in production, alive in CI as a false positive.
- Aggregator also swallows **all** projector failures to `facets[...]=None` (`:8-12`) despite its docstring "real facets, never log summary" — a partial-outage would surface as silent `null` facets with no `PLATFORM_DEGRADED` signal (contrast the ISR projector's explicit 503-over-fake policy).

---

## 5. Sequence integrity — allocate, then hope

### EV-A07-005 — Counter and log are not updated atomically; a failed `persist` burns the sequence forever; emit failures are swallowed
`[PARTIAL]` · Confidence **CONFIRMED** (static + memory probe)

- Dispatcher holds one `asyncio.Lock` across `next()` + `persist()` (`dispatcher.py:44-60`) — but for `PersistedSequenceStore` those are **two separate DB transactions** (`atomic_next` commits, then `insert_envelope` opens its own). Failure between them (or any exception in `persist`) leaves `next_val` advanced with no envelope.
- In-memory equivalent probe: `gap_memory: next=0 current=0 envelopes=0 (counter ahead of log by 1)` — `current()` reports sequence 0 while the log is empty. Downstream: `_materialize_state(store, stream, 0)` finds no tail → `consistentThrough=0, lastEvent=None` — AM-3 claims consistency through an event that does not exist; `recover_state`'s `gap = current - after` counts phantom sequences and can raise spurious `SYNC_REPLAY_EXHAUSTED`.
- Callers swallow emit failures: `evolution.py:37-38` / `elite_evolution.py:35` wrap `dispatcher.emit` in `try/except → logger.error("Envelope emission failed")` — run continues, gaps accumulate, no reconcile/re-allocate path, no `event.dropped` emission (002), and per EV-A06-001 that error log lands only on stderr-without-file for stdlib… (here loguru, but the gap itself is never surfaced on any API).
- No test covers persist-failure recovery (suite covers happy-path monotonicity and PG concurrency, not counter/log divergence).

---

## 6. Integrity hashes — written, never read back

### EV-A07-006 — `contentHash` is write-only on events; `signature` is never set; evidence E-3 existence check is not enforced by referencers
`[PARTIAL]` · Confidence **CONFIRMED**

- `make_envelope` computes payload-only `integrity.contentHash` (`events.py:85-101`) ✓ — tested (`test_sequence_store.py:51-61`). **No read path re-verifies it**: `replay`/`read_after`/`/observation/state` return envelopes as stored; grep shows no `recompute → compare` anywhere for events. Tampering with stored payload JSON would go undetected by the platform.
- `EventIntegrity.signature` — **zero assignments in `app/`** (grep `signature\s*=` empty): every envelope ships `signature: null`. Expected today (HMAC/Ed25519 is EV-A08/09 territory per AGENTS) but the field's presence implies a check that never happens.
- Evidence subsystem enforces E-1 (hash at write) and E-2 (immutable overwrite refusal) — tested. **E-3** ("referencing subsystems validate existence via this subsystem before recording their evidenceRefs" — `evidence/subsystem.py:3-4`) is **not enforced**: `governance/subsystem.py` copies `list(cmd.evidenceRefs)` into decisions/gates/certifications with no `EvidenceSubsystem.exists()` call. Dangling evidence refs are structurally possible.

---

## 7. Two error systems, one advertised

### EV-A07-007 — Legacy `core/error_handler.py` (AppError/`ErrorResponse`) is dead in routes but exported and tested as if canonical
`[PARTIAL]` · Confidence **CONFIRMED**

- **Live path:** `main.py` installs `middleware/error_handler.py` → `ErrorEnvelope` for every response (probe bodies confirm `metadata/error/recovery/provenance`).
- **Legacy path:** `core/error_handler.py` (266 lines) — `AppError` hierarchy, `handle_app_error` decorator raising `HTTPException(detail=ErrorResponse(...))`, `CircuitBreaker`, `create_error_response`. **No production module imports it** (grep: definitions only). Its shape (`{error, message, details, request_id, timestamp}`) is *not* the contract envelope.
- Yet `app/schemas/__init__.py` exports `ErrorResponse` in `__all__` as a first-class schema, and `tests/test_production_features.py:8` imports `AppError/EvolutionError/retry_with_backoff` — the only consumer. Docs (EV-A04-016) point operators at this legacy style too.
- Risk: a future route "standardizes" on the exported name and ships a second wire shape — the exact class of drift EV-A04-002 already caught between middleware 401s and envelopes.

### EV-A07-008 — Contract-version negotiation codes exist only on paper
`[UNIMPLEMENTED]` · Confidence **CONFIRMED**

`ContractVersionError` (`exceptions.py:100`) has **zero raise sites**; `CLIENT_INVALID_CONTRACT_VERSION`, `CONTRACT_DEPRECATED`, `CONTRACT_UNSUPPORTED_VERSION` appear only in the taxonomy table. No route reads a contract-version header/param, no deprecation state machine, no `renegotiate_contract` recovery path is reachable. Taxonomy totality tests pass over codes nothing can emit — completeness theater for the versioning dimension (contrast: `SYNC_*` codes are fully live).

---

## 8. Schema-surface inconsistencies

### EV-A07-009 — Serialization and fold drift across the served surface
`[PARTIAL]` · Confidence **CONFIRMED**

- **`GenomeRecord.to_dict` / `EvolutionRun.to_dict`** use `str(datetime)` (naive, space-separated, `2026-09-23 19:56:23.123456`) — `/evolve/runs` and `/evolve/run/{id}` responses are *not* ISO-8601, unlike envelope `occurredAt`/`evaluatedAt` (tz-aware ISO). Two datetime dialects on one API.
- **`ErrorResponse.timestamp`** default: `datetime.utcnow().isoformat()` — deprecated naive UTC (schemas/evolution.py:106), inconsistent with `now_utc()` used by contracts.
- **`FitnessReport.candidates`**: non-frontier candidates are appended with **`scores={}`** (`fitness.py:69-76`, comment "per-candidate detail available via engine" — no API serves it). Contract field is `scores: dict` without min-content; dashboards get hollow rows for every non-frontier candidate.
- **`FitnessReport.objectives` / `candidates` typed bare `list`** (observations.py:77-78) — no `list[FitnessObjective]`/`list[CandidateFitness]`; frozen but untyped, so wrong-shaped elements pass validation.
- **Reducer drops `operational.feedback_received`**: `FACET_FOR_EVENT` has no entry → `fold` returns state unchanged (`reducer.py:17-19`) while the lineage contract models a `feedback` list (`lineage.py:61-82`, incl. `influencedNextGeneration`). Feedback events never reach the read-model facet. (`observation.heartbeat`/`event.dropped` no-op is intentional for the first, missing-emitter for the latter — 002/003.)
- **Elite `_EVENT_TYPE_MAP` lacks `evolution_failed`** (`elite_evolution.py:24`) — falls back to `evolution.stage_changed` (same as standard engine's explicit mapping): failure semantics live only in `payload.type`, not `eventType`; contract consumers filtering `eventType` cannot distinguish failure streams. Design smell, not a crash.
- **`schemas/query.py` `QueryInput.query: str`** — no `min_length`; unbounded query string accepted wherever used.

### EV-A07-010 — Observation acceptance suite is real but outside the canonical local gate
`[PARTIAL]` · Confidence **CONFIRMED**

- `autonomous-api/tests/observation/` — 16 files: taxonomy totality, envelope audit (UUIDv7 uniqueness, per-stream sequences), sequence store (10k monotonic, concurrent streams, bounded replay, payload hash), replay exhaustion + AM-3 state assertions, auth fail-closed, provenance integrity, reducer equivalence, fitness authoritative Pareto, ISR projector, evidence/governance/lineage subsystems, snapshot aggregator, PG concurrency (`pytest.mark.integration`).
- Verified this session: **`63 passed, 3 deselected, 2.34 s`** (venv, `-m 'not integration'`).
- **CI runs them** (`ci-cd.yml` `working-directory: autonomous-api`, `pytest tests/` with a Postgres service for integration).
- **The canonical local gate does not:** workspace `pyproject.toml` `testpaths = ["tests"]` (root) — `python -m pytest` never collects `autonomous-api/tests/**`. A green 4252-run can coexist with a broken observation suite until CI reports. (Inverse of EV-A04-015: root suite untested in CI, observation suite untested locally.)

### EV-A07-011 — Observation route dependencies resolve store before auth
`[PARTIAL]` · Confidence **INFERRED** (static ordering; misconfiguration not reachable in shipped import order)

Every route signature lists `Depends(get_store)` (or projector getter) *before* `Depends(require_auth)` (e.g. `observation_routes.py:111-114`). FastAPI solves in declaration order: if `configure_observation` had not run, an **unauthenticated** caller would receive `Observation subsystem not configured` (500-envelope) instead of 401 — leaking configuration state pre-auth. In the shipped app `configure_observation` runs at import, so `_store` is always set; probe confirms unauth → **401** today. Latent ordering bug, not a live hole.

---

## 9. Positives — the kernel that holds

### EV-A07-012 — Contract kernel and acceptance suite are production-grade
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

- **Error contract:** taxonomy is a single source of truth with **totality enforced by test** (`test_error_taxonomy.py:23-26` — every `ErrorCode` classified exactly once); `build_error_envelope` rejects unknown codes; contentHash over error body; traceId correlation-only (asserted null when unused).
- **Event contract:** UUIDv7 layout correct (`ids.py:19-35` matches RFC 9562 bit layout; version/variant asserted in tests); payload-only canonical hash survives re-wrapping; `correlationId` mandatory (`min_length=1`); frozen envelopes; per-stream sequence scoping tested (100 emits, concurrent streams, PG 20×500-row-lock suite in CI).
- **Replay/recovery:** bounded `limit≤1000`, honest `SYNC_REPLAY_EXHAUSTED` + `resyncFromSequence` (probe/test: 409 + recovery action), unknown stream → `SYNC_STREAM_NOT_FOUND` envelope with metadata+provenance, AM-3 `consistentThrough`/`lastEvent` semantics asserted (`test_replay_exhaustion.py:50-64`).
- **Auth:** every observation route `Depends(require_auth)`; probe production unauth → 401; `test_auth_fail_closed.py` in suite.
- **ISR projector:** 503-over-fake policy, per-revision memo for byte-identical projections, sorted facets for stable hashes — declared gap surfaced honestly (`/observation/isr` 503 until `CanonicalIsrAccessor` bound — matches `main.py` not passing `isr_projector`).
- **Fitness:** Pareto frontier computed platform-side (`pareto_front_analysis`), dashboard forbidden to recompute (contract comment + test `test_fitness_authoritative_pareto.py`); empty generation returns a valid empty report (probe 200).
- **Governance contract:** legal-transition + required-gate tables data-driven (`governance.py:38-46,143-154`), frozen decisions with supersede-not-mutate rule.
- **Evidence E-1/E-2** enforced at write with tests (E-3 gap noted in 006).
- **`schema.sql`** is DDL-canonical, `CREATE TABLE IF NOT EXISTS`, PK `(stream_id, sequence)` + CHECK — correct *as Postgres spec* (gap is execution, EV-A07-001).
- Contracts are import-light (`pydantic` only) — the "no FastAPI/DB in contracts" rule holds on inspection.

---

## 10. Verification appendix (evidence log)

- Static reads: `contracts/{errors,events,provenance,observations,governance,lineage,evidence}.py`, `ids.py`, `sequences/{store,memory,persisted,sql_binding,schema}.py`, `observation_routes.py` (full), `dispatcher.py`, `capabilities.py`, `heartbeat.py`, `reducer.py`, `snapshot_aggregator.py`, `projectors/{base,fitness,isr,governance,lineage}.py`, `storage/{db,models}.py`, `schemas/{evolution,query}.py`, `core/error_handler.py`, `evidence/subsystem.py`, `evolution.py`, `main.py:1-170`, `tests/observation/{conftest,test_sequence_store,test_replay_exhaustion,test_error_taxonomy,test_event_envelope_audit}.py`.
- Greps: `HeartbeatEmitter` references (self only); `event.dropped|observation.error` emitters (definitions only); `signature\s*=` (none); `ContractVersionError` raise sites (none); `LineageProjector|GovernanceProjector` routes (none); `SnapshotAggregator|project_generation` (self + mock test); `handle_app_error|AppError` in `app/` (defs only); `dispatcher.emit|set_dispatcher` (wired via `main.py:125-126` ✓); `contentHash` consumers (compute-only for events); governance `evidenceRefs` (copied, never validated).
- Probes (`Temp/opencode/ev07/ev07_probe.py`):
  - `heartbeat_import: FAIL ModuleNotFoundError: No module named 'core'`.
  - `governance_projector_methods=['get_candidate','get_generation'] aggregator_wants='project_generation' MATCH=False`.
  - `tables_after_init_db=['evolution_runs','genomes']`, `observation_tables_present=False`.
  - `prod_store_next/current: FAIL TypeError` (sync engine vs `async with`) — **first fault before SQL**.
  - `fitness_empty: OK candidates=0 frontier=[]`; `gap_memory: next=0 current=0 envelopes=0`.
  - Production server boot OK (`ENVIRONMENT=production` + `SECRET_KEY` accepted); `prod_capabilities: 200`; **`prod_state: 500 PLATFORM_INTERNAL`** (envelope-valid); `prod_fitness_empty: 200`; `prod_capabilities_unauth: 401`.
  - `persisted_has_counter: False`.
- Suite: `autonomous-api venv -m pytest tests/observation -m 'not integration'` → **63 passed, 3 deselected, 2.34 s**.
- CI cross-read: `ci-cd.yml` lines 14, 28-37, 48-50 (Postgres service + `pytest tests/` in `autonomous-api`); `test_sequence_concurrency_pg.py` `pytestmark = pytest.mark.integration`.
- Git: `schema.sql` tracked (`ba0e59c`); `git ls-files app/observation/sequences/` lists all six files.
- Gates: root `python -m pytest` re-run after report write; PR #1 head poll at close-out.
- Not probed: PG `SqlSequencePersistence` against live Postgres (integration tests cover happy path in CI; the shipped-runtime failure occurs before SQL); read-time hash-tamper simulation (static: no verify path exists to invoke); `Renegotiate` contract flows (no implementation to probe).

---

## 11. Conclusion & next gate

**FAIL.** Split cleanly in two: the **contract kernel** (taxonomy, envelope, UUIDv7, hashing, sequence monotonicity, bounded replay, auth, Pareto authority, ISR honesty) is real, tested, and among the strongest code in this audit sequence — ship it. The **runtime shell around that kernel** is not: production durability is a three-layer lie (async/Postgres code bound to a sync SQLite engine with tables nobody creates), capabilities negotiate contracts and event types with no server behind them, one liveness emitter cannot import its own module, one aggregator's tests mock a method that does not exist, sequences can burn silently on persist failure, and hashes stop mattering the moment they are stored.

Must-fix order: make production store path executable end-to-end or remove it from `main.py` until a migration exists (001); stop advertising unserved schemas/emitters or serve them (002/003); delete or correctly wire `SnapshotAggregator` and fix its tests (004); make allocate+persist atomic or reconcile gaps + surface `event.dropped` (005); verify `contentHash` on replay and enforce E-3 (006); retire legacy `ErrorResponse` from exports/tests (007); implement or strike version-negotiation codes (008); unify datetime/ISO + type the report lists + give the reducer a feedback facet (009); put `autonomous-api/tests` into the local gate story (010).

**NEXT GATE: EV-A08 — Change Safety.**

*(Sequence: EV-A08 → EV-A09 Governance. Bandit-fix verification track remains separate; PR #1 head last known `6e1aa1a`.)*
