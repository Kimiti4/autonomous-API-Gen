# PROD-A01 — Production Boundary / Implementation Inventory Audit

- **State audited:** `6e1aa1a` (PR #1, `evolution/second-backend-lowering-hardening`), local tree clean.
- **Method:** READ-ONLY, NON-MUTATING, EVIDENCE-FIRST, FAIL-CLOSED. Every classification cites `file:line`.
- **Taxonomy:** `IMPLEMENTED_REAL` / `IMPLEMENTED_BOUNDED` / `IMPLEMENTED_SIMULATED` / `PARTIAL` / `UNIMPLEMENTED` / `UNKNOWN`.
- **Field set per subsystem:** component · source file · interface · actual behavior · evidence · production dependency · failure mode · security implications · remaining work.

---

## 0. Executive summary

The platform has two separate "production" stories that must never be conflated:

1. **The Evolution Engine platform** (`autonomous-api/`) — a real FastAPI service with a real, mostly-hardened control boundary, real Docker-based runtime verification of generated artifacts, real SQLite persistence, real Prometheus/Grafana observability, and a real publish-only CI/CD (image push to GHCR). This layer is substantially **real**, with bounded gaps.
2. **The Deployment Engine** (`constitutional_architecture/deployment/`) — a **standalone, unwired library** of deployment *models*. It is imported **only by its own unit tests** (`constitutional_architecture/tests/test_deployment_engine.py`, `test_deployment_constitutional_boundary.py`). No platform runtime imports it (the telemetry engine even asserts it away: `tests/test_operations/test_telemetry_engine.py:134`). Every actuation stage and target returns synthetic success. Nothing it reports reflects the world.

**Headline blocker (matched to user's PROD-002/-003/-004/-010/-011/-012/-014/-016 class):** deployment modules behave as models/simulators — confirmed at code level. The platform's *only* real deployment pathways are `docker-compose.yml` (local/preview) and the GHCR publish steps in `v1.1-release-gate.yml` (main-only). **There is no deployment to any live environment anywhere — zero CD** (no kubectl/helm/terraform/ssh/apply/argocd/gcloud/aws found in any workflow).

---

## 1. Platform runtime (`autonomous-api/app`)

### 1.1 HTTP API surface and control boundary
- **Component:** FastAPI composition root.
- **Source:** `app/main.py`, `app/api/routes.py`, `app/middleware/security.py`.
- **Interface:** `/health`, `/docs`, `/stream` (SSE), `/evolve/start|sync|runs|run/{id}`, `/evolve/elite/*`, `/production/readiness`, `/ws/evolution{/{run_id}}`, `/metrics`, `/observation/*` (via `api/observation_routes.py`).
- **Actual behavior:** `SecurityHeadersMiddleware` deny-by-defaults protect control prefixes `/evolve` + `/production/readiness` (`security.py:24,31-45`), returns 401 `SEC_UNAUTHENTICATED`. WS auth happens **before accept** (`ws.py:84-101`, close 4401 with envelope). Response hardening headers set on all responses (`security.py:50-71`).
- **Evidence:** `security.py:24-45,50-71,171-177`; `ws.py:84-101`.
- **Classification:** **IMPLEMENTED_REAL** — control boundary is real and fail-closed.
- **Production dependency:** relies on `ADMIN_API_KEY` being configured; if unset, protected endpoints reject (`main.py:36-39`).
- **Failure mode:** misconfigured key → total lockout (fail-closed, correct).
- **Security implications:** `ApiKeyAuthProvider` is a **single shared key** with hardcoded `scopes=("observe","control")` (`security.py:131,143`); no per-user identity, no RBAC, no rotation, no issue/expiry. `/stream` SSE is **unauthenticated** (`routes.py:50-64`).
- **Remaining work:** per-tenant auth, RBAC/scope model, key rotation, auth for `/stream`.

### 1.2 Platform observability
- **Component:** Prometheus metrics + /metrics.
- **Source:** `app/core/metrics.py`, `monitoring/prometheus.yml`, `docker-compose.yml` (prometheus/grafana services).
- **Actual behavior:** `Instrumentator().instrument(app).expose(app, endpoint="/metrics")` + custom counters/gauges (`metrics.py:100-108`). Prometheus scrapes `app:8000/metrics` (`prometheus.yml:5-10`).
- **Classification:** **IMPLEMENTED_REAL**.
- **Security implication:** Grafana in compose runs with **hardcoded `GF_SECURITY_ADMIN_PASSWORD=admin`** (`docker-compose.yml:77`).

### 1.3 Persistence
- **Component:** SQLAlchemy storage.
- **Source:** `app/storage/db.py`, `app/core/config.py`.
- **Actual behavior:** `DATABASE_URL = "sqlite:///data/evolution.db"` **hardcoded** (`db.py:9`); `init_db()` = `Base.metadata.create_all` (`db.py:44-47`, no migrations anywhere — grep for `alembic` finds only docs/checklist refs). **`Settings.DATABASE_URL` (`config.py:17`) is unused** — db.py imports only `os`/`sqlalchemy`, never config. Compose's `DATABASE_URL=sqlite:///./data/evolution.db` (`docker-compose.yml:10`) is therefore also inert for selection. Pool args (`pool_size`, `max_overflow`…) at `db.py:11-20` are cosmetic-to-misleading for SQLite.
- **Classification:** **IMPLEMENTED_BOUNDED** (functions, but contradicts the documented Postgres story; configuration trap).
- **Production dependency:** single SQLite file; `os.makedirs("data")` at import (`db.py:7`).
- **Failure mode:** **PROD-003**: operator sets a Postgres `DATABASE_URL` expecting the app to honor it → silently ignored, app stays on SQLite. No migration path, no backup/restore.
- **Security implications:** **PROD-004**: schema created on the fly with no versioning; no encryption/secret-hostage; DB file on disk unencrypted.
- **Remaining work:** honor `DATABASE_URL`, migrations (Alembic), backup, Postgres for real deployments.

### 1.4 Configuration fail-closed validation
- **Source:** `app/core/config.py:57-66`.
- **Actual behavior:** production refuses to start without `ADMIN_API_KEY`, non-default `SECRET_KEY`, and non-empty `CORS_ORIGINS`.
- **Classification:** **IMPLEMENTED_REAL** (real fail-closed gate at Settings validation).
- **Caveat:** `APP_VERSION` hardcoded `"3.1.0"` (`config.py:13`); compose does not set `SECRET_KEY`/`ADMIN_API_KEY` → `ENVIRONMENT=production` under compose fails fast (acceptable, but undocumented).

### 1.5 Runtime verification of generated artifacts (the real verification path)
- **Component:** candidate evaluation → real containers.
- **Source:** `app/engine/candidate_evaluator.py`, `app/engine/docker_runner.py`.
- **Actual behavior:** `evaluate_candidate` builds the artifact then **actually runs it in Docker** (`subprocess` `docker build`/`docker run`, `docker_runner.py:21-33`; random host port 8001–9000) and performs **live HTTP probes**: health, OpenAPI path prefix contract, auth-boundary (401/403 anonymous), full CRUD, metrics `http_requests_total`, tracing `X-Trace-ID`, timeout 504, retry attempts, circuit-breaker open/recover, cache hit/invalidate/TTL, rate-limit 429 (`candidate_evaluator.py:102-213`). Failure contract: `contract_ok = not failed and runtime_required ⊆ verified and no runtime_failed` (`candidate_evaluator.py:210`). Container always stopped in `finally` (`:221-222`).
- **Classification:** **IMPLEMENTED_REAL** (bounded: local host Docker, ephemeral, per-test SQLite env passed via `-e`).
- **Production dependency:** Docker daemon on the platform host; not an orchestrator.
- **Security implications:** containers run from untrusted genome candidates — the evaluator hands them `DATABASE_URL`, `API_KEY`, `JWT_SECRET`, `BASIC_PASSWORD` env values, but ephemeral/scoped; still a supply-chain surface if the host is multi-tenant.
- **Note:** this is the strongest contrast: artifact *verification* is real; artifact *deployment* (below) is simulated.

### 1.6 Capability truthfulness boundary (compiler intent)
- **Source:** `app/engine/capability_contract.py`, `capability_semantics.py`, `builders`, `backends.py` registry.
- **Actual behavior:** capabilities report `implemented=False` unless a concrete lowering exists; external `backends` are **never** represented as implemented (`capability_contract.py:110-115`); OAuth2 explicitly declared "not yet a true OAuth2 implementation" (`:59`); unknown middleware rejected instead of silently dropped (`:82`); runtime support resolution goes through the backend registry (fix `4b1b1f6`). `capability_semantics.py` stays technology-neutral at the compiler boundary.
- **Classification:** **IMPLEMENTED_REAL** (fail-closed truthfulness boundary).
- **Remaining work:** none structurally; keep guarded by the `grep -R "runtime_supported" app/engine` CI invariant proposed on PR #1 (not yet implemented).

### 1.7 Self-healing engine
- **Source:** `app/engine/self_healing.py`.
- **Actual behavior:** `_get_genome_by_id` is a **placeholder returning `None`** (`self_healing.py:359-362`); `_analyze_and_heal` therefore never heals a real genome; strategies are canned mutation rules; `ProductionReadinessGate(strict_mode=False)` is not part of any release gate.
- **Classification:** **PARTIAL → IMPLEMENTED_SIMULATED** for actuation.
- **Failure mode:** **PROD-013**: evolutions "self-heal" against estimated scores, not execution.

### 1.8 Production readiness scoring & gate
- **Source:** `app/engine/production_readiness.py`, `production_gate.py`, `production_analyzers.py`, `app/api/routes.py`.
- **Actual behavior:** all three layers are **heuristic scoring over genome fields**, not runtime truth: OpenAPI coverage is simulated per service-type (`production_analyzers.py:141-163`), test coverage is *estimated* (`_estimate_test_coverage`, `:683-702`), latency is a heuristic (`LatencyAnalyzer._calculate_base_latency`, `:526-550`). `/production/readiness` returns this heuristic report (`routes.py:66-68`). `ProductionReadinessGate` is invoked only by self-healing (`self_healing.py:97`).
- **Classification:** **PARTIAL** — real analysis machinery, but **no release-blocking enforcement on the real gate** (the `v1.1` gate job that fails on the PR is pytest, not this gate).
- **Failure mode:** **PROD-015/-017**: a genome can score "ready" heuristically while failing at runtime; conversely static "not_ready" may block valid candidates.

---

## 2. Container supply chain

### 2.1 Platform image
- **Source:** `autonomous-api/Dockerfile`.
- **Actual behavior:** `python:3.11-slim`, non-root `app` user (`Dockerfile:9,19`), `uvicorn app.main:app` on 8000 (`:23`). Single-stage, `pip install .` from pyproject (unpinned deps), no digest pinning, no SBOM/signing, no in-image healthcheck.
- **Classification:** **IMPLEMENTED_REAL** (usable; not supply-chain-hardened).

### 2.2 Compose topology
- **Source:** `autonomous-api/docker-compose.yml`.
- **Actual behavior:** app + ollama + prometheus + grafana + nginx(profile `ssl`). Healthcheck hits `/health` (`:19-24`); resource limits set (`:27-34`); volume for `data/` and `logs/`.
- **Security failures (evidence):**
  - Grafana `admin`/`admin` hardcoded (`:76-77`).
  - Ollama published `11434:11434` with **no auth** (`:41-42`).
  - No `SECRET_KEY`/`ADMIN_API_KEY` for production; `DATABASE_URL` is sqlite.
  - Nginx "ssl" profile mounts `./nginx/ssl` which contains **only `.gitkeep`** — no certs.
- **Classification:** **IMPLEMENTED_BOUNDED** — functional preview posture, not a hardened production topology.

### 2.3 Reverse proxy / TLS
- **Source:** `autonomous-api/nginx/nginx.conf`.
- **Actual behavior:** **only `listen 80`** — no `listen 443 ssl` block, no cert/key directives (`nginx.conf:15-40`); `/ws/` upgrade passthrough present.
- **Classification:** **PARTIAL → TLS UNIMPLEMENTED.** The "ssl" profile name overstates readiness (**PROD-008**).
- **Security implication:** TLS off at the edge (the app's `Strict-Transport-Security` header is inert without HTTPS).

### 2.4 Generated-artifact registry & promotion
- **Actual behavior:** container stage fabricates `registry.local/{image}` (`container_stage.py:41`) — no real registry for generated artifacts exists. GHCR is used **only for the platform's own** `dashboard`/`platform-api` images on main (`v1.1-release-gate.yml` Gate 5).
- **Classification:** **UNIMPLEMENTED** (generated artifacts); **IMPLEMENTED_REAL** (platform self-publish).

---

## 3. Deployment Engine (`constitutional_architecture/deployment`) — the simulated core

**Cross-cutting evidence:** no runtime imports it (grep: only its own package + 2 test files). `test_telemetry_engine.py:134` enforces `"from constitutional_architecture.deployment" not in source`.

| Component | Source | Classification | Evidence of simulated behavior |
|---|---|---|---|
| DeploymentPipeline | `deployment_pipeline.py:25-71` | **IMPLEMENTED_REAL** (control flow) | Topo-order by deps, pre-condition `can_execute`, sequential, **fail-closed halt** + events on any failure. |
| DeploymentEngine | `deployment_engine.py:67-112` | **PARTIAL** (orchestration real, actuation delegated) | Emits events, records metrics, fails closed on pipeline/rollout failure; but every subordinate is simulated. |
| DeploymentRegistry | `deployment_registry.py` | **IMPLEMENTED_REAL** (in-memory stage/target registry) | Register/get/list/clear — bookkeeping only. |
| BuildStage | `build_stage.py:19-46` | **IMPLEMENTED_SIMULATED** | Does not compile: only creates a `DeploymentArtifact` at `./build/` with `metadata={"source_files": n}`. |
| PackageStage | `package_stage.py:23-48` | **IMPLEMENTED_SIMULATED** | No tarball produced; artifact `application-package.tar.gz` is metadata-only. |
| InfrastructureStage | `infrastructure_stage.py:19-50` | **IMPLEMENTED_SIMULATED** | No IaC emitted; returns `docker-compose.yml`/`infrastructure.tf` artifact objects with metadata only. |
| ProvisionStage | `provision_stage.py:39` | **IMPLEMENTED_SIMULATED** | `metrics={"infrastructure_provisioned": True}`; no provisioning call anywhere. |
| ContainerStage | `container_stage.py:41` | **IMPLEMENTED_SIMULATED** | `location=f"registry.local/{image_name}"`, `tag":"latest"`; no build/push. |
| DeployStage | `deploy_stage.py:49` | **IMPLEMENTED_SIMULATED** | `metrics={"deployed": True}`; no actuation. |
| HealthStage | `health_stage.py:38` | **IMPLEMENTED_SIMULATED** | Constant `response_time_ms=15.0` `"healthy"`. |
| DockerTarget | `targets/docker_target.py:18-32` | **IMPLEMENTED_SIMULATED** | Constant `http://localhost:8080`, `5.0ms`, `"Container running"`; `cleanup()` = `pass`; **no docker calls** (unlike `docker_runner.py`, the real one). |
| KubernetesTarget | `targets/kubernetes_target.py:18-32` | **IMPLEMENTED_SIMULATED** | Constant `https://k8s-cluster.example.com`, `12.0ms`. |
| LocalTarget | `targets/local_target.py:16-34` | **IMPLEMENTED_SIMULATED** | Constants `http://localhost:5000`, `2.0ms`; `cleanup()` = `pass`. |
| HealthMonitor | `health/health_monitor.py:39-45` | **IMPLEMENTED_SIMULATED** | Measures `perf_counter()` between function entry/exit — **no HTTP request ever issued**; "healthy" unless elapsed > threshold. |
| RolloutManager | `rollout/rollout_manager.py:73-96,98-121` | **IMPLEMENTED_SIMULATED** (actuation) | Canary validates `pct>0` then claims `"Canary rollout completed (10% routed to new version)"` — **no traffic routing**; same for rolling/immediate. Real: validation + events. |
| RollbackManager | `rollout/rollback_manager.py:46-55` | **IMPLEMENTED_SIMULATED** | Appends `reason`/`snapshot` dict to `_rollback_history`; `_find_last_snapshot` returns `{"version": msg, "status": "stable"}`; no infra restoration. |
| PromotionManager | `rollout/promotion_manager.py:35-65` | **PARTIAL** | Real policy (`allowed_jumps`, `require_approval`) + history records; **no environment mutation** (nothing connects to an environment). |
| EnvironmentManager | `environment_manager.py:71-88` | **IMPLEMENTED_REAL** (policy) | `can_promote` enforces adjacent-tier + required `VerificationLevel`; `requires_rollback_plan`/`requires_health_check` derive from tier. No environment connectivity (by design). |
| Deployment events/metrics | `deployment_events.py`, `deployment_metrics.py` | **IMPLEMENTED_REAL** | In-process event emission/collection — no external sink. |
| Deployment tests | `tests/test_deployment_engine.py` | **IMPLEMENTED_REAL** (tests of the model) | Assert `status==RUNNING`/`FAILED` bookkeeping — they **cannot** prove actuation because there is none. |

---

## 4. CI/CD

### 4.1 CI (pull-request / push)
- **Source:** `.github/workflows/ci-cd.yml`.
- **Jobs:** `test` (3.11/3.12/3.13 + real Postgres 16 service), `lint` (flake8 E9/F63/F7/F82 + generated-template F821 guard), `security-scan` (bandit `-ll`), `multi-backend` (registers Go; compile + execute in CI when Go present), `build-docker` (main only), `capability-runtime` (real-container circuit-breaker certification).
- **Classification:** **IMPLEMENTED_REAL.**

### 4.2 Release gates
- **Source:** `.github/workflows/v1.1-release-gate.yml` (+ v1.2/v1.3/v1.4, identity, cbc1 variants).
- **Jobs:** Gate 1 observation-client TS; Gate 2 platform unit + reducer equivalence; Gate 3 Postgres V1-07 durability (real 20×500 counters, uniqueness); Gate 4 dashboard; Gate 4b integration-evidence chain; Gate 5 release → **verify evidence manifest (verdict CERTIFIED + empty failures + sha256 chain) then `build-push-action` to GHCR** (dashboard + platform-api, main/tag only); aggregate job.
- **Deployment gap:** searched all workflows for deploy actuation keywords (`kubectl`, `helm`, `terraform`, `ssh`, `apply -f`, `argocd`, `gcloud`, `aws`, `deploy`) — **zero matches**. Release = **publish only**. No staging/live deployment, no rollout, no rollback, no environment promotion anywhere in automation.
- **Classification:** **IMPLEMENTED_BOUNDED** — CI/CD automation is real and fail-closed on evidence, but **CD is `UNIMPLEMENTED`** (**PROD-016**).

---

## 5. Environment topology & lifecycle facilities

| Facility | Classification | Evidence |
|---|---|---|
| Migrations | **UNIMPLEMENTED** | Only `create_all` (`db.py:47`, `builder.py:392`); no alembic (grep). |
| Backup / restore | **UNIMPLEMENTED** | None found; readiness analyzer merely *recommends* managed backups (`production_readiness.py:273,308`). |
| Secret management / rotation | **UNIMPLEMENTED** | Env-only `SECRET_KEY`/`ADMIN_API_KEY`; Grafana `admin/admin`; Ollama anonymous. |
| TLS | **UNIMPLEMENTED** | `nginx.conf` 80-only; `ssl/` empty. |
| Environments (dev/staging/prod) | **PARTIAL** | `EnvironmentManager` tiers are logical policy only; no infra. |
| IaC for platform hosting | **UNIMPLEMENTED** | `InfrastructureStage` is metadata-only; no terraform/k8s manifests for the platform. |

---

## 6. Cross-cutting production risks (evidence-derived)

- **PROD-blocking:** deployment engine = simulators; no CD; `DATABASE_URL` config trap; no migrations/backup; no TLS; default secrets in compose; no generated-artifact registry.
- **False-confidence risks:** `/production/readiness` + production gate report *heuristic* scores as readiness (1.8); the failure-evidence discipline that exists (real runtime probes in 1.5, real evidence chain in Gate 4b/5) is **not yet connected** to a deployment decision.

## 7. Recommended evidence-first sequence (PROD-A02+)

1. **EV-A01** repository & CI integrity (secrets scan, workflow review, bandit gate).
2. **EV-A02** artifact correctness (real runtime probes from 1.5 already exist for Python/Go sequence).
3. **EV-A03** capability truthfulness (keep the 4b1b1f6/registry discipline; add CI `grep runtime_supported` invariant).
4. **EV-A04** security boundary (auth before accept, middleware, WS, `/stream`, API key model).
5. **EV-A05** persistence & migration (honor `DATABASE_URL`; alembic; backup).
6. **EV-A06** container supply chain (Dockerfile hygiene, pinned digests, SBOM, image signing).
7. **EV-A07** deployment actuator reality (replace simulation with real Docker/k8s targets or **delete** the simulate claims).
8. **EV-A08** health, observability, and rollout/rollback/promotion + gate-to-deploy wiring.
9. **EV-A09** authorization → deployment enforcement; escalation policy binding.
10. **EV-A10** staging topology + TLS; then **EV-A11** production readiness gate connected to actual release evidence.

*Internal analysis doc — working tree only, not tracked (per AGENTS.md .md policy).*