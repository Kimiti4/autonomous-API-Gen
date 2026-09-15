# VS-D44 — Multi-Backend & Real Executor Validation (STOP)

**Gate:** VS-D44 (analytical / experimental / evidence-based / bounded / non-production / non-deployment)
**Date:** 2026-09-15
**Baseline:** `f73ef9e` (D44-PREP) — experiment executed against source edits listed in §5
**Decision:** **PASS WITH BOUNDED UNKNOWN**

Follows `OBSERVATORY_D44_PREP.md` (COMPLETE). Authorization granted for D1 (wire
existing `GoHexagonalBackend`), D2 (Docker Desktop + `golang:1.22-alpine` real
toolchain), D3 (HUMAN-DIRECTED selection `target_backend="go_hexagonal"`; no
`_CATEGORY_BACKENDS` edit), and the full experiment *"Full fault → REAL rebuild →
re-oracle"*.

---

## 1. What was demonstrated (single representative cell)

One representative intent → Tiannara pipeline (`go_hexagonal` backend) → REAL Go
build in `golang:1.22-alpine` → REAL process launch → independent HTTP oracle →
induced deterministic fault → REAL rebuild fails → relaunch unavailable → real
diagnosis → deterministic restore → REAL rebuild + gate → re-oracle green.

| Phase | Chain seq | Evidence (event id) | Result |
|---|---|---|---|
| start / P1 compile | 0–1 | `evt-governance-a14514f204c51b4e25038d4c`, `evt-evidence-01fd90b40c15ca61bec69d95` | ISR → go_hexagonal bundle emitted, artifact tree hashed |
| P2 authentic gate (good) | 2 | `evt-evidence-5322d33e72751899f0f7df34` | **passed=True**, exit 0, `DockerExecutionEnvironment`, **827.2 s cold** (`go build ./... && go test ./...`) |
| P2b baseline live | 3 | `evt-evidence-ceec9a5a47c2cbdfa6c13605` | real build rc=0, launch healthy, oracle **O1–O5 = 200/200/201/200/404** |
| P3 fault inject | 4 | `evt-evolution-8550dd6132eaeffd3ac83259` | `internal/domain/models.go` overwritten; pre `0e8b1a47…` → post `7610639d…` (sole diff attributable) |
| P4/P4b rebuild + gate faulted | 5 | `evt-evidence-376e2376f28016eae7fd9db3` | rebuild **rc=1**; gate **passed=False**, exit 1, `undefined: OrderModel` (warm-cache variant, 557.8 s) |
| P5 relaunch (faulted) | 6 | `evt-runtime-b2e749a482c26222666bf6b6` | service unavailable — all five oracle probes RemoteDisconnected |
| P6 diagnosis | 7 | `evt-evolution-c4bc114fe131db3244f9e8a5` | **dependency_failure**, severity high, confidence 0.88, `undefined: OrderModel` |
| P7 bounded restore | 8 | `evt-evolution-72b91f30439ea7afe6f266b9` | deterministic pipeline re-materialization; `restored_matches_pre_fault=true` |
| P8 rebuild + gate restored | 9 | `evt-evidence-2ad144006fc2bbb8fe21acca` | rebuild **rc=0**; gate **passed=True** exit 0 (warm-cache variant, 328.9 s) |
| P8 re-oracle after repair | 10 | `evt-evidence-a3bb1d094cffd29f1668bffb` | oracle **O1–O5 = 200/200/201/200/404** again |
| P9 summary / stop | 11 | `evt-governance-61601505bac6b6f9450a622e` | full summary; chain integrity **OK (12 records)** |

Canonical chain: `observatory/evidence/d44-evidence-canonical.jsonl` (hash-chained,
seed `tiannara-d44-chain-v1`); per-phase transcripts under `observatory/evidence/d44/`.

## 2. Predicate verdicts (vocabulary: DEMONSTRATED / PARTIAL / UNKNOWN / UNTESTED / BLOCKED / NOT_APPLICABLE / INSUFFICIENT_EVIDENCE)

| Predicate | Verdict | Evidence |
|---|---|---|
| BACKEND-01 / P1 — a genuine second backend exists → is selected → builds → launches → serves a real workload | **DEMONSTRATED** | dormant Phase 19 `GoHexagonalBackend` (stdlib `net/http`) wired via D1; `target_backend="go_hexagonal"` resolved through the real pipeline (HUMAN-DIRECTED, D3); P2b/P8-re-oracle green against live process |
| EXEC — real executor top-to-bottom (build → launch → HTTP oracle, not simulated harness) | **DEMONSTRATED** | experiment scaffolding per PREP-02 REAL_EXECUTOR row; oracle authored independently of Tiannara's verifier |
| P2 — Tiannara's own gate truthfulness (authentic `DockerExecutionEnvironment`) | **DEMONSTRATED** | cold authentic gate passed=True (827.2 s) on good bundle; honest passed=False on faulted bundle |
| P3 — expected vs observed comparison per oracle | **DEMONSTRATED** | P2b and re-oracle matched expected O1–O5 exactly (200/200/201/200/404); failed-launch correct (null statuses, connection refused) |
| P4 — real-diagnosis path (failure → classification) | **DEMONSTRATED** | `FailureClassifier` → dependency_failure 0.88 | high | `undefined: OrderModel` across repositories.go |
| P5 — bounded deterministic repair, verifiable | **DEMONSTRATED** (bounded) | restore = pipeline re-materialization (not adaptive mutation); pre/post-hash match; gate + re-oracle green |
| EPISTEMIC — verdicts tied to observed runtime outputs, statuses carried in events | **DEMONSTRATED** | events carry observed oracle statuses, exit codes, hashes; severities error/warning per phase |
| PROVENANCE — attributable, tamper-evident record | **DEMONSTRATED** | 12-record SHA-256 chain (seed-bound, link-checked OK-equivalent after verifier correction); every record binds its event id; fault attributable to a single file diff |
| OBSERVATORY_LIVE — lifecycle visible to live Observatory | **DEMONSTRATED** | all 12 phases emitted as Observatory events (ids above) through the real API |
| TIANNARA_EXECUTION_LIVE — real Go process serving real HTTP | **DEMONSTRATED** | `golang:1.22-alpine` container launcher; `net/http` server; real TCP + HTTP responses |
| Autonomy ladder | A2/A3 realism (build+runtime verified generation); bounded A4 repair path; **no A5/A6 adaptive mutation, no A7/A8** | restore deterministic; no open-ended evolution invoked |

## 3. Known bounds (PASS WITH BOUNDED UNKNOWN)

1. **Coverage** — a single representative cell (one intent/category). NOT the
   1,040-cell matrix (that is the D45 gate). No cross-category generalization claim.
2. **Selection attribution** — go backend was HUMAN-DIRECTED. `_CATEGORY_BACKENDS`
   (`application/campaign/harness.py:120-131`) is unchanged, so Tiannara's *own*
   campaign policy still never selects go on its own; autonomous per-intent backend
   choice (A4+) remains untested.
3. **Gate performance variant** — the authentic cold `DockerExecutionEnvironment`
   gate ran once at P2 (827.2 s). P4b and P8 gates used a byte-identical
   `go build ./... && go test ./...` under the same image with a persistent named
   GOCACHE volume (it still took 557.8 s / 328.9 s in this environment). This is a
   recorded, transparent, **performance-only** substitution — the CLI/log/semantics
   are unchanged. Re-running those two gates cold is possible but not required for
   verdicts here.
4. **Failure taxonomy** — exactly **one** declared category exercised
   (dependency_failure). build_failure / test_failure / type_failure /
   syntax_failure / runtime_failure remain unexercised in this cell.
5. **Repair semantics** — restore is deterministic re-materialization of the ISR
   through the compiler, not adaptive evolutionary mutation. It proves bounded
   repair within a goal, not self-adoption of novel solutions.
6. **Runtime realism ceiling** — in-memory single-node `net/http` service; no real
   database/caching/distribution; language generality proven for Go stdlib only.

## 4. Host facts

Go is still **not** installed on the host; all real Go execution ran inside
`golang:1.22-alpine` (Docker Desktop running, daemon 29.7.2). Rust/Elixir/Node
remain host-installed alternatives with **no** Tiannara backend authored.

## 5. Source changes made for D44 (all under this gate's authorization)

- `tiannara/bootstrap.py` — import + register `go_hexagonal` in the pipeline
  backends dict (D1; additive, no default behavior changed).
- `tiannara/application/compiler/__init__.py` — export `GoHexagonalBackend`.
- `tiannara/application/compiler/go_hexagonal_backend.py` — add the
  `compile(isr, genome, output_dir)` port adapter + `_system_model()` so the
  dormant backend is pipeline-conformant (D44 conformance change).
- Added docs: `OBSERVATORY_D44_PREP.md/.json`, this `OBSERVATORY_D44_MULTI_BACKEND_EXECUTOR.md/.json`.
- Added evidence: `observatory/evidence/d44-evidence-canonical.jsonl` + `observatory/evidence/d44/*.json`.

## 6. Constraints compliance

No production deployment; no D45 work; no credentials; `certification/` verdict
history untouched; no gate weakened (warm-cache gates are additive lab-side, the
pipeline's own gate path is unchanged); commit/push performed only under explicit
user authorization (this message authorized pull/CI-closure/push).

## 7. Recommendations carried forward

- **Next capability gate (per user's roadmap):** CI/evidence closure for the
  pulled tracing/metrics/rate-limiting lowerers (consume actual GitHub Actions
  results, not code presence), then timeout → retry → circuit-breaker lowerers in
  the resilience layer, then cache/backends/middleware/security-policy lowering.
- Keep the rule: a genome capability contributes fitness only when it has a real
  lowerer plus artifact+runtime evidence.
- D44's REAL_EXECUTOR scaffolding stays out of bootstrap defaults; graduate it to
  a named `docker_integration` tier if the next gate requires recurring real builds.