# VS-D30 — Observatory Inventory / Reconciliation

**Gate:** VS-D30 · **Objective:** VS1-OBJ-001 · **Mode:** ANALYTICAL / READ-ONLY
**Status of this document:** CURRENT_IMPLEMENTATION_EVIDENCE except where a
section is explicitly marked DESIGN_REFERENCE.
**Upstream alias:** the Observatory track cites the VS-D29 evidence-sufficiency
decision (`vertical_slice/evolution_decision_d29.py`, PASS / HOLD) as **D30A**.
No file was moved or renamed for this alias (authorized 2026-09-12).

---

## 1. Repository baseline

```text
HEAD:    ba952d48c998861b25f2ad160cf99bc52e018cd3
branch:  main
log -1:  ba952d4 vs1: D18 runtime interpretation, D19 evolution decision, D20 post-decision closure
diff:    evidence/factory.jsonl | 1 +   (1 insertion; pre-existing, untouched by D30)
```

Working-tree inputs D30 inspected but did not create (all untracked before D30):
`observatory/`, `docs/observatory/`, `generated/observatory/`,
`tests/observatory/`, `folder/*.md`, `vertical_slice/*d2[2-9]*`,
`certification/contracts/`, `docs/capability_boundaries/`, `docs/evolution/`.

Read-only assurance (entire D30 execution):

```text
files_created_inside_governed_repo=1 (this artifact, required by gate section 25)
tracked_modifications=0
generated_artifacts_mutated=0
formatters_run=0
generators_run=0
migrations_run=0
dependencies_installed=0
lockfiles_updated=0
services_mutating_state_started=0
external_state_mutated=0
runtime_execution=0 (no tests, builds, servers, or installs run during D30;
  all test counts below are static counts or pre-D30 verified runs cited as history)
```

## 2. Scope methodology

Discovery procedure (static inspection only; Read/Glob/Grep; no execution):

```text
search_terms: observatory dashboard telemetry event evidence trace timeline runtime
  evolution requirement capability governance authorization audit projection
  "read model" subscription stream websocket SSE metrics health diagnostic
  explain provenance Phoenix PubSub GenServer ETS OTP kafka redis rabbitmq
directories_scanned: observatory/ docs/observatory/ generated/observatory/
  tests/observatory/ compiler/ knowledge/ civilization/ evolution/
  product_factory/ learning/ constitutional_architecture/ certification/
  tiannara/ vertical_slice/ release/ autonomous-api/app dashboard reasoning-ui
  (first-party only)
file_extensions: .py .ts .tsx .md .json .jsonl .toml .sh
generated_vendor_exclusions: autonomous-api/.venv/** node_modules/**
  .git/** __pycache__/** (matched noise from these paths is disregarded)
unresolved_paths: package interiors below 2 levels (constitutional_architecture,
  tiannara deeper layers); dashboard/ and reasoning-ui/ interiors (name +
  top-level refs only); .env file contents (never read); runtime behavior
  (no execution per gate section 30)
inspection_limitations: static-only; breadth-first on core packages (2 levels);
  test counts are static `def test_` counts, not executions; no wire traffic observed
```

Runtime-neutrality check: zero Phoenix/PubSub/GenServer/ETS/OTP/mix.exs references
in first-party code outside `generated/`, `docs/`, `folder/` (design-reference
surfaces only). Zero kafka/redis/rabbitmq/websocket references in first-party
Python outside vendored environments. No Sentinel/Omega/ASC/Crucible directories
exist in this workspace.

## 3. Discovered components

| COMPONENT_ID | PATH | BOUNDARY | IMPLEMENTATION? |
|---|---|---|---|
| OBS-PY-BE | `observatory/backend/` (23 .py) | DIRECT_OBSERVATORY | YES — FastAPI + SQLite + in-memory bus |
| OBS-PY-FE | `observatory/frontend/` (Next.js 14.2.3) | UI_SURFACE | YES — pages, lib clients, 5 server proxy routes |
| OBS-ADAPTER | `observatory/adapters/tiannara/` (7 .py) | OBSERVATORY_DATA_SOURCE | YES — observe-only bridge into OBS-PY-BE |
| OBS-EX | `generated/observatory/` (27 .ex) | OUT_OF_SCOPE | NO — inert design output, see section 4.8 |
| CORE-COMPILER | `compiler/` | RELATED_BUT_OUTSIDE_SCOPE | YES (own service; zero coupling observed) |
| CORE-KNOWLEDGE | `knowledge/` | RELATED_BUT_OUTSIDE_SCOPE | YES (own service + SQLite; zero coupling observed) |
| CORE-CIV | `civilization/` | RELATED_BUT_OUTSIDE_SCOPE | YES (routers + in-memory bus; zero coupling observed) |
| CORE-EVO | `evolution/` | OBSERVATORY_DATA_SOURCE (potential) | YES — has `EvolutionObservabilityBus` + `/v1/evolution/observability`, `/metrics`; not wired to OBS-PY-BE (static) |
| CORE-PF | `product_factory/` | RELATED_BUT_OUTSIDE_SCOPE | YES (routers; zero coupling observed) |
| CORE-LEARN | `learning/` | OBSERVATORY_DATA_SOURCE (potential) | YES — `TelemetryEvent`, `PrometheusMetricsAdapter`, `/v1/learning/observability` (`/metrics`, `/health`, `/dashboard`, `/report`); not wired to OBS-PY-BE (static) |
| CORE-CONST | `constitutional_architecture/` | GOVERNANCE_SOURCE | YES — ISR schemas, evidence signing, governance dashboard; the constitutional authority OBS-PY-BE must not duplicate |
| CORE-TIAN | `tiannara/` | RUNTIME_SOURCE | YES — calibration harness CLI, JSONL hash-chain ledger; observed BY OBS-ADAPTER, never imports observatory |
| CORE-CERT | `certification/` | OBSERVABILITY_INFRASTRUCTURE | YES — trial ledgers, verdicts, escalation; LEARN-ONLY infra-storm ledger; no broker |
| VS-AUTH | `vertical_slice/*d2[2-9]*` + `tests/vs1/` | (upstream authority records, not components) | YES — D22–D28 VERIFIED pattern, D29 PASS/HOLD (= D30A) |
| EXT-API | `autonomous-api/app/` | RELATED_BUT_OUTSIDE_SCOPE | YES — separate FastAPI service; zero `observatory` references; own `observation/evidence/lineage` dirs (names only — see INV-001) |
| EXT-DASH | `dashboard/` (`@esap/dashboard`), `reasoning-ui/` | RELATED_BUT_OUTSIDE_SCOPE | UNKNOWN detail — zero `observatory` references observed |

Coupling fact: repo-wide static search finds `observatory.backend` imported only
by `tests/observatory/*` (63 matches, all tests). No core package imports
observatory; OBS-PY-BE imports no core package (stdlib + fastapi/pydantic/httpx
+ relative imports only). OBS-ADAPTER mirrors the event vocabulary without
importing backend (`adapters/tiannara/events.py:1-6` — see DUP-001).

## 4. Component inventory

Epistemic convention: fields not establisable statically read UNKNOWN (runtime),
NOT_OBSERVED (static absence), or NOT_APPLICABLE.

### 4.1 OBS-PY-BE — Python observatory backend

```text
COMPONENT_ID: OBS-PY-BE
PATH: observatory/backend/ (domain, config, store, bus, gateway, governance,
  projections{,_experiments,_fitness,_genomes,_knowledge,_provenance},
  api/routes, api/deps, main, workspaces_{store,service,routes},
  workspace_governance{,_store,_service})
RUNTIME / LANGUAGE: Python (>=3.11 per root pyproject) + FastAPI/Pydantic;
  deps: fastapi, uvicorn, pydantic, httpx (root pyproject, nothing else)
PURPOSE: observation/control surface over Tiannara: validated event ingest,
  canonical SQLite store, pure read projections, SSE fan-out, governed commands
RESPONSIBILITY: event observation, read models, UI data, command intake proxy
INPUTS: POST /observatory/events, POST /observatory/events/batch (writer role +
  X-Observatory-Token when configured); GET reads (no auth beyond headers)
OUTPUTS: 25 read endpoints under /observatory/*; GET /observatory/stream (SSE);
  POST /observatory/commands (operator clearance); export JSON/CSV; audit bundles
EVENTS_CONSUMED: canonical Event envelope (source/category/type/subject_id,
  correlation_id, causation_id, payload, epistemic_status, authorization,
  evidence_refs, provenance, severity)
EVENTS_EMITTED: workspace_* (knowledge category, OBSERVED); command_requested /
  command_rejected (governance); adapter-originated runtime/evolution/knowledge/
  evidence/governance events via ingest
STATE_HELD: events table; workspaces + audit; governance state/roles/snapshots/
  audit-chain (7 tables, one SQLite file, WAL mode)
PERSISTENCE: single SQLite file shared by 3 stores (main.py:27,31,33);
  default observatory.sqlite3 or OBSERVATORY_DB_PATH; content-hash idempotency
  (same id + same hash = dedupe; same id + different hash = StoreIntegrityError);
  batch append atomic (all-or-nothing); workspace snapshot/audit hash-chains
READ_MODEL: pure functions events-in/state-out (projections*.py); never-fabricate
  rule stated (projections.py, domain.py:3-4); unknown/not_measured/missing
  preserved (see section 11)
API_SURFACE: GET dashboard/overview/runtime/governance/health/timeline/
  evolution+evidence+requirement+capability by id / experiments(+id) /
  fitness(+id) / genomes(+id) / knowledge(+subject/memory) / provenance(+subject) /
  search / export / audit-bundle+trace+explain; exception map 404/403/409/400
  (main.py:63-81)
UI_SURFACE: none (backend only; served to OBS-PY-FE)
SUBSCRIPTION / STREAMING: AsyncEventBus (asyncio.Queue per subscriber,
  drop-oldest on full, never raises for slow consumers); SSE endpoint only;
  no websocket; no broker; no replay endpoint
DEPENDENCIES: stdlib + fastapi/pydantic/httpx; zero sibling-package imports
UPSTREAM_SOURCES: HTTP ingest callers (OBS-ADAPTER via HttpObservatoryTransport);
  no core package wired (static)
DOWNSTREAM_CONSUMERS: OBS-PY-FE (browser-direct reads/stream; proxied commands
  and workspaces)
AUTHORIZATION_BOUNDARY: deps.py require_writer (token + role in
  {operator,architect,admin,system}) on 3 write routes; require_operator
  (clearance in {operator,architect,admin}) on /commands; GovernanceBoundary
  (fail-closed, executes nothing); workspace routes disabled by default
  (OBSERVATORY_WORKSPACES_ENABLED=true) with trusted-proxy identity
GOVERNANCE_DEPENDENCIES: env config only (OBSERVATORY_API_TOKEN,
  OBSERVATORY_MAX_BATCH_SIZE, workspace flags); NOT the constitutional kernel
  (see authority matrix)
CONFIGURATION_DEPENDENCIES: OBSERVATORY_DB_PATH, OBSERVATORY_API_TOKEN,
  OBSERVATORY_CORS_ORIGINS, OBSERVATORY_MAX_BATCH_SIZE (default 500 on
  invalid/non-positive), workspace + proxy flags
FAILURE_SEMANTICS: explicit 400/401/403/404/409/413 on HTTP paths;
  audit-failure must not mask original (gateway.py:430-432); slow-subscriber
  drops contained to subscriber (bus.py:29-36); bad-iso search bound propagates
  (500 path — see GAP-003); missing timestamp → now (domain.py:55-56)
SECURITY_CHARACTERISTICS: token header compare; marker-substring redaction of
  command params (8 markers); workspace secret-pattern scan (7 patterns);
  payloads stored verbatim JSON (see GAP-006); actor headers self-declared on
  reads (see section 12)
TEST_EVIDENCE: tests/observatory/ — 27 files, ~291 static test functions;
  pre-D30 verified run 290 passed; covers domain/store/bus/gateway/governance/
  all projections/API surfaces/safe-mode/batch/workspaces/frontend-boundary
DOCUMENTATION_EVIDENCE: docs/observatory/* is DESIGN_REFERENCE (section 4.9),
  not implementation evidence
PROVENANCE_EVIDENCE: event id evt-{category}-{sha256[:24]} over
  category/source/type/subject/payload/timestamp (domain.py:133-140);
  content hash sha256(canonical_json) (domain.py:129-130); provenance dict
  carried, never verified (see section 14)
CLASSIFICATION: CANONICAL_SOURCE_CANDIDATE (strongest evidenced observation
  surface in this repository; NOT a canonicalization decision)
CONFIDENCE: HIGH (implementation) / MEDIUM (production suitability — never
  runtime-verified by D30)
OVERLAPS: DUP-001..DUP-004, DUP-007
GAPS: GAP-001..GAP-007
RISKS: single-file SQLite shared by 3 stores; unauthenticated reads when token
  unset; verbatim payload persistence; trusted-proxy identity spoofable on
  direct backend access
UNRESOLVED_QUESTIONS: AQ-001, AQ-002, AQ-003, AQ-005, AQ-006, AQ-008, AQ-009
```

### 4.2 OBS-PY-FE — Next.js frontend

```text
COMPONENT_ID: OBS-PY-FE
PATH: observatory/frontend/ (17 page routes + components/* + lib/* +
  5 server proxy routes); deps: next 14.2.3, react 18.3.1, TS 5.4.5
RUNTIME / LANGUAGE: TypeScript/React, App Router; all data pages "use client";
  server-only: layout, app/api/* routes, lib/auth.ts, lib/rate-limit.ts
PURPOSE: display/correlate/explain/request surface over OBS-PY-BE
INPUTS: backend reads via NEXT_PUBLIC_OBSERVATORY_API_URL (default
  http://127.0.0.1:8000); session cookie (httpOnly, HMAC-SHA256, 8h) for proxy
  routes; operator passphrase (login, React state only, never stored)
OUTPUTS: rendered views (overview/console/runtime/knowledge/experiments/
  fitness/genomes/audit/workspaces/governance/evolution+evidence detail);
  saved-trace localStorage (explicitly disclaimed as non-evidence);
  export/audit links; command + workspace mutations via same-origin /api/*
SUBSCRIPTION / STREAMING: SSE hook (use-event-stream.ts:33, overview page only
  with dashboard fallback) + 5s setInterval polling on 15 pages; console +
  workspaces one-shot; no websocket; no reconnect/backpressure handling observed
AUTHORIZATION_BOUNDARY: command proxy (enabled flag + session + clearance-gated
  action set + 10/min rate limit, server-side); workspaces proxy (enabled flag +
  session, role mapping); login/logout/status session routes; backend token
  (OBSERVATORY_BACKEND_TOKEN) server-side only — never in client bundle
  (static); reads/stream/export/audit go browser-direct (backend auth UNKNOWN
  from frontend — see section 12)
SECRETS_HANDLING: passphrase httpOnly cookie session; no tokens in localStorage
  (only saved traces); NO client-side redaction (KeyValue/EventTimeline/detail
  pages render raw provenance/actors/hash_chain/evidence_refs); server-workspace
  secrets warning banner (ServerWorkspacePanel.tsx:50-53)
FAILURE_SEMANTICS: NOT_OBSERVED in depth (fetch error paths not surveyed);
  workspace create button disabled on empty name; delete behind window.confirm
TEST_EVIDENCE: tests/observatory/test_frontend_boundary.py (static surface
  assertions); no component/E2E tests observed
CLASSIFICATION: UI_SURFACE (CANONICAL_SOURCE_CANDIDATE for presentation only
  within the observatory boundary; no authority claims)
CONFIDENCE: HIGH (structure) / MEDIUM (fetch-failure behavior — not surveyed)
OVERLAPS: none evidenced
GAPS: GAP-004 (audit() client defined, no UI call-site); client fetch-failure
  semantics not inventoried (limitation)
UNRESOLVED_QUESTIONS: AQ-004, AQ-010
```

### 4.3 OBS-ADAPTER — Tiannara runtime bridge

```text
COMPONENT_ID: OBS-ADAPTER
PATH: observatory/adapters/tiannara/ (config, events, redaction, client,
  runtime_adapter, logging_handler)
RUNTIME / LANGUAGE: Python (stdlib + httpx); mirrors backend vocab WITHOUT
  importing backend (events.py:1-6)
PURPOSE: observe-only, non-blocking bridge: Tiannara runtime → OBS-PY-BE ingest
INPUTS: observe()/observe_blocking() calls; stdlib logging handler;
  batch loop (size 100, flush 0.5s, retries 3, backoff)
OUTPUTS: POST /observatory/events + /events/batch (actor system, token header
  when configured); failure JSONL (observatory_adapter_failures.jsonl);
  sent/dropped/failed counters
EVENT_IDENTITY: evt-{category}-{sha256[:24]} (same construction, separate code —
  DUP-001); invalid category/severity/epistemic → ValueError; bad timestamp
  raises (no silent now — differs from backend domain default)
REDACTION: 9-marker superset + depth cap + 4000-char truncation (DUP-002);
  applied to payload + provenance when enabled
FAILURE_SEMANTICS: taxonomy RetryableTransportError (timeout/transport/5xx)
  vs PermanentTransportError (409/other 4xx, body truncated 200 chars);
  queue-full → dropped_events += 1 + warning (never blocks caller);
  loop-closed → silent return; stop timeout → warning + cancel; audit of
  command paths: never commands/deploys/mutates (doc 1-9)
STATE_MUTATION: local counters + failure log only
SIDE_EFFECTS: network (HTTP POST); IO (failure log)
TEST_EVIDENCE: test_adapter.py, test_adapter_batch.py, test_adapter_runtime.py
CLASSIFICATION: ADAPTER_CANDIDATE (already functioning as one; classification
  records observed role, not a promotion)
CONFIDENCE: HIGH
OVERLAPS: DUP-001, DUP-002
UNRESOLVED_QUESTIONS: AQ-002 (cross-process transport is plain HTTP; adequacy
  for scale unassessed — D30 records only)
```

### 4.4 CORE-EVO / CORE-LEARN — observability-capable core packages

```text
COMPONENTS: evolution/ (SelfEvolutionEngine, EvolutionObservabilityBus with
  LoggingObservabilityEmitter, /v1/evolution/observability + /metrics);
  learning/ (TelemetryEvent, TelemetryAdapterRegistry, PrometheusMetricsAdapter,
  /v1/learning/observability with /metrics /health /dashboard /report,
  kill-switch governance)
BOUNDARY: OBSERVATORY_DATA_SOURCE (potential — capability present, wiring absent)
CLASSIFICATION: ADAPTER_CANDIDATE (candidate sources, not decisions)
CONFIDENCE: MEDIUM (2-level breadth; interiors UNKNOWN)
EVIDENCE: evolution/observability.py:68,151,160; evolution/observability_api.py:127;
  learning/telemetry/models.py:27; learning/telemetry/adapters.py:59;
  learning/observability/api.py:93,99,105,120
OPEN: whether their events/metrics should flow into OBS-PY-BE (D31 scope, not D30)
```

### 4.5 CORE-CONST — constitutional architecture (governance source)

```text
COMPONENT: constitutional_architecture/ (ConstitutionISR, GovernanceDecision,
  AuditEvent/AuditEvidenceISR, HMAC-SHA256 evidence signing via
  AUDIT_EVIDENCE_SIGNING_KEY, FileBackedConstitutionVersionRepository,
  governance dashboard FastAPI app with require_user/permission,
  /health/live + /metrics; TelemetryEngine/MetricsCollector/TracingEngine;
  in-memory VerificationEventBus/CompilerEventBus/DeploymentEventBus)
BOUNDARY: GOVERNANCE_SOURCE
CLASSIFICATION: CANONICAL_SOURCE_CANDIDATE for constitutional authority,
  governance decisions, and evidence signing (strongest evidenced; NOT a
  decision to route observatory auth through it)
CONFIDENCE: MEDIUM (2-level breadth; 28-file local test dir + central tests)
NOTE: OBS-PY-BE governance (GovernanceBoundary, workspace governor) is a
  SEPARATE, smaller, display-boundary mechanism. Any convergence is D31+ scope.
```

### 4.6 CORE-COMPILER / CORE-KNOWLEDGE / CORE-CIV / CORE-PF

Each is an independently serving package (FastAPI apps/routers, own auth +
audit events, health endpoints; knowledge persists to SQLite; civilization and
evolution use in-memory buses; no external brokers found). Zero static coupling
to `observatory/` in either direction. Boundary: RELATED_BUT_OUTSIDE_SCOPE.
Classification: UNKNOWN (as observatory inputs — capability present in principle,
wiring absent in evidence). No duplication claimed: separate responsibilities
with no overlapping-responsibility evidence.

### 4.7 CORE-TIAN / CORE-CERT — runtime source / observability infrastructure

`tiannara/` (Phase 31 harness CLI; JsonlEvidenceLedger hash-chain;
`evidence/factory.jsonl` default path — the one tracked modification);
observed BY OBS-ADAPTER, imports nothing from observatory. Boundary:
RUNTIME_SOURCE. `certification/` (hash-chained verdict/infra-storm/governance
ledgers under release/evidence/, gitignored run output; escalation policy;
cost/energy metrics). Boundary: OBSERVABILITY_INFRASTRUCTURE. Neither is an
observatory authority; both are candidate evidence inputs (D31 scope).

### 4.8 OBS-EX — generated Elixir observatory (DESIGN_REFERENCE, inert)

27 `.ex` modules mechanically extracted from `folder/ob_backend.md`
(Supervisor + Store(ETS) + Phoenix.PubSub EventBus + Gateway + Projections +
typed Events + API). No mix.exs, no config, parse-checked only
(`Code.string_to_quoted`); README states "not runtime code of this workspace.
Nothing here is compiled, executed, or depended upon"; zero references from
first-party code/config/scripts. Classification: OUT_OF_SCOPE as implementation;
retained as DESIGN_REFERENCE for the Elixir-era design. DUP-007 records the
nominal overlap with OBS-PY-BE explicitly as non-duplication (different
epistemic kinds: inert design output vs live implementation).

### 4.9 docs/observatory/ — DESIGN_REFERENCE (all 10 files)

README (principle + "draft for review… Nothing here authorizes implementation"),
ARCHITECTURE, API_CONTRACT (Elixir surface), EVENT_MODEL, EVIDENCE_MODEL
(anchors VS1 D22–D29 as reference implementation of the pattern),
GOVERNANCE_BOUNDARY (marks itself "illustrative shape"; cites `D30 NOT
AUTHORIZED` — now superseded by this execution), UI_SPEC, CODE_QUALITY
(Elixir CI gates with no workspace config observed), TEST_STRATEGY,
DEFINITION_OF_DONE. UNVERIFIED-as-implementation claims: ARCHITECTURE.md:6-8
(Omega/Sentinel/ASC/Crucible layering — no such modules in workspace);
CODE_QUALITY.md:59-69 (Elixir CI — no config observed). Per section 24 of the
gate: IMPLEMENTED=NO / DESIGN_REFERENCE=YES for all ten; none cited as proof
of implementation anywhere in this inventory.

### 4.10 Test surfaces (evidence, not components)

`tests/observatory/` (~291 static tests, pre-D30 run 290 passed) covers OBS-PY-BE
+ OBS-ADAPTER + frontend boundary. `tests/vs1/` (30 files, >200 static tests)
covers the D22–D29 chain. `tests/cbc1/` (15 files, ~240+ static tests) covers
certification contracts. Canonical run excludes `docker_integration` and
`certification` markers (pyproject). No E2E/component tests for OBS-PY-FE
observed. No runtime verification performed by D30 (static only).

## 5. Responsibility matrix

Columns: BE = OBS-PY-BE · FE = OBS-PY-FE · AD = OBS-ADAPTER · CORE = aggregate
of section 4.4–4.7 (best present capability, wiring absent) · EX = OBS-EX as
DESIGN_REFERENCE (describes the generated artifact, not a system claim).

| Responsibility | BE | FE | AD | CORE | EX |
|---|---|---|---|---|---|
| requirement_observation | PRESENT | PRESENT | ABSENT | UNKNOWN | design |
| capability_observation | PRESENT | PRESENT | ABSENT | UNKNOWN | design |
| evolution_observation | PRESENT | PRESENT | PARTIAL (emits; no consume) | PRESENT (own bus/API) | design |
| runtime_observation | PRESENT | PRESENT | PRESENT | PRESENT (own) | design |
| event_ingestion | PRESENT | NOT_APPLICABLE | PRESENT (producer) | ABSENT (no shared ingest) | design |
| event_normalization | PRESENT | NOT_APPLICABLE | PRESENT (redact/validate) | UNKNOWN | design |
| event_identity | PRESENT | NOT_APPLICABLE | PRESENT (mirrored) | PRESENT (own chains) | design |
| event_persistence | PRESENT (SQLite) | NOT_APPLICABLE | ABSENT (failure log only) | PRESENT (own ledgers) | design |
| projection | PRESENT (pure) | NOT_APPLICABLE | NOT_APPLICABLE | UNKNOWN | design |
| read_model | PRESENT | PRESENT (renders) | NOT_APPLICABLE | PRESENT (own) | design |
| query | PRESENT (search/export) | PRESENT (console) | NOT_APPLICABLE | PRESENT (own APIs) | design |
| live_updates | PRESENT (SSE) | PRESENT (SSE+poll) | NOT_APPLICABLE | UNKNOWN | design |
| timeline | PRESENT | PRESENT | NOT_APPLICABLE | UNKNOWN | design |
| traceability | PRESENT (trace) | PRESENT (links) | ABSENT | PRESENT (knowledge/traceability) | design |
| explanation | PRESENT (explain) | PRESENT (renders) | NOT_APPLICABLE | UNKNOWN | design |
| evidence_reference | PRESENT | PRESENT | ABSENT | PRESENT (own ledgers) | design |
| provenance | PRESENT (audit) | PRESENT (renders raw) | PARTIAL (carries, unverified) | PRESENT (bundles) | design |
| governance_state | PRESENT (projection) | PRESENT (renders) | ABSENT | PRESENT (kernel) | design |
| authorization_state | PRESENT (projection) | PRESENT (renders) | ABSENT | PRESENT (kernel) | design |
| command_intake | PRESENT (proxy) | PRESENT (panel+proxy) | ABSENT (refuses) | PRESENT (own guards) | design |
| health | PRESENT | PRESENT | ABSENT | PRESENT (own endpoints) | design |
| metrics | PARTIAL (latest_metric only) | PRESENT (renders) | ABSENT (counters local) | PRESENT (own) | design |
| logging | ABSENT (no log ingest) | NOT_APPLICABLE | PRESENT (handler) | PRESENT (getLogger) | design |
| failure_reporting | PARTIAL (explicit HTTP; 500 path) | UNKNOWN (not surveyed) | PRESENT (taxonomy+counters) | UNKNOWN | design |
| replay | ABSENT | NOT_APPLICABLE | ABSENT | ABSENT (no replay observed) | design |
| backpressure | PARTIAL (drop-oldest) | ABSENT (no handling) | PARTIAL (drop+count) | UNKNOWN | design |
| redaction | PRESENT (params) | ABSENT (renders raw) | PRESENT (payload) | UNKNOWN | design |
| secret_safety | PARTIAL (scan: workspaces only) | PARTIAL (warning, no enforce) | PARTIAL (patterns differ) | UNKNOWN | design |
| auditability | PRESENT (bundles+chains) | PRESENT (links) | PARTIAL (failure log) | PRESENT (ledgers) | design |
| UI_rendering | NOT_APPLICABLE | PRESENT | NOT_APPLICABLE | PARTIAL (learning dashboard) | design |

Tallies (BE/FE/AD/CORE only; EX excluded as design reference):
PRESENT=63 · PARTIAL=11 · ABSENT=23 · NOT_APPLICABLE=14 · UNKNOWN=9.
Every PARTIAL/UNKNOWN above carries its note in sections 4, 7–14.

## 6. Authority matrix

| STATE | CURRENT_SOURCE | SOURCE_TYPE | EVIDENCE | CONFIDENCE | CONFLICTS / QUESTIONS |
|---|---|---|---|---|---|
| requirements | ISR (D28-recorded; D30A accepts for definition) | record chain | vertical_slice/*d28*; folder/D29.md:444,452 (transcription/provenance ambiguity preserved) | MEDIUM | AQ-007 |
| ISR | D28-recorded hash (decision use, not execution) | record chain | same as above | MEDIUM | AQ-007 |
| capabilities | implementation code (per-package) | code | package sources; no central registry observed | LOW | AQ-006 |
| evolution | evolution/ engine + promotion audit | code+records | evolution/models.py:312, promotion_audit.py:47 | MEDIUM | wiring to observatory absent |
| authorization | OBS-PY-BE headers/token (display boundary); constitutional kernel (real authority) | config+code | deps.py:23-57; constitutional_architecture/governance | MEDIUM / MEDIUM | two layers unconverged; AQ-005 |
| governance | CORE-CONST kernel; OBS-PY-BE GovernanceBoundary (display only) | code | governance/schemas.py:286; observatory/backend/governance.py:30 | MEDIUM | same as above |
| runtime_state | owning services (each its own) | code | health/live endpoints per package | LOW (aggregate) | no central source; AQ-006 |
| evidence | per-system ledgers (SQLite events; JSONL chains; bundles) | mixed | store.py; ledger.py; integrity.py | MEDIUM | formats unconverged |
| provenance | carried dicts + recomputed chains (unverified) | code | projections_provenance.py:270-280 | LOW | section 14 breaks |
| health | per-service endpoints; observatory derives display | code | */health/live; derive_runtime_health | MEDIUM | derived ≠ measured |
| configuration | env vars consumed at runtime | config | config.py:32-33; adapter config.py | HIGH | CONFIGURATION_INFLUENCE=PRESENT; CONSTITUTIONAL_AUTHORITY=UNKNOWN |
| commands | UI → proxy → GovernanceBoundary → audit event (executes nothing) | code | routes.py:305; gateway.py:392-418 | HIGH (path) | bypass risks §12 |

Configuration-influence findings: OBSERVATORY_API_TOKEN present ⇒ enforcement
on; absent ⇒ reads/writes degrade to header trust (section 12). `Application.
get_env`-class questions do not arise (Python: `os.getenv` at config.py:32-33,
adapter config) — recorded as influence, never authority.

## 7. Event-model reconciliation

PRESENT: canonical envelope (Event/EventInput, domain.py:72-106) with
source/category/type/subject, correlation_id + causation_id fields,
epistemic_status (OBSERVED default), severity (INFO default), authorization,
evidence_refs, provenance dict; identity `evt-{category}-{sha256[:24]}` over
six fields; content hash over canonical JSON; UTC normalization with naive→UTC
coercion and ValueError on invalid (domain.py:54-69); per-category constructors
(runtime/evolution/knowledge/evidence/governance, the last two with required
claim/result and rejection-reason rules).
PROPAGATION: correlation/causation fields exist but end-to-end propagation is
NOT_OBSERVED (no evidence of chains carried across systems) — UNKNOWN.
DELIVERY: synchronous SQLite append then in-memory fan-out; no broker, no queue
(except adapter's bounded local queue, 10000), no ordering guarantee beyond
rowid/timestamp, no dedupe beyond id+hash, no replay endpoint (ABSENT).
DUPLICATES: same id + same hash ⇒ dedupe (PRESENT); same id + different hash ⇒
409 conflict (PRESENT). Cross-system schema compatibility: backend vs adapter
mirror (DUP-001) — compatible today by inspection, no contract test binds them
(see GAP-005). No canonical event model spans core packages (each owns audit
event types; buses are in-memory and package-local).

## 8. Read-model reconciliation

MECHANISM: pure projection functions over SQLite events, recomputed per request;
no materialized views, no cache, no in-memory state (stateless gateway).
CONSISTENCY: read-your-write within one process (WAL); cross-process: UNKNOWN
(single file, multi-writer contention unassessed — AQ-001).
REBUILDABILITY: full rebuild from the events table is a property of purity
(PRESENT as property); no rebuild endpoint or procedure observed (NOT_OBSERVED).
STALENESS: SSE drops (drop-oldest) + 5s poll cadence bound staleness loosely;
no staleness signaling observed (PARTIAL). Governance/audit overviews scan up
to 20000 events per request (gateway.py) — cost unassessed (NOT_APPLICABLE to
correctness; noted for D31).

## 9. Live-update reconciliation

| MECHANISM | SOURCE | EVIDENCE |
|---|---|---|
| SSE | GET /observatory/stream → AsyncEventBus.subscribe | routes.py:315-331; bus.py:14-37 |
| polling (5s) | 15 frontend pages via setInterval | app/*/page.tsx (26/28/34/36/50/65/77); lib/api.ts |
| one-shot | console (on filter change), workspaces, login | console/page.tsx:91-115; workspaces/page.tsx |
| websocket | none | ABSENT (static) |
| broker queue | none | ABSENT (static) |

TOPIC/CHANNEL: single undifferentiated fan-out (no topics). DELIVERY: at-most
(verified paths) with silent per-subscriber drops. BACKPRESSURE: drop-oldest +
adapter counters (PARTIAL — no end-to-end signal). DISCONNECT/RECONNECT:
server-side NOT_OBSERVED (browser EventSource auto-reconnect is client
behavior, not server evidence) — UNKNOWN. DUPLICATES on stream: UNKNOWN.
AUTHORIZATION on stream: none (get_gateway only — section 12 finding).

## 10. Failure-semantics audit

| Surface | unavailable | timeout | invalid_response/input | process_crashed | silent_default |
|---|---|---|---|---|---|
| HTTP reads | 404 NotFoundError paths | NOT_OBSERVED | 400 validation | NOT_OBSERVED (static) | timeline/summary fallbacks `f"{type}: {subject}"` |
| HTTP ingest | 400/413 explicit | NOT_OBSERVED | 400 invalid_event w/ index+reason | NOT_OBSERVED | empty batch ⇒ accepted/0 (no error) |
| store | StoreIntegrityError→409 | NOT_OBSERVED | bad-iso search bound ⇒ 500 path (GAP-003) | NOT_OBSERVED | empty search ⇒ []; `max(x,0)` clamps |
| bus | n/a (in-process) | n/a | n/a | n/a | drop-oldest, contained |
| adapter | Retryable vs Permanent taxonomy | Retryable | ValueError→logged | loop-closed ⇒ silent return | queue-full ⇒ dropped+counted |
| projections | None on empty (→404 upstream) | n/a | n/a | `assert latest is not None` (500 path, UNKNOWN mapping) | not_measured/unknown/missing preserved; genome `observed` default (finding §11) |
| config | n/a | n/a | invalid MAX_BATCH ⇒ 500 | n/a | anonymous/observer actor defaults |
| frontend | NOT surveyed in depth | NOT surveyed | NOT surveyed | n/a | dashboard falls back to SSE items; empty-name guard only |

Fallback scalars (0/{}/[]/false) appear as initializers and benign defaults
(counts, payload `{}`, tag lists); none observed masquerading as measured
success. Timestamp None→now is the one fabrication-adjacent default (§11).

## 11. Epistemic-integrity audit

PRESERVED (good): empty events ⇒ `unknown` (projections.py:94-95,166-167);
unmeasured ⇒ `not_measured` (88-89); missing result ⇒ False, never success
(64-65); no decision ⇒ `unknown` (202-203); unknown vocab ⇒ `recorded`
(207-208); fitness missing ⇒ `missing`/`contradicted` (228-234); knowledge
status echoes source epistemic value; no-decision ⇒ `unknown`
(experiments 108, fitness 114); explicit contradiction registers.
COLLAPSED (findings, not repairs):
- F-001: missing timestamp ⇒ now (domain.py:55-56; adapter events.py:36-37)
  while epistemic_status defaults OBSERVED — an inferred value inside an
  OBSERVED envelope. Severity: LOW (documented constructor semantic).
- F-002: missing actor ⇒ `anonymous`/`observer` (deps.py:29-31) — fail-open
  identity on reads; writes still token-gated when configured.
- F-003: genome/gene/chromosome status defaults `observed` (projections_
  genomes.py:140,249,279) where sibling projections default `unknown` —
  inconsistent collapse surface. Severity: LOW (display), flagged for D31.
- F-004: lifecycle default `active`, sensitivity default `general`
  (workspace_governance.py:184-185; store defaults 123-126) — benign-default
  posture in a deny-default engine; noted, not upgraded.
No `unknown → healthy/success/certified` conversions observed. No
`unverified → certified` observed. `not_applicable` used correctly
(evolution cycle absent ⇒ `not_applicable`, gateway.py:452-457).

## 12. Governance-boundary audit

Command path (static): CommandPanel → POST /api/observatory/command →
session + clearance-gated action set + rate limit → backend POST
/observatory/commands → require_operator → safe-mode pre-check →
GovernanceBoundary.authorize → audit event (command_requested/rejected);
executes nothing. Workspace path: ServerWorkspacePanel → /api/workspaces/*
→ trusted-proxy identity + token → governed service → policy engine →
snapshot/audit-chain writes.
ENFORCEMENT_POINTS: Next proxy (session/clearance/rate), backend deps
(token/role/clearance), GovernanceBoundary (authority rules), WorkspaceGovernor
(roles/lifecycle/sensitivity/approval/immutable), secret scan (create/update).
BYPASS_RISKS (findings):
- B-001: all read endpoints + SSE + export + audit-bundle carry no backend
  auth dependency; when OBSERVATORY_API_TOKEN is unset, reads are header-trust
  only, and the frontend calls them browser-direct. Severity: MEDIUM (config-
  dependent; intended for local use, but the boundary is configuration, not code).
- B-002: workspace trusted-proxy identity (X-Operator-* headers) is spoofable
  by anyone reaching the backend directly; mitigation exists only if the
  backend is not directly exposed (undeclared in repo — AQ-010).
- B-003: UI clearance filtering is convenience-only (server re-checks — GOOD);
  recorded to prevent future "UI hides it so it's safe" reasoning.
Backend cannot be bypassed BY the UI (server re-checks); the backend CAN be
bypassed AROUND the UI (direct HTTP). No runtime verification performed.

## 13. Security reconciliation (no certification; scope-preserved)

| Area | State | Evidence |
|---|---|---|
| authentication (backend) | OBSERVED (token when configured; session in Next) | deps.py:40,52; lib/auth.ts:33-36 |
| authorization (backend) | OBSERVED (roles/clearance/policy) | deps.py:35-57; governance.py; workspace_governance.py:173-209 |
| command authorization | OBSERVED (static path) | gateway.py:392-418 |
| secret handling (params) | OBSERVED (redaction + scan) | gateway.py:475-485; workspace_governance.py:100-105 |
| secret handling (stored payloads) | NOT_OBSERVED (verbatim JSON) | store.py:97-100; GAP-006 |
| PII exposure | UNKNOWN (no PII survey performed) | — |
| API access (reads) | OBSERVED as unauthenticated-capable | routes.py (no Depends on reads); B-001 |
| stream access | OBSERVED as unauthenticated | routes.py:315; section 9 |
| logging of sensitive values | UNKNOWN (adapter failure log redacts when enabled; backend audit of rejections redacts) | runtime_adapter.py:276-285; gateway.py:427 |
| redaction (UI) | NOT_OBSERVED | KeyValue/EventTimeline render raw |
| audit trails | OBSERVED | workspace_audit_chain; command audit events; bundles |
| certification | NONE (D30 does not certify) | — |

`.env` contents never read. `autonomous-api/.env` exists (presence only).
Frontend `.env.example` shows empty-default secrets (env-only posture).

## 14. Provenance reconciliation

Chain (static): constructor id+hash ⇒ SQLite row (verbatim payload) ⇒ pure
projection ⇒ API JSON ⇒ UI raw render; export CSV/JSON; audit bundles
(`observatory-audit-bundle-v1`, `observatory-workspace-export-v1`).
BREAKS / WEAKNESSES:
- P-001: provenance dicts are carried, never verified against sources.
- P-002: provenance hash-chain is recomputed at read (evidence of ordering,
  not a stored ledger) — honest but weaker than the JSONL ledgers.
- P-003: adapter/backend vocab mirror (DUP-001) can drift silently (no binding
  test — GAP-005).
- P-004: saved browser traces are correctly disclaimed in-UI (console
  page.tsx:307-311) — preserved, commended, must survive redesign.
- P-005: D30A (VS-D29) preserves an ISR transcription/provenance ambiguity in
  its contradiction register (folder/D29.md:444,452) — inherited, not resolved.
- P-006: stored payloads verbatim ⇒ redaction at command time does not clean
  already-ingested secrets (GAP-006).

## 15. Duplication register

```text
DUP-001 | event vocabulary | domain.py vs adapters/tiannara/events.py |
  EVIDENCE: parallel Event/category/severity/epistemic definitions; explicit
  non-import (events.py:1-6) | RANK: code(2) | OVERLAP: near-total |
  DIVERGENCE_RISK: HIGH (timestamp-invalid: backend ValueError vs adapter raise;
  defaults differ) | NOTE: unification is D31+ scope; today: record only
DUP-002 | secret markers | gateway.py:53-54 (8) vs redaction.py:11-21 (9,
  superset) | RANK: code(2) | OVERLAP: substantial | DIVERGENCE: MEDIUM |
  NOTE: same as above
DUP-003 | secret detection | marker-substring redaction vs 7 workspace regex
  patterns (workspace_governance.py:54-68) | RANK: code(2) | OVERLAP: intent |
  DIVERGENCE: MEDIUM (different mechanisms, different recall) | NOTE: same
DUP-004 | audit/ledger primitives | event content-hash vs workspace hash-chains
  vs certification JSONL ledgers vs tiannara EvidenceChain | RANK: code(2)+
  artifacts(3) | OVERLAP: responsibility (tamper-evidence) | DIVERGENCE: HIGH
  (four formats, no shared verifier) | NOTE: convergence is D31+ scope
DUP-005 | observation/evidence/lineage dirs in autonomous-api/app vs
  observatory/ | EVIDENCE: directory names only | RANK: name(7) — INSUFFICIENT
  for candidacy | CONCLUSION: FURTHER_INVESTIGATION_REQUIRED (INV-001), NOT a
  duplication finding
DUP-006 | governance dashboards (constitutional dashboard vs observatory
  governance view) | EVIDENCE: coexisting surfaces, different layers |
  CONCLUSION: INVESTIGATE (INV-002); layering suggests complement, not overlap
DUP-007 | Elixir generated/observatory vs Python observatory/backend |
  CONCLUSION: NOT duplication — inert DESIGN_REFERENCE vs live implementation
  (section 4.8). Recorded to prevent future confusion.
```

No deletion, deprecation, or consolidation recorded. None authorized.

## 16. Gap register

```text
GAP-001 | replay capability | CONTRACT: EVENT_MODEL(design)/read-model needs |
  STATE: ABSENT (no replay endpoint; store append-only queryable) | SEVERITY: MEDIUM
GAP-002 | cursor/offset pagination | STATE: ABSENT (limit-only everywhere;
  overviews scan to 20000) | SEVERITY: LOW (correctness) / UNKNOWN (scale)
GAP-003 | search bound error mapping | bad-iso since/until propagates as 500 |
  STATE: PARTIAL failure semantics | SEVERITY: LOW
GAP-004 | workspaces audit UI | audit() client exists, no call-site in app/ |
  STATE: PARTIAL | SEVERITY: LOW
GAP-005 | backend↔adapter contract binding | no test/code binds the mirrored
  vocabularies | STATE: ABSENT | SEVERITY: MEDIUM (drift breaks DUP-001 silently)
GAP-006 | stored-payload secrecy | verbatim JSON persistence; redaction is
  ingest-time only; UI renders raw | STATE: PARTIAL | SEVERITY: MEDIUM
GAP-007 | documented serve/deploy path | no repo launcher/config for the
  observatory backend (operator-run uvicorn assumed; 127.0.0.1:8000 defaults) |
  STATE: ABSENT | SEVERITY: LOW (inventory) / UNKNOWN (operations)
```

## 17. Architectural questions (all OPEN; evidenced only; no Elixir-specific items)

```text
AQ-001 read-model persistence: single SQLite file shared by 3 stores — suitability,
  contention, backup, retention? (evidenced: main.py:27,31,33; WAL mode)
AQ-002 event transport: in-process bus + plain-HTTP adapter — cross-process and
  scale story? (evidenced: bus.py; client.py)
AQ-003 live-update adequacy: SSE + 5s poll — sufficiency, staleness signaling,
  stream auth? (evidenced: routes.py:315; 15 polling pages; B-001)
AQ-004 UI command boundary: direct-backend reads vs proxied writes — intended
  exposure model? (evidenced: lib/api.ts:37-41; proxy routes)
AQ-005 authorization authority: display-boundary token/roles vs constitutional
  kernel — relationship? (evidenced: deps.py; governance/schemas.py:286)
AQ-006 ownership boundaries: who owns event vocab, redaction sets, DB file,
  per-package observability feeds? (evidenced: DUP-001..004; zero wiring)
AQ-007 ISR transcription ambiguity inherited from D30A (folder/D29.md:444,452)
AQ-008 redaction boundary: verbatim storage + raw UI render vs ingest-time
  redaction — intended secrecy model? (evidenced: store.py:97-100; GAP-006)
AQ-009 schema compatibility/versioning: no envelope version field observed
  (NOT_OBSERVED — confirm, don't assume); adapter/backend drift binding?
  (GAP-005)
AQ-010 deployment exposure: is the backend directly reachable, or only via the
  Next proxy? Decides B-002 severity. (evidenced: trusted-proxy identity)
```

## 18. Reconciliation options (options only; none selected)

```text
OPT-001 | TARGET: DUP-001 vocab mirror | RETAIN (cost: drift risk; evidence:
  works today, zero coupling is also isolation) | ADAPT (share one package;
  cost: dependency direction decision; risk: import weight) | INVESTIGATE
  (contract test first — recommended evidence step, not selected)
OPT-002 | TARGET: DUP-004 ledger plurality | RETAIN (each ledger fits its
  system) | INVESTIGATE (shared verifier properties) | SEPARATE (declare
  per-system ledgers permanently distinct)
OPT-003 | TARGET: B-001/B-002 exposure | WRAP (document + enforce proxy-only
  exposure) | INVESTIGATE (threat model for local vs shared deployment)
OPT-004 | TARGET: GAP-001 replay | INVESTIGATE (is replay required for the
  Observatory's observation role?) | PROJECT (derive from events table later)
OPT-005 | TARGET: CORE-EVO/CORE-LEARN feeds | ADAPT (adapter-pattern bridge
  per source) | RETAIN (leave unwired) | INVESTIGATE (which signals matter)
OPT-006 | TARGET: OBS-EX | SEPARATE (keep as design history, explicitly
  non-authoritative) — recorded so a future cleanup has evidence, not approval
OPT-007 | TARGET: GAP-007 serve path | INVESTIGATE (how is it run today?) |
  (no packaging option recorded — insufficent evidence of operations context)
```

## 19. Evidence index (material claims ledger)

| ID | SUBJECT | CLAIM | EVIDENCE | TYPE/RANK | STATE | CONF |
|---|---|---|---|---|---|---|
| E-001 | repo baseline | HEAD ba952d4, main, 1-line pre-existing diff | git rev-parse/status/diff/log | config(3) | OBSERVED_FACT | HIGH |
| E-002 | D30 read-only | 0 tracked mods; 0 runs/installs/services | §1 assurance block; no exec tool use | runtime(1)-by-absence | OBSERVED_FACT | HIGH |
| E-003 | OBS-PY-BE exists | 23-file FastAPI+SQLite observatory | backend tree + main.py:25 | code(2) | OBSERVED_FACT | HIGH |
| E-004 | OBS-PY-FE exists | Next.js 14.2.3, 17 routes, 5 proxy routes | package.json; app tree | code(2)+config(3) | OBSERVED_FACT | HIGH |
| E-005 | OBS-ADAPTER exists | observe-only bridge, never commands | runtime_adapter.py:1-9,27-40 | code(2) | OBSERVED_FACT | HIGH |
| E-006 | runtime neutrality | no Phoenix/PubSub/OTP/ETS in first-party code | repo-wide search (excl. vendor/design) | code(2)-by-absence | OBSERVED_FACT | HIGH |
| E-007 | no broker | no kafka/redis/rabbit/WS in first-party py | same search | code(2)-by-absence | OBSERVED_FACT | HIGH |
| E-008 | absent surfaces | no Sentinel/Omega/ASC/Crucible dirs | directory search | config(3)-by-absence | OBSERVED_FACT | HIGH |
| E-009 | zero coupling | no imports either way (excl. tests) | 63-match grep, all tests | code(2) | OBSERVED_FACT | HIGH |
| E-010 | OBS-EX inert | parse-checked design output, uncompiled | generated/observatory/README.md:8-15 | doc(5) self-declared | OBSERVED_FACT | HIGH |
| E-011 | docs are design-ref | all 10 PROPOSED; 2 unverified claims | §§4.9 citations | doc(5) | DERIVED_CLASSIFICATION | HIGH |
| E-012 | test evidence | ~291 static tests; 290 pre-D30 passed | static counts; session history | test(1)-historical | OBSERVED_FACT | MEDIUM |
| E-013 | SSE+poll live | 1 SSE endpoint; 15 pages poll 5s | routes.py:315; page sources | code(2) | OBSERVED_FACT | HIGH |
| E-014 | read auth posture | reads header-trust; token-gated only if set | routes.py; deps.py | code(2) | OBSERVED_FACT | HIGH |
| E-015 | proxy secrecy | backend token server-only | proxy routes vs lib/ | code(2) | OBSERVED_FACT | HIGH |
| E-016 | epistemic preserved | unknown/not_measured/missing paths | projections citations §11 | code(2) | OBSERVED_FACT | HIGH |
| E-017 | F-001 timestamp | None→now inside OBSERVED envelope | domain.py:55-56,99 | code(2) | OBSERVED_FACT | HIGH |
| E-018 | F-003 genome default | `observed` vs siblings' `unknown` | projections_genomes.py:140 | code(2) | OBSERVED_FACT | HIGH |
| E-019 | DUP-001 mirror | parallel vocab, explicit non-import | events.py:1-6 | code(2) | DERIVED_CLASSIFICATION | HIGH |
| E-020 | DUP-004 ledgers | 4 tamper-evidence primitives, formats differ | store/governance_store/ledger/integrity | code(2) | DERIVED_CLASSIFICATION | HIGH |
| E-021 | INV-001 names-only | autonomous-api dirs insufficient for candidacy | name-only evidence rule §26 | name(7) | INSUFFICIENT_EVIDENCE | HIGH |
| E-022 | config≠authority | env gates enforcement; authority UNKNOWN | config.py:32-33; deps.py:40 | config(3)+code(2) | DERIVED_CLASSIFICATION | HIGH |
| E-023 | D30A alias | Observatory track cites D29 as D30A, no moves | authorization record (chat) | governance | OBSERVED_FACT | HIGH |
| E-024 | envelope unversioned | no schema_version field observed | domain.py:72-106 field survey | code(2)-by-absence | INSUFFICIENT_EVIDENCE | MEDIUM |
| E-025 | deploy path absent | no repo launcher for observatory backend | release/*.sh; scripts; configs | config(3)-by-absence | OBSERVED_FACT | MEDIUM |
| E-026 | CORE-EVO/LEARN feeds | buses+metrics exist, unwired to observatory | §4.4 citations | code(2) | OBSERVED_FACT | MEDIUM |
| E-027 | CONSTITUTIONAL authority | kernel signing + dashboard exist | evidence_signing.py; dashboard/app.py | code(2) | OBSERVED_FACT | MEDIUM |
| E-028 | P-005 inherited | ISR transcription ambiguity preserved in D30A | folder/D29.md:444,452 | record | OBSERVED_FACT | MEDIUM |
| E-029 | UI renders raw | no client redaction; secrets warning only | KeyValue/EventTimeline; Panel:50-53 | code(2) | OBSERVED_FACT | HIGH |
| E-030 | promo invariant held | no UNKNOWN→PRESENT/CANDIDATE→CANONICAL moves | this document (candidates only) | process | OBSERVED_FACT | HIGH |

Epistemic summary: OBSERVED_FACT=24 · DERIVED_CLASSIFICATION=4 ·
FUTURE_HYPOTHESIS=0 (options are labeled options, not hypotheses) ·
UNKNOWN embedded in matrices · INSUFFICIENT_EVIDENCE=2 · CONTRADICTION=0.

## 20. D30 boundary declaration

```text
UNDERSTAND-BEFORE-CONSOLIDATE — the terrain map above is the complete D30 output.
IMPLEMENTATION = NONE · REFACTOR = NONE · CONSOLIDATION = NONE · DELETION = NONE
DEPENDENCY_CHANGE = NONE · CONFIGURATION_CHANGE = NONE · RUNTIME_EXECUTION = NONE
DEPLOYMENT = NONE · PRODUCTION = NONE · COMMIT = NONE · PUSH = NONE
REPOSITORY_FILES_WRITTEN = docs/observatory/INVENTORY_RECONCILIATION.md (this
  file; the single artifact required by gate section 25)
PROMOTION_INVARIANT: MAINTAINED (candidates only; DUP-005/006 kept at
  INVESTIGATE; OBS-EX kept OUT_OF_SCOPE; options unselected)
NON-DECISIONS: canonical implementation · module deletion · consolidation ·
  persistence · transport · live-update mechanism · authorization source ·
  gate-state authority · implementation scope · refactor · dependencies ·
  deployment — all UNDECIDED, all D31-or-later scope.
NEXT_GATE: D31 — OBSERVATORY IMPLEMENTATION SCOPE DEFINITION = NOT_AUTHORIZED.
```

**Terrain answer:** a live Python observatory (backend + UI + adapter) already
observes, stores, projects, streams, and governs display-level commands over
SQLite + SSE + 5s polling, with strong epistemic hygiene and four honest
collapse findings; nine capable core packages stand unwired beside it; the
Elixir surface and all ten design docs are reference, not reality; authority
for authorization/governance/evidence lives in the constitutional kernel, not
in the observatory; reads and the stream are configuration-gated rather than
code-guaranteed; seven gaps and ten architectural questions bound what D31 may
define. **What to build now:** nothing — that is D31's question, unauthorized.
