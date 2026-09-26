# EV-A02 — Artifact Correctness

- **State audited:** `6e1aa1a` (PR #1 head), fetched tree clean.
- **Method:** READ-ONLY, NON-MUTATING, EVIDENCE-FIRST, FAIL-CLOSED. Code-level reads + controlled generation experiments in a temp sandbox (`C:\Users\user\AppData\Local\Temp\opencode\ev02`, outside the repo); CI log/run evidence where applicable. No repository file was created, modified, or deleted.
- **Taxonomy:** `IMPLEMENTED_REAL` / `IMPLEMENTED_BOUNDED` / `IMPLEMENTED_SIMULATED` / `PARTIAL` / `UNIMPLEMENTED` / `UNKNOWN`.
- **Confidence:** `CONFIRMED` / `INFERRED` / `UNVERIFIED`.
- **Two-state discipline:** `6e1aa1a` is canonical. The pending Bandit remediation (module-level SQL constants) is NOT incorporated; at this state `backends.py:207` still carries the `// # nosec B608` template form. CodeQL/ruleset/main-tip items stay EV-A01 §12 pending-state.

---

## 0. STATUS

**STATUS: FAIL** — *bounded to the trust chain, not to generation quality.*

The generation core is **real and deterministic**: the same architecture dict produces byte-identical Python (8 files) and Go (2 files) artifacts (experiments E1/E2, `CONFIRMED`), the compiler boundary fails closed on drift, and the Python backend's runtime verification is genuine multi-layer Docker probing. But the audited question — *"can the artifact be trusted as the input to subsequent verification, promotion, and deployment stages?"* — is answered **NO** at three specific joints: (1) **static-evidence mode can certify an artifact that cannot even compile** (E7+E8: `build_ok=True`, `static_score=4.274` on an artifact where both `main.py` and `services/models.py` fail `py_compile`); (2) **promotion binds the genome, not the artifact** — no digest, no output-path, no identity link between the verified candidate directory and the promoted default directory, which can diverge by stale files (E3); (3) the **Go backend's non-runtime evidence is a stub** (`capability_evidence = {"verified": True}`, `candidate_evaluator.py:76`), so default-settings evolution toward the Go target promotes on heuristic scores only.

---

## 1. Artifact pipeline (as built, not as documented)

```
genome (Genome dict, genome.py)
  → CompilationRequest (backend_contract.py:91-111; validate_architecture :52-77, fail-closed on unknown keys/types/missing services|auth|database)
  → capability plan (capability_semantics.py:32-43 → capability_contract.assess_genome :51-116; unmapped ⇒ ValueError, backends.py:50-53)
  → backend.compile (PythonFastAPI :35-87 | GoHTTPBackend :91-139)
  → CompiledArtifact {backend_id, files, metadata{language, framework, schema, architecture_hash sha256 (backends.py:479-486)}}
  → materialize (backends.py:495-506: makedirs + sequential open("w"); NO atomicity, NO stale-file cleanup, NO metadata written to disk)
  → filesystem artifact under output_dir (default "output/generated_api", builder.py:498 — CWD-relative)
  → Docker build (docker_runner.py:21, `docker build -t <container_name> <dir>`; no .dockerignore emitted)
  → runtime container (random host port 8001-9000, docker_runner.py:18; fixed 3 s readiness sleep :32)
  → evaluator probes (candidate_evaluator.py:102-213; CAPABILITY_EVIDENCE_MODE-gated probes return 404 unless env=1)
  → evidence dict (genome_hash = sha256(genome.encode() sorted), candidate dir = <hash[:16]>)
  → evolution: fitness from evidence (evolution.py:45-61 fail-closed), GenomeRecord rows (all individuals), best_genome
  → promotion build: build_genome_output(best_genome, target) → CWD "output/generated_api" (evolution.py:100)
  → EvolutionRun row (best_genome JSON only; NO output_path, NO digest — models.py:26-39)
  → PUBLISH: generated artifacts are never published (no registry job anywhere); platform self-images go to GHCR (v1.1 Gate 5 :331-406, v1.2 :130+)
```

Lifecycle entry note: the declared source-of-truth endpoint `/observation/isr` returns **503 until `CanonicalIsrAccessor` is bound** (`observation_routes.py:131-137`) — at the audited state the ISR accessor is **UNIMPLEMENTED**; the Genome/evolution system is the de-facto source of truth.

## 2. Source → artifact determinism

| Check | Result | Evidence | Conf |
|---|---|---|---|
| Same input → same Python artifact | **Byte-identical** (8 files incl. `services/*`) | E1: two `build_genome_output` runs into separate temp dirs, recursive byte compare = identical | CONFIRMED |
| Same input → same Go artifact | **Byte-identical** (`go.mod`, `main.go`) | E2, same method; matches in-repo test `test_backends.py:343-352` | CONFIRMED |
| Stable ordering | Yes — `services_imports`/route order follow genome list order; Go OpenAPI doc `json.dumps(..., sort_keys=True)` (`backends.py:457`); mutation sorts services (`mutation.py`) | code + E1 | CONFIRMED |
| Timestamps / random IDs / host paths in files | **None** — file content is a pure function of genome fields; no `datetime`/`uuid`/`getcwd` in emitted text | all 10 generated files inspected in E1/E2 | CONFIRMED |
| Genome-level randomness | `genome_id = uuid4()` at construction (`genome.py:36`) — not seeded; candidate dir + DB records therefore differ per instantiation even for identical gene content | code + `candidate_evaluator.py:59-60` | CONFIRMED |
| Seeded evolution reproducibility (gene space) | **CONFIRMED**: `random.seed(42); run_synchronous(1,4)` ×2 → identical best-gene (excl. genome_id/lineage), identical history, identical fitness | E5 | CONFIRMED |
| `run_id` | `uuid4()` regardless of seed (metadata only) | `evolution.py:65` | CONFIRMED |

Classification: determinism `IMPLEMENTED_REAL` (bounded: genome_id/run_id identity streams are unseeded by design).

## 3. Artifact completeness

- **Python file set** (full, asserted by `test_backends.py:44-59`): `main.py, database.py, security.py, requirements.txt, Dockerfile, services/__init__.py, services/models.py, services/{svc}.py`. No `.dockerignore`, no `README`, no env-sample — bounded.
- **Go file set**: only `go.mod` + `main.go` (`backends.py:137`) — **no Go Dockerfile, no go.sum**. `go.sum` is generated on the fly by `go mod tidy` in the CI test (`test_backends.py:262`). Raw-artifact build check, reproduced locally: `go build` **fails** with `missing go.sum entry for modernc.org/sqlite`; after `go mod tidy` (network) it **builds** (rc=0, binary produced). → the Go artifact is **not buildable as materialized**; buildability requires toolchain + network + a tidy step.
- **No references to absent files**: all imports resolve within the emitted tree (`from services.*`, `from database import ...`); verified by E1 tree + E7 compile attempts.
- **Dependencies present**: `requirements.txt` generated per genome (tracing ⇒ opentelemetry trio, jwt ⇒ PyJWT, db driver per engine) — but all `>=`-only (`builder.py:489-495`), so the *installed* closure is time-varying (see §9).
- **Placeholders masquerading as implementations:** none in the Python backend (every emitted capability has a working body). **Go backend: the evaluator's static "verification" is a placeholder** — `capability_evidence = {"backend_id", "verified": True}` with no inspection (`candidate_evaluator.py:76`) — see EV-A02-010.
- **Committed exemplars are stale by layout**: 52 tracked files under `generated/` — `testshop`/`monolithshop` (DDD layout: `api/application/domain/infrastructure`) and `observatory` (Elixir: `lib/observatory/*.ex`). The audited builder emits a flat `main.py + services/` tree; **these exemplars cannot be produced by the current builder** and no CI job regenerates/diffs them (grep: no such job). Drift between exemplars and builder is silent.

## 4. Source/artifact consistency

| Check | Result | Evidence | Conf |
|---|---|---|---|
| Backend routing consistent | `target` carried end-to-end; evidence `backend_id` = target; wrong-target/unknown-backend ⇒ ValueError (fail-closed, tested `test_backends.py:75-98`) | code + tests | CONFIRMED |
| `architecture_hash` bound across backends | sha256 of canonical architecture JSON, equal for Python/Go of same architecture (asserted `test_backend_neutral_evolution.py:31-40`) | code + test | CONFIRMED |
| **Hash persisted with artifact?** | **No.** `materialize()` writes files only; `architecture_hash`/`backend_id`/schema exist in memory only (`backends.py:475-506`). No manifest file on disk. | code | CONFIRMED |
| Selection fidelity (requested ⇔ present) | `inspect_artifact` checks presence/absence per capability (e.g. `CORSMiddleware`, probe routes, negative checks when not requested) (`capability_evidence.py:32-121`) — real string-level fidelity checks | code + E1 inspection | CONFIRMED |
| **logging_level fidelity hole** | `assess_genome` marks `logging_level` *implemented* for DEBUG/INFO/WARNING/ERROR (`capability_contract.py:104-109`) but `inspect_artifact` **never inspects it** → contract loop marks it requested/unverified (`capability_evidence.py:123-125`) → **`contract_ok` is structurally False for any genome with a log level** (runtime score capped at 0.90, "probes did not fully pass" error recorded, `candidate_evaluator.py:210,214`) while the capability *is* correctly emitted | code + E8 output (`failed_or_unverified: ['logging_level']`, 13/14 "verified") | CONFIRMED |
| Go unselected surface | Go always emits `/health` + `/openapi.json` even when `health_endpoints=False` (extra surface, not requested) | `backends.py:284-291` | CONFIRMED |
| **Backend posture divergence (same capability, different security)** | Python auth is fail-closed (401 unless env creds set, `builder.py:411-427`); Go auth is **fail-open with shipped default credentials**: `API_KEY→"generated-api-key"` (`:301`), basic `→"generated-user"/"generated-pass"` (`:317-321`), `JWT_SECRET→"generated-jwt-secret"` (`:350`). The CI Go test itself signs with that default secret (`test_backends.py:289`). Same genome ⇒ different security behavior by backend. | code | CONFIRMED |
| Stale-artifact possibility | materialize has no cleanup → **E3: rebuild without `orders` into the same dir left `services/orders.py` behind** | E3 | CONFIRMED |

## 5. Build correctness

- **Python:** "build_ok" is set the moment `compile_and_materialize` returns — i.e., **files were written** (`candidate_evaluator.py:70-71`). There is **no per-candidate syntax/type/compile check** anywhere: the CI lint smoke flake8s a *single fixed representative genome* (`ci-cd.yml:70,99`; selectors E9,F63,F7,F82 — E9 catches syntax, but only for that fixed genome, not each candidate). E7 proves a genomewise-valid architecture (`services: ["users orders"]`) yields files that **fail `py_compile`** in both `main.py` and `services/models.py`, while passing every builder gate.
- **Go:** real compile+execute exists only in CI for one fixed genome (`test_backends.py:231-340`: `go mod tidy` → `go build` → run on **:8000** → health/root/openapi/JWT-401/POST-201/list/tampered-401). Evolved Go candidates are never compiled in the pipeline (evolution → static evidence, §6).
- **Docker (platform + generated):** `docker build` from candidate dir with **no `.dockerignore`** → stale files enter the image via `COPY . .` (`builder.py:515`). Generated Dockerfile: mutable `python:3.11-slim`, runs as **root**, no healthcheck (`:511-517`). Readiness = fixed `sleep(3)` (`docker_runner.py:32`), not a probe → flaky-startup false negatives possible. Port = `random.randint(8001,9000)` → collision risk under parallel evaluation.
- **What a green build establishes:** file materialization only (Python) / compile of one fixed genome (Go) / image build (platform). It does **not** establish the candidate's claimed properties — those require the runtime layer (§6).

## 6. Runtime artifact correctness (layer separation)

| Layer | Established by | Status at audited state |
|---|---|---|
| Build success | `docker build` rc=0 | real, but see §5 (stale context, root, no healthcheck) |
| Container startup | `sleep(3)` + first HTTP | **bounded** (no readiness loop; 3 s assumption) |
| Endpoint availability | `/health` probe (presence OR absence asserted per genome, `:104`) | real |
| Functional behavior | OpenAPI prefix-subset check (`:105-111`); **full CRUD only for `services[0]`** (`:113-127`: create/list/read/update/404/validation-422/delete) | real, **bounded to one service** |
| Capability behavior | gated probes: timeout-504, retry≥2, circuit open/recover, cache hit/invalidate/TTL, rate-limit 429-after-100 (`:138-202`); probes 404 unless `CAPABILITY_EVIDENCE_MODE=1` (can't be faked statically) | real (Python backend only) |
| Failure behavior | auth-boundary 401/403 anonymous (`:115-116`); not-found 404; validation 422; circuit/transient paths probed | real |
| **Static-evidence layer** | `use_docker=False` **or** `runtime_supported=False` (Go) → `build_ok` + `static_score = calculate_fitness` (pure genome-field heuristic, `fitness.py:62-72`) + substring inspection | **E8 CONFIRMED: certifies a non-compilable artifact** (`build_ok=True, static_score=4.274, 13/14 "verified"`). And for the Go target this is the *default* path even with `use_docker=True` (`:81-84`) — so **Go-target evolution promotes on heuristics by default** |
| Cross-layer leakage in scoring | `runtime_score` weights health/openapi/auth/crud/contract (`:28-29`); contract includes the always-failing `logging_level` (§4) → max 0.9 for any logging genome | CONFIRMED |

Classification: Python runtime verification `IMPLEMENTED_REAL` (bounded depth); static layer `IMPLEMENTED_SIMULATED`-grade evidence with `IMPLEMENTED_REAL` mechanism; Go runtime `UNIMPLEMENTED` in the pipeline (CI-fixed-genome only).

## 7. Artifact isolation

| Risk | Finding | Conf |
|---|---|---|
| Repo-local state changing *artifact content* | **None found** — content is pure f(genome fields) (E1/E2); `data/evolution.db` (EV-A01-002) affects evolution tests, not generated files | CONFIRMED |
| Generated app consuming host state at use-time | `DATABASE_URL` default = `sqlite:///./generated.db` **CWD-relative** (`builder.py:381`); pre-existing `generated.db` changes behavior. Evaluator pins it via `-e` (clean) | CONFIRMED (design) |
| Env/host-path leakage into artifact *files* | None — env accessed only via runtime `os.getenv`/`os.Getenv` references; no absolute paths in emitted text (E1/E2) | CONFIRMED |
| Env/host-path leakage into *records* | **Yes:** evidence `artifact_path` = host path `output/candidates/<hash16>` is embedded in `GenomeRecord.genome_data` via `payload["evaluation"]` (`evolution.py:81-82`, `models.py:11`) — host topology persisted in the DB | CONFIRMED |
| Previous builds contaminating next | **Yes** — E3: stale `services/orders.py` persists in the output dir; `materialize` never removes (backends.py:495-506); combined with no-`.dockerignore` + `COPY . .`, stale files enter Docker images and the promoted tree (§8) | CONFIRMED |
| Default output dir | `output/generated_api` CWD-relative (`builder.py:498`); evolution's promotion build uses this default (`evolution.py:100`) → **last run wins** at a fixed, uncleaned location; no per-run identity on disk | CONFIRMED |
| Candidate dir isolation | content-addressed `genome_hash[:16]` subdirs (`candidate_evaluator.py:60`) — the *verification* side is clean per genome (unless 64-bit prefix collision) | CONFIRMED |

## 8. Promotion/publish integrity

1. **Verified artifact** = `output/candidates/<hash16>` (content-addressed, clean).
2. **Promoted artifact** = rebuild of the winning genome into `output/generated_api` (default dir, no cleanup) — `evolution.py:100`.
3. **Identity link between (1) and (2): NONE.** No digest is computed, stored, or compared. `EvolutionRun` stores `best_genome` JSON only (`models.py:26-39` — no `output_path`, no hash); the returned `result["output_path"]` (`:108`) is not persisted. `GenomeRecord` stores genome+evidence (incl. host path) but no artifact digest.
4. **Consequence (demonstrated, not hypothetical):** E3 shows a rebuild into a non-cleaned dir diverges from a clean build. If the promotion dir retained a stale file from an earlier candidate, **the promoted tree ≠ the verified tree** while no check exists that could detect it. Content identity holds *only* under the (true) determinism invariant plus a clean directory.
5. **genome_id identity is not unique:** mutation children **inherit the parent's genome_id** (E4; `mutation.py` child = `Genome(data)` where `data` carries `genome_id`; `genome.py:48`), while crossover children get a fresh uuid → `genome_id` is not a stable identity; `genome_hash` (which includes genome_id) is therefore not a pure content address of the architecture; `select_parents` tie-breaks on `genome_id` membership (`population.py`).
6. **Can an artifact be replaced after verification?** Yes — nothing prevents re-running `build_genome_output` into either directory later; there is no signed/immutable artifact representation.
7. **Promotion basis:** genome state (rebuildable), **not** artifact identity.

Classification: promotion identity `UNIMPLEMENTED`; promotion control flow `IMPLEMENTED_REAL` (fail-closed fitness gating `evolution.py:45-61,83` is genuine — a runtime-failed candidate scores 0 and cannot win, per the PR fix).

**Publish (platform only):** Gate 5 verifies the evidence chain (verdict `CERTIFIED` + empty failure sets + per-gate `evidence_sha256` re-hash, `v1.1-release-gate.yml:331-384`) — real — then pushes `dashboard` (context = repo root) and `platform-api` with tags `branch | tag | sha | latest(default-branch)`; **no digest references**; images are built from the source tree, not from any verified artifact bytes. Generated artifacts: **never published** (no registry job exists; cross-ref PROD-016). "Published" = source-committed code rebuilt under `packages: write`; the exact-tested-artifact=published invariant holds only by source-tree determinism, and GHCR tag mutability means consumers pinning tags follow the latest rebuild of the tag (`latest`/branch tags are mutable). Direct package enumeration `UNVERIFIED` (403 `read:packages`).

## 9. Reproducibility

| Scenario | Verdict | Evidence |
|---|---|---|
| Fresh checkout, CI | Python generation: deterministic; *installed dependencies* time-varying (all `>=`, no lockfile in generated or platform image — `builder.py:489`, `autonomous-api/Dockerfile` `pip install .`; EV-A01-004). Go: requires `go mod tidy` + network (`go.sum` not in artifact) — CONFIRMED locally (build fails pre-tidy, passes post-tidy). | E1/E2 + go experiment |
| Clean workspace | Artifact content: fully reproducible (E1/E2). Promotion dir: **not** reproducible as a tree if previously used (E3). | E1/E2/E3 |
| CI environment | Same content; toolchain pins: Python 3.11/3.12/3.13 matrix, Go `1.27.x` (minor-range), generated app pinned `python:3.11-slim` (mutable tag). | workflows |
| Local environment | Reproducible except: Go execution on `:8000` blocked by host TCP exclusion `7973–8072` (environmental, not repo); Docker daemon state for runtime probes; gitignored `data/evolution.db` masks evolution tests (EV-A01-002) but does not mask generation. | EV-A01 + E5 |
| Repeated generation | Byte-identical (E1/E2); repeated *evolution* with seed: gene space identical (E5), identity streams (genome_id/run_id) differ by design. | E1/E2/E5 |
| Dependence on local ignored state | Generation: none confirmed. Test-suite outcomes: yes (EV-A01-002). Candidate/promotion dirs live under ignored `output/` → local history of artifacts is invisible to git and to the record layer. | CONFIRMED |

## 10. Failure modes (demonstrated or code-proven)

| Mode | Status | Evidence |
|---|---|---|
| Partial generation | **Real risk** — sequential non-atomic writes, no cleanup on mid-write failure (no try/finally in `materialize`); a torn tree is indistinguishable from a valid one (no checksum) | code |
| Build failure (detected) | Docker build rc≠0 → `build_and_run` returns error → evidence error, fitness 0 | code + evaluator flow |
| Stale artifacts | **DEMONSTRATED** (E3); promotion dir + Docker context affected | E3 |
| Wrong backend | fail-closed at registry + `supports()` (tested) | code + tests |
| Missing dependency | Docker `pip install` failure → build fails (detected); no lockfile ⇒ *version drift*, not absence | code |
| Corrupted artifact | undetectable post-hoc — no digest/manifest on disk (§4/§8) | code |
| Artifact/metadata mismatch | metadata not materialized → nothing on disk to mismatch, i.e., the integrity anchor is absent | code |
| Successful-but-invalid artifact | **DEMONSTRATED** (E7/E8): valid-vocab genome with `services=["users orders"]` passes all builder gates; artifact fails `py_compile`; static evidence reports `build_ok=True, static_score=4.274`. Runtime mode *would* catch it (container import crash → health fail) — static mode (incl. **default Go-target mode**) does not | E7/E8 |
| Path traversal via service name | **DEMONSTRATED** (E6): `services=["../escape"]` writes `escape.py` to the artifact root, escaping `services/` (deeper `../..` reaches outside the output dir). Reachable at library boundary; **not reachable via the HTTP API at this state** (`EvolutionRequest` carries no genome input, `schemas/evolution.py:10-24`; `/evolve/*` generates internally from fixed vocab) | E6 + code |
| Verification/promotion identity mismatch | **DEMONSTRATED mechanism** (verified dir ≠ promotion dir + no digest + no cleanup) | §8 + E3 |
| Readiness flake | `sleep(3)` startup assumption; random port collisions | code |
| Go artifact unbuildable as-is | missing `go.sum` → build fails until `go mod tidy` (network) | go experiment |

## 11. Evidence gaps (UNVERIFIED)

- GHCR image digests/tag states (token lacks `read:packages`, 403) — publish-side identity checks stop at workflow structure.
- Go *executed* behavior beyond CI's single fixed genome (local `:8000` port exclusion; CI evidence: `multi-backend` success at both `6e1aa1a` and main).
- Whether committed `generated/*` exemplars were ever regenerated or diffed against the builder (no CI job; 52 tracked files in DDD/Elixir layouts vs builder's flat layout ⇒ silent drift, CONFIRMED absent).
- `/observation/isr` source-of-truth binding (503 until `CanonicalIsrAccessor` bound — accessor implementation absent from audited tree).
- Observability of parallel-evaluator port collisions (no telemetry; code-level risk only).
- Post-verification tamper windows: no store exists to observe (no digests) — classified as `UNIMPLEMENTED` rather than measured.

## 12. Blocker register — EV-A02-001 … EV-A02-012

| ID | Finding | Classification | Conf | Evidence | Impact / failure mode | Security implication | Remaining work |
|---|---|---|---|---|---|---|---|
| **EV-A02-001** | Static-evidence path certifies non-compilable artifacts; static layer = `build_ok` (files written) + heuristic score; Go static "verification" is a `{verified: True}` stub; Go-target evolution defaults to this path even with `use_docker=True` | static gate `UNIMPLEMENTED`; stub `IMPLEMENTED_SIMULATED` | CONFIRMED | E7/E8 (`static_score=4.274` on py_compile-failing artifact); `candidate_evaluator.py:76,81-84`; `fitness.py:62-72` | successful-but-invalid promotion; "verified" ≠ verified | invalid artifacts can reach promotion with a high-looking score | per-candidate syntax/compile gate (py_compile/vet) as part of static evidence; replace Go stub with real static inspection |
| **EV-A02-002** | Promotion binds the genome, not the artifact: no digest, no output_path, no verified↔promoted identity check | identity `UNIMPLEMENTED` | CONFIRMED | `models.py:6-51`; `evolution.py:100,108`; §8 | verification/promotion identity mismatch; artifact replaceable post-verification | none direct; integrity of the audit trail | content-addressed artifact store + digest in `EvolutionRun`/`GenomeRecord`; compare verified vs promoted hashes |
| **EV-A02-003** | `materialize` never cleans: stale files persist (E3: `services/orders.py`), entering the promotion tree and Docker images (no `.dockerignore`, `COPY . .`) | materializer `PARTIAL` | CONFIRMED | E3; `backends.py:495-506`; `builder.py:515` | stale artifact; published/promoted tree ≠ verified tree | extra stale endpoints/services may ship | exclusive-dir materialization (build in fresh dir, atomic swap) + emitted `.dockerignore` |
| **EV-A02-004** | Provenance (`architecture_hash`, backend_id, schema) exists only in memory; nothing persisted next to the artifact; DB records embed host paths (`artifact_path`) | on-disk provenance `UNIMPLEMENTED` | CONFIRMED | `backends.py:475-506`; `evolution.py:81-82`; `models.py:11` | artifact/metadata mismatch undetectable; host topology in records | minimal (no secrets leaked) | write a signed manifest (hash, backend, schema, genome_id) into the artifact dir; store digests not paths |
| **EV-A02-005** | Service names unvalidated: path traversal (E6: `../escape` → `escape.py` at artifact root) and broken identifiers (E7: space ⇒ syntax error) pass the compiler boundary (type-checked only, `backend_contract.py:52-77`) | input validation `UNIMPLEMENTED` | CONFIRMED (code) / latent (API-unreachable at this state: no genome input in `EvolutionRequest`) | E6/E7; `schemas/evolution.py:10-24` | file writes outside the artifact tree; broken artifacts | **path-traversal write primitive** at the library boundary; any future API exposing genome input inherits it | strict identifier charset for `services` (and `api_version`); canonicalize+validate in `validate_architecture` |
| **EV-A02-006** | `genome_id` not a unique identity: mutation children inherit parent's id (E4); `genome_hash` therefore not a pure architecture content address; parent selection tie-breaks on it | identity model `PARTIAL` | CONFIRMED | E4; `mutation.py` child construction; `genome.py:36,48`; `population.py` | lineage ambiguity; candidate-dir collisions only via fields, but identity records are unreliable | low | fresh id per individual (keep parent link in lineage only) |
| **EV-A02-007** | Backend posture divergence for the same `authentication` capability: Python fail-closed vs Go fail-open default credentials (`generated-api-key`, `generated-user/generated-pass`, `generated-jwt-secret`); Go always emits `/health` even when unrequested | semantic consistency `PARTIAL` | CONFIRMED | `backends.py:297-396` vs `builder.py:411-427`; CI test signs with the default secret (`test_backends.py:289`) | same genome ⇒ different security behavior by backend; wrong-backend or stale-artifact confusion in mixed fleets | **shipped default credentials = fail-open auth surface** in Go artifacts | make Go auth env-required (fail-closed) or explicitly provision+inject; honor unselected `/health` |
| **EV-A02-008** | `logging_level` contract/evidence mismatch: declared implemented (`capability_contract.py:104-109`) but never inspected (`capability_evidence.py`) → `contract_ok` structurally False, runtime score capped at 0.90 + "probes did not fully pass" error for every genome with a log level; static summary permanently lists it as failed | consistency `PARTIAL` | CONFIRMED | E8 `failed_or_unverified: ['logging_level']`; `candidate_evaluator.py:210,214` | systematic false-negative contract failure; scoring distortion (0.1 weight lost) | none | add a logging-config check to `inspect_artifact` (or remove the capability from the contract) |
| **EV-A02-009** | Build gates weaker than claimed: no per-candidate syntax/compile check (CI flake8 covers one fixed genome only, E9/F82 selectors); Go artifact unbuildable without `go mod tidy`+network (no `go.sum` emitted) | build gate `PARTIAL` | CONFIRMED | §5; `ci-cd.yml:70,99`; go experiment (fail→tidy→pass); `backends.py:130-134` | broken candidates pass "build_ok"; Go reproducibility depends on network at build time | low | per-candidate `py_compile`/`go vet` in evaluation; emit `go.sum` in the artifact |
| **EV-A02-010** | Go runtime verification absent from pipeline (`runtime_supported=False`, `backends.py:99`; static stub §EV-A02-001); only CI-fixed-genome compile+execute exists (`:8000` hardcoded) | Go runtime `UNIMPLEMENTED` (pipeline) / `IMPLEMENTED_REAL` (CI fixed-genome) | CONFIRMED | `test_backends.py:231-340`; `test_backend_neutral_evolution.py:56-68` (encodes the stub as expected) | evolved Go candidates never runtime-probed; capability claims unverified | fail-open defaults (§007) untested at runtime | Go runtime backend (container or host-exec) + capability probes mirroring the Python set |
| **EV-A02-011** | Time-reproducibility: artifact files byte-stable, but installed dependency closures are unpinned (generated `requirements.txt` `>=`-only; platform image `pip install .` without lock; EV-A01-004) → same genome, different closure over time | reproducibility `PARTIAL` | CONFIRMED | `builder.py:489-495`; `autonomous-api/Dockerfile`; EV-A01-004 | silent behavior/security drift between builds of the same artifact | dependency drift (vuln + behavior) | lockfile (per generated artifact family) or pinned bases+deps |
| **EV-A02-012** | Published-artifact identity: GHCR tags mutable (`branch`/`latest`/`sha` refs, no digest refs); published = source-tree rebuild, not verified bytes; generated artifacts never published; committed `generated/*` exemplars (52 files, DDD/Elixir layouts) stale vs builder output with no regeneration check | publish `IMPLEMENTED_BOUNDED`; generated-artifact publish + exemplar freshness `UNIMPLEMENTED` | CONFIRMED (listings `UNVERIFIED` — 403 scope) | `v1.1:395-441`; `v1.2:125-143`; `git ls-files generated/` (52); §8 | tag-followers get rebuilt images; no auditable generated-artifact registry; silent exemplar drift | mutable tags + no digests weakens supply-chain pinning | digest-pinned tags/manifests; publish verified generated artifacts to a registry; CI diff of committed exemplars |

## 13. EV-A02 CONCLUSION

**The artifact is a trustworthy compiled representation of the architecture selection — for the Python backend's *content*, and only under clean-directory conditions.**

What is solid (`IMPLEMENTED_REAL`, CONFIRMED): byte-level determinism of both backends (E1/E2); fail-closed compiler boundary (drift/types/unmapped/unknown-backend); genuine, layered, probe-gated Python runtime verification; content-addressed verification directories; seeded gene-space reproducibility (E5); fail-closed promotion scoring (runtime-failed ⇒ zero fitness, `evolution.py:45-61`); real evidence-chain verification before the platform's only publish (Gate 5).

What breaks the trust chain (the FAIL): static evidence can certify artifacts that cannot compile (§10/E8) — including the *default* path for the Go target; promotion is by genome state with no artifact identity or digest, into an uncleaned directory that demonstrably retains stale files (E3); provenance never reaches the filesystem; the Go backend lowers the same authentication capability to fail-open default credentials; a valid-vocab genome can traverse the artifact tree (E6); and the two committed "generated" exemplars are not producible by the builder at all.

Carried forward, not fixed here (per audit boundary): EV-A02-001…012; interacts with EV-A01-002 (state-dependent tests), EV-A01-004/011 (unpinned supply chain, no CD), PROD-016 (no deployment actuation).

**Positive controls** (recorded for the next gates): determinism invariants E1/E2/E5; `test_backend_outputs_are_deterministic_for_same_architecture`; `architecture_hash` cross-backend equality tests; probe 404-gating (`CAPABILITY_EVIDENCE_MODE`); Go `go.mod` version pin (`modernc.org/sqlite v1.33.1`); non-root platform image.

## 14. NEXT GATE

**EV-A03 — Capability Truthfulness.** Natural entry points from this evidence: the `logging_level` contract/evidence split (EV-A02-008), the proposed-but-absent `grep -R "runtime_supported" app/engine` CI invariant, the Go capability stubs (EV-A02-010), and the `backends`/external-descriptor reservation discipline (`capability_contract.py:110-115`).

Verification appendix (reproducible):

```text
sandbox: C:\Users\user\AppData\Local\Temp\opencode\ev02 (py1/py2=byte-diff, go1/go2=byte-diff,
         stale=E3 leftovers, trav=E6, broken=E7/E8 input, cand=E8 evidence)
probe:   C:\Users\user\AppData\Local\Temp\opencode\ev02_probe.py (E1..E8, venv python 3.14)
go:      go1: `go build` (fails: missing go.sum) -> `go mod tidy` + `go build` (rc=0)
        go execution blocked locally: host TCP exclusion 7973-8072 covers :8000
```

*Internal analysis doc — working tree only, not tracked (per AGENTS.md .md policy).*
