# R1_D2_COMPILER_CONSUMER_MIGRATION (R1-D.2 D2-D6)

**Status:** R1-D.2 Deliverable D2-D6. Compiler consumer migration. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md` (D2-D5).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

---

## 1. Purpose

Inventory and classify all consumers of Compiler IR representations. For each: consumer, current representation, canonical representation, migration action, status, risk, tests.

---

## 2. Canonical CompilationPlan consumers (10 consumers, KEEP)

| Consumer | Path | Import | Migration action | Status | Risk | Tests |
|---|---|---|---|---|---|---|
| Plan builder | `certification/campaign/plan_builder.py:13-14, 142-144` | `compiler.core.lowering.isr_to_plan`, `CompilationPlan` | None | KEEP | None | `tests/cbc1/test_plan_builder.py` |
| Campaign runner | `certification/campaign/runner.py:10-13` | `CompilationPlan`, `CHECKER`, `GeneratedRepository`, `build_repository`, `BEHAVIORAL_CLASSES` | None | KEEP | None | `tests/cbc1/test_campaign_*.py` |
| Verdict | `certification/campaign/verdict.py:8` | `CompilationPlan` | None | KEEP | None | `tests/cbc1/test_verdict.py` |
| Verify campaign | `certification/campaign/verify_campaign.py:8` | `CompilationPlan` | None | KEEP | None | `tests/cbc1/test_*.py` |
| Campaign A | `certification/campaign/campaign_a.py:20-23` | `compiler.core.*` | None | KEEP | None | `tests/cbc1/test_campaign_a.py` |
| Campaign B | `certification/campaign/campaign_b.py:20-23` | `compiler.core.*` | None | KEEP | None | `tests/cbc1/test_campaign_b.py` |
| Stub stages | `certification/stages/stub_stages.py:32` | `compiler.core.*` | None | KEEP | None | `tests/cbc1/test_*.py` |
| Docker stages | `certification/stages/docker_stages.py:188` | `compiler.core.*` | None | KEEP | None | `tests/cbc1/test_*.py` |
| Independent verify | `certification/stages/independent_verify.py:33` | `compiler.core.*` | None | KEEP | None | `tests/cbc1/test_*.py` |
| Provenance bundle | `certification/provenance/bundle.py:116` | `plan.model_dump()` (SHA-256 hash) | None | KEEP | None | `tests/cbc1/test_*.py` |

**Total: 10 canonical CompilationPlan consumers, all KEEP (no migration required).**

---

## 3. Constitutional compiler consumers (4 consumers, LEGACY → RETIRE)

| Consumer | Path | Import | Migration action | Status | Risk | Tests |
|---|---|---|---|---|---|---|
| Gen-C end-to-end | `constitutional_architecture/tests/test_end_to_end.py:68, 567` | `constitutional_architecture.compiler.*` | None | LEGACY → RETIRE (R1-D.5) | None (not in Tier A) | (constitutional; not in canonical baseline) |
| Gen-C init | `constitutional_architecture/compiler/__init__.py:17` | `constitutional_architecture.compiler.backends.fastapi_backend` | None | LEGACY → RETIRE (R1-D.5) | None | (constitutional) |
| Gen-C pipeline | `constitutional_architecture/compiler/pipeline.py:66` | `constitutional_architecture.compiler.backends.fastapi_backend` | None | LEGACY → RETIRE (R1-D.5) | None | (constitutional) |
| Gen-C backends init | `constitutional_architecture/compiler/backends/__init__.py:11` | `constitutional_architecture.compiler.backends.fastapi_backend` | None | LEGACY → RETIRE (R1-D.5) | None | (constitutional) |

**Total: 4 Gen-C consumers, all LEGACY → RETIRE (R1-D.5).**

---

## 4. Per-category compiler consumers (~11 consumers, LEGACY → RETIRE)

| Consumer | Path | Import | Migration action | Status | Risk | Tests |
|---|---|---|---|---|---|---|
| Build system test | `tests/test_build_system.py:5-8` | `constitutional_architecture.compilers.backend.fastapi.compiler` | None | LEGACY → RETIRE (R1-D.5) | None (not in Tier A) | (test) |
| Backend compiler test | `tests/test_backend_compiler.py:5` | `constitutional_architecture.compilers.backend.fastapi.compiler` | None | LEGACY → RETIRE | None | (test) |
| Deployment compiler test | `tests/test_deployment_compiler.py:3-7` | `constitutional_architecture.compilers.deployment.cicd.compiler` | None | LEGACY → RETIRE | None | (test) |
| Documentation compiler test | `tests/test_documentation_compiler.py:5` | `constitutional_architecture.compilers.documentation.markdown.compiler` | None | LEGACY → RETIRE | None | (test) |
| Operational compiler test | `tests/test_operational_compiler.py:6` | `constitutional_architecture.compilers.operational.intelligence.compiler` | None | LEGACY → RETIRE | None | (test) |
| React compiler test | `tests/test_react_compiler.py:5` | `constitutional_architecture.compilers.frontend.react.compiler` | None | LEGACY → RETIRE | None | (test) |
| Runtime policy compiler test | `tests/test_runtime_policy_compiler.py:3` | `constitutional_architecture.compilers.runtime_policy.compiler` | None | LEGACY → RETIRE | None | (test) |
| Terraform compiler test | `tests/test_terraform_compiler.py:5-8` | `constitutional_architecture.compilers.infrastructure.terraform.compiler` | None | LEGACY → RETIRE | None | (test) |
| Test compiler test | `tests/test_test_compiler.py:3` | `constitutional_architecture.compilers.testing.pytest.compiler` | None | LEGACY → RETIRE | None | (test) |
| Capability compiler tests | `tests/test_cap_*.py` | `constitutional_architecture.compilers.*` | None | LEGACY → RETIRE | None | (test) |
| Backend conformance test | `tests/test_r29_10_7_backend_conformance.py:44` | `constitutional_architecture.compilers.backend.fastapi.compiler` | None | LEGACY → RETIRE | None | (test) |

**Total: ~11 per-category compiler consumers, all in tests, all LEGACY → RETIRE (R1-D.5).**

---

## 5. BIR consumers (3+ consumers, LEGACY → RETIRE)

| Consumer | Path | Import | Migration action | Status | Risk | Tests |
|---|---|---|---|---|---|---|
| Lowering pass | `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` | `BIR`, `BIRModule`, `BIRNode` | None | LEGACY → RETIRE (R1-D.5) | None (not in canonical) | (constitutional) |
| FastAPI backend | `constitutional_architecture/compiler/backends/fastapi_backend.py:31-32, 73-86` | `BIR` | None | LEGACY → RETIRE (R1-D.5) | None (not in canonical) | (constitutional) |
| BIR tests | `constitutional_architecture/tests/test_*bir*.py` | `BIR` | None | LEGACY → RETIRE (R1-D.5) | None | (constitutional) |

**Total: 3+ BIR consumers, all LEGACY → RETIRE (R1-D.5).**

---

## 6. Canonical backends (2 consumers, KEEP)

| Consumer | Path | Import | Migration action | Status | Risk | Tests |
|---|---|---|---|---|---|---|
| Python FastAPI backend | `compiler/backends/python_fastapi.py` | `compiler.core.protocol.CompilerBackend`, `CompilationPlan` | None | KEEP | None | `tests/v14/test_multi_backend.py` |
| Rust Axum backend | `compiler/backends/rust_axum.py` | `compiler.core.protocol.CompilerBackend`, `CompilationPlan` | None | KEEP | None | `tests/v14/test_multi_backend.py` |

**Total: 2 canonical backends, both KEEP.**

---

## 7. Consumer migration summary

| Category | Count | Status |
|---|---|---|
| Canonical CompilationPlan consumers | 10 | KEEP (no migration) |
| Gen-C compiler consumers | 4 | LEGACY → RETIRE (R1-D.5) |
| Per-category compiler consumers | ~11 | LEGACY → RETIRE (R1-D.5) |
| BIR consumers | 3+ | LEGACY → RETIRE (R1-D.5) |
| Canonical backends | 2 | KEEP |
| **Total** | **~30** | |

---

## 8. Verdict

The canonical runtime has **10 direct CompilationPlan consumers** and **2 canonical backends** that consume `CompilationPlan`. All 12 are KEEP — no migration required. The constitutional substrate has ~18 consumers (4 Gen-C + ~11 per-category + 3+ BIR) that are all LEGACY → RETIRE in R1-D.5.

The R1-D.2 contract refinement (D2-D4) does **not** change the canonical runtime. The current `CompilationPlan` is preserved. The future canonical Compiler IR module (R1-D.5) will provide a migration path: `from_plan(plan: CompilationPlan) -> CanonicalCompilerIR`.

---

## 9. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D5: `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md`
- D2-D7: `folder/R1_D2_COMPILER_LEGACY_DISPOSITION.md` (next)

---

*End of D2-D6. The R1-D.2 consumer migration is complete. 10 canonical CompilationPlan consumers KEEP; 2 canonical backends KEEP; ~18 constitutional consumers LEGACY → RETIRE. No canonical consumer requires migration. D2-D7 (legacy disposition) follows.*
