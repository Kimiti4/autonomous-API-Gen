# EV-A05 — Deployment

**Audit:** evidence-first production readiness, sequence EV-A01 → EV-A02 → EV-A03 → EV-A04 → **EV-A05 (this)** → EV-A06 → EV-A07 → EV-A08 → EV-A09
**Canonical audited state:** `6e1aa1a` (PR #1 head; 20 ahead / 1 behind `origin/main`, main tip `1f26e42`)
**Scope:** deployability of the platform API — env-var wiring, compose/Docker, start scripts, deployment guide, proxy/TLS topology, monitoring-stack defaults, backup, CI image publish, dashboard k8s. Read-only; collaborator remediation reported separately (none pending).
**Taxonomy:** `IMPLEMENTED_REAL / IMPLEMENTED_BOUNDED / IMPLEMENTED_SIMULATED / PARTIAL / UNIMPLEMENTED / UNKNOWN` · Confidence `CONFIRMED / INFERRED / UNVERIFIED`.

---

## STATUS: **FAIL**

No documented deployment path ever sets `ENVIRONMENT=production`, the shipped compose stack has no way to inject `ADMIN_API_KEY`, the recommended reverse-proxy topology collapses rate-limiting into a single shared bucket (EV-A04-004 upgraded to CONFIRMED), the `ssl` compose profile terminates no TLS, and `DEPLOYMENT_GUIDE.md` still tells operators to hand-write a second, timing-unsafe auth middleware the platform already ships in hardened form. The platform *can* be deployed safely (the building blocks exist — see §10), but every shipped happy-path points at a development configuration.

Register: **EV-A05-001 … EV-A05-014**.

---

## 1. Deployment surface inventory (what actually exists)

| Artifact | Path | Verdict |
|---|---|---|
| Runtime image | `autonomous-api/Dockerfile` | non-root (`addgroup/adduser` `app`, `USER app`), minimal `COPY` (pyproject/README/app/src — `.env` cannot enter image), **no `HEALTHCHECK`, no `--proxy-headers`**, CMD uvicorn `0.0.0.0:8000` |
| Stack definition | `autonomous-api/docker-compose.yml` | app + ollama + prometheus + grafana + nginx (`profiles: [ssl]`); healthcheck/restart/resource-limits present; **no `env_file`, no `ADMIN_API_KEY`/`SECRET_KEY`/`ENVIRONMENT` anywhere** (full-file read, 110 lines) |
| Reverse proxy | `autonomous-api/nginx/nginx.conf` + `nginx/ssl/.gitkeep` | `listen 80` only, sets `X-Forwarded-For`/`X-Real-IP`/WS upgrade; **no `listen 443`, no `ssl_certificate`**; ssl dir empty |
| Monitoring config | `autonomous-api/monitoring/prometheus.yml` | scrapes `app:8000/metrics` @15s, no auth, no alert rules |
| Deployment guide | `autonomous-api/DEPLOYMENT_GUIDE.md` (553 lines, tracked) | primary doc: env block, uvicorn/gunicorn/Docker, nginx-TLS snippet, "Add API Key Authentication", hypothetical `deploy.yml`, systemd unit, checklist |
| Start scripts | `autonomous-api/start.sh`, `start_all.sh` (+ `START_ALL.ps1`/`.bat`, README §quickstart) | dev posture: `--reload --host 0.0.0.0`, readiness = `curl /`, no key bootstrap |
| Backup | `autonomous-api/scripts/backup.sh` | `set -e`, 30-day retention, assumes `/opt/evolution-engine` (matches guide scp target) |
| Env templates | `autonomous-api/.env.example` (tracked), local `autonomous-api/.env` (gitignored, `.gitignore:39`) | example omits production vars; local file contains **only** `OPENAI_API_KEY` (a dead name — no consumer in `app/`) |
| CI image publish | `v1.1-release-gate.yml` / `v1.2-release-gate.yml` | GHCR push of `platform-api` + `dashboard`, **main/tag-only** (no PR-image publish) — two-state intact |
| K8s (dashboard only) | `dashboard/k8s/{deployment,configmap,service,ingress,hpa}.yaml` | `runAsNonRoot`, no priv-esc, probes, resources, ConfigMap; **no k8s/compose for the platform API itself** |
| Not present | systemd unit files, Procfile, fly.toml, render.yaml, entrypoint scripts, `deploy.yml` | systemd exists only as a guide snippet (§4) |

Integration-only: `tests/integration/docker-compose.yml` (test postgres `esap/esap` @5433, tmpfs) — acceptable for tests, not a deploy surface.

---

## 2. Production activation gate — no path ever turns production on

### EV-A05-001 — `ENVIRONMENT=production` is set by nobody
`[UNIMPLEMENTED]` · Confidence **CONFIRMED**

Exhaustive search of `DEPLOYMENT_GUIDE.md`, `.env.example`, `docker-compose.yml`, `PRODUCTION_HARDENING.md`, `README.md` env sections: **zero** `ENVIRONMENT=` occurrences. Consequences:

- `_validate_production_security` (`config.py:58`) — the startup gate that enforces `ADMIN_API_KEY` + rejects placeholder `SECRET_KEY` — **never runs on any documented path**.
- Every production-only behavior audited in EV-A04 (auth fail-closed probes were run *with* `ENVIRONMENT=production` manually) is dormant in real deployments; the app runs development defaults while the guide declares "Version: 3.1.0 - Production Ready" (`DEPLOYMENT_GUIDE.md:552`).
- The pre-deploy checklist (`:468-483`) has no environment-activation step either — "All environment variables configured" is untethered to the one variable that matters.

### EV-A05-002 — Compose cannot deliver the admin key; template omits required vars
`[UNIMPLEMENTED]` · Confidence **CONFIRMED**

- `docker-compose.yml:9-13` `environment:` = `DATABASE_URL`, `OLLAMA_URL`, `LOG_LEVEL`, `CORS_ORIGINS` only. No `env_file:`, no `${ADMIN_API_KEY:?}` interpolation, no `ENVIRONMENT`.
- `.env.example` (tracked) carries `API_HOST`/`API_PORT`/`OPENAI_API_KEY` (all **dead names** — absent from `Settings`, silently dropped by `extra="ignore"`) and omits `ADMIN_API_KEY`, `SECRET_KEY`, `ENVIRONMENT` entirely. `DEPLOYMENT_GUIDE.md:47-78` is the only file that mentions them (§3, EV-A05-003).
- Net effect for the shipped stack: with no key set, every `/evolve*` call is a permanent 401 (fail-closed — safe but operationally dead, with no troubleshooting hint anywhere: the guide's "Server Won't Start" section never mentions auth); an operator who then sets `ENVIRONMENT=production` without discovering `SECRET_KEY` gets the startup refusal — also correct, also undocumented. There is no documented, non-plaintext way to inject either variable (compose must be hand-edited).

---

## 3. The guide actively misconfigures security

### EV-A05-003 — Guide's `SECRET_KEY` example defeats the production validator; dead knobs documented as live; PostgreSQL path unreachable; self-contradiction on rate limiting
`[IMPLEMENTED_SIMULATED]` (documented controls that do not behave as stated) · Confidence **CONFIRMED**

- `DEPLOYMENT_GUIDE.md:66` ships `SECRET_KEY=your-super-secret-key-change-in-production`; the validator (`config.py:62`) only rejects the exact string `"change-this-in-production"` → **the repo's own published example passes the production security gate**. (Bounded today: `SECRET_KEY` has zero runtime readers — EV-A04-007 — but the validator's sole purpose is defeated by the guide.)
- Same env block documents `RATE_LIMIT_GENERAL/EVOLUTION/WINDOW`, `LOG_FILE`, `API_KEY_HEADER` (`:67-77`) — all confirmed dead in EV-A04-007 — while the troubleshooting section (`:522-528`) instead tells operators to **edit `rate_limit.py` source**. The guide contradicts itself; both halves are wrong about env (dead) / only half-right about source (works, but never reconciled).
- `:55-56` recommends `DATABASE_URL=postgresql://…` "for production use" — `db.py` hardcodes `sqlite:///data/evolution.db` and never reads the setting (EV-A04-007). The guide's flagship production database path is unreachable.

### EV-A05-005 — Guide instructs operators to author a second, timing-unsafe auth layer
`[UNIMPLEMENTED as advice; doc defect]` · Confidence **CONFIRMED**

`DEPLOYMENT_GUIDE.md:197-226` ("Add API Key Authentication") tells operators to create `app/middleware/auth.py` with `if not api_key or api_key != expected_key` (non-constant-time), a path skip-list, and bare `HTTPException(401)`, then register it in `main.py`. Facts:

- The platform already ships timing-safe (`compare_digest`), envelope-consistent auth in `middleware/security.py` — the guide pretends it does not exist.
- Following it stacks a duplicate middleware → a **third** 401 body shape (beyond EV-A04-002's two), reintroduces allow-list thinking that underpins EV-A04-017's prefix boundary, and repeats the `!=` anti-pattern class already flagged in EV-A01/Bandit findings.
- The guide's "Security Hardening" section never mentions the shipped header schemes (`X-API-Key`, bearer, cookie).

---

## 4. Proxy topology — EV-A04-004 upgraded from INFERRED to CONFIRMED

### EV-A05-004 — Documented reverse-proxy deployment collapses the rate limiter into one shared bucket; systemd path cannot receive secrets
`[PARTIAL]` · Confidence **CONFIRMED** (was INFERRED in EV-A04-004)

Chain, all static and now complete:

1. Shipped `nginx/nginx.conf:26,37` sets `X-Forwarded-For` / `X-Real-IP`; guide's TLS snippet does too (`:185-186`); upstream is `server app:8000` (`nginx.conf:7`).
2. The app has **zero** readers: grep `X-Forwarded|proxy_headers|forwarded_allow` across `app/**/*.py` → no hits. Rate limiting and security middleware use `request.client.host` only.
3. No command anywhere starts uvicorn/gunicorn with `--proxy-headers` / `forwarded-allow-ips`: guide `:93-98` (uvicorn), `:106-111` (gunicorn), shipped `Dockerfile:23`, `start.sh:16`, `start_all.sh:85`, guide systemd `:458` — grep of guide + scripts → zero hits.

→ Behind the recommended proxy, `request.client.host` = the proxy/Docker-bridge address for **all** clients → everyone shares one rolling 60-second bucket → the EV-A04-004 demonstrated operator-lockout (anonymous 401s burning `/evolve` quota → authed 500s) applies to **every real deployment**, not just proxied topology in the abstract.

Additionally, the guide's systemd unit (`:449-464`) has **no `EnvironmentFile=`/`Environment=` line** — the documented Linux-service path cannot deliver `ADMIN_API_KEY` or `ENVIRONMENT` at all (same dead-end as EV-A05-002, second path).

---

## 5. LLM wiring — configured value never reaches the client

### EV-A05-006 — `OLLAMA_URL` has zero LLM consumers; compose reasoning is broken while the startup log claims health; model name four-way drift
Wiring `[UNIMPLEMENTED]` · Confidence **CONFIRMED** (wiring) / **INFERRED** (container runtime — Docker daemon down, not probed)

- Grep `OLLAMA_URL|OPENAI_API_KEY|API_HOST|API_PORT` over `app/**/*.py` → exactly two hits: `config.py:19` (definition) and `main.py:150` (`logger.info(f"Ollama URL: {settings.OLLAMA_URL}")`). **No LLM code path reads it.**
- The only client, `llm.py:8`, hardcodes `http://localhost:11434/api/generate` with `"model": "llama3"` (`:10`); errors are swallowed as `"[OLLAMA ERROR] …"` (`:20`). All three agents (`explorer/heuristic/optimizer`) and `llm_guided_mutation.get_llm_client` route here (EV-A04-001 already proved `/stream` yields this shape).
- Compose sets `OLLAMA_URL=http://ollama:11434` (`docker-compose.yml:11`) and the startup log prints it as fact — but inside the `app` container `localhost:11434` is the app container itself, not the `ollama` service → `/stream` and reasoning **cannot reach Ollama in the shipped stack** (INFERRED: static topology is conclusive; runtime not probed because the Docker daemon is down).
- Model drift, four sources of truth: `settings` default `llama3.2` · `.env.example:8` `llama3` · `start_all.sh:73-78` pulls `llama3.2` · `llm.py:10` hardcodes `llama3`.

---

## 6. TLS — the `ssl` profile terminates none

### EV-A05-007 — Compose profile named `ssl` ships an HTTP-only proxy and an empty cert dir
`[IMPLEMENTED_SIMULATED]` · Confidence **CONFIRMED**

- `nginx/nginx.conf:16` is the only `listen` directive: `listen 80`. No `listen 443`, no `ssl_certificate`/`ssl_protocols` anywhere in the shipped config.
- Compose maps `443:443` (`:92`) and mounts `./nginx/ssl` (`:95`) — the directory contains only `.gitkeep`. Enabling `--profile ssl` yields a reverse proxy where **port 443 accepts nothing** (connection refused) and all traffic stays plaintext.
- The guide's full TLS server block (`:165-194`) is a *snippet never wired to the shipped nginx.conf* — classic guide/artifact drift on the primary transport-security control.

---

## 7. Monitoring stack defaults and exposure

### EV-A05-008 — Grafana `admin`/`admin`; Prometheus, Ollama, and app all host-published unauthenticated
`[PARTIAL]` · Confidence **CONFIRMED**

- `docker-compose.yml:77` `GF_SECURITY_ADMIN_PASSWORD=admin` (Grafana's default user is `admin`) with `3000:3000` published → admin/admin web UI on the host when the stack is up.
- `9090:9090` Prometheus (no auth config in `prometheus.yml`, none natively) and `11434:11434` Ollama (unauthenticated model API) likewise published on all interfaces (no `127.0.0.1:` bind prefix). App publishes `8000:8000`.
- Only `nginx` is profile-gated (`profiles: [ssl]`, `:100-101`); ollama/prometheus/grafana start on a default `up`.

### EV-A05-009 — `/metrics` is anonymous and proxy-reachable
`[PARTIAL]` · Confidence **CONFIRMED**

- `metrics.py:108` `Instrumentator().expose(app, endpoint="/metrics")`, wired at `main.py:133`.
- `PROTECTED_CONTROL_PREFIXES = ("/evolve", "/production/readiness")` (`security.py`) — **`/metrics` not in the list**; no rate-limit exemption either (general bucket only).
- Through the guide's nginx (`location / → proxy_pass`, `nginx.conf:21-28`) or direct `8000` publish, request metrics are world-readable — feeding EV-A04-014's "unauthenticated observability" surface with concrete request-rate data. (Prometheus scrape from inside the bridge is fine; the exposure is the same open path as the API.)

---

## 8. Guide ↔ artifact drift cluster

### EV-A05-010 — CI/CD example doesn't exist; backup targets a file that doesn't; guide Dockerfile ≠ shipped Dockerfile; post-deploy test unstated; README quickstart is the dev script
`[IMPLEMENTED_SIMULATED]` / `[PARTIAL]` · Confidence **CONFIRMED**

- **CI/CD** (`:313-375`): presents a ready-to-copy `deploy.yml` (scp → `/opt/evolution-engine`, compose restart). `Test-Path .github/workflows/deploy.yml` → **false**. Real publish jobs are main/tag-only GHCR builds in the v1.x release gates (§1 inventory). The guide's "Deploy to Production" pipeline never existed.
- **Backup**: guide `:412-416` says copy `app/engine/memory.json` — `Test-Path` → **false**; `scripts/backup.sh` step 2/4 checks `$APP_DIR/memory.json` (repo root under `/opt`) → also absent → always "not found, skipping". Guide's own backup snippet (`:392-401`, retention 7d) also diverges from the shipped script (retention 30d, 4 steps).
- **Dockerfile**: guide's inline image (`:118-143`: `useradd -m appuser`, `HEALTHCHECK curl …`, no `src/`) ≠ shipped `Dockerfile` (`addgroup/adduser app`, no HEALTHCHECK, copies `src/`). Guide's `docker run` (`:149-155`) passes only the dead `DATABASE_URL` — no key, no `ENVIRONMENT` (EV-A05-001/002 again).
- **Post-deploy** (`:540-548`): "Run `python test_production.py`. All tests should pass" — the file exists but is an out-of-suite, live-server test needing a running API + admin key (AGENTS.md; nothing in the section says so).
- **README** quickstart (`:173,207-220`) launches `start_all.sh` / `START_ALL.*` — the `--reload` dev scripts (EV-A05-013) — and itself hedges: "The exact startup commands and environment requirements should be checked against the current scripts before deployment" (`:243`). The primary documented run path is development mode.

---

## 9. K8s image lineage and secrets-at-rest

### EV-A05-011 — Dashboard k8s references an image name CI never publishes
CI side **CONFIRMED**, registry existence **UNVERIFIED**

- `dashboard/k8s/deployment.yaml:16` → `image: ghcr.io/kimiti4/esap-dashboard:v1.1.0`.
- `v1.1-release-gate.yml:393` pushes `images: ${{ env.GHCR_IMAGE }}/dashboard` (= `ghcr.io/kimiti4/<repo>/dashboard`), tags from build metadata — a **different repository path**, not `kimiti4/esap-dashboard`. Whether a separately-published `esap-dashboard` package exists in GHCR is unverified (no registry query performed).
- Positives stand: `runAsNonRoot`, `allowPrivilegeEscalation: false`, probes, resources, ConfigMap-mounted config (no inline secrets), full manifest set (service/ingress/hpa/configmap).

### EV-A05-012 — `backup.sh` copies `.env` with plain `cp`; no permission tightening
`[PARTIAL]` · Confidence **INFERRED** (umask-dependent)

Step 4/4: `cp $APP_DIR/.env $BACKUP_DIR/env_$TIMESTAMP` under `/backups/evolution-engine`, 30-day retention, no `chmod`/`umask` guard — file lands with default umask perms, unencrypted. Path consistency with the guide's scp target is good (`APP_DIR=/opt/evolution-engine`); the missing piece is secret handling plus the fact that no automation ever installs to that path (EV-A05-010). Local repo `.env` hygiene is correct (gitignored at `autonomous-api/.gitignore:39`; never tracked — `git ls-files` clean).

---

## 10. What is actually right (positives)

### EV-A05-014 — Sound building blocks, wrong happy-path
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

- **Image hygiene:** non-root system user; explicit `COPY` of only `pyproject/README/app/src` — secrets and git metadata cannot enter the layer even from a dirty tree; slim base.
- **Compose ops basics:** `restart: unless-stopped`, real `/health` healthcheck (python urllib, correct — python exists in image), cpu/memory limits, bridge network isolation, volume mounts for `data/`+`logs/`, nginx WS-upgrade `map` correct, ssl profile *opt-in* (not on by default).
- **`.env` discipline:** local secrets gitignored; only `.env.example` tracked; backup of `.env` exists as a concept (chmod gap in EV-A05-012).
- **Metrics pipeline real:** `/metrics` implemented via Instrumentator + declared Prometheus scrape target matches — monitoring scaffolding is not simulated (exposure question is EV-A05-009, existence is real).
- **CI publishes only from main/tag** — no PR-image supply path; two-state release discipline intact.
- **Dashboard k8s** securityContext/probes/resources/ConfigMap pattern is production-shaped (EV-A05-011 is an image-name lineage bug, not a shape bug).
- **`requirements.txt`** covers the guide's `pip install -r` path (incl. pytest) — but **not `hypothesis`**, reconfirming EV-A04-015's clean-env root-suite abort for the requirements-based path too.
- **Integration compose** isolated, test-only, tmpfs postgres — correctly out of the deploy surface.

---

## 11. Verification appendix (evidence log)

- Full reads: `docker-compose.yml` (110), `DEPLOYMENT_GUIDE.md` (553), `nginx.conf` (41), `prometheus.yml`, `requirements.txt`, `Dockerfile` (23), `.env.example` (18), `start.sh`, `start_all.sh`, `dashboard/k8s/deployment.yaml`, `tests/integration/docker-compose.yml`, `backup.sh` (full), `llm.py` (20).
- Greps: `ENVIRONMENT=` across guide/example/compose/hardening/README → zero; `OLLAMA_URL|OPENAI_API_KEY|API_HOST|API_PORT` in `app/**` → 2 hits (`config.py:19`, `main.py:150`); `X-Forwarded|proxy_headers|forwarded_allow` in `app/**` → **0 hits**; `proxy-headers|forwarded-allow|EnvironmentFile` in guide+scripts → 0 hits; `PROTECTED_CONTROL_PREFIXES` → `("/evolve", "/production/readiness")`; `setup_metrics|Instrumentator|/metrics` → `metrics.py:100,108`, `main.py:26,133`; `esap` in workflows → integration DSN + `GHCR_IMAGE/dashboard` only.
- File existence: `.github/workflows/deploy.yml` false · `app/engine/memory.json` false · `test_production.py` true · `requirements.txt` true · `nginx/ssl/` contains only `.gitkeep` · `dashboard/k8s/` = deployment/configmap/service/ingress/hpa.
- Git/GH: `git ls-files autonomous-api/.env` → empty (untracked); `git check-ignore` → `autonomous-api/.gitignore:39:.env`; PR #1 `headRefOid` = `6e1aa1a…` (21 commits, last = Bandit suppression) — **no new collaborator push**; `origin/main` = `1f26e42`.
- Not probed (Docker daemon down): container boot, `--profile ssl` nginx bind, compose healthcheck execution, ollama reachability inside the bridge → container-runtime claims marked INFERRED where noted; all file/static claims CONFIRMED.
- Harness notes: none required this phase (no live probes; EV-A04's undrained-`stdout=PIPE` artifact lesson not applicable).
- Gates: root `python -m pytest` re-run after report write (session smoke, see close-out).

---

## 12. Conclusion & next gate

**FAIL.** The platform's deployment *components* are mostly real and well-shaped (EV-A05-014), but the deployment *system of record* — guide, compose, env template, start scripts, README quickstart — converges on one outcome: a development-mode process, without the admin key reachable, behind a proxy that flattens rate limiting, optionally "SSL-secured" by a profile that terminates no TLS, with monitoring defaults of `admin`/`admin` on published ports and anonymous `/metrics`. Three separate documented paths (compose, docker run, systemd) each independently fail to deliver the two variables production requires, and the one document that does name them teaches a validator-bypassing `SECRET_KEY` and a duplicate timing-unsafe auth middleware.

Must-fix before any production claim survives (ordered): set/document `ENVIRONMENT=production` + secret injection in compose/env template (001/002); fix proxy client-IP (`--proxy-headers` or trusted-proxy handling) (004); replace guide auth/TLS/CI sections with the shipped reality (003/005/007/010); wire `settings.OLLAMA_URL` into `llm.py` (006); gate or bind-localize grafana/prometheus/ollama and protect `/metrics` (008/009).

**NEXT GATE: EV-A06 — Observability.**

*(Sequence unchanged: EV-A06 → EV-A07 Schema/Observation Integrity → EV-A08 Change Safety → EV-A09 Governance. Bandit-fix verification track runs separately on any collaborator push.)*
