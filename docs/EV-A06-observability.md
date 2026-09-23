# EV-A06 — Observability

**Audit:** evidence-first production readiness, sequence EV-A01 → EV-A02 → EV-A03 → EV-A04 → EV-A05 → **EV-A06 (this)** → EV-A07 → EV-A08 → EV-A09
**Canonical audited state:** `6e1aa1a` (PR #1 head; main `1f26e42`)
**Scope:** platform-API observability — logging (destinations, levels, redaction, correlation), metrics (instrumentation wiring vs definition), health/readiness, error reporting/traceability, tracing, observability tests, observability docs claims, plus a bounded inventory of the repo's `observatory/` subsystem. Read-only.
**Taxonomy:** `IMPLEMENTED_REAL / IMPLEMENTED_BOUNDED / IMPLEMENTED_SIMULATED / PARTIAL / UNIMPLEMENTED / UNKNOWN` · Confidence `CONFIRMED / INFERRED / UNVERIFIED`.

---

## STATUS: **FAIL**

The platform has three working observability layers — a loguru file+stderr log with rotation, a real `/health` with DB/memory/disk probes, and instrumentator HTTP metrics — but they do not form a usable production loop: **client-facing `traceId` values never appear in any log** (error path uses an unconfigured stdlib logger), **all 12 domain custom metrics are defined but never wired** (zeros forever or absent from the scrape), **failed authentication is never logged at all**, the repo's own tested secret-redaction/logging bridge has **zero production importers**, and the named observability subsystem (`observatory/`) is a real but fully detached component. Test coverage of observability is health-only smoke; `/metrics` has no test at all.

Register: **EV-A06-001 … EV-A06-012**.

---

## 1. Surface inventory

| Layer | Implementation | Verdict |
|---|---|---|
| Business log | `app/core/logger.py` (loguru): stderr (colored) + `logs/app_{date}.log`, rotation 500 MB / retention 10 d / zip, level from `settings.LOG_LEVEL`; **83 call sites** across `app/` | `[IMPLEMENTED_REAL]` — file+console proven in probe |
| Error/event log | `logging.getLogger("observation.errors")` (`error_handler.py:25`), `logging.getLogger("observation.gateway")` (`dispatcher.py:21`) — **no `basicConfig`/`dictConfig` anywhere in `app/`** (only the *generated-app template* configures stdlib, `builder.py:347`) | `[PARTIAL]` — records emitted, transport broken (EV-A06-001) |
| Metrics | `app/core/metrics.py`: `Instrumentator` on `/metrics` + 12 custom series + 10 `track_*`/`update_*` helpers; `setup_metrics(app)` at `main.py:133` | HTTP layer REAL; domain layer `[IMPLEMENTED_SIMULATED]` (EV-A06-002) |
| Health | `GET /health` (`routes.py:26-48`): `SELECT 1` DB ping, psutil memory %, disk %, degraded logic; `HealthCheckResponse` model; 4 tests | `[IMPLEMENTED_REAL]` |
| Readiness | `POST /production/readiness` behind `PROTECTED_CONTROL_PREFIXES`; endpoint test exists | `[IMPLEMENTED_REAL]` |
| Error contract | `error_handler.py`: envelope for domain/validation/HTTP/unhandled; server-side `logger.exception` + client `traceId` uuid4 | contract REAL; correlation broken (EV-A06-001/007) |
| Tracing | None in platform (no OTel, no inbound `X-Request-ID`); OTel exists only in **generated** artifacts when `genome.tracing_enabled` (`builder.py:57-77`) | platform `[UNIMPLEMENTED]`; generated = EV-A02/03 surface |
| Redaction | `observatory/adapters/tiannara/redaction.py` (tested) — **not imported by any production module** | `[UNIMPLEMENTED]` (EV-A06-004) |
| Observatory subsystem | `observatory/` backend (gateway/store/bus/projections, own FastAPI) + tiannara adapters; `tests/observatory/*` in root suite (all green in the 4252) | component REAL, detached from platform `[IMPLEMENTED_BOUNDED]` (EV-A06-005) |
| Alerting/Sentry/ELK | none (docs checklist items honestly unchecked) | `[UNIMPLEMENTED]` (optional tier) |

---

## 2. Logging — two stacks, one broken

### EV-A06-001 — Client `traceId` never reaches any log; all error-handler and dispatcher records miss the dated log file
`[PARTIAL]` · Confidence **CONFIRMED** (live probe + static)

The error path is designed as "full detail server-side, safe message + `traceId` client-side" (`error_handler.py:91,164-165`) — but the server side uses **stdlib logging with no handler/formatter configured anywhere in the platform**:

- `app/**`: zero `basicConfig` / `dictConfig` / `fileConfig`; loguru's `logger.remove()` does not touch stdlib; no intercept bridge between the stacks.
- Result (probe, EV-A06): triggered the rate-limit unhandled-500 path; response envelope carried `traceId: d8556a60-9395-427f-ad0f-2e1a64aad32d` —
  - **stderr**: bare `unhandled_error` line (no timestamp, no level, no logger name — Python `lastResort` handler) + traceback; string `trace_id` **absent** (the `extra={}` payload is never rendered by the default formatter).
  - **dated file** `logs/app_2026-09-23.log`: `unhandled_error=False`, `trace_id=False` — the record **does not exist** there. Same for `subscriber_delivery_failed` (`dispatcher.py:75-79`, the isolation boundary for WS-bridge fan-out failures).
  - The file *did* contain the parallel loguru line: `WARNING | app.middleware.rate_limit:dispatch:121 - Rate limit exceeded for 127.0.0.1 on /evolve/start` ✓.
- Correlation consequence: an operator holding a customer's `traceId` can find **no log line carrying it**; the only join key left is wall-clock adjacency to an unformatted stderr traceback. The contract comment "traceId is correlation-only" (`errors.py:10`) is satisfied by the client envelope and violated by the server logs.

Affected record families: **every** `PLATFORM_INTERNAL` 500 (incl. the EV-A04-003 rate-limit 500s), every `ObservationDomainError`, and every event-dispatcher subscriber failure.

### EV-A06-006 — `LOG_FILE` is dead; log path is CWD-relative hardcoded
`[UNIMPLEMENTED as a setting]` · Confidence **CONFIRMED**

`config.py:33 LOG_FILE` has exactly one occurrence repo-app-side: its own definition. `logger.py:26` hardcodes `"logs/app_{time:YYYY-MM-DD}.log"`. Setting the documented `LOG_FILE` (DEPLOYMENT_GUIDE `:77`) does nothing — extends **EV-A04-007** (dead settings) with a new member. Rotation/retention/level themselves are real (500 MB, 10 days, zip, `LOG_LEVEL` read at `logger.py:19,30` ✓). Path is CWD-relative: correct in container (`WORKDIR /app` + compose `./logs` mount) and under the guide's systemd `WorkingDirectory`, scattered if launched from elsewhere — bounded.

### EV-A06-003 — Failed authentication is never logged
`[PARTIAL]` · Confidence **CONFIRMED** (static: zero logger references in `security.py`)

- `middleware/security.py` contains **no logger at all** (grep `logger` → no hits): anonymous/expired/wrong-key 401s leave no application-log trace — no failed-auth audit trail, no identity of the caller beyond uvicorn's stderr access line (status only, not file-persisted, proxy-topology IP per EV-A04-004).
- By contrast `rate_limit.py:121` **does** log (loguru, client IP + path) ✓ — asymmetry is within one middleware package.
- The `StarletteHTTPException` envelope handler (`error_handler.py:146-159`) likewise never logs (404s etc. rely on access logs only — acceptable; the auth gap is the material one).

### EV-A06-004 — No log redaction on the platform; the repo's tested redactor is never imported
`[UNIMPLEMENTED]` · Confidence **CONFIRMED**

- Platform: grep `redact|sanitiz|scrub` over `app/**` → one hit, a docstring (`security.py:75` "Validate and sanitize CORS origins") — **zero log redaction**.
- Repo ships `observatory/adapters/tiannara/redaction.py` — a complete `redact()` (secret-shaped keys → `[REDACTED]`, 4000-char truncation, depth cap) — and `ObservatoryRuntimeLogHandler` (stdlib → observatory bridge, fail-safe `emit`) — both covered by `tests/observatory/test_adapter*`.
- Importers of `observatory` / `adapters.tiannara`: **`tests/observatory/*` only** (grep across `learning/`, `tiannara/`, `autonomous-api/app/` → zero). Nothing in the runtime ever attaches the handler or redacts a payload.

---

## 3. Metrics — HTTP real, domain simulated

### EV-A06-002 — All 12 custom Prometheus metrics have zero callers; half never appear in a scrape, half are stuck at `0.0`
`[IMPLEMENTED_SIMULATED]` · Confidence **CONFIRMED** (static zero-caller grep + live `/metrics` dump)

Static: grep of the ten helpers (`track_evolution_run`, `track_generation_fitness`, `track_genome_evaluation`, `track_genome_build`, `track_api_request`, `update_active_connections`, `update_memory_stats`, `update_adaptive_bias`, `update_group_metrics`, `track_cross_pollination`) over `app/**/*.py` excluding `metrics.py` → **zero hits**.

Live (`GET /metrics`, 200, 8711 bytes, probe after 25 requests):

| Series | Observed | Why |
|---|---|---|
| `http_requests_total{handler,method,status}` | **live** (`/health` 2xx=1, `/evolve/start` 4xx=20, 5xx present) | instrumentator auto-wiring ✓ |
| `http_request_duration_seconds*` | **live** histograms | instrumentator ✓ |
| `python_info`, process metrics | present | client defaults ✓ |
| `genome_evaluations_total 0.0` | exposed, **always 0** | unlabeled → registers at import, never `.inc()` |
| `active_websocket_connections 0.0` | exposed, **always 0** — while `ws.py` logs real connect counts to loguru | `update_active_connections` never called |
| `cross_pollination_events_total 0.0` | exposed, **always 0** | never called |
| `evolution_runs_total` | **no sample lines** (labeled; children never instantiated) | never called |
| `evolution_duration_seconds`, `generation_best_fitness`, `population_size`, `genome_build_*`, `api_request_duration_seconds`, `memory_entries_total`, `adaptive_mutation_bias`, `group_*` | **no sample lines / always 0** as applicable | never called |

Consequence: the custom-metric dashboard an operator builds from `metrics.py`'s docstring ("Tracks … evolution runs, and system health") renders **absent or zero series forever**, including the WebSocket gauge that contradicts the loguru connection lines. `prometheus.yml` scrapes the endpoint correctly (EV-A05) — the scrape target is real; the domain payload is simulated.

### EV-A06-008 — Observability test coverage: health real, logger smoke-only, metrics untested
`[PARTIAL]` · Confidence **CONFIRMED**

- `/health`: 4 tests (`test_production_features.py:59-71`) exercising status/components ✓.
- Logger: `TestLogger` only asserts importability and `hasattr` for `info/warning/error/debug` (`:221-230`) — no test writes-then-reads the file, no level propagation, no rotation.
- **`/metrics`: zero hits in platform tests** (grep `/metrics` over `autonomous-api/tests` → none); no test asserts any custom series value or increment — consistent with the unwired helpers (a wiring test would have failed).
- No test asserts `traceId` appears in logs (it would fail — EV-A06-001).
- Readiness endpoint has a real test (`test_production_readiness.py:56`) ✓.

---

## 4. Tracing & correlation

### EV-A06-007 — No request-scoped correlation; `traceId` only on some envelopes; platform has no tracing system
`[PARTIAL]` · Confidence **CONFIRMED**

- `traceId` set only in `_domain` (`error_handler.py:90,121`) and `_unhandled` (`:163,178`) — **absent** from validation (422) and mapped-HTTP envelopes (`_http` never assigns one).
- No middleware reads/propagates inbound `X-Request-ID`; no response header carries the id except inside the error body; uvicorn access lines have no request id.
- No OTel/`structlog`/correlation middleware in `app/` (grep). OTel exists solely in the **generated-app template** when `genome.tracing_enabled` (`builder.py:57-77`, evidence-checked at `capability_evidence.py:45-53`) — a generated-artifact capability (EV-A02/03 scope), not platform observability.
- Event envelopes **do** mandate `correlationId` (`events.py:61` "missing correlation is a bug, not a default") — real and tested at contract level; emitters pass `correlation_id=run_id` (`evolution.py:37`, `elite_evolution.py:35`) — real but coarse (one id per run, not per request).
- Net: three unjoined id spaces (error uuid, run_id, none-for-success) + broken log transport (EV-A06-001).

---

## 5. Docs claims vs runtime

### EV-A06-009 — Honest unchecked boxes, but two actionable claims are wrong or stale
`[PARTIAL]` · Confidence **CONFIRMED**

- `PRODUCTION_HARDENING.md`: §5 health-check description matches the shipped endpoint ✓; checklist `[ ]` logging aggregation and `[ ]` monitoring alerts are honestly unchecked ✓ (no false claim).
- Wrong: "Key Metrics to Track: **1. Rate limit hits — Monitor 429 responses**" (`:304`) — rate-limit responses are **500 `PLATFORM_INTERNAL`, not 429** (EV-A04-003, reconfirmed in this probe: burn → 401×20 → 500×5). The metric the guide tells you to alert on does not exist; the loguru `Rate limit exceeded` warning does.
- Stale: `DEPLOYMENT_GUIDE.md` §Monitoring instructs operators to *add* `Instrumentator` to `main.py` (`:271-287`) and *add* the loguru file handler (`:291-307`) — both shipped years-in-repo already (`metrics.py:108`, `logger.py:25-32`); Sentry/ELK remain checklist-aspirations with no code (acceptable as optional, but listed under "Production" without status).

---

## 6. Adjacent inventory — observatory subsystem

### EV-A06-010 — `observatory/` is a real, tested event backend; nothing in the running platform feeds it
`[IMPLEMENTED_BOUNDED]` · Confidence **CONFIRMED**

- Backend: `observatory/backend/main.py` (`create_app` → `SqliteEventStore` + `AsyncEventBus` + `ObservatoryGateway`, CORS optional, workspaces/governance stores) — a genuine ingest/projection service with its own contract ("does not execute evolution, deployment, or production mutation").
- Tests: `tests/observatory/*` (adapter, batch, runtime, api, backend contract — dozens of assertions) run inside the canonical root suite — all green in the 4252-gate runs.
- Adapters: `logging_handler` (stdlib → observatory, fail-safe) and `redaction` are library-grade **but imported by tests only** (EV-A06-004).
- Platform `app/`: zero `observatory` imports. Platform logs go to stderr/file; metrics to Prometheus; neither reaches observatory. The subsystem is deployable (own FastAPI) but **not wired into the platform observability story** — bounded, not simulated: its own scope is real, the integration is absent.
- (Frontend `observatory/frontend` + `docs/observatory/*` exist; not probed this phase.)

### EV-A06-011 — Production image ships 5+ unused packages as runtime dependencies
`[PARTIAL]` · Confidence **CONFIRMED**

`autonomous-api/pyproject.toml` main `dependencies` include `streamlit`, `locust`, `pytest`, `pytest-asyncio` (tooling in the runtime set) plus clients `ollama`, `openai`, `imagekitio` — grep over `app/**`: **zero imports of all five** (LLM calls go through `httpx` in `llm.py:6`). Dockerfile `pip install .` therefore installs them into the production image (bloat + supply-chain surface; `locust` is a load-attacker toolkit, `streamlit` pulls a heavy tree). Conversely `hypothesis` is absent from **both** `pyproject.toml` and `requirements.txt` — reconfirms **EV-A04-015** for the package-install path too (root suite aborts on a clean install either way). Positive note: `loguru`, `prometheus-fastapi-instrumentator`, `psutil`, `sse-starlette` **are** declared → no missing-dependency boot failure in the image.

---

## 7. Positives (what holds)

### EV-A06-012 — The non-simulated core
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

- `/health` is a genuine multi-probe check (DB `SELECT 1`, process memory %, disk %, degraded aggregation) with a response model and 4 tests; compose healthcheck consumes it (EV-A05).
- `/production/readiness` is authenticated (EV-A04) and endpoint-tested.
- Loguru stack: file rotation + retention + compression + level-from-settings, 83 call sites covering startup, CORS config, evolution starts, WS connect/disconnect/errors, health-check failures, rate-limit warnings (with client IP + path).
- Instrumentator HTTP request count/latency by handler/method/status — live in the probe, correctly scraped by shipped `prometheus.yml`.
- Error envelopes: stack traces and raw detail never cross the wire (probe body: clean `PLATFORM_INTERNAL` + recovery guidance + provenance hash) — the *pattern* is right; only the server-side transport of `traceId` is broken (EV-A06-001).
- Event contract hard-requires `correlationId` with an explicit "missing correlation is a bug" rule.
- `pyproject` declares the observability runtime deps → Docker image boots without hand-installing requirements.

---

## 8. Verification appendix (evidence log)

- Static reads: `logger.py`, `metrics.py` (full), `error_handler.py` (full), `routes.py:1-130`, `main.py:1-170`, `dispatcher.py:1-80`, `observatory/adapters/tiannara/{logging_handler,redaction}.py`, `observatory/backend/main.py:1-50`, `autonomous-api/pyproject.toml`, workspace `pyproject.toml`.
- Greps: `track_*`/`update_*` callers outside `metrics.py` → **0**; `basicConfig|dictConfig|getLogger` in `app/**` → only `error_handler.py:25`, `dispatcher.py:21` (template hit in `builder.py:347` is generated code); `LOG_FILE` readers → definition only; `observatory` imports in `learning|tiannara|autonomous-api/app` → **0** (hits only under `tests/observatory/`); `redact|sanitiz|scrub` in `app/**` → 1 docstring; `logger` in `middleware/security.py` → **0**; unused-dep imports (`ollama|openai|imagekitio|streamlit|locust`) → all NONE; platform tests `/metrics` → **0 hits**.
- Live probe (`Temp/opencode/ev06/ev06_probe.py`, port 19621, file-redirected uvicorn stdio — EV-A04 harness lesson applied):
  - burn: 20× `POST /evolve/start` → `401` ×20, then `500` ×5 (evolution bucket = 20) — reconfirms EV-A04-003/004.
  - 500 envelope: `traceId=d8556a60-9395-427f-ad0f-2e1a64aad32d`, contract `platform.observation.errors`, recovery `retry_with_backoff` — **id absent from stderr and from `logs/app_2026-09-23.log`**; stderr has bare `unhandled_error` + traceback (no timestamp/level); file has loguru rate-limit warnings + startup lines only.
  - `GET /metrics` 200, 8711 B: instrumentator series live (`http_requests_total{...2xx,4xx}`, duration histograms, `python_info`); custom: `genome_evaluations_total 0.0`, `active_websocket_connections 0.0`, `cross_pollination_events_total 0.0`; `evolution_runs_total` / `api_request_duration_seconds` / `generation_best_fitness` → **no sample lines**.
  - `LOG_FILES: ['app_2026-09-23.log']` — rotation path live in probe CWD ✓.
- Docs cross-reads: `PRODUCTION_HARDENING.md:117-136,265-304`, `DEPLOYMENT_GUIDE.md:240-309` (monitoring sections).
- Gates: root `python -m pytest` re-run after report write (session close-out); PR #1 head `6e1aa1a` unchanged at last poll (no collaborator push).
- Not probed: observatory backend boot + its frontend (component inventory only; its tests ran in the root suite), Prometheus/Grafana live scrape (Docker daemon down), log rotation under real 500 MB load (config read, not exercised).

---

## 9. Conclusion & next gate

**FAIL.** Production observability needs one loop: *signal → persistent record → queryable id → alert*. The platform delivers signals (health probes, HTTP metrics, rate-limit warnings) and persistence for the happy path (loguru file), but breaks the loop at the two points production depends on most: the **error path's `traceId` dies in an unconfigured logger** (EV-A06-001), and the **domain metrics an evolution platform exists to display are unwired decoys** (EV-A06-002). Add a silent-auth gap (003), a tested-but-uninstalled redactor (004), a detached observatory (010), stale docs pointing operators at a 429 that never fires (009), and health-only tests (008) — and no production observability claim survives.

Must-fix order: route `error_handler`/`dispatcher` through loguru (or configure stdlib) **and render `trace_id` into the record** (001); wire or delete the 12 custom metrics (002); log auth failures in `security.py` (003); attach redaction + make `LOG_FILE` live (004/006); decide observatory wiring or document it as standalone (010); add `/metrics` and trace-correlation tests (008); fix the 429 claim (009).

**NEXT GATE: EV-A07 — Schema / Observation Integrity.**

*(Sequence: EV-A07 → EV-A08 Change Safety → EV-A09 Governance. Bandit-fix verification track remains separate.)*
