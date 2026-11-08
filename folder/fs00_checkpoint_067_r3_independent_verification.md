# FS-00 Checkpoint CP067-R3-IV — Independent ISR Digest Verification (Wave 1)

**Checkpoint status:** **`PARTIAL_EVIDENCE`** — independent verification **recorded** for W01/W02 **+ Tier B (F-04/F-05)** on **Payroll human ISR slice**; **P0 findings not closed**; **W03–W10 largely not implemented**.

**Verifier identity:** `certification.isr_independent_verification.digest_oracle.v1` (structural separation from generator/orchestration success paths).

**Human authorization:** `release/evidence/cp067_r3_expanded_remediation_authorization_2026-11-08.json` (Amos Kimiti Kariuki).

---

## 1. Evidence artifacts

| Artifact | Path |
| --- | --- |
| Oracle report (Payroll fixture) | `release/evidence/cp067_r3_independent_verification_report.json` |
| Expanded package authorization | `release/evidence/cp067_r3_expanded_remediation_authorization_2026-11-08.json` |

---

## 2. What was independently verified

| Check | Method | Result |
| --- | --- | --- |
| F-01 content digest | Oracle `sha256(canonical_bytes_f01)` vs `ISRRevision.content_hash` | **PASS** (Payroll) |
| F-04 plan bytes | `canonical_bytes_f04` determinism via `isr_to_plan` | **PASS** |
| F-05 contract digest | Oracle bytes vs `contract_digest()` | **PASS** |
| Cross-domain policy | Constitutional vs certification envelope substitution | **FAIL_CLOSED** (expected) |
| Tampered digest | Negative test in conformance suite | **REJECT** |

**Not verified in this checkpoint:** all workloads, constitutional F-06 production ingress, W04 plan binding execution gate, W05 ImplIR enforcement, W08 full ingress matrix, W10 integration adversarial corpus.

---

## 3. Tests executed

| Command | Result |
| --- | --- |
| `tests/conformance/test_cp067_r3_independent_isr_digest_verification.py` | **3 passed** |
| `tests/isr/test_cp067_tier_b_canonicalization.py` | **3 passed** |
| `tests/isr/test_cp067_r3_w01_w02_digest_and_canonicalization.py` | **10 passed** (regression) |

**Total IV gate:** **16 passed**

---

## 4. Work-package verification status

| Package | verification_status |
| --- | --- |
| R1-W01 | `INDEPENDENTLY_VERIFIED` (F-01 slice + orchestration gate present; not universal) |
| R1-W02 | `INDEPENDENTLY_VERIFIED` (Tier A + Tier B contracts; not 17 families) |
| R1-W03 | `NOT_VERIFIED` (helper only) |
| R1-W04 … W10 | `NOT_VERIFIED` / not implemented |

---

## 5. P0 register

All **five** §N P0 findings remain **`OPEN`**. CP067-ISR-001 has **reduced risk** on F-01 Payroll orchestration path only — **not closed**.

---

## 6. CP068

**`CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`** — unchanged.
