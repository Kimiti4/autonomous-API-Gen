# FS-00 Checkpoint CP067-R10 — R1-W10 Independent Integration Gate

**Status:** **`PARTIAL_EVIDENCE`** — governed three-workload slice + HTTP adversarial + governance ratification bundle; **CP068 conditional**.

**Harness:** `certification/isr_independent_verification/wave10_integration_gate.py`

**Verifier:** `certification.isr_independent_verification.wave10_integration_gate.v1`

**Evidence:** `release/evidence/cp067_r10_w10_integration_gate_report.json`

**Tests:** `tests/conformance/test_cp067_r10_w10_integration_gate.py`

## Gates (slice)

| Gate | Scope |
| --- | --- |
| W01–W02 digest | Payroll F-01 / F-04 / F-05 independent digest |
| W04 | Plan binding oracle × payroll, orders, appointments |
| W06 B-04 | Obligation oracle × same workloads |
| W05 | ImplIR / publication policy oracle |
| W02 inventory | F-01..F-17 + F-06 canonicalization oracle |
| W08 matrix | Ingress catalog (slice; not all boundaries `IMPLEMENTED`) |
| W08 HTTP | `test_cp067_r5_http_ingress_adversarial` subprocess |
| Governance | All five §N P0 `CLOSED_SCOPED` ratification JSON on file |

**Not claimed:** `CP068_READY_FOR_GOVERNED_RUNTIME_CONFORMANCE`, universal ISR, full ingress matrix enforcement on every route.
