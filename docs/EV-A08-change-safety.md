# EV-A08 — Change Safety

**Audit:** evidence-first production readiness, sequence EV-A01 → … → EV-A07 → **EV-A08 (this)** → EV-A09 Governance
**Canonical audited state:** `6e1aa1a` (PR #1 head; main `1f26e42`)
**Scope:** how safely the platform can be *changed* — schema/data migrations, backup/restore, deployment rollback, concurrent mutation of evolution state, atomicity of file persistence, API/config versioning and rotation, destructive operations, and the CI change-gates that stand in front of all of it. Read-only.
**Taxonomy:** `IMPLEMENTED_REAL / IMPLEMENTED_BOUNDED / IMPLEMENTED_SIMULATED / PARTIAL / UNIMPLEMENTED / UNKNOWN` · Confidence `CONFIRMED / INFERRED / UNVERIFIED`.

---

## STATUS: **FAIL**

There is no path to change the durable schema of this system without hand-editing production files, no restore procedure for the backups the docs advertise, no actuation behind the rollback constructs, and no serialization of concurrent evolution runs against a non-WAL SQLite database shared by singletons. The *semantic* layer (constitutional ISR) models migrations and rollbacks correctly — as invariants, never commands — and the file-backed constitution repo does atomic writes properly; but the **shipped API service** (`autonomous-api/`) cannot safely absorb a code change that touches data, cannot prove a backup is restorable, and can tear its own memory files on crash. CI gates exist and are real; they gate *tests*, not *change safety*.

Register: **EV-A08-001 … EV-A08-012**.

---

## 1. Surface inventory

| Change-safety area | Where it lives | Verdict |
|---|---|---|
| Schema migrations | `app/storage/db.py:44-47` `create_all` only; no `alembic.ini`/`migrations/` anywhere in project (probe) | `[UNIMPLEMENTED]` (001) |
| Observation DDL | `observation/sequences/schema.sql` claims "platform migration path"; none exists | `[PARTIAL]` — cross-ref EV-A07-001 |
| Backup | `autonomous-api/scripts/backup.sh` — live `cp` of SQLite, 30-day retention | `[PARTIAL]` (002) |
| Restore | **zero** restore scripts in `autonomous-api/` (probe) | `[UNIMPLEMENTED]` (002) |
| Rollback actuation | `constitutional_architecture/deployment/rollout/rollback_manager.py` history-append only; no CD (PROD-A01) | `[IMPLEMENTED_SIMULATED]` (003) |
| Rollback/migration *semantics* | `isr/model.py` `DeploymentIntent`/`DataMigrationIntent`; tests `test_r29_10_3c/3g` | `[IMPLEMENTED_REAL]` (invariant-not-command, by design) |
| Concurrent evolve | `api/routes.py:70-105` fire-and-forget `BackgroundTasks`; no single-flight lock (probe) | `[UNIMPLEMENTED]` (004) |
| SQLite durability | `db.py:12-20` — `check_same_thread=False`, no `journal_mode=WAL`, no `busy_timeout` (probe: 0 files set PRAGMA) | `[PARTIAL]` (004) |
| Atomic JSON writes | `models/memory.py`, `engine/memory.py:208-215`, `self_healing.py:615`, `policy_aware_generation.py:553`, `blueprint_marketplace.py:778` — `open(w)+json.dump` | `[PARTIAL]` (005) |
| Atomic file writes (positive) | `constitutional_architecture/governance/versioning.py:106-114` fsync+`os.replace`; `vertical_slice/app/store.py:45`; `tiannara/.../ledger.py` fsync | `[IMPLEMENTED_REAL]` (011) |
| Artifact materialization | `engine/backends.py:495-506` direct `open(w)` into final `output_dir` | `[PARTIAL]` (006) |
| Destructive ops | `/evolve/elite/clear-memory` one-shot wipe; middleware-protected, no confirm/backup/audit | `[PARTIAL]` (007) |
| Config change | `core/config.py` process-lifetime singleton; boot-time production validators | `[IMPLEMENTED_BOUNDED]` (008) |
| Feature flags | none in app (only tailwind in `reasoning-ui/node_modules`) | `[UNIMPLEMENTED]` (008) |
| Platform API versioning | no `/v1` prefix, no OpenAPI snapshot/diff in workflows | `[UNIMPLEMENTED]` (009) |
| CI change gates | 8 workflows: unit, multi-Python, bandit, Go certify, docker smoke, v1.x/CBC1 evidence chains | `[IMPLEMENTED_REAL]` (011) |
| Rollback of failure state | `evolution.py:86-88,120-128` — `db.rollback()` + status=`failed` on exception | `[IMPLEMENTED_REAL]` (011) |

---

## 2. Schema change is a foot-gun

### EV-A08-001 — No migration system; `create_all` cannot evolve an existing database; schema change fails at INSERT time with no upgrade path
`[UNIMPLEMENTED]` · Confidence **CONFIRMED** (probe + static)

- `init_db()` (`storage/db.py:44-47`) and every generated app's `init_db` (`builder.py:390-392`) call `Base.metadata.create_all` only. Project-wide scan: **no `alembic.ini`, no `migrations/versions/*.py`** (probe: `alembic_or_migrations: NONE`).
- **Probe (live SQLite):** create v1 `genomes(id, fitness_score)` → run v2 `create_all` with added `nullable=False` column → `inspect` shows column **absent** (`migration_create_all_altered: NO`) → ORM insert using the v2 model raises
  `OperationalError: table genomes has no column named new_required_col`.
  `create_all` only creates *missing tables*; it never `ALTER`s existing ones. First boot against a pre-existing `data/evolution.db` built by older code = hard failure on first write, with zero tooling to fix it.
- Same gap for the observation layer: `schema.sql` header claims deployments consume it "via the platform migration path" — that path does not exist (EV-A07-001).
- The platform's *own* readiness analyzer already knows this matters: `production_readiness.py:273,308` recommends "add schema migrations" / lists `database_migrations` as a required production capability — **for generated genomes**, while the control plane itself has none (`OPTIONS_CD_COMPLETE.md:554` still unchecked: "Database migration system (Alembic)").

---

## 3. Backup without restore is just a copy

### EV-A08-002 — Backup is a non-atomic live `cp` of SQLite to assumed paths; no restore script, no verification; docs claim automation while checklists say not done
`[PARTIAL]` · Confidence **CONFIRMED** (probe + static)

- `scripts/backup.sh:24-25`: `cp $APP_DIR/data/evolution.db $BACKUP_DIR/evolution_db_$TIMESTAMP.db` — **plain `cp` of a live SQLite file**. SQLite explicitly documents that a filesystem-level copy of a database under concurrent write can be torn/inconsistent; the safe APIs are `sqlite3 .backup`, `VACUUM INTO`, or a snapshotting filesystem — none used. No `PRAGMA wal_checkpoint` first; no integrity check (`PRAGMA integrity_check`) after.
- **Restore: none.** `restore_in_api: NONE`. No documented procedure, no script, no drill, no checksum verify of the backup after write (sha256sum absent from script).
- Path assumptions: `APP_DIR=/opt/evolution-engine` matches the guide's scp target but nothing installs there (EV-A05-010); step 2/4 `memory.json` target does not exist in repo layout (EV-A05-010) — always "not found, skipping"; guide's inline snippet (`DEPLOYMENT_GUIDE.md:383-416`) diverges from shipped script (different `BACKUP_DIR`, retention).
- Secret handling: step 4 copies `.env` with plain `cp`, no `chmod`/`umask` (EV-A05-012).
- **Truthfulness split (cross-ref EV-A03 style):**
  - `COMPLETE_TECHNICAL_DOCS.md:434` → "✅ **Backup Automation** - Daily backups with cleanup"
  - `OPTIONS_CD_COMPLETE.md:594` → "✅ **Complete Automation** - CI/CD pipeline, automated backups"
  - vs `CHECKLIST_COMPLETE.md:219`, `IMPLEMENTATION_COMPLETE.md:271`, `FINAL_SUMMARY.md:317`, `PRODUCTION_HARDENING.md:280`, `PRODUCTION_READINESS_CHECKLIST.md` → all still `[ ] Set up automated backups (cron job)` in the *same* tree.
  Cron is never installed by any script; "automation" is a file that would work if someone scheduled it — on a host that was never provisioned.

---

## 4. Rollback exists as story, not as action

### EV-A08-003 — `RollbackManager` records history only; no deployment unit, no CD, no image retention policy to roll back to
`[IMPLEMENTED_SIMULATED]` · Confidence **CONFIRMED** (static; re-affirms PROD-A01)

- `rollback_manager.py:31-55`: on rollback, appends `{reason, snapshot}` where snapshot is `{"version": r.metadata.get("message",""), "status":"stable"}` (`:62-66`) — **no artifact pull, no traffic shift, no DB restore**. Returns `RUNNING` with a message string.
- Workflows: no deploy actuation keywords anywhere (PROD-A01 inventory); `build-docker` tags `evolution-engine:${{ github.sha }}` and smoke-tests locally, never pushes a rollback-capable release channel. **No `latest`/`stable` pointer, no previous-tag retention documented.**
- The *semantic* layer is honest and better: `DeploymentIntent.rollback_*` fields are deliberately **invariants, never commands** (`test_r29_10_3g` docstring: "Rollback reuses C's rollback-as-invariant pattern… no rollback_command, no scripts, no kubectl"). That is a design choice for the ISR gene model — but it leaves the *platform* with no runnable counterpart, and `RollbackManager` is the only Python class that even pretends.

---

## 5. Concurrent change of evolution state

### EV-A08-004 — No single-flight control on evolution runs; shared singletons + shared output tree + non-WAL SQLite = racing writers
`[UNIMPLEMENTED]` · Confidence **CONFIRMED** (probe + static)

- `POST /evolve/start` (`routes.py:70-75`) and `/evolve/elite/start` (`:100-105`) do `background_tasks.add_task(...)` and return immediately. Probe: **`evolve_single_flight_lock: ABSENT`**. No `asyncio.Lock`, no active-run table check, no 409-if-busy. Two authenticated clients (or a retry loop) start N runs in parallel.
- Shared mutable singletons: module-level `evolution_engine` / `elite_engine` (`routes.py:22-23`); `set_websocket_callback` / `set_dispatcher` re-assign on every start (`:73-74`, `:103-104`) — last writer wins; earlier run's events can be redirected mid-flight.
- Shared artifact path: `build_genome_output(best_genome)` defaults to **`output/generated_api`** (`builder.py:498`) — concurrent/overlapping runs overwrite the same tree file-by-file with no staging (006).
- Database: SQLite with `check_same_thread=False` (`db.py:14`), **no `journal_mode=WAL`, no `busy_timeout`** (probe: 0 files under `app/` set these PRAGMAs). Parallel runs → interleaved `SessionLocal` writers → classic `database is locked` / lost-update territory under load. Pool of 5+10 connections multiplies concurrent writers on one file.
- `POST /evolve/sync` (`:95-98`) blocks a worker thread with the same unlocked engine path — sync + async runs can overlap too.
- Failure handling *within* a run is good (011); the gap is **cross-run** mutual exclusion.

---

## 6. Files that must not tear, but can

### EV-A08-005 — Elite memory, self-healing logs, blueprints, policies: `open("w")` + `json.dump` with no temp+rename — crash mid-write destroys prior content; loader silently returns `{}`
`[PARTIAL]` · Confidence **CONFIRMED** (probe)

Writers (all direct truncate-on-open):
| File | Lines |
|---|---|
| `app/models/memory.py` | `:12-14` `save()` |
| `app/engine/memory.py` | `:208-215` `_save()` (swallows exceptions to log only) |
| `app/engine/self_healing.py` | `:615-616` |
| `app/engine/policy_aware_generation.py` | `:553-554` |
| `app/engine/blueprint_marketplace.py` | `:778-779` |

**Probe:** open `w`, `json.dump`, flush, truncate mid-file, close → `json.load` → `JSONDecodeError`; prior content **already gone** (Python `"w"` truncates at open). `models/memory.py:5-10` `load()` then `except: return {}` — **silent total loss**, no backup fallback, no `.bak` sibling.

Contrast (positive, 011): `FileBackedConstitutionVersionRepository._write` (`versioning.py:106-114`) does tmp → `flush` → `os.fsync` → `os.replace` — probe: `HAS_fsync+os.replace`. Same repo learned the pattern; the evolution-memory writers did not.

### EV-A08-006 — `materialize()` writes compiled artifacts file-by-file into the final output directory with no staging transaction
`[PARTIAL]` · Confidence **CONFIRMED** (static probe)

`backends.py:495-506`: `os.makedirs(output_dir)` then per-file `open(full_path,"w")`. Probe: `materialize_staging_rename: NO`. Crash or kill mid-loop leaves a **half-written tree** at the path callers treat as complete (`compile_and_materialize` returns it; evolution emits `building_best` with `output_path`). No write-to-tmpdir + `os.replace` directory swap, no completeness manifest, no checksum re-verify on read.

---

## 7. Destructive operations and change controls

### EV-A08-007 — `POST /evolve/elite/clear-memory` permanently wipes learned state in one call; auth-gated by middleware deny-list, but no confirmation, backup, soft-delete, or audit trail
`[PARTIAL]` · Confidence **CONFIRMED** (static)

- `routes.py:110-112`: `elite_engine.clear_memory()` → resets in-memory structures + `_save()`s empty state (`elite_evolution.py:83`, `memory.py:217-230`). Irreversible from the API's point of view (no undelete, no export-first).
- Auth: route has no `Depends(require_auth)`, but `SecurityHeadersMiddleware` enforces `PROTECTED_CONTROL_PREFIXES = ("/evolve", ...)` (`security.py:24,31-45`) — **deny-by-default comment at `:21-23` is a real control** (positive, 011). So it is authenticated whenever an auth provider is configured; fail-closed 401 otherwise.
- Still missing the *safety* half of change safety: typed confirmation (e.g. require `{"confirm":"CLEAR"}`), automatic snapshot/export of memory before clear, structured audit event beyond loguru, and rate-limit class distinct from generic `/evolve` (EV-A04 rate-limit behavior carries over — over-limit is 500, not a clean 429).
- No other soft-delete/versioning on `GenomeRecord`/`EvolutionRun` rows: no `deleted_at`, no retention job, no `DELETE` endpoint found — rows accumulate forever (bounded growth is a different concern; the point is **no undo** for anything that *does* delete).

### EV-A08-008 — Config changes require process restart; singleton freezes first-read forever; no feature flag to disable a bad change
`[IMPLEMENTED_BOUNDED]` · Confidence **CONFIRMED** (static)

- `get_settings()` (`config.py:79-84`) caches `_settings` with no TTL/refresh; `.env` is read once at first `Settings()`. Rotating `ADMIN_API_KEY`/`SECRET_KEY` ⇒ full process restart. Production boot validators (`:57-66`) are a **good** fail-closed gate (positive).
- No hot-reload, no SIGHUP handler, no staged config drain — acceptable *if* documented as "restart to change config"; DEPLOYMENT_GUIDE does not state a rotation procedure (restart is implicit only).
- **Feature flags: none** in application code (probe; only CSS toolchain hits). A bad rollout has no `ENABLE_X=0` kill switch — recovery is redeploy-previous (which does not exist, 003) or revert+rebuild.
- `extra="ignore"` on Settings (`:72`): typos in env vars are **silently dropped** — a config change that misspells `ADMIN_API_KEY` boots with empty key (dev) or fails production validator only for the exact names checked; misspelled `RATE_LIMIT_GENERAL` falls back to default 100 without warning. Silent-ignore undermines change feedback.

---

## 8. Wire compatibility under change

### EV-A08-009 — Platform HTTP API is unversioned; no OpenAPI snapshot/diff gate; only *generated* services get `/api/{version}` prefixes
`[UNIMPLEMENTED]` · Confidence **CONFIRMED** (static)

- Control-plane routers: `APIRouter()` with no prefix version (`routes.py:20`), observation `prefix="/observation"` — **no `/v1`**, no `Accept` versioning, no sunset headers. `APP_VERSION` is cosmetic in `/health` and OpenAPI `version=`.
- Contrast: **generated** genomes correctly lower `api_version` into route prefixes (`builder.py:9`, `backends.py:182`) and CI even flake-gens a template (`ci-cd.yml:71-96`) — the *product* versioned its outputs but not its own surface.
- CI: no job diffs `openapi.json` between base and head; no contract tests pinning response shapes of `/evolve/*` or `/observation/*` against a golden file (observation suite asserts contract *models*, not HTTP route snapshots).
- Contracts layer (EV-A07) has `schemaVersion` + version error codes (unused — EV-A07-008) — the *hooks* for negotiation exist; the *URL/header policy* does not.

---

## 9. What is actually solid

### EV-A08-010 — CI change gates, failure-state persistence, deny-by-default control prefix, and the semantic migration/rollback model are real
`[IMPLEMENTED_REAL]` · Confidence **CONFIRMED**

- **Eight workflows** on `main`/PR: `ci-cd.yml` (3× Python matrix, bandit `-ll`, multi-backend Go compile+execute, docker smoke, circuit-breaker runtime cert) plus versioned evidence gates (`v1.1`–`v1.4`, `cbc1`, `identity`) that archive `release/evidence/` with `aggregate.yaml` verdict checks (`v1.4-release-gate.yml:68-88` refuses non-`CERTIFIED`). PR #1 has a ruleset on the remote (id 23822498, EV-A01 track). These are genuine change gates — they just don't cover migrations/restore/rollback (above).
- **Evolution failure handling:** per-generation genome batches commit atomically with `db.rollback()+raise` on error (`evolution.py:86-88`); top-level exception marks `EvolutionRun.status="failed"` with `completed_at` + error history (`:120-128`); `build_error` degrades to `failed` without lying `completed` (`:113`). Seed RNG restored in `finally` (`:129-130`).
- **Atomic constitution versions:** `FileBackedConstitutionVersionRepository` — probe confirmed `fsync`+`os.replace`; covered by Phase 28 durability tests (AGENTS).
- **Hash-chained append-only ledgers** (`tiannara/.../ledger.py` fsync paths; CBC1 infra-storm independent ledger with tamper tests) — append discipline where it matters most (evidence).
- **`PROTECTED_CONTROL_PREFIXES`** deny-list with an explicit comment that new `/evolve*` routes cannot silently go public (`security.py:21-24`) — the right default for destructive control plane (even though EV-A04 showed `/stream` and headers issues elsewhere).
- **Semantic layer honesty:** migration/rollback genes structurally cannot carry technology (`assert_migration_technology_agnostic`, `DEPLOYMENT_MECHANISM_TERMS` lint); rollback-as-invariant is tested (`test_r29_10_3c/3g`) — the ISR does not pretend to execute what it cannot.
- **Temp code execution hygiene:** `executor.py` uses `NamedTemporaryFile` + `finally: os.remove` (`:7-24`).
- **Production boot validators** fail closed on missing `ADMIN_API_KEY`/`SECRET_KEY` (`config.py:57-66`, `security.py:171-176`) — config *changes* that weaken security are rejected at process start when `ENVIRONMENT=production`.

---

## 10. Verification appendix (evidence log)

- **Probe** `Temp/opencode/ev08/ev08_probe.py` (cwd=temp; system Python 3.14):
  - `migration_create_all_altered: NO` · `migration_v2_select_new_col: would fail` · `migration_orm_v2_insert: FAILED OperationalError: table genomes has no column named new_required_col`
  - `torn_memory_json: parse FAILED JSONDecodeError — prior content GONE` · `memory_load_on_torn: returns {}`
  - `filebacked_atomic_write: HAS_fsync+os.replace`
  - `evolve_single_flight_lock: ABSENT` · `evolve_clear_memory_auth: NO require_auth on route` (middleware prefix still applies — see 007)
  - `restore_in_api: NONE` · `alembic_or_migrations: NONE` · `materialize_staging_rename: NO` · `wal_journal_mode_files: 0` · feature flags in app: none (node_modules tailwind only)
  - Note: first run timed out mid-`rglob` across `.venv`; re-run `-u` captured all stages before that. Results above are from the successful stage-complete portion + follow-up targeted scan.
- **Static reads:** `storage/{db,models}.py`, `scripts/backup.sh` (full), `rollback_manager.py` (full), `evolution.py` (full), `routes.py` (full), `main.py`, `core/config.py` (full), `middleware/security.py` (full), `backends.py:495-517`, `builder.py:380-393,498`, `engine/memory.py:208-230`, `models/memory.py`, `self_healing.py:615`, `governance/versioning.py:106-114`, `DEPLOYMENT_GUIDE.md` backup section, `ci-cd.yml` (full), `v1.4-release-gate.yml` (full), `cbc1-release-gate.yml` (head), `test_r29_10_3c_data_migrations.py` (docstring), `test_r29_10_3g_deployment_rollout_rollback.py` (docstring).
- **Greps:** `create_all|drop_all` (10 hits, all create-only); `journal_mode|PRAGMA|busy_timeout` (0); `os.replace` in app writers (0 — only constitution + vertical_slice); restore/migration scripts; `Backup Automation` claims vs checklist boxes; `PROTECTED_CONTROL_PREFIXES`; `BackgroundTasks.add_task`.
- **Glob:** no `alembic*`, no `migrations/**`, no `feature*flag*` in app, no `restore*.sh` under `autonomous-api/`.
- **Not probed:** actual concurrent dual `/evolve/start` against live uvicorn (static lock-absence + singleton analysis sufficient; live race would need two long runs); real torn-backup under write load (SQLite docs + plain `cp` line are conclusive); restore drill (nothing to run).

---

## 11. Conclusion & next gate

**FAIL.** Change safety is the weakest link in the sequence so far because it is *entirely load-bearing on operators doing the right thing manually*, while the docs variously claim the automation exists:

1. **Schema:** ship Alembic (or equivalent) + baseline migration before any `models.py` column touches prod; wire observation `schema.sql` into the same runner (closes EV-A07-001's third layer).
2. **Backup:** replace `cp` with `sqlite3 .backup`/`VACUUM INTO`, add `sha256` + `PRAGMA integrity_check`, write a **restore script + drill** (restore-to-temp + open + row-count); fix `memory.json` target; stop claiming ✅ until cron+path exist.
3. **Rollback:** either implement image promote/demote (GHCR `previous` tag policy + compose pin) or strike `RollbackManager` as non-operational in docs; keep ISR rollback-as-invariant (it is correct *as semantics*).
4. **Concurrency:** single-flight guard on `/evolve*` (409 when a run is active), per-run output dirs, `PRAGMA journal_mode=WAL` + `busy_timeout` on SQLite.
5. **Atomicity:** adopt the constitution repo's tmp+fsync+`os.replace` pattern for all five JSON writers; stage `materialize()` into a temp dir then rename.
6. **Destructive ops:** confirmation body + pre-wipe export on `clear-memory`; distinct audit event.
7. **Compat:** version the control-plane API (at least `/v1`) or freeze+snapshot OpenAPI in CI; document config-restart semantics; fail loudly on unknown settings keys in production.

**NEXT GATE: EV-A09 — Governance** (final in sequence).

*(Sequence: EV-A09 → close-out. Bandit-fix verification track remains separate; PR #1 head last known `6e1aa1a`, main `1f26e42`.)*
