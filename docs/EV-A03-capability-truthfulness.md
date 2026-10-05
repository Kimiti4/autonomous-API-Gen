# EV-A03 — Capability Truthfulness

- **State audited:** `6e1aa1a` (PR #1 head), fetched tree clean; pending Bandit fix excluded from baseline.
- **Method:** READ-ONLY, NON-MUTATING, EVIDENCE-FIRST. Code-path tracing + reuse of EV-A02's demonstrated artifacts (E1–E8 in `C:\Users\user\AppData\Local\Temp\opencode\ev02`); no file in the repo was created, changed, or deleted.
- **Taxonomy:** `IMPLEMENTED_REAL` / `IMPLEMENTED_BOUNDED` / `IMPLEMENTED_SIMULATED` / `PARTIAL` / `UNIMPLEMENTED` / `UNKNOWN`.
- **Confidence:** `CONFIRMED` / `INFERRED` / `UNVERIFIED`.
- **Scope boundary:** "generation correctness" / "artifact identity" / "promotion authorization" are **not** re-argued here beyond their truthfulness surface (see EV-A02).

---

## 0. STATUS

**STATUS: FAIL** — bounded to truthfulness of capability *claims*.

The platform's capability vocabulary is well-defined and the **compile-time** contract is fail-closed (unknown backend, schema drift, unmapped capabilities, unsupported Go semantics → `ValueError`). The Python **runtime** path is real and evidence-based: `inspect_artifact` (static text checks) + a large set of gated, `CAPABILITY_EVIDENCE_MODE`-hidden probes (`candidate_evaluator.py:102-213`; `contract_ok = not failed and runtime_required ⊆ runtime_verified and not runtime_failed`, `:210`). The failures are concentrated in **three places where a capability is allowed to be *called* implemented/verified without demonstrated artifact behavior**:

1. the **static / non-runtime path** — `build_ok` = "files were written", `static_score` = a genome-field heuristic (and EV-A02 E8 showed it can certify an artifact that fails `py_compile`);
2. the **Go backend's evidence** — a single unconditional `{"backend_id","verified": True}` with no inspection (`candidate_evaluator.py:76`);
3. the **`runtime_supported=False` + `use_docker=True`** case — Go-target evolution silently degrades to (2) and promotes on heuristic fitness while reporting `build_ok=True` + `verified=True`.

Because the evidence that feeds promotion is genome-field heuristics for any non-runtime backend, and because `logging_level` is declared *implemented* (architecture contract) while never *verified* (artifact inspection) and simultaneously makes `contract_ok` structurally false (false-negative on an otherwise-healthy container), **Tiannara cannot truthfully claim a generated capability is implemented-and-verified when the evidence describes the heuristic/genome path**.

This is a *refinement* of EV-A02-001/010, not a repetition: EV-A02 asks "does the artifact compile/persist?" EV-A03 asks "does a *verified* badge on a capability actually correspond to demonstrated artifact behavior?" Answer: only on the Python runtime path.

---

## 1. Artifact pipeline (the truthfulness joints)

```
Genome (genome.py)                                    # declared intent
  → make_compilation_request (validate_architecture, FAIL-CLOSED drift/types)  backend_contract.py:49-111
  → plan_capabilities (assess_genome)                # the IMPLEMENTED contract  capability_contract.py:51-116
      → capabilities: services, database, authentication, cors, health_endpoints,
         openapi, api_version, rate_limiting, metrics_endpoints, tracing,
         timeout_config, retry_policy, circuit_breaker, cache,
         middleware, security_policies, logging_level, backends
  → backend.compile                                    # lowering (Python vs Go)
  → materialize (no digest, no cleanup, no provenance on disk)   backends.py:495-506
  → [static] inspect_artifact(substring checks) + static_score(calculate_fitness heuristic)
      OR       inspect_artifact + runtime probes (health/openapi/auth/CRUD×svc0/timeout/retry/
               circuit/cache/rate-limit) -> contract_ok -> runtime_score    candidate_evaluator.py:204-213
  → _fitness_from_evidence (FAIL-CLOSED: build_ok=False or mode≠runtime/static => 0)   evolution.py:45-61
  → promotion (best_genome JSON to GenomeRecord/EvolutionRun; NO digest)  models.py:6-51; evolution.py:98-108,113
```

Truthfulness joints to audit: (contract ↔ artifact ↔ verification) at each capability, and the **mode selector** `runtime_supported` (`candidate_evaluator.py:81`) which decides whether a genome is *verified* (runtime probes) or only *fitnessed* (heuristic).

Note: the external observation projection (`/observation/isr`, `/observation/capabilities`) is bound to a `None` projector (`observation_routes.py:35,72-77`) and returns 503 ("Phase B audit gap"). **No externalized `verified`/`implemented` claim for generated capabilities reaches consumers at the audited state** (`build_capabilities` advertises only platform observation-stream features, not genome capabilities). The truthfulness question is therefore internal: the fitness/verification that drives `global_best_fitness`/`select_parents`/promotion.

---

## 2. `logging_level` truthfulness — the contradiction

- **Contract declaration** (`capability_contract.py:104-109`): `add("logging_level", requested=bool(level), implemented = level in {"DEBUG","INFO","WARNING","ERROR"}, ...)`. So for a normal genome, `logging_level` is *implemented* per the architecture contract.
- **Genome representation** (`genome.py:55,114-115`): a plain string field, serialized in `encode()`; `_load` stores it verbatim, no enum validation at load (only the `_generate_*`/`mutate` paths constrain it to `LOG_LEVELS`).
- **Builder/lowering** (`builder.py:342-348`): the level is spliced into `logging.basicConfig(level=logging.{level!r})` *only when `genome.logging_level` is truthy*. The emitted string is **not validated** at codegen (`logging.INFOX` would be syntactically valid but crash at import).
- **Inspection** (`capability_evidence.py`): there is **no `logging_level` check** in `inspect_artifact` — its results dict is services/database/authentication/cors/health_endpoints/openapi/api_version/rate_limiting/metrics_endpoints/tracing/timeout_config/retry_policy/circuit_breaker/cache. The fallback loop (`capability_evidence.py:123-125`) then marks any *other* requested capability as `requested=True, verified=False` → logged in `summarize.failed_or_unverified`.
- **Verification effect (CONFIRMED)**: `candidate_evaluator.py:206-210`:
  ```
  failed = requested - verified                 # includes logging_level for any logging genome
  runtime_required = requested ∩ {metrics,rate,tracing,timeout,retry,circuit,cache}
  contract_ok = not failed and runtime_required ⊆ runtime_verified and not runtime_failed
  ```
  So a Python-runtime container that passes **every** runtime probe still gets `contract_ok=False` and `runtime_score ≤ 0.90` whenever `logging_level` is set, and `error = "runtime capability or contract probes did not fully pass"` (`candidate_evaluator.py:214-215`). EV-A02 E8 observed exactly this: `failed_or_unverified: ['logging_level']`.
- **Why it can be structurally false while "treated as implemented"**: `assess_genome` (contract) says implemented; `inspect_artifact` (verification) says unverified; nothing reconciles the two, so `contract_ok` is *structurally* false for a whole class of otherwise-valid architectures. The contract treats logging_level implemented, the verifier treats it unverified — **two authorities disagree without a tie-break**.

Classification: contract `IMPLEMENTED_REAL` (honest), verifier omission `PARTIAL` → false negative.

---

## 3. Go verification stubs — unconditional claims

- The **only** unconditional verification claim in the entire evidence path is:
  `candidate_evaluator.py:76` — `evidence["capability_evidence"] = {"backend_id": target.backend_id, "verified": True}` for every **non-Python** backend (i.e., the Go backend).
- Contrast the Python path (`:73-74`): `artifact_capabilities = inspect_artifact(genome, candidate_dir)` + `capability_evidence = summarize(...)` — a real static inspection producing `requested/verified/failed/coverage`.
- No build, no probe, and **no static inspection** runs for the Go artifact in the evaluation path. The CI `test_go_backend_compiles_and_executes_when_go_toolchain_available` (`test_backends.py:231-340`) compiles and execs **one fixed genome** and signs its JWT probe with the **Go default secret** `generated-jpt-secret` (`test_backends.py:289`) — so even the CI evidence for Go assumes the fail-open default.
- The evidence schema is the in-process `dict` from `evaluate_candidate` (`candidate_evaluator.py:61-68`): booleans `build_ok`, `contract_ok`; floats `static_score` (heuristic), `runtime_score`; strings `evaluation_mode ∈ {static, runtime}` *plus the initial sentinel `"runtime_failed"`* (`:63`); nested dicts `capability_evidence`, `runtime_capabilities`, `crud_checks`. There is no `verified` boolean on capabilities in the Python path (uses `capability_evidence.coverage`); the single `verified: True` is the Go stub. **The schema permits a `verified: True` claim with zero artifact inspection.**

Classification: Go static evidence `IMPLEMENTED_SIMULATED`; Python static+runtime `IMPLEMENTED_REAL` (bounded).

---

## 4. `runtime_supported` — not a hard invariant

- Defined once: `CompilerBackend.runtime_supported: bool` (Protocol, `backend_contract.py:127`).
- Implementations: `PythonFastAPIBackend.runtime_supported = True` (`backends.py:39`); `GoHTTPBackend.runtime_supported = False` (`backends.py:99`).
- Consumed in three places (all informational — a *mode switch*, not a *gate*):
  - `candidate_evaluator.py:81`: `if not use_docker or not get_backend(target.backend_id).runtime_supported: evaluation_mode="static"; static_score=calculate_fitness(...)`.
  - `evolution.py:72` and `evolution.py:108`: the `evaluation_mode` / `evaluation_mode`-label in the emitted event and result dict.
- **Decision:** it is a heuristic selector, **not** a hard invariant. A Go-target (`runtime_supported=False`) evolution with `use_docker=True` (the default, `schemas/evolution.py: EvolutionRequest.use_docker: bool = True`) still:
  1. sets `build_ok=True` after `materialize` succeeds (`:70-71`);
  2. sets `capability_evidence={"verified": True}` (`:76`, the stub);
  3. sets `static_score=calculate_fitness(...)` (`:83`);
  4. is scored by `_fitness_from_evidence` → **non-zero static score can still win** and the genome is built and "promoted" while its capabilities were never runtime-verified (only heuristics).
- So: **`runtime_supported=False` does not suppress a build_ok/verified/static_score claim; it suppresses only the live probes.** The hard invariant "no runtime, therefore no verified claim" is **absent**.

Classification: selector `IMPLEMENTED_REAL`; hard invariant `UNIMPLEMENTED`.

---

## 5. Contract → artifact → verification closure

- **Implemented-without-observable-artifact**:
  - `logging_level` (§2): declared implemented, emitted (builder), but **never inspected** → no observable behavior tied to a verification.
  - `backends` (external cache/MQ descriptors, `capability_contract.py:110-115`): `implemented=False` always → fail-closed, *no* false positive (a **positive** example of the contract refusing to claim implementation).
  - `cors` (`cors_enabled`): inspected by substring (`CORSMiddleware` in main text, `capability_evidence.py:32-33`) — but the check is "string present/absent," not "behaves correctly under OPTIONS" — bounded verification.
- **Verified-without-executing**:
  - `inspect_artifact` is **substring/presence** checks on `main_text`/`security_text`/`requirements_text` — no import, no compile, no execution (`capability_evidence.py:21-23` read files).
  - Any **static-mode** run (Go default, or `use_docker=False`) verifies by genome fields only (`static_score = calculate_fitness`, `fitness.py:62-72` = heuristic scores; **no** file read).
  - `contract_ok` (`:210`) folds the static inspection into the "runtime" verdict — but for static mode the probes never run, so `contract_ok` is derived from static substrings while `runtime_score=0`.
- **Is a capability's truth bound to the actual bytes?** Only on the **Python runtime path**: probes hit the live container and `contract_ok` requires `runtime_required ⊆ runtime_verified and not runtime_failed` (genuine binding). On the Go path and `use_docker=False` path, truth is genome-heuristic → **not bound to bytes**. EV-A02 E8 demonstrated the breach: the heuristic "verified" artifact fails `py_compile`.

Classification: Python runtime-verification closure `IMPLEMENTED_REAL`; Go/static closure `UNIMPLEMENTED`-grade (`IMPLEMENTED_SIMULATED`).

---

## 6. Cross-backend semantic equivalence (auth + beyond)

Same capability vocabulary, two backends, divergent security posture (the user asked to focus on auth, then others):

| Capability | Python lowering (builder.py) | Go lowering (backends.py) | Equivalent? |
|---|---|---|---|
| authentication (api_key) | `API_KEY = os.getenv("API_KEY")`; **no default → 401 if unset** (`security.py:404-414` in generated text) → fail-closed | `expected := os.Getenv("API_KEY"); if expected=="" { expected="generated-api-key" }` (`:301`) → **fail-open default** | **NO** (contract violation of fail-closed posture) |
| authentication (basic) | `BASIC_USER`/`BASIC_PASSWORD` envs, no default → 401 (`security.py:423-426`) | defaults `"generated-user"`/`"generated-pass"` (`:317-321`) → fail-open | **NO** |
| authentication (jwt) | `JWT_SECRET = os.getenv("JWT_SECRET")`; no secret → 401; `import jwt; jwt.decode(...)` (builder uses PyJWT) | `secret := os.Getenv("JWT_SECRET"); if secret=="" { secret="generated-jwt-secret" }` (`:350`); hand-rolled HS256 verifier, loose `exp` check (`claims.Exp != 0`), no aud/nbf/iss (`backends.py:356-376`) | **NO** (fail-open default + weaker cryptography, though `test_backends.py:289` signs with the default secret → CI assumes it) |
| auth (oauth2) | `assess_genome`: implemented=False → unmapped → **ValueError** (never lowered) | rejected by allowlist (`:124-128`) → ValueError | Yes (both refuse) |
| database | postgres/mysql/sqlite (`SUPPORTED_DATABASES`) | only `sqlite` (`:119-123` rejects postgres/mysql) | **NO** (different expressivity) |
| health_endpoints=False | `/health` omitted (`:337-341`) | `/health` **always emitted** (`:284-291`) — extra surface | **NO** (selection fidelity) |
| CORS | opt-in (`cors_enabled`) | opt-in; Go CORS is static `*` (`withCORS`) | roughly yes |
| metrics/tracing/cache/circuit/retry/timeout/logging | Python: full lowering; Go: **not in `allowed`** (`:115`) → ValueError if requested | — | Yes-by-design (both refuse) |

The auth fail-open is the security-relevant semantic divergence; the health-endpoints-inversion and database expressivity gap are correctness/expectation divergences.

---

## 7. Evidence integrity — what the fields actually prove

| Field | Appears to prove | Actually proves | Gap |
|---|---|---|---|
| `build_ok` (`candidate_evaluator.py:71`) | the artifact compiled/starts | `compile_and_materialize` returned without raising (files were *written*) | not "compiles" — E7 showed `py_compile` failure with `build_ok=True`. EV-A02-009. |
| `static_score` (`candidate_evaluator.py:83`) | measured quality | `calculate_fitness(genome)` — genome-field heuristics (security, "architecture" = service count, performance-capability checks, best-practices, database, `production_score` heuristic) → **can exceed 1.0 (E8 = 4.274)** | not a measured artifact score; not [0,1] |
| `verified` (Go, `:76`) | capability verified | literal `True`, no inspection | no verification performed |
| `contract_ok` (`:210`) | runtime contract holds | `not failed and runtime_required ⊆ runtime_verified and not runtime_failed` | `failed = (static verification's requested−verified)` — so a missing static inspection (§2) makes this false even when **all runtime probes pass** → false negative |
| `runtime_score` (`:213`) | normalized quality in [0,1] | weighted sum, capped at 0.90 when `contract_ok` is false | can be <1.0 with a fully-healthy container |
| `evaluation_mode` (`:63`) | `static`/`runtime` | initial value `"runtime_failed"` (a verdict string used as a mode label) when `use_docker=True` and the path returns before assigning | naming/semantics confusion; currently non-fatal (worst path still yields fitness 0) but a mislabel hazard |
| elite `evaluate_genome` | fitness via fitness | `calculate_fitness` + `ProductionReadinessAnalyzer.analyze` + ad-hoc `performance_score` bonuses (`cache_enabled +0.2`, `logging_level in WARNING/ERROR +0.1`, `elite_evolution.py:65-71`) | arbitrary bonuses; no artifact check; `evaluation_mode` hardcoded `"static"` (`:87`) |

Field names over-promise: `static_score` (sounds measured), `verified` (boolean, unconditional for Go), `contract_ok` (sounds runtime-bound but includes unverified static items).

---

## 8. Invariant search (absences recorded as findings)

| Invariant | Present? | Evidence of (absence) |
|---|---|---|
| unsupported runtime ⇒ no verified/build-success claim | **NO** | `runtime_supported=False` still yields `build_ok=True` + `verified:True` stub; §4. |
| verification ⇒ artifact digest binding | **NO** | `materialize` writes files with no digest; `EvolutionRun`/`GenomeRecord` carry no digest (`models.py:6-51`). EV-A02-004. |
| verification ⇒ artifact existence (post-hoc) | Weak | `build_ok` is set by materialize's success (so ≈ files exist), but there is no re-assertion before a capability is marked verified. |
| verification ⇒ actual executable/static validation per candidate | **NO (partial)** | CI flake8 E9/F82 inspects a *single fixed representative genome* (`ci-cd.yml:70,99`); no per-candidate `py_compile`/`go vet`; runtime probes are Python-only. EV-A02-009. |
| contract implementation ⇒ observable use in artifact | **NO** | `logging_level`: implemented (contract) but `inspect_artifact` never checks it. §2. |
| backend verification ⇒ backend-specific real evidence | **NO for Go** | Go static evidence = `{verified: True}` stub; Go runtime evidence = one CI genome. EV-A02-010. |
| `contract_ok` ⇒ all *runtime-verified* capabilities pass | **NO** | `contract_ok` is `False` whenever any *static* inspection is missing (§2), regardless of runtime probes. |
| elite/fitness ⇒ artifact inspected | **NO** | `EliteEvolutionEngine.evaluate_genome` (`elite_evolution.py:61-71`) uses genome-field scoring only; the global-best is materialized once (`elite_evolution.py:94`) and never re-verified by probes. |

Present positives: compile-time fail-closed boundary (unknown backend / schema drift / unmapped / unsupported Go semantics all `ValueError`, tested); capability `backends` always `implemented=False` (no false positive); `contract_ok` correctly returns False on static-inspection gaps (even if for the wrong reason here); `_fitness_from_evidence` fail-closed on `build_ok`/`mode` (E5-style: a failed build ⇒ 0 fitness).

---

## 9. Blocker register — EV-A03-001 … EV-A03-010

| ID | Finding | Taxonomy | Conf | Evidence | Affected trust boundary | Security/integrity implication | Independent of EV-A02? |
|---|---|---|---|---|---|---|---|
| **EV-A03-001** | `logging_level` false-negative: contract declares it implemented and the builder emits it, but `inspect_artifact` never verifies it; it is auto-listed as `failed_or_unverified` ⇒ `contract_ok` is structurally False and `runtime_score` capped at 0.90 for any logging-enabled genome, even when every live runtime probe passes | verifier `PARTIAL` → false negative | CONFIRMED | `capability_contract.py:104-109`; `capability_evidence.py:123-125,206-210`; E8 output | capability-claim truthfulness; scoring | healthy artifact misreported as "contract did not fully pass"; coverage undercount | Refinement |
| **EV-A03-002** | Static/Go `verified` cannot rest on artifact behavior: `build_ok` = "files written"; `static_score` = heuristic (>1 possible, E8=4.274); a non-compilable artifact earns `build_ok=True` and a positive score | static evidence `UNIMPLEMENTED` (claim) / `IMPLEMENTED_SIMULATED` (path) | CONFIRMED | E7/E8; `candidate_evaluator.py:70-71,83`; `fitness.py:62-72` | capability verified claims on the non-runtime path | uncompilable/broken artifacts can be selected as "best" via heuristic fitness | Refinement |
| **EV-A03-003** | `runtime_supported=False` is a mode switch, **not** a hard invariant: Go (and `use_docker=False`) evolution can still claim `build_ok=True`, `static_score>0`, `verified:True`, and promote on that basis at default `use_docker=True` | invariant `UNIMPLEMENTED` | CONFIRMED | `candidate_evaluator.py:63,76,81-83`; `evolution.py:72,108`; `schemas/evolution.py: EvolutionRequest.use_docker=True` | backend verification authorization; promotion of un-verifiable-backend artifacts | artifacts with no runtime evidence enter the promoted set as if verified | **Independent** |
| **EV-A03-004** | Go backend capability evidence is a single unconditional `{"verified": True}` stub — no compile, no static inspection, no runtime probe of the candidate | Go static `IMPLEMENTED_SIMULATED` | CONFIRMED | `candidate_evaluator.py:76` (and the test that encodes it, `test_backend_neutral_evolution.py:56-68`) | Go capability verification | Go capability claims rest on the CI fixed-genome test alone (which uses default secrets) | Refinement (of EV-A02-010) |
| **EV-A03-005** | Evidence field semantics over-promise: `static_score` (heuristic, not [0,1]); `verified` (Go, unconditional); `contract_ok` (folds static gaps into runtime verdict); `evaluation_mode` defaults to the verdict string `"runtime_failed"` | evidence schema `PARTIAL` | CONFIRMED | `candidate_evaluator.py:61-68` | evidence integrity / external reasoning over the dict | false confidence; naming drift | Refinement (of EV-A02-009) |
| **EV-A03-006** | Elite engine promotes on **genome-field heuristics only**: `evaluate_genome` (`elite_evolution.py:61-71`) never reads an artifact; the global-best is materialized once (`:94`) and never runtime-probed; `evaluation_mode` hardcoded `"static"` | elite verification `UNIMPLEMENTED` | CONFIRMED | `elite_evolution.py:61-71,87,94-99` | elite-path capability truthfulness; `/evolve/elite/start` promote authorization | elite "best" can be selected by heuristic only, then emitted to the default directory unverified | **Independent** (distinct path) |
| **EV-A03-007** | Cross-backend semantic divergence — auth is fail-open in Go (default `generated-api-key`/`generated-user`/`generated-pass`/`generated-jwt-secret`, `backends.py:301,317,321,350`) but fail-closed in Python (env required); `oauth2` is "secure" in the score table (`security.py`) but unimplementable (unmapped); Go always emits `/health` even when not requested | backend equivalence `PARTIAL` | CONFIRMED | `backends.py:297-396`; `builder.py:411-427`; `security.py:24-34`; `capability_contract.py:22` | capability semantic equivalence; auth posture | same genome ⇒ different security behavior; fail-open defaults in shipped Go artifacts | Refinement (of EV-A02-007) |
| **EV-A03-008** | No per-candidate artifact validation reaches a `verified` claim: compile-time only catches architecture drift, not generated-code validity; `py_compile`/`go vet` absent per candidate (CI lints one fixed template) | static validation gate `UNIMPLEMENTED` (per-candidate) | CONFIRMED | `ci-cd.yml:70,99` (fixed template only); builder emits un-validated strings (e.g. `logging.{level}`) | static-validation truthfulness | non-compilable artifacts are not rejected by the verifier | Refinement (of EV-A02-009) |
| **EV-A03-009** | Absent hard invariants (table §8): `unsupported runtime ⇒ no verified claim`; `verification ⇒ digest`; `verification ⇒ executable validation`; `contract implementation ⇒ observable artifact behavior`; `backend verification ⇒ backend-specific real evidence` | invariants `UNIMPLEMENTED` (the set) | CONFIRMED (via code reachability) | sections §4/§5/§8 | the verification/claim contract | the system can (and does, via Go) claim verification without the supporting evidence | **Independent** (structural) |
| **EV-A03-010** | External truthfulness surface is unbound: `/observation/*/isr` is 503 (`_isr_projector = None`, `observation_routes.py:35,131-134`); `CandidateProjection` (frozen schema) carries `lifecycleState`/`evidenceRefs` but is not populated; no external `verified`/`implemented` claim for genome capabilities is ever produced | external projection `UNIMPLEMENTED` | CONFIRMED | `observation_routes.py:35,72-77,131-137`; `capabilities.py:16-46` | external truthfulness / consumer trust | downstream consumers (dashboard) cannot obtain authoritative capability truth; any future consumer trusting the projection shape would inherit these gaps | **Independent** |

---

## 10. EV-A03 CONCLUSION (direct answer)

**Can Tiannara truthfully say a generated capability is implemented and verified when the evidence may describe the genome/heuristic path rather than the actual artifact's demonstrated behavior?**

- For the **architecture contract** (`assess_genome`): yes, honestly — implemented iff a concrete lowering exists; `backends` is always "not implemented."
- For the **Python runtime path**: yes, on the probes that ran — `contract_ok`/`runtime_score` are derived from live container probes, probe-gated by `CAPABILITY_EVIDENCE_MODE`.
- For the **static path** (Go target, `use_docker=False`): **no.** `build_ok` only means files were written; `static_score` is a genome-field heuristic that can exceed 1.0 and can certify a non-compilable artifact (E8); the Go `verified=True` stub performs no inspection.

Since the default for `/evolve/start` and `/evolve/elite/start` can route a run away from live probes (Go target via `runtime_supported=False`; `use_docker=False` for elite), and since promotion keys off `_fitness_from_evidence` (which accepts the static score), **the platform can and does select a "best" artifact whose capability claims rest on heuristics rather than demonstrated behavior.** That is the truthfulness breach.

The breach is *localized, not systemic*: the compile-time boundary and the Python runtime probes are genuine. Closing it requires (a) a per-candidate compile/static gate so `build_ok` ⇒ "actually compiles/imports," and (b) either real Go static inspection + a Go runtime backend, or a **hard invariant**: `runtime_supported=False` ⇒ no `verified`/`build_ok=true`-as-success claim and no promotion on heuristic score alone.

**Positive controls:** fail-closed compile boundary (4 tested cases + code); `_fitness_from_evidence` rejects build/runtime failure (fitness 0, `evolution.py:45-61`); `contract_ok` correctly stays False when static inspection is missing (the failure mode is over-conservatism, not over-claim, for Python); architecture-hash cross-backend equality contract (`test_backend_neutral_evolution.py:37`); frozen external schema design (`observations.py: ISRObservation/FitnessReport/CandidateProjection`) that separates `isrRevision`/`provenance`/`evidenceRefs`.

Carried forward: EV-A03-001…010; interact with EV-A02-001 (static stub), EV-A02-010 (Go static), EV-A02-009 (build gate), EV-A02-007 (backend divergence), and PROD-015 (heuristic readiness scoring).

## 11. NEXT GATE

**EV-A04 — Security Boundary.** Truthfulness feeds authorization: if `contract_ok` and `verified` are over-claiming, what does `SecurityHeadersMiddleware`, the API-key model (`security.py:131,143`), `/stream` auth-before-accept (`ws.py:84-101`), and the auth mode selection (`security.py` `AUTH_MODE` per request path) actually enforce — and where do the Go fail-open defaults and the auth fail-open reach the public boundary? EV-A03-007 (auth semantic divergence) is the direct bridge.

## 12. Verification appendix (reproducible)

```text
probe script: C:\Users\user\AppData\Local\Temp\opencode\ev02_probe.py (reused; E7/E8 evidence)
go build:    locally succeeds (go1.27.1) after `go mod tidy` (network); execution on :8000 blocked
            by host TCP exclusion 7973-8072 (environmental; CI covers via ubuntu, green on both commits)
static checks:
   git grep -n "runtime_supported"          # backend_contract.py:127, backends.py:39,99, candidate_evaluator.py:81, evolution.py:72,108
   git grep -n '"verified": True'           # candidate_evaluator.py:76 (only one)
   git grep -n "evaluation_mode" autonomous-api/app/engine/candidate_evaluator.py
```

*Internal analysis doc — working tree only, not tracked (per AGENTS.md .md policy).*
