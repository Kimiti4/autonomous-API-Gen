# EV-A01 — Repository & CI Integrity Audit

- **State audited:** `6e1aa1a` (PR #1 head, `evolution/second-backend-lowering-hardening`), fetched tree clean except untracked `docs/PROD-A01-deployment-inventory.md`.
- **Method:** READ-ONLY, NON-MUTATING, EVIDENCE-FIRST, FAIL-CLOSED. Every classification cites `file:line`, a git fact, a GitHub API response, a CI log, or a local reproduction.
- **Taxonomy (per PROD-A01):** `IMPLEMENTED_REAL` / `IMPLEMENTED_BOUNDED` / `IMPLEMENTED_SIMULATED` / `PARTIAL` / `UNIMPLEMENTED` / `UNKNOWN`.
- **Evidence confidence (per finding):** `CONFIRMED` (observed directly during this audit) / `INFERRED` (confirmed facts + platform-documented behavior) / `UNVERIFIED` (not observable with current access).
- **Run attribution labels:** `PR-CAUSED` / `PRE-EXISTING` / `ENVIRONMENTAL` / `EVIDENCE-GAP` / `SKIPPED-BY-CONDITION`.
- **Two-state discipline:** `6e1aa1a` is the canonical audited state. Server-side and `origin/main` changes dated 2026-09-22 (CodeQL workflow direct-push, repository ruleset, collaborator Bandit fix still pending) are reported only in §12 Pending-state, never merged into audited-state classifications.

---

## 0. Executive summary

1. **CI at the audited commit is RED — and both reds are PR-caused (`CONFIRMED`).** Of 9 workflow runs at head `6e1aa1a`, 7 succeed and 2 fail: `autonomous-api CI/CD` (run `35742917271`) and `v1.1 Release Gate` (run `35742917564`). Root causes: (a) Bandit B608 introduced by PR commit `7b593d6` (present in `6e1aa1a`, absent from `main` — both ancestry directions tested); (b) two **PR-added, non-hermetic tests** in `tests/engine/test_evolution_fail_closed.py` that die on fresh checkouts with `sqlite3.OperationalError: no such table: evolution_runs` (same 2 tests fail in ci-cd `test (3.12)` and v1.1 Gate 2).
2. **Prior "pre-existing" labels are invalidated.** The earlier comparison base `ea63ff4` is **not an ancestor of `origin/main`**; current main tip `1f26e42` runs the **entire chain green** (38 checks: 37 success, 1 skipped). There is no longer any evidence of a pre-existing platform-test failure on main.
3. **Local green ≠ CI green (`CONFIRMED` masking).** The same 2 tests pass locally (5/5 in the venv) only because a gitignored `autonomous-api/data/evolution.db` (94,208 B; ignored by `autonomous-api/.gitignore:43 *.db`) already contains the `evolution_runs` table. Fresh CI checkouts have no such table.
4. **Python-version matrix evidence is incomplete at the audited commit (`EVIDENCE-GAP`).** Default matrix `fail-fast` (no `fail-fast:` key exists anywhere in the repo; `ci-cd.yml:19` is the only `strategy:` in any workflow) cancelled `test (3.11)` and `test (3.13)` after `3.12` failed — their status for PR content is `UNKNOWN`. On main all three pass.
5. **Green gates on this PR do not mean certified.** CBC-1, Identity, v1.2, v1.3, v1.4 gate runs report `success` at `6e1aa1a` while their certification/consume-evidence, Gate 3/4b/5, and publish jobs were **skipped** by `if: github.ref == 'refs/heads/main'` (+ tag) conditions — and their suites are scoped subdirectories (`tests/v12`, `tests/v13`, `tests/v14`, `tests/identity`, `tests/cbc1`) that never execute platform tests.
6. **GitHub supply-chain controls are all off (`CONFIRMED`):** secret scanning disabled, push protection disabled, Dependabot security updates disabled, no `dependabot.yml`, no dependency-vulnerability scan in any workflow, zero repository secrets (only `secrets.GITHUB_TOKEN`), Actions pinned to mutable major tags, all Docker bases unpinned.
7. **Repository governance is bypassable by design:** no required-review rule in the active ruleset, **no PR has ever been merged** (PR history = only open PR #1), and `codeql.yml` landed on main by **direct push** (`pulls=[]` for `1f26e42`). The same-day ruleset (`Protection`, id `23822498`) blocks deletion and non-fast-forward updates only; its `code_quality` rule semantics are `INFERRED`, merge-blocking effect `UNVERIFIED`.
8. **CodeQL exists only in the pending state (added to main today, absent from the audited tree) and already reports 5 open medium alerts** while its `Analyze` checks stay green — green static-analysis check ≠ no findings.
9. **Release boundary stops at GHCR.** Publish jobs (`Gate 5`, `v1.2 publish`) succeed on main → images pushed → **STOP**. Zero CD actuation anywhere (cross-ref PROD-016). Direct package listing `UNVERIFIED` (token lacks `read:packages`, HTTP 403).
10. **Blocker register: EV-A01-001 … EV-A01-011** (§11).

---

## 1. Provenance & drift

| Fact | Value | Confidence |
|---|---|---|
| Audited HEAD | `6e1aa1acf96d4f619d5331ff9d1056a7c4e46034`, tree `08702498027f031cb8074c59b87ec3916c133cbd` | CONFIRMED |
| Merge-base with main | `95ca5f7dca3cc8a7ac1f4e489ba150f7fa0943fe` | CONFIRMED |
| Divergence | `6e1aa1a` = **20 ahead / 1 behind** `origin/main` (`git rev-list --left-right --count`) | CONFIRMED |
| `origin/main` tip | `1f26e42` "Create codeql.yml", parent = `95ca5f7`, authored 2026-09-22T15:32:29+03:00, **`pulls=[]` (direct push)** | CONFIRMED |
| Main-only content vs audited tree | exactly `1f26e42` (`.github/workflows/codeql.yml`); CodeQL workflow is **not** in `6e1aa1a` | CONFIRMED |
| B608 introducer | `7b593d6` is ancestor of `6e1aa1a`, **not** ancestor of `origin/main` | CONFIRMED |
| Working tree | clean; 1 untracked (`docs/PROD-A01-deployment-inventory.md`); `out/calibration-baseline-6/` = 122 tracked generated files (inert: GitHub runs only root workflows) | CONFIRMED |
| PR history | only PR ever = #1 (open); no merged PRs | CONFIRMED |
| `ea63ff4` (prior comparison base) | exists locally, **not an ancestor of `origin/main`** → prior labels against it are void | CONFIRMED |

## 2. CI topology (audited tree)

| Workflow | Triggers | Suite / key jobs | Concurrency | Certification/publish condition |
|---|---|---|---|---|
| `ci-cd.yml` | push `main`,`develop`; PR `main` | `test` matrix 3.11/3.12/3.13 → `pytest tests/` (`:50`); `lint` (flake8 `:70`, template F821 `:99`, black non-blocking `:101`); `security-scan` (bandit `:115`); `multi-backend` (Go); `build-docker` (`if: github.ref == 'refs/heads/main'` `:152`); `capability-runtime` (real container) | **none** (asymmetric vs all gates) | n/a |
| `v1.1-release-gate.yml` | push/PR `main`, tags `v1.1.*`, dispatch | Gate 1 `tests/observation` TS; **Gate 2 `pytest tests -m "not integration"` (`:110`)**; Gate 3 `tests -m integration` (`:185`, needs Gate 2 `:138`); Gate 4 dashboard; Gate 4b evidence chain; Gate 5 verify manifest → GHCR push; aggregate `if: always()` (`:441`, verdict logic `:459-470`) | `cancel-in-progress: true` (`:11-13`) | Gate 5: `main \|\| tags/v1.1.*` (`:331`) |
| `v1.2-release-gate.yml` | same pattern | fast = `pytest tests/v12` (`:36`) | cancel-in-progress | certification `:82`, publish `:130`: `main \|\| tags/v1.2.*` |
| `v1.3-release-gate.yml` | same | fast = `pytest tests/v13` (`:36`) | cancel-in-progress | `:82` `main \|\| tags/v1.3.*` (verify only, no publish job) |
| `v1.4-release-gate.yml` | same, no tags | fast = `pytest tests/v14` (`:32`) | cancel-in-progress | `:70` `main` only |
| `identity-release-gate.yml` | same | fast = `pytest tests/identity` (`:32`) | cancel-in-progress | `:70` `main` only |
| `cbc1-release-gate.yml` | same | fast = `pytest tests/cbc1` (`:32`) | cancel-in-progress | `:70` `main` only |
| `cbc1-campaign-a.yml` | (campaign) | 13 categories × 2 backends | cancel-in-progress | n/a |

Structural facts (`CONFIRMED`): `permissions: contents: read` on ci-cd (minimal token); `needs` chains are fail-closed (`multi-backend`←`lint` `:125`; `build-docker`/`capability-runtime`←`test`,`lint` `:151,163`); **the only matrix in the entire repo is ci-cd's** and it sets no `fail-fast` → GitHub's documented default **true** (`INFERRED` from docs + observed cancellations); gates all cancel superseded runs, ci-cd does not.

## 3. Security gates & blocking behavior

| Gate | Command / location | What it blocks | Findings |
|---|---|---|---|
| Bandit | `bandit -ll -r app/ -f json -o bandit-report.json` (`ci-cd.yml:115`) | Job failure → **whole ci-cd run fails** (no dependents needed — run-level). `security-scan` has **no `needs` dependents** and no aggregate job; it blocks by failing the run, not by gating other jobs. | RED at audited commit: B608 at `app/engine/backends.py:192` (introduced `7b593d6`). **PR-CAUSED, CONFIRMED.** Collaborator fix PENDING (§12). |
| Bandit report upload | `ci-cd.yml:117`, **no `if: always()`** | — | Failed runs lose the report: red run artifacts = **0**, green main run = `security-report` (1,843 B) — `CONFIRMED` via runs API. → EV-A01-009 |
| Template lint | generated-artifact flake8 F821 (`:99`) | lint job → multi-backend, build-docker, capability-runtime (via needs) | GREEN at audited commit |
| Flake8 | syntax-level selectors only `E9,F63,F7,F82` (`:70`) | lint job | GREEN — but shallow → EV-A01-010 |
| Black | `black app/ --check` + **`continue-on-error: true`** (`:101`) | nothing | never blocks → EV-A01-010 |
| Mypy | installed (`:68`) and **never executed** (grep: only hit is `:68`) | nothing | dead gate → EV-A01-010 |
| Codecov | `fail_ci_if_error: false` (`:55`) | nothing | coverage upload never blocks → EV-A01-010 |
| Dependency vuln scan | **no** pip-audit / safety / trivy / npm-audit / dependabot anywhere (grep empty) | — | `UNIMPLEMENTED` → EV-A01-005 |
| Secret scan (repo) | GitHub secret scanning **disabled**, push protection **disabled** (API) | — | `UNIMPLEMENTED` → EV-A01-005 |
| CodeQL | `.github/workflows/codeql.yml` — **only on pending main**, triggers push/PR `main` + weekly cron; `Analyze (actions/python/go/javascript-typescript)` green on both commits | nothing that fails on findings | Pending-state; **5 open medium alerts** (§7) → EV-A01-008 |
| Docker image checks (hadolint/trivy image) | none | — | `UNIMPLEMENTED` (cross-ref EV-A06 later) |
| Evidence-manifest verify | Gate 5 verifies manifest verdict CERTIFIED + empty failures + sha256 chain before push (`v1.1-release-gate.yml` Gate 5 region) | GHCR publish | `IMPLEMENTED_REAL`, only on main/tags |

## 4. Secrets & credentials

- Repository Actions secrets: **0** (API). Only `secrets.GITHUB_TOKEN` used (`v1.1-release-gate.yml:384`, `v1.2-release-gate.yml:143`).
- Plaintext findings: `.env.example:18` placeholder `your-api-key-here`; `tests/integration/docker-compose.yml:7` `POSTGRES_PASSWORD: esap`; `docker-compose.yml:77` `GF_SECURITY_ADMIN_PASSWORD=admin` (cross-ref PROD-004 class). `.env.example` omits required `SECRET_KEY`/`ADMIN_API_KEY`.
- No `SECURITY.md`, no `SECURITY` policy file, no issue templates with bounty/security routing.
- Classification: credentials handling `PARTIAL` (no live secrets in repo — `CONFIRMED` by repo secret scan of tracked files earlier + API secrets list) but **no rotation story, defaults committed, platform secret-scanning off**.

## 5. Dependency integrity & supply chain

| Item | Evidence | Classification / Conf |
|---|---|---|
| Lockfile not committed | `uv.lock` exists on disk but `autonomous-api/.gitignore:72` ignores it; CI installs with plain `pip install -e .` (`ci-cd.yml:47,68,141,174`) | reproducibility `UNIMPLEMENTED` / CONFIRMED → EV-A01-004 |
| Pins | `pyproject.toml` all `>=` lower bounds (sole bounded dep: `uv_build>=0.11.3,<0.12.0`); `requirements*.txt` unpinned | `UNIMPLEMENTED` / CONFIRMED |
| GitHub Actions pins | `actions/checkout@v4`, `setup-python@v5`, `setup-go@v5`, `upload-artifact@v4`, `codecov/codecov-action@v5`, `docker/build-push-action` — major tags, **not commit SHAs**; runner logs show Node-20 deprecation forcing Node 24 | `PARTIAL` / CONFIRMED |
| Docker bases (all mutable, no digests) | `python:3.11-slim`, `node:20-alpine`, `nginxinc/nginx-unprivileged:1.27-alpine` (dashboard), `grafana:latest`, `prom/prometheus:latest`, `ollama:latest`, `postgres:16-alpine`, `generated/Dockerfile` → `python:3.11-slim` (runs as root) | `PARTIAL` / CONFIRMED |
| Go module (generated) | no `go.mod` in source; emitted by `backends.py:131-137` with `modernc.org/sqlite` unpinned | `PARTIAL` / CONFIRMED |
| Dependabot | no `.github/dependabot.yml`; Dependabot security updates **disabled** (API) | `UNIMPLEMENTED` / CONFIRMED → EV-A01-005 |

## 6. Branch protection & repository governance

- Classic branch protection: `404 "Branch not protected"` on `main`.
- Active **repository ruleset** `Protection` (id `23822498`, API `CONFIRMED`): enforcement `ACTIVE`, targets `~ALL`, bypass list **none**, `current_user_can_bypass: never`; rules = `deletion`, `non_fast_forward`, `code_quality` (`severity: all`). Created 2026-09-22T12:35Z, updated 14:48Z (same day as audit — attribution `UNVERIFIED`, reported in §12).
- **No `pull_request` rule → no required reviews, no required PRs.** Empirically confirmed: `1f26e42` has `pulls=[]` (direct push to main, parent `95ca5f7`), and PR history contains zero merged PRs. `code_quality` semantics `INFERRED` (requires status checks to pass); actual merge-blocking effect `UNVERIFIED` (not attempted).
- No `CODEOWNERS`. Classification: `PARTIAL` (force-push/deletion blocked — real) / `UNIMPLEMENTED` (review gate) → EV-A01-006.

## 7. CI truthfulness — deception risks

| # | Risk | Evidence | Classification / Conf |
|---|---|---|---|
| T1 | **Green release gate ≠ certified.** On PR runs, CBC-1/Identity/v1.4 gates report `success` with certification jobs **skipped** (`cbc1-release-gate.yml:70`, `identity-release-gate.yml:70`, `v1.4-release-gate.yml:70` = `if: github.ref == 'refs/heads/main'`; v1.1 `:331`, v1.2 `:82,130`, v1.3 `:82` = main/tags). Observed at `6e1aa1a`: 5× `certification (consume evidence) = skipped`, `Gate 3/4b/5 = skipped`, `v1.2 publish = skipped`, yet runs = `success` (runs `35742917243/7505/7356/7389/7439`). | `PARTIAL` (chains fail-closed where they run) / CONFIRMED → EV-A01-007 |
| T2 | **Scoped suites can't see platform failures.** `pytest tests/v12\|v13\|v14\|identity\|cbc1` never import `tests/engine/*`: v1.2 gate = `success` at the exact commit where ci-cd `test (3.12)` = `failure`. | `PARTIAL` / CONFIRMED → EV-A01-007 |
| T3 | **Static-analysis green with open findings.** `Analyze (*)` + `CodeQL` = `success` on both commits while code-scanning API reports **5 open alerts, 0 fixed, 0 dismissed**: `py/url-redirection` ×3 (medium) in `constitutional_architecture/governance/dashboard/app.py`; `py/stack-trace-exposure` (medium) in `compiler/sdk/routes.py`, `compiler/api.py`. | `IMPLEMENTED_REAL` tool / alerts `UNFIXED` / CONFIRMED → EV-A01-008 |
| T4 | **Quality gates weaker than names.** black non-blocking (`:101` + `continue-on-error`), mypy never runs, flake8 syntax-only (`:70`), codecov `fail_ci_if_error: false` (`:55`). | `PARTIAL` / CONFIRMED → EV-A01-010 |
| T5 | **Local green masks CI red.** 5/5 tests pass in local venv against gitignored `data/evolution.db` (`*.db` → `.gitignore:43`); same 2 tests fail on fresh CI (`no such table: evolution_runs`). | `PARTIAL` / CONFIRMED → EV-A01-002 |
| T6 | **"Image published" ≠ "deployed."** Publish success on main (`Gate 5`, `v1.2 publish` = success at `1f26e42`); grep for `kubectl/helm/terraform/ssh/apply -f/argocd/gcloud/aws/deploy` across all workflows = **zero matches**. Boundary stops at GHCR. Direct GHCR listing `UNVERIFIED` (403 `read:packages`). | publish `IMPLEMENTED_BOUNDED` / deploy `UNIMPLEMENTED` / CONFIRMED → EV-A01-011 |
| T7 | **Failed runs lose their own evidence.** ci-cd red run artifacts = **0** vs green run = 1 (`security-report`) because upload at `ci-cd.yml:117` lacks `if: always()`; same structural pattern at `v1.1-release-gate.yml:65` (observation-client dist) and `:244` (dashboard dist) — conditional risk `INFERRED` (those builds passed on the red run so artifacts survived). | `PARTIAL` / CONFIRMED (ci-cd) → EV-A01-009 |

## 8. Run evidence at the audited commit

### 8.1 Workflow runs at head `6e1aa1a` (all `event=pull_request`, `attempt=1`, actor `Kimiti4`)

| Run | ID | Conclusion |
|---|---|---|
| autonomous-api CI/CD | `35742917271` | **failure** |
| v1.1 Release Gate | `35742917564` | **failure** |
| v1.2 Release Gate | `35742917356` | success (certification+publish skipped) |
| v1.3 Release Gate | `35742917389` | success (certification skipped) |
| v1.4 Release Gate | `35742917439` | success (certification skipped) |
| Identity Release Gate | `35742917505` | success (certification skipped) |
| CBC-1 Release Gate | `35742917243` | success (certification skipped) |
| CBC-1 Campaign A | `35742917285` | success |
| PR #1 (dynamic) | `35742915142` | success |

### 8.2 Job-level detail — the two red runs

**ci-cd `35742917271`:** `lint=success`, `security-scan=**failure**`, `test (3.11)=**cancelled**`, `test (3.12)=**failure**`, `test (3.13)=**cancelled**`, `multi-backend=success`, `build-docker=skipped` (main-only `:152`), `capability-runtime=skipped` (needs failed `test`).

**v1.1 `35742917564`:** `Gate 1=success`, `Gate 2=**failure**`, `Gate 4=success`, `aggregate=**failure**`, `Gate 4b/3/5=skipped` (needs propagation from Gate 2).

### 8.3 Root causes & attribution (every red classified)

| Red | Root cause (log-confirmed) | Attribution | Conf |
|---|---|---|---|
| `security-scan` | Bandit **B608** at `app/engine/backends.py:192` (Go-template f-string SQL); introducer `7b593d6` ∈ PR, ∉ main | **PR-CAUSED** | CONFIRMED |
| `test (3.12)` | `tests/engine/test_evolution_fail_closed.py::test_async_evolution_fails_closed_when_runtime_evaluation_fails` + `::test_runtime_failed_candidate_is_never_promoted` → `sqlite3.OperationalError: no such table: evolution_runs` (INSERT at `app/engine/evolution.py:69` against hardcoded `sqlite:///data/evolution.db`, `db.py:9`; tests never create schema). Suite: `2 failed, 167 passed`. | **PR-CAUSED** (both tests exist only on PR branch: file diff vs main = +58/−3; main's copy has just the 2 non-monkeypatched tests) + **environmental mask locally** (5/5 pass on gitignored DB) | CONFIRMED |
| v1.1 `Gate 2` / `aggregate` | Same 2 tests (`2 failed, 164 passed, 3 deselected`, `v1.1-release-gate.yml:110` suite); aggregate fails via needs-verdict logic `:459-470` | **PR-CAUSED** (downstream of same cause) | CONFIRMED |
| `test (3.11)`, `test (3.13)` cancelled | Default matrix fail-fast after `3.12` failed (`strategy` at `ci-cd.yml:19`, no `fail-fast` key anywhere in repo) | **EVIDENCE-GAP** — status of PR content on 3.11/3.13 = `UNKNOWN` (on main: both `success`) | CONFIRMED (mechanism) / UNKNOWN (cell status) |
| `build-docker`, `capability-runtime`, Gates 3/4b/5, certification×5, publish | `if: github.ref == 'refs/heads/main'` or `needs` ← failed job | **SKIPPED-BY-CONDITION** (not failures) | CONFIRMED |
| Local Go E2E on `:8000` | Windows TCP exclusion range `7973–8072` on this host | **ENVIRONMENTAL** (local-only; CI unaffected) | CONFIRMED |

Contrast set: **main `1f26e42` ci-cd run `35727803463` = all 7 jobs success**; all 38 checks green except 1 skipped (`Adjust Configuration`). Same runner image, same suite → failures are content-driven, not infrastructure-driven.

## 9. Artifact & evidence retention inventory

- ci-cd produces exactly **one** artifact step: `security-report` (`ci-cd.yml:117`, success-path only). Green run: 1 artifact (1,843 B). Red run: **0 artifacts**.
- v1.1 red run retained 3 artifacts (`dashboard-dist` 577,315 B, `observation-client-dist` 41,684 B, `platform-coverage` 14,036 B) — coverage uploads use `if: always()` (`:72,118,251`); dist uploads (`:65,244`) do not.
- Gates with `if: always()` uploads: cbc1/identity/v1.2/v1.3/v1.4 evidence archives + campaign logs (grep hits at each gate `:51/:60-61` region).
- Codecov upload is non-blocking and external (`:53-55`).
- Retention: dist/coverage `retention-days: 7`; evidence archives 90/180-day settings in gates (from workflow defaults).

## 10. Release boundary (EV-A01 scope item 7)

```
source (git) → CI (ci-cd + gates) → [main/tag + all jobs green + evidence manifest
  verdict CERTIFIED + empty failures + sha256 chain verified in Gate 5]
  → GHCR push (platform-api + dashboard) → ★ STOP ★
```

- Confirmed stop point: no workflow contains any deploy actuation (keyword grep zero matches; cross-ref PROD-016/PROD-017).
- Current main tip satisfies the full chain (`Gate 5=success`, `v1.2 publish=success`, all 5 certification jobs `success` at `1f26e42`) → **main is releasable-to-registry today; the audited PR state is not** (broken at ci-cd + Gate 2).
- GHCR package existence: `INFERRED` from successful publish jobs; direct listing `UNVERIFIED` (HTTP 403 — token needs `read:packages`).
- Audited state does **not** contain the CodeQL workflow; publishing therefore also does not depend on CodeQL.

## 11. Blocker register — EV-A01-001 … EV-A01-011

| ID | Finding | Taxonomy | Conf | Boundary affected | Evidence | State |
|---|---|---|---|---|---|---|
| **EV-A01-001** | Bandit B608 fails security-scan at audited commit (gate itself works) | gate `IMPLEMENTED_REAL`; fix `UNIMPLEMENTED` @ `6e1aa1a` | CONFIRMED | merge of PR #1; ci-cd run | `backends.py:192`; `7b593d6` ancestry; run `35742917271` | **PENDING-collaborator fix** (two-state: LIVE at audited state) |
| **EV-A01-002** | 2 PR-added fail-closed tests non-hermetic (fresh CI: `no such table: evolution_runs`); locally masked by gitignored DB | `PARTIAL` | CONFIRMED | ci-cd `test (3.12)`; v1.1 Gate 2 + aggregate | CI logs; file diff +58/−3; local 5/5 pass; `.gitignore:43` | **OPEN** (PR-side content) |
| **EV-A01-003** | Python matrix evidence gap: 3.11/3.13 cancelled by default fail-fast; ci-cd lacks concurrency control all gates have | `PARTIAL` (cells `UNKNOWN`) | CONFIRMED | version-coverage claim for PR content | `ci-cd.yml:19`; job conclusions; repo-wide no `fail-fast` key | **OPEN** |
| **EV-A01-004** | Non-reproducible installs: `uv.lock` gitignored, CI `pip install -e .` unpinned, `>=`-only constraints | reproducibility `UNIMPLEMENTED` | CONFIRMED | build/release supply chain | `.gitignore:72`; `ci-cd.yml:47,68,141,174`; `pyproject.toml` | **OPEN** |
| **EV-A01-005** | Supply-chain controls off: secret scanning, push protection, Dependabot updates all disabled; no `dependabot.yml`; no dep-vuln scan; mutable action/Docker pins | `UNIMPLEMENTED` | CONFIRMED | secret/vuln detection; supply chain | GitHub settings API; tree listing; workflow greps | **OPEN** (server-side — collaborator-owned) |
| **EV-A01-006** | Governance: no required review (no `pull_request` rule; direct pushes proven; zero merged PRs; no CODEOWNERS/SECURITY.md); same-day ruleset only blocks deletion/force-push | `PARTIAL` / `UNIMPLEMENTED` (review gate) | CONFIRMED / rule semantics `INFERRED` / merge-block `UNVERIFIED` | main-line integrity | ruleset `23822498` JSON; `1f26e42` `pulls=[]`; `gh pr list --state all` | **OPEN** (server-side) |
| **EV-A01-007** | Green gate ≠ certified: certification/publish skipped on PR context while runs report success; scoped suites never run platform tests | `PARTIAL` | CONFIRMED | release-decision integrity | `if:` conditions + run IDs §8.1; pytest scoping §2 | **OPEN** |
| **EV-A01-008** | CodeQL absent from audited tree (pending on main); 5 open medium alerts (3× url-redirection governance dashboard, 2× stack-trace exposure compiler); Analyze checks green anyway | tool `IMPLEMENTED_REAL` (pending); alerts `UNFIXED` | CONFIRMED | static analysis boundary | code-scanning API (5 open/0 fixed); `codeql.yml` triggers; check-runs | **OPEN alerts**; workflow itself = **PENDING-state** |
| **EV-A01-009** | Failure-path evidence loss: security-report upload lacks `if: always()` (dist uploads same pattern) | `PARTIAL` | CONFIRMED (ci-cd) / `INFERRED` (v1.1 dist) | audit-evidence retention | `ci-cd.yml:117`; artifacts count 0 (red) vs 1 (green); `v1.1:65,244` | **OPEN** |
| **EV-A01-010** | Quality gates weaker than advertised: black non-blocking, mypy never executed, flake8 syntax-only, codecov non-blocking | `PARTIAL` | CONFIRMED | code-quality gate depth | `ci-cd.yml:55,68,70,101` | **OPEN** |
| **EV-A01-011** | Release boundary stops at GHCR; zero CD; GHCR listing unverified (token scope) | publish `IMPLEMENTED_BOUNDED`; deploy `UNIMPLEMENTED` | CONFIRMED / listing `UNVERIFIED` | production deployment boundary | keyword grep zero; Gate 5 success @`1f26e42`; packages API 403 | **OPEN** (cross-ref PROD-016) |

## 12. Pending-state / two-state notes (never merged into audited classifications)

1. **Collaborator Bandit fix:** not pushed as of this audit (PR head still `6e1aa1a`; remote main lacks `7b593d6` anyway). Proven local fix exists as PR comment `#issuecomment-5779014985` (module-level SQL constants; bandit exit 0, byte-identical `main.go`, gate 25 passed/1 deselected). At `6e1aa1a` the defect remains live — EV-A01-001 stays OPEN until a new commit is verified.
2. **`codeql.yml` direct-pushed to main** (`1f26e42`, 2026-09-22T12:32+03:00, `pulls=[]`): not part of the audited tree; already executing against PR #1 (`Analyze (*)` = success on `6e1aa1a` via `pull_request` trigger from base). Surfaced the 5 open alerts (EV-A01-008).
3. **Repository ruleset `Protection`** created/updated same day (12:35Z / 14:48Z): content `CONFIRMED`, intent/attribution `UNVERIFIED`.
4. **`origin/main` vs audited state:** main = merge-base `95ca5f7` + CodeQL commit only; the audited PR does not contain it (merge would require reconciling histories — 20/1 divergence noted).

## 13. Positive controls (what is genuinely real)

- Minimal workflow token permissions (`permissions: contents: read`).
- Bandit gate **actually blocks** the run on MEDIUM/HIGH findings (proven by the red run).
- Fail-closed `needs` chains end-to-end (Gate 2 → integration → evidence chain → publish; `test` → `capability-runtime`/`build-docker`); aggregate verdict reads `needs.*.result` with `if: always()` (`v1.1:441,459-470`).
- Evidence-manifest verification (verdict + sha256 chain) **before** GHCR push — publish cannot bypass certification on main/tags.
- Real CI substance: Postgres 16 service integration (V1-07), real Docker runtime certification (`capability-runtime`), real Go backend compile+execute (`multi-backend`), reducer equivalence suite, campaign A (13×2) — all green at `6e1aa1a` where they ran.
- Gates cancel superseded runs (`cancel-in-progress: true` on all 7 gate workflows).
- Main tip fully green (37/38 checks success, 1 skipped) including all 5 certification jobs, Gate 5, and v1.2 publish.

## 14. Verification appendix (commands used)

```bash
git rev-list --left-right --count 6e1aa1a...origin/main        # 20 1
git merge-base --is-ancestor 7b593d6 origin/main               # not ancestor
git diff origin/main 6e1aa1a -- .../test_evolution_fail_closed.py  # +58 -3
gh api repos/.../actions/runs/{35742917271,35727803463,35742917564}/jobs
gh api repos/.../commits/{6e1aa1a,1f26e42}/check-runs?per_page=100
gh api repos/.../code-scanning/alerts?per_page=100            # 5 open, medium
gh api repos/.../commits/1f26e42/pulls                        # []
gh pr list --state all --limit 20                             # only #1 open
gh api repos/.../actions/runs/35742917271/artifacts           # count=0 (red)
git check-ignore -v autonomous-api/data/evolution.db          # .gitignore:43 *.db
venv: pytest tests/engine/test_evolution_fail_closed.py -v    # 5 passed (local)
```

*Internal analysis doc — working tree only, not tracked (per AGENTS.md .md policy).*
