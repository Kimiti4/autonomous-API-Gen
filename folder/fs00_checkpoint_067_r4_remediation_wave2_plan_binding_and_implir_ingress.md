# FS-00 Checkpoint CP067-R4 — Remediation Wave 2: Plan Binding and ImplIR Ingress

**IV addendum:** `folder/fs00_checkpoint_067_r4_independent_verification.md` — W04/W05 **`INDEPENDENTLY_VERIFIED`** (Payroll slice).

**Checkpoint status:** **`PARTIAL_EVIDENCE`** — W04/W05 **implemented**; **independent verification pending**; **P0 findings not closed**.

**Authorization:** `release/evidence/cp067_r3_expanded_remediation_authorization_2026-11-08.json` (R1-W04, R1-W05).

**Branch:** `remediation/w12-executable-effect-contract`

---

## 1. Scope executed

| Package | Status | Evidence |
| --- | --- | --- |
| **R1-W04** | `IMPLEMENTATION_PRESENT_UNVERIFIED` | `PlanBindingRecord`, execution gate in orchestration authority |
| **R1-W05** | `IMPLEMENTATION_PRESENT_UNVERIFIED` | Model C guards on orchestration + publication ingress |
| R1-W03 (slice) | `assert_revision_integrity_at_boundary` at ISR/plan gate | W01 helpers |

**Prohibitions observed:** No P0 closure claims; no governed CP068 claims; plan_id surrogate retained (`plan:{digest[:16]}`) alongside full `plan_digest`.

---

## 2. Implementation summary

### R1-W04

| Module | Purpose |
| --- | --- |
| `compiler/core/plan_binding.py` | `PlanBindingRecord`, `compute_plan_digest`, verify helpers |
| `certification/orchestration/plan_binding_gate.py` | `assert_plan_binding_before_compile` |
| `certification/orchestration/authority.py` | Gate before compile; report `plan_binding_digest` |

### R1-W05 (Model C)

| Module | Purpose |
| --- | --- |
| `certification/orchestration/implir_ingress_guard.py` | Trusted path blocks `autonomous-api.implementation_ir`; publication requires `isr.core.revision` |
| `tiannara/application/orchestration/production_ingress.py` | Ingress guard + parameter forwarding |
| `autonomous-api/app/engine/*_gateway.py` | HTTP bridge guards |
| `autonomous-api/app/schemas/orchestration.py` | Optional `isr_ingress_authority` fields |

---

## 3. Tests (this checkpoint)

| Target | Role |
| --- | --- |
| `tests/conformance/test_cp067_r4_plan_binding.py` | Binding record + gate unit tests |
| `tests/orchestration/test_cp067_r4_plan_binding_orchestration.py` | Authority wiring |
| `tests/orchestration/test_cp067_r4_implir_ingress_guard.py` | Model C ingress policy |

---

## 4. Next IV steps

1. Independent verifier lane for plan binding (stale plan digest, cross-workload matrix, tampered JSONL evidence).
2. HTTP ingress adversarial corpus (`implementation_ir` body on CP056/057 routes).
3. W08 full ingress matrix; W10 integration adversarial corpus.
4. Human IV sign-off before W04/W05 → `INDEPENDENTLY_VERIFIED`.

---

## 5. P0 register (unchanged closure)

| ID | Status |
| --- | --- |
| CP067-ISR-002 | **OPEN** — W04 implementation slice only |
| CP067-ISR-003, 008 | **OPEN** — W05 Model C slice only |
| CP068 | **`CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`** |
