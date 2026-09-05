# R1_D1_ISR_TEST_REPORT (R1-D.1 D8)

**Status:** R1-D.1 Deliverable D8. ISR test report. Index: `folder/R1_D1_ISR_SEMANTIC_MIGRATION.py` (test file), `folder/R1_D1_CANONICAL_INTEGRATION_REPORT.md` (D7).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

---

## 1. Test commands and counts

| Suite | Command | Count | Result | Wall time |
|---|---|---|---|---|
| Tier A | `python -m pytest tests/cbc1/` | 243 | **PASS** | ~260s |
| R1-C | `python -m pytest tests/r1c/` | 15 | **PASS** | ~4s |
| v12 | `python -m pytest tests/v12/` | 23 | **PASS** | ~3s |
| R1-D.1 | `python -m pytest tests/r1d1/` | 21 | **PASS** | ~1s |
| **Combined** | `python -m pytest tests/r1d1/ tests/cbc1/ tests/r1c/ tests/v12/` | **302** | **PASS** | ~50s |

**No failures. No regressions. No new deselections.**

---

## 2. R1-D.1 test coverage

| Test class | Tests | What it verifies |
|---|---|---|
| `TestM01RequirementSemanticObligation` | 5 | M-01: testing-mechanism terms constant exists; pytest/playwright in `REQUIREMENT_REF.ref_id` rejected; valid `ref_id` accepted; missing `ref_id` still rejected (preserved invariant). |
| `TestM02TestingMechanismGeneralPrinciple` | 5 | M-02: pytest/selenium/jest in node properties rejected (CAPABILITY, SERVICE, DATA_MODEL); valid content accepted; case-insensitive matching. |
| `TestM03SecurityByDesign` | 5 | M-03: SECURITY_POLICY node accepted; SECURED_BY edge accepted; EDGE_TYPE_COMPATIBILITY includes SECURED_BY; security-by-design docstring present in source. |
| `TestR1D1ISRRevisionIntegration` | 2 | Integration: valid revision with no testing contamination creates a valid ISRRevision; revision with testing contamination rejected. |
| `TestR1D1CanonicalStillSoleAuthority` | 4 | Invariant: canonical NodeType count = 9, EdgeType count = 8, no new types introduced. |
| **Total** | **21** | |

---

## 3. Semantic coverage

| Migration | Test coverage | Status |
|---|---|---|
| M-01 (requirement) | `TestM01RequirementSemanticObligation` (5 tests) | **COVERED** |
| M-02 (testing anchor) | `TestM02TestingMechanismGeneralPrinciple` (5 tests) | **COVERED** |
| M-03 (security) | `TestM03SecurityByDesign` (5 tests) | **COVERED** |
| M-04 (capability) | None (deferred; breaking change) | **DEFERRED** |
| M-05 (deployment) | None (deferred; breaking change) | **DEFERRED** |
| AC-01 (boundary) | `test_edge_type_compatibility_includes_secured_by` (via M-03) | **COVERED (existing)** |
| AC-02 (content hash) | `test_revision_with_testing_contamination_rejected` (integration) | **COVERED (existing)** |

---

## 4. Negative cases

| Negative case | Test | Status |
|---|---|---|
| Invalid node types | `test_node_with_testing_mechanism_rejected` | **COVERED** |
| Duplicate edge IDs | (existing in `tests/v12/test_isr_gates.py`) | **PRESERVED** |
| Missing `ref_id` | `test_requirement_ref_with_missing_ref_id_still_rejected` | **COVERED** |
| Testing mechanism in `REQUIREMENT_REF` | `test_requirement_ref_with_pytest_in_ref_id_rejected` | **COVERED** |
| Testing mechanism in CAPABILITY | `test_capability_with_pytest_in_properties_rejected` | **COVERED** |
| Testing mechanism in SERVICE | `test_service_with_selenium_in_properties_rejected` | **COVERED** |
| Testing mechanism in DATA_MODEL | `test_data_model_with_jest_in_properties_rejected` | **COVERED** |
| Case-insensitive testing mechanism | `test_testing_mechanism_case_insensitive` | **COVERED** |
| Edge type compatibility violation | (existing) | **PRESERVED** |
| Edge references missing node | (existing) | **PRESERVED** |

---

## 5. Regression tests

| Suite | Before R1-D.1 | After R1-D.1 | Regression? |
|---|---|---|---|
| Tier A (tests/cbc1/) | 243/243 | 243/243 | **NO** |
| R1-C (tests/r1c/) | 15/15 | 15/15 | **NO** |
| v12 (tests/v12/) | 23/23 | 23/23 | **NO** |
| **Combined** | 281/281 | 302/302 (+21) | **NO** |

**Zero regressions. All existing tests pass.**

---

## 6. Adapter coverage

R1-D.1 does **not** introduce any adapter (per D7 §5). The constitutional ISR semantics are migrated directly into `isr/core/`, not through an adapter layer. There is no adapter coverage to report.

---

## 7. Failure modes

| Failure mode | Handling |
|---|---|
| Implementation terms (e.g. `aws`, `fastapi`) in node properties | `ISRInvariantViolation` raised (preserved invariant) |
| Testing mechanism terms (e.g. `pytest`, `playwright`) in node properties | `ISRInvariantViolation` raised (NEW M-01/M-02) |
| Missing `ref_id` on `REQUIREMENT_REF` | `ISRInvariantViolation` raised (preserved invariant) |
| Edge references missing node | `ISRInvariantViolation` raised (preserved invariant) |
| Edge type compatibility violation | `ISRInvariantViolation` raised (preserved invariant) |
| Duplicate edge IDs | `ISRInvariantViolation` raised (preserved invariant) |

All failure modes are **fail-closed** (raise an exception, do not silently coerce to success).

---

## 8. Test execution

```bash
# R1-D.1 tests alone
python -m pytest tests/r1d1/ -v
# 21 passed in 1.04s

# Full regression suite
python -m pytest tests/r1d1/ tests/cbc1/ tests/r1c/ tests/v12/
# 302 passed, 1 deselected in 49.52s
```

---

## 9. Cross-references

- D7: `folder/R1_D1_CANONICAL_INTEGRATION_REPORT.md`
- D9: `folder/R1_D1_GATE_REPORT.md` (next)

---

*End of D8. R1-D.1 test report is complete. 302 tests pass (was 281; +21 R1-D.1). Zero regressions. All 3 MIGRATE semantics are covered. M-04 and M-05 are deferred.*
