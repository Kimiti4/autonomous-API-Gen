# VS-D43 — General Software Autonomy Capability Validation & Live Observatory

**Gate:** VS-D43 (analytical / experimental / evidence-based / bounded / non-production / non-deployment / non-destructive)
**Date:** 2026-09-13
**Baseline:** HEAD `ba952d4` (unchanged; no commits, pushes, deployments made)
**Decision:** **PASS WITH BOUNDED UNKNOWN**

---

## 1. What was validated (experiments)

All experiments used a hermetic lab venv (ephemeral, under the OS temp dir),
scratch Observatory DB, ephemeral generated cell bundles, and the deterministic
template compiler
(`FastAPIHexagonalBackend`, no LLM). Live LLM provider is rejected in this
environment; intent is exercised only through recorded transcripts or UNKNOWN.

| Experiment | Focus | Result |
|---|---|---|
| EXP-1 | Category cells: real generated software | **PASS** — 16/16 cells (13 categories × simple + 3 complex) each: ISR → bundle → syntax gate → independent `pytest` green ("3 passed" each) |
| EXP-2 | Language generality | **NOT DEMONSTRATED** — registry = `fastapi_hexagonal` only; pipeline = + `minimal-container` (Python stub); `generated/observatory` Elixir is inert design text (27 `.ex`, no `mix.exs`) |
| EXP-3 | Failure injection + repair | **PASS WITH BOUND** — injected `main.py` deletion was detected, repaired in 1 attempt (`repaired=true`, fitness build/scan/test/verification = 1.0); **bound**: default `LocalExecutionEnvironment` *simulates* runtime verification (harness pass vs independent `pytest` rc=1) |
| EXP-4 | Epistemic honesty | **PASS** — hermetic missing-transcript refusal rc=1; tampered ledger integrity break rc=1; unknown experiment preserved as `status=UNKNOWN`, unknowns populated, no defaulting |
| EXP-5 | Prior artifacts | **PASS** — prior generated FastAPI services (`testshop`, `monolithshop`) still functional (deps installed): `1 passed` each |
| Frontend | Live data, not mock/static | **PASS** — see §4 |

## 2. Capability matrix (honest envelope)

| Capability | Demonstrated? | Autonomy | Evidence |
|---|---|---|---|
| Intent → working FastAPI service (13 categories) | YES (bounded templates) | A4 | EXP-1 (16/16 pytest-green) |
| Retry / bounded repair | YES (static verification) | A4 | EXP-3 (`repair_attempts=1, repaired=true`) |
| Hermetic intent reasoning | YES (recorded only) | A3 | EXP-4 refusal rc=1 |
| Integrity enforcement | YES | A3 | EXP-4 tamper rc=1; ledger hash chain |
| Honest-UNKNOWN handling | YES | A3 | EXP-4 projection UNKNOWN at state |
| Language-general code output | NO (unbounded) | A0-A2 | EXP-2 registry = 1 backend |
| Real runtime validation | NO (simulated default) | A3 | EXP-3 bound finding |
| Live observability | YES | — | §4, SSE push proof |

Autonomy ladder mapping: rule-guided/bounded goal execution (A3–A4) within the
FastAPI category envelope; autonomy above A5 (supervised execution of
arbitrary-scale novel work) is **not** demonstrated and not claimed.

## 3. Reconciliation: "1,040 cells" formula

Prompt arithmetic `13 × 10 × 8` is reconciled to code: 13 categories × **80 cells**
each = 1,040 (contracted population); **10** variation axes; **8** constituent
exit-gate metrics. No corpus/coverage reconstruction was performed. Sources:
`docs/phase31_certification_closure.md`, `certification/corpus/corpus.py`,
`stratified_corpus.py`.

## 4. Frontend = live data (not mock/static)

- API `http://127.0.0.1:8000` served, in real time: `evidence_count=97`,
  `recent_event_count=195`, 22 experiment subjects, 100 timeline events across
  types `experiment_started/proposed/authorized/running/result`.
- Home page streams via `EventSource /observatory/stream`; push proof: injected
  event `evt-runtime-0f301d60f2621057934b60a4` appeared as a `data:` frame in the
  subscribed stream instantly.
- Frontend source (`lib/api.ts`) uses `cache: "no-store"`; no hardcoded/mock
  payloads exist. All views are served from the scratch Observancy DB.

## 5. Bounded unknowns (carry forward)

1. **Language generality** — unproven beyond Python/FastAPI; claims must not be
   made without new backends. (P-005 conceptually aligned)
2. **Real runtime verification** — harness default is simulated; any "runtime"
   claim needs a real executor (docker/orch) bound to `docker_integration`.
3. **Intent = LLM?** — only recorded hermetic transcripts available here; live
   provider rejected; model-freedom of the generator (no LLM in compiler) is
   proven, not general intelligence.

## 6. Constraints compliance

No commits/pushes/deploys; certification untouched; governance data intact;
baseline unchanged; artifacts file-native + Observatory-observed.

## 7. Next-step options (at executor discretion)

1. **D44 proposal**: implement a 2nd backend (e.g. `fastapi-generic` or a non-FastAPI
   target) + real executor for `docker_integration` runtime, re-run EXP-2/EXP-3.
2. **D45 proposal**: scale EXP-1 to the 1,040-cell matrix (batch light) and emit
   a full cell matrix into the Observatory.
3. **HOLD**: keep D43 as the standing capability envelope; freeze D30-D42 records.