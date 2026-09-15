# Phase 31 — Execution Contract (No-Workload-Reduction)

**Status:** CONSTITUTIONAL
**Scope:** All `pytest -m certification` runs (Phase 31.1–31.5)
**Owner:** Governance Kernel

This contract is the authoritative answer to: *"How do we make the
certification suite faster without weakening the certification?"* It
distinguishes **evidence production** from **evidence validation** and
codifies the optimizations that are permitted (fixture reuse, immutable
evidence reuse, artifact caching, parallel independent phases, process
isolation, Docker layer caching, test scheduling) versus the
optimizations that are forbidden (workload reduction, evidence
substitution, skipped stages, weakened assertions, mutable state reuse).

---

## 1.5 — The infra-storm side-channel (LEARN-ONLY, off the verdict chain)

A separate, hash-chained JSONL ledger —
`release/evidence/cbc1-{wave}-infra-storm.jsonl` — captures every
**infrastructure-classified** trial failure during a Campaign B wave.

It exists because:

  - Infrastructure failures (registry network outages, Docker daemon
    failures, port exhaustion) are the dominant failure mode in
    real-Docker waves.
  - Per the master prompt §13, these failures are **LEARN-ONLY** — they
    must not trigger evolution candidates.
  - But the signal is valuable for post-wave platform engineering
    (e.g. "registry instability caused N% of NOT_CERTIFIED trials").
  - And the signal must NOT pollute the verdict ledger, because the
    verdict ledger feeds the certification chain.

Design rules (see
[`certification/evidence/infra_storm.py`](../evidence/infra_storm.py)
for the implementation):

  1. **Separate file.** `cbc1-{wave}-infra-storm.jsonl` is never written
     to by the verdict ledger, and the verdict ledger is never written
     to by the infra-storm ledger.
  2. **Independent hash chain.** SHA-256 of `prev_hash + canonical(body)`,
     same primitive as `EvidenceLedger`, but a separate chain head.
  3. **Content-addressable schema.** Every record carries `schema_id`
     (`tiannara.infra_storm.record`), `schema_version`, `record_hash`,
     `cause`, `feedback_domain`, `cause_mark`, `retry_signatures`.
  4. **One-way correlation only.** Records carry `trial_id` so an
     auditor can look up the parent trial in the verdict ledger by id.
     The verdict ledger does NOT carry any reference to the
     infra-storm ledger.
  5. **Never feeds the certifier.** `CertificationHarness`,
     `CertificationRig`, and the Phase 31.5 certification event read
     only the verdict ledger.
  6. **Never auto-evolves.** A record in the infra-storm ledger is
     by construction `repair_eligible=False`. It is a learn signal,
     not an action.
  7. **Optional, opt-out.** `CBC1_INFRA_STORM=0` disables the side
     channel (default: enabled). The verdict ledger's behavior is
     identical in both modes.

---

## 1. Invariant — certification semantics are non-negotiable

The following are locked. They are not subject to performance
optimization, scheduling changes, or release pressure:

1. **Scale levels are real.** The certification must run the full
   `26 → 100 → 500` scale climb. A 26-only certification is a
   *prototype* certification, not a Phase 31 certification.
2. **The backend matrix is real.** All 7 backends × 26 intents = 182
   cases must compile and verify.
3. **The failure taxonomy is real.** All 26 intents × 7 backends ×
   5 failure categories = 910 injection cases must be exercised.
4. **Calibration is fresh.** Calibration MUST re-measure the campaign
   under the same campaign-id; it must not be cached across
   certification runs (it may be cached within a run).
5. **The canary is re-run.** A certification that trusts yesterday's
   evidence without reproducing it is one step from trusting
   yesterday's claim. The canary RE-RUNS the canary subset against
   the live backend matrix and confirms reproducibility.
6. **The novelty-grounding check is live.** It must exercise the
   generative capacity, not corpus recall.
7. **The verdict is bounded, never inflated.** `CERTIFIED` /
   `QUALIFIED_PARTIAL` / `NOT_CERTIFIED` with every bound declared
   in the verdict, not in a footnote.
8. **Anti-vacuity applies.** A certification that produces fewer
   evidence entries than a re-run of the same campaign under the
   same seed is invalid; the certification produces a *new*
   evidence entry that *aggregates and verifies* pre-produced
   evidence.

No reduction of any of the above is acceptable to make the suite
faster.

---

## 2. What is allowed — the permitted optimization surface

The following optimizations are explicit and auditable. They
**re-use evidence that has been produced once and is now
immutable**, they do **not** skip evidence production, and they
preserve the invariants of §1.

### 2.1 Session-scoped evidence bundle

Phase 31.1–31.4 evidence (calibration, matrix, taxonomy, scale-ramp)
must be produced exactly **once per pytest session** and shared via
session-scoped fixtures in `tests/conftest.py`:

  - `phase31_base` — the single `CampaignReadinessHarness` whose
    ledger accumulates the entire Phase 31 chain.
  - `phase31_calibration` — `CalibrationReport`.
  - `phase31_matrix` — `MatrixReport` (182 cases, all 7 backends).
  - `phase31_taxonomy` — `TaxonomyValidationReport` (910 cases).
  - `phase31_ramp` — `ScaleRampReport` (26 / 100 / 500 climb).
  - `phase31_evidence` — the immutable
    `CertificationEvidence(calibration, matrix, taxonomy, ramp)`
    bundle that the certification consumes.

Pytest's session scope guarantees that all
31.1 / 31.2 / 31.3 / 31.4 / 31.5 tests in a single `pytest` invocation
read the same evidence objects from the same ledger.

### 2.2 Immutable evidence consumption

The certification (`test_r29_31_5_certification.py`) MUST consume the
shared `phase31_evidence` bundle. The certifier independently
verifies the chain — it never rebuilds the evidence its verification
depends on.

  - `CertificationRig.__init__(base, evidence)` — the rig takes the
    *already-produced* evidence and exposes it to the certification
    tests. Building evidence inside the rig is forbidden when a
    shared fixture is in scope.
  - The canary RE-RUN is still permitted (and required) because the
    canary's purpose is to reproduce the canary subset against the
    *current* backend, not to repeat the entire campaign.

### 2.3 Per-test scope for non-shared harnesses

`drift_ramp_harness` and `envelope_ramp_harness` in 31.4 build
their own special-purpose ramps (drifted corpus, 1ms budget).
They are not shared with the standard ramp. Each is module-scoped
to share its report within the 31.4 module.

### 2.4 Marker-based test tiering

`pyproject.toml` declares two markers:

  - `docker_integration` — opt-in for real-Docker tests; default
    `python -m pytest` excludes them.
  - `certification` — the authoritative Phase 31 release gate; the
    default run excludes it. The release pipeline MUST run
    `python -m pytest -m certification` before any new B3 wave.

The default run (`python -m pytest`) MUST remain fast enough to be
the dev loop (~12 min for ~2786 tests).

### 2.5 Process isolation, layer caching, artifact reuse

  - Process isolation (per test) is permitted where it does not
    require re-running the campaign; it is forbidden where it would
    re-run a non-fixture campaign.
  - Docker layer caching of generated images is permitted.
  - Reusing a generated artifact across tests is permitted
    *when* the artifact is structurally tied to the evidence chain
    (e.g. the shared ramp's per-level results).

### 2.6 Test scheduling (the "tier" architecture)

| Tier | Marker | Default? | Purpose | Cost |
|---|---|---|---|---|
| A | (none) | yes | dev loop, contract checks, classifier/policy/ledger invariants, cbc1 self-repair | ~12 min / ~2786 tests |
| B | `docker_integration` | no (opt-in) | real-Docker gates | depends on Docker |
| C | `certification` | no (release gate) | Phase 31.1–31.5 | ~30+ min / 40 tests |

The release pipeline runs Tier C before any new B3 wave.

---

## 3. What is forbidden — the anti-vacuity surface

The following "optimizations" are **constitutional violations**:

  1. **Workload reduction.** Lowering the scale levels (e.g.
     `26 → 100` only) or removing backends from the matrix.
  2. **Evidence substitution.** Reading pre-computed reports from
     a file that was not produced in the current pytest session.
  3. **Skipped stages.** `@skip` / `xfail` on a stage gate that
     should fail.
  4. **Weakened assertions.** Tolerating a `NOT_READY` verdict
     where the test asserts `READY_FOR_31_5`.
  5. **Mutable state reuse.** Reusing a per-trial mutation across
     tests in a way that could mask a regression.
  6. **Cached "fresh" calibration.** Calibration must re-measure
     within the run; it may not be loaded from a previous run.
  7. **Hidden parallelism.** Running two phases in parallel when
     they share a mutable registry, ledger, or backend instance
     (this would produce evidence that is no longer reproducible
     in serial execution).
  8. **Skipping the canary RE-RUN.** The canary is the
     reproducibility proof; it must run.

---

## 4. Phase-isolation contract (for future parallelization)

Before any two phases are run concurrently, the following must be
proven:

  - They do not share a mutable campaign state.
  - They do not share a port range.
  - They do not share an evidence ledger.
  - They do not share a backend singleton (a `rust-axum` compiler
    instance, a `python-fastapi` process).
  - They can each be run independently in a separate pytest
    invocation and produce equivalent evidence.

Until all five are demonstrated, the certification remains serial.

---

## 5. Audit trail

Every `pytest -m certification` run records:

  - source revision (`git rev-parse HEAD`),
  - environment (`python --version`, `docker --version`),
  - pytest version,
  - session fixture hash (the corpus hash at fixture materialisation),
  - ledger SHA-256 chain head before the certification event,
  - certification event ref,
  - per-dimension verdicts,
  - final verdict.

The certification event is appended to the evidence ledger exactly
once. Re-running the certification produces a new event, never
overwrites the old.

---

## 6. Non-negotiable final answer to "make it faster"

If the certification suite is too slow, the ONLY acceptable
responses are:

  (a) **Use the shared evidence bundle** (this contract, §2.1–2.2).
  (b) **Parallelize independent phases** (this contract, §4).
  (c) **Cache Docker layers / artifacts** (this contract, §2.5).
  (d) **Schedule Tier C out of the dev loop** (this contract, §2.4).

Never:

  (e) Reduce scale levels.
  (f) Skip stages.
  (g) Cache "fresh" calibration across runs.
  (h) Reuse mutable state across tests.
  (i) Trust a non-reproduced canary.

This contract is the boundary.
