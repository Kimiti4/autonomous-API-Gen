# FS-00 Checkpoint CP067-R5 — Expanded Verification (Multi-Workload, W08, W10)

**Status:** **`PARTIAL_EVIDENCE`** — expanded IV on **payroll / orders / appointments** + HTTP adversarial slice; **P0 open**; **CP068 conditional**.

**Evidence:** `release/evidence/cp067_r5_independent_verification_report.json`

**Verifier:** `certification.isr_independent_verification.wave5_integration_gate.v1`

---

## Scope delivered

| Work package | Delivered in R5 |
| --- | --- |
| **W04 (multi)** | Independent plan-binding oracle on 3 human workloads |
| **W05** | Policy oracle (re-run) + HTTP **403** on ImplIR orchestration & publication |
| **W08** | `ingress_trust_matrix()` catalog (4 boundaries) + HTTP adversarial tests |
| **W10** | Integration gate = multi-workload W04 + W05 policy (slice) |

**Not delivered:** inventory/projects binding IV, synthesized ISR paths, full publication happy-path, governed CP068.

---

## Tests (this checkpoint)

| Suite | Result |
| --- | --- |
| `tests/conformance/test_cp067_r5_multi_workload_and_matrix.py` | **3 passed** |
| `autonomous-api/tests/test_cp067_r5_http_ingress_adversarial.py` | **3 passed** |

Combined with R4 IV regression: **11 passed** (R5 gate).

---

## P0 register

§N P0 governed statuses after **CP067-P0-IV** ratification (2026-11-08T20:30+03:00): **001/003/008 `CLOSED_SCOPED`**, **002/004 `PARTIAL_REMEDIATION_OPEN`** (see `cp067_p0_closure_human_ratification_2026-11-08.json`).

---

## CP068

`CP068_CONDITIONAL_ISOLATED_TESTING_ONLY` — unchanged.
