# FS-00 Checkpoint CP067-R4-IV — Independent Verification (W04 / W05)

**Status:** **`PARTIAL_EVIDENCE`** — W04 and W05 **`INDEPENDENTLY_VERIFIED`** on **Payroll human ISR** + **policy matrix**; **not universal**; **P0 findings not closed**.

**Verifiers:**
- `certification.isr_independent_verification.plan_binding_oracle.v1`
- `certification.isr_independent_verification.implir_ingress_oracle.v1`

**Evidence:** `release/evidence/cp067_r4_independent_verification_report.json`

---

## Verified

| Package | Checks | Scope |
| --- | --- | --- |
| **R1-W04** | Independent ISR/plan digests; stale record; tampered ISR; orchestration `plan_binding_digest` | Payroll human fixture |
| **R1-W05** | Model C matrix (orch + publication blocks); non-authoritative marker | Policy / ingress guard |

**Not verified:** all workloads, all HTTP routes under adversarial load, full W08 ingress matrix, W10 integration corpus.

---

## Tests

| Suite | Result |
| --- | --- |
| `tests/conformance/test_cp067_r4_independent_verification.py` | **5 passed** |
| R4 implementation regression (plan + orch) | **13 passed** (combined gate run) |
| **Total IV gate** | **18 passed** |

---

## P0 / CP068

- **CP067-ISR-002 / 003 / 008:** risk reduced on governed Payroll orchestration path — **OPEN**
- **CP068:** `CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`
