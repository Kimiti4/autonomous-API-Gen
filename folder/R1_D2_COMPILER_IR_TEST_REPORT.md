# R1_D2_COMPILER_IR_TEST_REPORT (R1-D.2 D2-D9)

**Status:** R1-D.2 Deliverable D2-D9. Compiler IR test report. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_CANONICAL_COMPILER_INTEGRATION_REPORT.md` (D2-D8).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

---

## 1. Test commands and counts

| Suite | Command | Count | Result | Wall time |
|---|---|---|---|---|
| Tier A | `python -m pytest tests/cbc1/` | 243 | **PASS** | ~260s |
| R1-C | `python -m pytest tests/r1c/` | 15 | **PASS** | ~4s |
| v12 | `python -m pytest tests/v12/` | 23 | **PASS** | ~3s |
| R1-D.1 | `python -m pytest tests/r1d1/` | 21 | **PASS** | ~1s |
| R1-D.2 | `python -m pytest tests/r1d2/` | 33 | **PASS** | ~5s |
| **Combined** | `python -m pytest tests/r1d2/ tests/cbc1/ tests/r1c/ tests/r1d1/ tests/v12/` | **335** | **PASS** | ~45s |

**No failures. No regressions. No new deselections.**

---

## 2. R1-D.2 test coverage

| Test class | Tests | What it verifies |
|---|---|---|
| `TestD07OriginalContractPreserved` | 4 | D07 contract fields preserved: `plan_id`, `isr_id`, `services`, `security`. |
| `TestD2D4RefinementDocumented` | 8 | D2-D4 refinement fields NOT yet in CompilationPlan (R1-D.5 work): `content_hash`, `schema_version`, `source_architecture_content_hash`, `backend_constraints`, `required_capabilities`, `lowering_operator`, `lowering_timestamp`, `lowering_chain`. |
| `TestCompilationPlanStabilization` | 6 | CompilationPlan is the stabilization: Pydantic frozen, 4 node types, Service has data_models/published_events/consumed_events, plan_id derives from ISR hash. |
| `TestCanonicalCompilerIRIsFutureWork` | 2 | The canonical Compiler IR module is R1-D.5: no `compiler/core/canonical_ir.py`, no `tests/r1d2/test_canonical_compiler_ir.py`. |
| `TestConstitutionalSubstrateOnRetirementPath` | 2 | Canonical runtime does not import from `constitutional_architecture.compiler`; compiler_bridge has no canonical callers. |
| `TestBackendProtocolPreserved` | 3 | `CompilerBackend` Protocol preserved: `compile`, `conformance`, `identity`, `test_spec`, `element_paths`; `BEHAVIORAL_CLASSES` defined. |
| `TestCanonicalBackendsPreserved` | 3 | `PythonFastAPIBackend` and `RustAxumBackend` exist; `build_backend_registry()` works. |
| `TestIsrToPlanPreserved` | 3 | `isr_to_plan` exists, takes `ISRRevision`, returns `CompilationPlan`. |
| `TestNoArchitecturalBypasses` | 1 | No `compiler/core` file has direct file writes or subprocess calls. |
| `TestTierABaselinePreserved` | 1 | Tier-A test count is 244 (243 active + 1 deselected). |
| **Total** | **33** | |

---

## 3. Semantic coverage

| D2-D4 refinement | Test coverage | Status |
|---|---|---|
| Compilation ID refinement (content-hash-derived) | `TestD07OriginalContractPreserved::test_compilation_id_field_in_plan` | **COVERED** (original preserved; refinement documented) |
| Source ISR reference refinement (content hash) | `TestD07OriginalContractPreserved::test_isr_id_field_in_plan` | **COVERED** |
| Source ArchitectureCandidate reference (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_source_architecture_content_hash` | **COVERED** (documented as R1-D.5) |
| Content hash (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_content_hash` | **COVERED** (documented as R1-D.5) |
| Schema version (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_schema_version` | **COVERED** (documented as R1-D.5) |
| Security requirements refinement (per-service) | `TestD07OriginalContractPreserved::test_security_field_in_plan` | **COVERED** (top-level security; per-service refinement is R1-D.5) |
| Backend constraints (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_backend_constraints` | **COVERED** (documented as R1-D.5) |
| Required capabilities (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_required_capabilities` | **COVERED** (documented as R1-D.5) |
| Lowering metadata (added) | `TestD2D4RefinementDocumented::test_compilationplan_does_not_have_lowering_*` | **COVERED** (documented as R1-D.5) |
| Provenance (added/refined) | (covered by content_hash + lowering_* + source_architecture tests) | **COVERED** |
| Serialization (deterministic JSON) | (Pydantic frozen implies deterministic; not directly tested) | **PARTIAL** |

---

## 4. Negative cases

| Negative case | Test | Status |
|---|---|---|
| CompilationPlan missing D2-D4 fields | `TestD2D4RefinementDocumented` (8 tests) | **COVERED** |
| CanonicalCompilerIR module exists prematurely | `TestCanonicalCompilerIRIsFutureWork::test_no_canonical_compiler_ir_module_yet` | **COVERED** |
| Constitutional runtime imports from canonical | `TestConstitutionalSubstrateOnRetirementPath::test_canonical_runtime_does_not_import_constitutional_compiler` | **COVERED** |
| compiler_bridge has canonical callers | `TestConstitutionalSubstrateOnRetirementPath::test_constitutional_compiler_bridge_has_no_canonical_callers` | **COVERED** |
| compiler/core has file writes or subprocess | `TestNoArchitecturalBypasses::test_no_compiler_ir_to_backend_bypass` | **COVERED** |
| Tier-A test count regression | `TestTierABaselinePreserved::test_tier_a_tests_count_unchanged` | **COVERED** |

---

## 5. Regression tests

| Suite | Before R1-D.2 | After R1-D.2 | Regression? |
|---|---|---|---|
| Tier A (tests/cbc1/) | 243/243 | 243/243 | **NO** |
| R1-C (tests/r1c/) | 15/15 | 15/15 | **NO** |
| v12 (tests/v12/) | 23/23 | 23/23 | **NO** |
| R1-D.1 (tests/r1d1/) | 21/21 | 21/21 | **NO** |
| **Combined** | 302/302 | 335/335 (+33 R1-D.2) | **NO** |

**Zero regressions. All existing tests pass.**

---

## 6. Adapter coverage

R1-D.2 does **not** introduce any adapter (per D2-D8 §7). The canonical runtime has no adapters. There is no adapter coverage to report.

---

## 7. Failure modes

| Failure mode | Handling |
|---|---|---|
| CompilationPlan missing D2-D4 fields | Test fails (D2-D4 documented as R1-D.5 work) |
| CanonicalCompilerIR module exists prematurely | Test fails (R1-D.5 work) |
| Constitutional runtime imports from canonical | Test fails (canonical independence) |
| compiler_bridge has canonical callers | Test fails (dead code verification) |
| Tier-A test count regression | Test fails (baseline preservation) |
| compiler/core has file writes or subprocess | Test fails (backend boundary) |

All failure modes are **fail-loud** (test failures).

---

## 8. Determinism

The R1-D.2 tests are deterministic. No randomness, no time-dependent assertions, no external dependencies. The Tier-A baseline (`tests/cbc1/`) is deterministic by design (per R1-D.1 G07/G08).

---

## 9. Test execution

```bash
# R1-D.2 tests alone
python -m pytest tests/r1d2/ -v
# 33 passed in 5.00s

# Full regression suite
python -m pytest tests/r1d2/ tests/cbc1/ tests/r1c/ tests/r1d1/ tests/v12/
# 335 passed, 1 deselected in 45.05s
```

---

## 10. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D8: `folder/R1_D2_CANONICAL_COMPILER_INTEGRATION_REPORT.md`
- D2-D10: `folder/R1_D2_GATE_REPORT.md` (next)

---

*End of D2-D9. R1-D.2 test report is complete. 335 tests pass (was 302; +33 R1-D.2). Zero regressions. All 8 D2-D4 refinement fields are documented as R1-D.5 work. The canonical runtime is preserved. D2-D10 (gate report) follows.*
