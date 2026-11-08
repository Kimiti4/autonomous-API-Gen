# FS-00 Checkpoint CP067-R6 — W06 B-04 Obligation Verifier

**Status:** **`PARTIAL_EVIDENCE`** — obligation diff + deterministic re-lowering oracle shipped; **CP067-ISR-002** IV stage may advance pending governance re-ratification; **W08 HTTP:** `wave6_http_verification` — **3/3** adversarial HTTP tests pass locally; evidence `release/evidence/cp067_r6_http_ingress_verification_report.json` (API routes **not** yet on remote).

**Deliverables:**

| Item | Path |
| --- | --- |
| Verifier | `certification/bridges/b04_lowering_obligation_verifier.py` |
| Oracle | `certification/isr_independent_verification/b04_lowering_oracle.py` |
| Tests | `tests/bridges/test_b04_lowering_obligation_verifier.py` |
| P0 harness | `p0_closure_harness._evaluate_002` uses B-04 oracle on R5 workloads |

**Scope:** Preserved ISR→plan behavioral ID sets + `CAUSES_EFFECT` bindings + `plan_id`/`isr_id` binding; explicit loss inventory for topology/requirement nodes; **no** inverse `plan→ISR` compiler.

**Governance (supplement):** Amos Kimiti Kariuki ratified **CP067-ISR-002** → **`CLOSED_SCOPED`** (`release/evidence/cp067_isr002_supplement_ratification_2026-11-08.json`, 2026-11-08T20:45+03:00). Acceptance criterion: **`b04-obligation-diff-verifier-v1`**.
