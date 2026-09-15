# OBSERVATORY D44-PREP — Multi-Backend & Real Executor Validation (Pre-Flight)

- Status: **COMPLETE** (inspection-only gate; no repo mutation, no D44 experiment execution).
- Authorization: User approved D44-PREP per VS-D44 §39 ("Authorize D44-PREP first").
- Execution scope: read-only inspection of source, tests, toolchain; baseline reconciliation.
- The full D44 experiment is **NOT** started; it requires a separate go/no-go authorization (§39).
- Follow-on required artifacts (post-experiment): `OBSERVATORY_D44_MULTI_BACKEND_EXECUTOR.md` + `.json` (§35).

## 1. Baseline

- `main` @ `f73ef9e` (275 files, +77,841 — observatory D30–D43 chain), working tree clean, `origin/main` in sync.
- Backend alive on `:8000` (1220ms HAR), frontend alive on `:3000` (evt-cmm-f2ee2894e5aa01d94a900bb2 / evt-runtime). Observatory live path (API + SSE) is the `OBSERVATORY_LIVE` witness surface throughout D44.
- Evidence angle carried forward: every D44 predicate is measured against evidence, never inferred from source existence, a simulated harness, or a healthy dashboard.

## 2. PREP-01 — Host toolchain & infrastructure survey

| Tool            | Host result                                                      | D44 relevance                                  |
|-----------------|------------------------------------------------------------------|------------------------------------------------|
| Go              | **NOT installed** (`go: command not found`)                      | Blocks host-side `go build` on generated Go    |
| Rust            | 1.94.1 (`rustc` + `cargo`)                                       | Installed alternate runtime; no Tiannara backend exists for it |
| Elixir/OTP      | 1.18.4 / OTP 28 (`mix` present)                                  | Installed alternate runtime; only a design prototype (`generated/observatory/`), NOT a registered backend |
| Node           | v24.11.1, npm 11.12.1                                             | Installed alternate runtime; no registered backend |
| Python          | 3.14.0 (PATH `python`)                                            | Current backend runtime                        |
| Docker CLI      | v29.7.2 present; **daemon NOT running** (Docker Desktop stopped)  | `DockerExecutionEnvironment.available()` → `False`; containerized executor unusable until daemon starts |
| Git             | 2.53.0                                                            | Repository publishing path                      |
| Port window     | 8000 (Observatory API) / 3000 (frontend) occupied                 | D44 experiment must avoid these; lab ports to be selected dynamically |

Toolchain implication: the only fully in-repo, real-toolchain executable second backend is **Go via Docker** (declared image `golang:1.22-alpine`), which requires the Docker daemon to be up, or Go to be installed on the host. A host-Rust or host-Elixir path would require authoring a brand-new Tiannara compiler backend (much larger, out of D44 scope unless so decided).

## 3. PREP-02 — Executor classification (evidence-anchored)

| Executor | Conditions | Actual behavior (source-verified) | Classification |
|---|---|---|---|
| `LocalExecutionEnvironment()` | `test_command=None` | `local_environment.py:23-24` returns `TestRunResult(passed=True, exit_code=0, total_tests=1, failed_tests=0)` **without spawning any process**. Structural guaranteed-pass. Used by `bootstrap.py:63/67` (auto-without-docker and non-auto paths) and `cli/main.py:178`. | **SIMULATION / HARNESS** (not a real gate) |
| `LocalExecutionEnvironment(test_command=[...])` | explicit command | `local_environment.py:27-51` real subprocess in `bundle.path`; exit-code-only gate; `total_tests` hardcoded to 1; stdout/stderr captured but discarded; no service launch; no HTTP oracle | **PARTIAL_REAL_EXECUTOR** |
| `DockerExecutionEnvironment` | Docker daemon up | real `docker run` in declared `runtime_image`, timeout + log capture per `docker_environment.py`; still a build/test-command gate; no server launch + live workload | **PARTIAL_REAL_EXECUTOR** (real toolchain, not full runtime truth) |
| **Required for D44 P1/P2** | — | build with declared toolchain in declared image → **launch server process** → run **independent HTTP oracle** on the live process → capture real exit codes/logs | **REAL_EXECUTOR** (must be created as isolated experiment scaffolding, not added to bootstrap defaults) |

D43 correlation: D43 EXP-1's runtime-verification outcome came from the `test_command=None` simulated-pass path — i.e. PASS-with-simulated-verification, already correctly bounded in the D43 STOP. Real executor is exactly the D44 gap.

## 4. PREP-03 — Backend registry state (the decisive finding)

Two distinct registries exist:

1. `tiannara/application/compiler/registry.py` — `CompilerRegistry`, capability-indexed. Registered in `bootstrap.py:31-34`: `minimal-container`, `fastapi_hexagonal` only. **There is a third compiler that is dormant: `GoHexagonalBackend`** (`application/compiler/go_hexagonal_backend.py`, 525 lines, `backend_id="go_hexagonal"`) — a *complete* Phase 19 second backend emitting stdlib-only Go (`net/http`), with hexagonal layout, in-memory repo, HTTP handlers, tests, Dockerfile/compose/CI/README. It declares its own verification contract via `build_profile()` (`go build ./...`, `go test ./...`, image `golang:1.22-alpine`). **It is never imported or registered** — not reachable by any pipeline, never exercised.
2. `tiannara/application/compilation/backend_capability_registry.py` — `BackendRegistry` (Phase 22 realizer layer) with `fastapi` and `postgres` entries + `cross_backend_campaign.py`/`backend_conformance.py` machinery. Also not wired into the harness selection used by Observatory-facing runs.

D43's "language generality NOT demonstrated" finding therefore means *not demonstrated*, **not** *not implemented*. The honest D44 statement will be: a genuine second backend exists in source; whether Tiannara can select→build→launch→verify it is unproven and is exactly the D44 experiment.

Test status of the dormant backend: `tests/test_go_hexagonal_backend.py` and `tests/test_go_verifier.py` assert generated **source shape only** ("without running Go"); a real `go build` has never executed against generated Go anywhere in the suite.

## 5. PREP-04 — Backend selection policy

- Campaign selection source: `tiannara/application/campaign/harness.py:120-131` `_CATEGORY_BACKENDS` maps all 13 `ProjectCategory` → `"fastapi"`/`"postgres"`; consumed by `backend_for()` / `target_for()`. Fixed policy — the campaign harness picks the backend for a category, i.e. the selection is **HARNESS-DIRECTED POLICY**, not autonomous per-intent choice.
- `ExecutionPipeline` (`application/pipeline/execution_pipeline.py:37-42`) takes `target_backend` explicitly and raises `ValueError` for an unknown backend — selection can be injected per-run, but resolution requires the backend to be in the pipeline's `backends` dict.
- For D44, honest selection readings: (a) policy says every category is fastapi → go unselected, or (b) experiment passes `target_backend="go_hexagonal"` → **HUMAN-DIRECTED selection** (attributed per §9), pipeline compiled through the normal backend resolution. No source edit to `_CATEGORY_BACKENDS` needed if attribution is human-directed; editing it would make selection Tiannara-policy-driven but change harness policy (not required for a valid demonstration).

## 6. PREP-05 — Second-backend gap analysis for P1/BACKEND-01

- P1/BACKEND-01 (second backend exists → builds → launches → real workload) is demonstrable via the dormant `go_hexagonal` backend IF: (a) it is registered at runtime (decision D1) and (b) a real Go toolchain exists (Docker daemon up, decision D2).
- Technologies with no backend (Rust, Elixir, Node) would each require authoring a new compiler backend (+ its shape tests + a working generation path). Out of scope for a single D44 cell; noted as future gates if Rust-in-repo is desired (Rust is the only fully host-installed compile target today).
- Elixir presence (`generated/observatory/`) is a design prototype: inert (27 `.ex` files, no `mix.exs`), confirmed during D43 EXP-2. Not a backend.

## 7. PREP-06 — Independent functional oracle (per D44 §14)

Purpose: verify the generated service is functionally alive and correct from OUTSIDE Tiannara — a permanent antidote to the simulated-pass path.

| Step | Probe | Expected independent outcome |
|---|---|---|
| O1 | `GET /health` on the launched server | 200, body `{"status":"ok"}` |
| O2 | `GET /readiness` | 200, body `{"status":"ready"}` |
| O3 | `POST /{entities}` (JSON create) | 201, echoed entity (id assigned) |
| O4 | `GET /{entities}/list` | 200, array containing the created record |
| O5 | `GET /nonexistent-route` | 404 (documented negative control) |
| O6 | Repeated O3–O4 with distinct payload | stateful behavior consistent (CRUD round-trip) |

Oracle is authored by the experiment, runs against the live process, independent of Tiannara's own verifier. All O1–O6 responses/states recorded verbatim into the experiment evidence. Expected/observed compared explicitly (§14 P3).

## 8. PREP-07 — Controlled failure mechanism (per D44 §15)

- Requirement: deterministic, reversible, attributable; exactly one declared failure-mode category.
- **Mechanism (recommended):** establish green baseline (O1–O6 pass) → stop server → inject a single, diff-visible fault into the generated artifact (e.g., delete a build-critical file `internal/domain/models.go`, or corrupt `go.mod`) → attempt rebuild + relaunch via the REAL executor → observe service unavailable / build failure → oracle returns timeout/5xx → **Tiannara detects failure and must diagnose** → restore the artifact (reversible) → bounded diagnostic output recorded (failure cause, evidence, classification).
- Attribution: the injected change is the ONLY artifact diff (pre/post hash), so the fault is fully attributable.
- Exact category label for the failure will be pinned from the D44 §15 taxonomy at execution time (intent is a service-runtime observable failure, not a resource/permission accident).

## 9. PREP-08 — Predicate execution plan (sketch)

- One representative category + one intent via the degraded corpus (not identical to D43 EXP-1 path; e.g. `api` or `crud_saas` repr). NO 1,040-cell matrix.
- Execution: intent → Tiannara pipeline (go_hexagonal backend) → REAL build (Go toolchain in `golang:1.22-alpine`) → REAL launch → oracle O1–O6 → induced fault → REAL rebuild/relaunch → re-oracle → repair/diagnosis evidence → observability over Observatory API/SSE → provenance records (ledger/JSONL) → STOP report with exactly one decision from PASS / PASS WITH BOUNDED UNKNOWN / PARTIAL / HOLD / FAIL / STOP.
- `OBSERVATORY_LIVE` (dashboard/SSE shows the whole lifecycle) and `TIANNARA_EXECUTION_LIVE` (real Go process serving real HTTP) are kept as distinct predicates; green dashboard never substitutes for execution liveness.
- Autonomy ladder: this experiment targets at most **A2 FUNCTIONAL GENERATION / A3 VERIFIED GENERATION** realism (real-build-verified), with repair per the A5/A6 definitions if the induced-fault diagnostic completes bounded self-repair. No A7/A8 upgrading.

## 10. Open decisions requiring go/no-go authorization (§39)

- **D1 — Second-backend wiring:** Allow a minimal, reviewable registration of the existing `GoHexagonalBackend` into the pipeline's backend resolution (one-line addition to the `backends` dict in `bootstrap.py`), so the experiment goes through Tiannara's real resolution path? (Recommended: YES. It adds a capability; it changes no verdict or default behavior. Alternative: invoke the backend class directly — weaker attribution, risks a "harness bypass" reading.)
- **D2 — Real Go toolchain:** Start Docker Desktop so the declared `golang:1.22-alpine` image can run `go build`/`go test`/launch containerized (Recommended), OR install Go on the host — OR accept host-inaccessible and downgrade the cell to PARTIAL (fails EXEC predicates) — OR pivot to a host-Rust/Elixir/Node backend (requires authoring a new backend; largest lift).
- **D3 — Attribution of selection:** confirm experiment passes `target_backend="go_hexagonal"` explicitly with **HUMAN-DIRECTED** attribution (no `_CATEGORY_BACKENDS` edit) — the honest minimal-surprise default.

## 11. Non-goals of D44 (recorded)

No production deployment; no D45 or beyond; no credentials/tokens; no commit/push without explicit authorization; no weakening of any existing gate or suite; `certification/` verdict history untouched.

## Evidence anchors

- `bootstrap.py:31-34` backend dict (two registered)
- `application/compiler/go_hexagonal_backend.py` (dormant complete Go backend, `backend_id="go_hexagonal"`)
- `application/compiler/registry.py` `CompilerRegistry`
- `infrastructure/sandbox/local_environment.py:23-24` (simulated pass when no test_command)
- `infrastructure/sandbox/docker_environment.py:56` + `.available()` (daemon-gated real container executor)
- `application/campaign/harness.py:120-135` `_CATEGORY_BACKENDS` policy + `backend_for`/`target_for`
- `application/pipeline/execution_pipeline.py:37-42` `target_backend` resolution, `ValueError` for unknown
- `tests/test_go_hexagonal_backend.py`, `tests/test_go_verifier.py` (source-shape only; real `go build` never run)
- Host facts (survey above): Go absent, Docker daemon down, Rust 1.94.1 / Elixir 1.18.4 / Node 24.11.1 present