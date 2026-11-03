# FS-00 Supplement — Dependency-Crossing Register

**Status:** REVIEW DRAFT — bounded source inspection, not a complete repository-wide import graph  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Purpose:** Make known dependency crossings and required follow-up evidence explicit without claiming the boundary audit is complete.

## Method and limits

This register records concrete crossings confirmed by source inspection at the current branch. It is not generated from a complete static dependency scan; dynamic imports, indirect dependencies, test-only edges, packaging configuration and dependencies outside these files may be missing. Accordingly, **Boundary Integrity remains PARTIAL**. No implementation or schema change is authorized by this supplement.

## Confirmed crossings

| ID | From → to | Evidence / observed relationship | Assessment | Required disposition |
|---|---|---|---|---|
| DEP-01 | `compiler/core/lowering.py` → `isr/core/{behavior,graph,revision}.py` | Lowerer consumes `ISRRevision`, graph node/edge enums and behavior validation. | Expected inward dependency for an ISR-to-IR adapter, but its mapping must be complete and fail closed. | FS-01 defines coverage for every node/edge/payload and tests unknown/unmapped semantics. |
| DEP-02 | `compiler/backends/android.py` → `isr/core/revision.py` and `compiler/core/lowering.py` | Android backend module imports `ISRRevision` and `isr_to_plan`; the module also exposes a source-bound helper. | Boundary leak: backend is not solely an IR consumer. | After approval, move source-revision binding/lowering to an orchestration or adapter layer; preserve compatibility through tests. |
| DEP-03 | `compiler/backends/_naming.py` → `compiler/core/plan.py` | Backend helper imports the shared plan carrier. | Acceptable shared-contract dependency if core remains target-neutral. | Confirm no target-specific semantics enter the core plan; include in IR ownership review. |
| DEP-04 | `compiler/backends/react_frontend.py` → `compiler/core/{capabilities,plan,repository}.py` | Frontend backend consumes shared plan, capability and repository contracts. | Expected backend-to-core direction. | Add backend conformance tests against a versioned IR/capability manifest. |
| DEP-05 | `compiler/composition.py` → `compiler/core/registry.py` and backend implementations | Composition root wires registry and concrete backends. | Appropriate composition-root direction; registry must not depend on concrete emitters. | Test registry composition and unknown backend/capability behavior. |
| DEP-06 | `certification/campaign/plan_builder.py` → compiler lowering, evolution, genesis, ISR and requirement graph | One builder constructs workload artifacts across several domains and invokes ISR lowering. | Mixed responsibility; currently used for campaign workloads. It is not evidence of a production orchestrator. | Name the owner and API for production full-stack orchestration separately from benchmark/campaign construction. |
| DEP-07 | `certification/campaign/runner.py` → `app.engine.source_bound_full_stack` | Campaign runner imports application engine verifier via application package bootstrap. | Packaging/path coupling; clean-environment behavior must be established. | Add clean checkout/install invocation tests; later extract a stable verifier protocol if warranted. |
| DEP-08 | `compiler/core/{protocol,conformance,capabilities,authorization,behavior_oracle}.py` → `compiler/core/plan.py` | Shared contracts and validators operate on the current `CompilationPlan`. | Tight coupling to a transitional carrier; not proof of a canonical IR contract. | Version the canonical IR contract and test consumer compatibility before migration. |
| DEP-09 | `certification/campaign/verdict.py` → `compiler/core/protocol.py` | Campaign verdict logic imports behavioral class definitions. | Potential ownership inversion if certification verdict policy is coupled to compiler protocol constants. | Decide a neutral shared contract owner; add tests that changing backend protocol cannot silently redefine certification authority. |
| DEP-10 | `autonomous-api/app/main.py` → app-local ISR observation implementation | `_DbGenerationProvider.get_isr()` raises `NotImplementedError` in the inspected source. | Concrete incomplete observation contract. | Assign authoritative ISR-store owner; implement only under a separately authorized task with API and persistence tests. |

## Directional rules proposed for review

1. `isr/core` owns source semantics and must not import compiler backend families or certification verdict code.
2. `compiler/core` owns the technology-neutral, versioned compiler contract; it must not import a concrete backend implementation.
3. `compiler/backends/*` consumes the canonical compiler contract and declares its own capability set; backend-specific code must not become the authoritative owner of ISR semantics.
4. Orchestration binds source revision, IR, backend policy, candidate and artifacts. It may call core and backend interfaces but must not manufacture missing requirements.
5. Certification independently evaluates bound evidence and records verdicts; it must not fill in missing semantics after generation.
6. Campaign/test harnesses may compose these components for experiments, but must not be mistaken for production orchestration without an explicit contract and runtime evidence.

## Required completion procedure

- Pin the exact source commit and dependency/tool versions.
- Run a repository-wide static import/dependency scan across production code, tests, scripts and package configuration.
- Classify each edge as allowed, conditional, legacy, test-only or violation; include dynamic imports and package-root/path manipulation.
- Verify the graph with targeted searches and clean-environment tests.
- Reconcile this register with Deliverables 1–4; document every exception and owner.
- Update the gate assessment only after evidence is reviewed. This draft does not change the gate result.

## Gate result

**Boundary Integrity: PARTIAL.** Ten concrete crossings are recorded, but the required complete graph and reviewed classifications are not yet supplied. No FS-01 authorization is implied.
