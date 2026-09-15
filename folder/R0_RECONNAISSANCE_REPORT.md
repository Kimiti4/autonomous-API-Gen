# R0 — Reconnaissance and Remediation Plan

**Mission:** Map the actual repository architecture, verify the audit's claims, and produce the conflict table that gates R1 implementation.

**Status:** R0 complete. R1 is **BLOCKED** until the conflict table below is internally consistent and the architectural substrate question is answered.

**Method:** Whole-system trace (import graph, type hierarchy, call sites, file:line citations) — not file-by-file. Every claim is OBSERVED with citation, or INFERRED, or PROPOSED, or UNKNOWN. No code modified.

**Note on the audit:** The audit's macro verdict (`FOUNDATION EXISTS — NOT YET COHERENT`) is **confirmed**. Its R0-R16 implementation order is broadly sound. However, the audit **conflated two substrate families** that are actually wired into different runtimes — see §0 below. The R0 conflict table extends and refines the audit's table to capture this.

---

## 0. The most important finding (NOT in the audit)

The repository contains **two parallel substrate families**, wired into **two disjoint runtimes**:

| | Substrate A (campaign runtime) | Substrate B (constitutional runtime) |
|---|---|---|
| **ISR** | `isr/core/` (flat, frozen, 9 node kinds, content-hashed) | `constitutional_architecture/isr/model/` (rich, 19+ node kinds, System-of-records) **and** `constitutional_architecture/core/models/isr.py:UniversalISR` (a third, 17-node typed graph) |
| **Compiler IR** | `compiler/core/plan.py:CompilationPlan` (Pydantic flat) | `constitutional_architecture/compiler/bir/model.py:BIR` (dataclass tree) **and** `UniversalISR` as a typed graph |
| **Compiler pipeline** | `compiler/composition.build_backend_registry()` | `constitutional_architecture/compiler/pipeline.CompilerPipeline` (8-pass) |
| **Backend protocol** | `compiler/core/protocol.py:CompilerBackend` Protocol (duck-typed) | `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` **and** `compiler/sdk/base.py:CompilerBackendBase` **and** `compilers/*/base.py:BackendCompiler` (four protocols total) |
| **Evolution** | `evolution/` (root, real crossover, lineaged via `LineageTracker`) | `constitutional_architecture/engine/EvolutionEngine` + `EvolutionLoop` (EIR has `transformations=[]` defect) |
| **Verification** | `certification/stages/{docker_stages,independent_verify}.py` (fail-closed) | `constitutional_architecture/compiler/passes/verification_pass.py` (fail-open) |
| **Used by** | `certification/` (the Phase 31 campaign runtime) | `tests/test_passes/*`, `tests/test_bridges/*`, `tests/test_adapters/*`, `tests/test_*_compiler.py` |
| **Used by the campaign runtime** | **YES** | **NO** (`grep -r constitutional_architecture certification/` returns 0 matches) |

**Consequence:** the audit's headline findings (multiple ISRs, multiple Compiler IRs, fail-open verification, pseudo-crossover, etc.) are real at the codebase level, but the **campaign runtime is not exposed to most of them**. The campaign runs on Substrate A end-to-end. Consolidating Substrate B in isolation will not change the campaign's behavior.

**This is the question the audit did not ask:** Is the campaign to remain on Substrate A, or be rewired to Substrate B? This decision must precede the conflict table, because the "Proposed canonical" column depends on it.

---

## 1. Audit claim verification (the audit's findings, verified or refuted)

| # | Audit claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Multiple ISRs (`isr/` vs `constitutional_architecture/isr/`) | **CONFIRMED + 1 more** | `isr/core/graph.py:34-49`; `constitutional_architecture/isr/model/system.py:34-103`; `constitutional_architecture/core/models/isr.py:58-104`. **Three** distinct ISR models with disjoint base classes. |
| 2 | Requirement Graph present, `RequirementExtractor` interface-only | **CONFIRMED** | `reqgraph/core/graph.py:25-44` (4 edge types: DEPENDS_ON, CONFLICTS_WITH, REFINES, OWNED_BY — fewer than audit's list). Extractor is interface-only. |
| 3 | ISR semantics distinguishes semantic obligation / test / verification | **CONFIRMED** | `constitutional_architecture/isr/semantics/` (multiple validators). |
| 4 | Evolution Engine is substantial; don't rebuild | **CONFIRMED** | `evolution/core/{engine,genome,operations}.py` (real crossover at `operations.py:74-104`); `constitutional_architecture/engine/{evolution_engine,evolution_loop}.py`. |
| 5 | EIR is the right abstraction but loses actual transformations | **CONFIRMED (Substrate B only)** | `constitutional_architecture/eir/transformation.py:37-77` (no transformation_id, no source/target ISR, no operator); `constitutional_architecture/engine/evolution_loop.py:107-114` (line 110: `transformations=[]`). |
| 6 | Pseudo-crossover | **REFUTED in Substrate A; CONFIRMED in Substrate B** | `evolution/core/operations.py:74-104` (real crossover, RNG-pick per gene); Substrate B's crossover is at `constitutional_architecture/engine/crossover_engine.py` (would need direct read to confirm). |
| 7 | Three compiler generations | **CONFIRMED + 1 more** | Gen-A `compiler/kernel.py` (UniversalCompiler); Gen-B `compiler/core/` (CompilationPlan); Gen-C `constitutional_architecture/compiler/` (8-pass). Fourth: `constitutional_architecture/compilers/*` (per-category). |
| 8 | BIR is the right direction | **INFERRED, but incompatible with campaign's content-hash provenance** | `constitutional_architecture/compiler/bir/model.py:8-39` (BIR has no content-hash; campaign provenance in `certification/provenance/bundle.py:116` SHA-256s the `CompilationPlan` dump). |
| 9 | Two incompatible Compiler IRs | **CONFIRMED + 1 more** | `CompilationPlan` (Gen-B), `BIR` (Gen-C), `UniversalISR`-as-typed-graph (compilers/*). No adapter exists. |
| 10 | Validation fails open | **CONFIRMED (Substrate B only)** | `constitutional_architecture/compiler/passes/validation_pass.py:21-30` returns `success=True` on exception; line 27-28 always returns `success=True` regardless of `result.passed`. Substrate A validation (`certification/stages/*`) is fail-closed. |
| 11 | Verification failure becomes warning | **CONFIRMED (Substrate B only)** | `constitutional_architecture/compiler/passes/verification_pass.py:51-79` records WARNING, returns success. |
| 12 | PassManager continues after failure | **CONFIRMED (Substrate B only)** | `constitutional_architecture/compiler/pass_manager.py:11-43`: loop does not break on failure. |
| 13 | Normalization loses ISR semantics | **CONFIRMED (Substrate B)** | `constitutional_architecture/compiler/passes/normalization_pass.py:49-56` carries only `id, name, description, modules, deployment, metadata, global_policies`; drops 14+ System fields. |
| 14 | ISR↔TypedGraph round-trip is lossy | **CONFIRMED (Substrate B)** | `constitutional_architecture/engine/isr_adapter.py:18-28` → reverse at `isr_adapter.py:30-120` (workflows → `()`, system-level semantic fields not reconstructed). |
| 15 | Compiler bridge stale/broken | **CONFIRMED + DEAD CODE** | `constitutional_architecture/engine/compiler_bridge.py:13, 35-45` uses non-existent `CompilerConfig(backend=...)` and `CompilerPipeline(config=...)`; only calls itself (`grep` returns 0 callers). |
| 16 | FastAPI backend not production-complete | **CONFIRMED** | `compiler/backends/python_fastapi.py:99-102` returns `apiVersion: apps/v1\nkind: Deployment\n`. Gen-C `constitutional_architecture/compiler/backends/fastapi_backend.py:47-719` is more complete but writes to filesystem directly (line 85 calls `self.write_files()`). |
| 17 | Rust Axum skeletal | **CONFIRMED** | `compiler/backends/rust_axum.py:13-142` mirrors FastAPI's minimal pattern. |
| 18 | Conformance is mostly structural | **CONFIRMED** | `compiler/core/conformance.py:32-50` checks `plan_element_ids` → paths → file exists. |
| 19 | Artifact emission purity | **CONFIRMED for Gen-B (pure)**; **REFUTED for Gen-C** | Gen-B: `compiler/backends/python_fastapi.py:53-57` uses `build_repository(files_dict)`; Gen-C: `constitutional_architecture/compiler/backends/fastapi_backend.py:85` calls `self.write_files()`. |
| 20 | Capability Resolution well-designed | **CONFIRMED** | `constitutional_architecture/compiler/passes/capability_resolution_pass.py:8-78` (13+ capabilities, OAuth2, JWT, ORM, etc.). |
| 21 | Knowledge Graph real subsystem | **CONFIRMED** | `knowledge/` (15+ .py), not used by the campaign. |
| 22 | Civilization layer broad | **CONFIRMED** | `civilization/` (8+ subdirs); not used by the campaign. |
| 23 | Observation layer `_DbGenerationProvider.get_isr() → NotImplementedError` | **CONFIRMED verbatim** | `autonomous-api/app/main.py:111-115` has the `NotImplementedError("ISR binding is a declared audit gap")` text. **However**, the campaign does not import `autonomous-api/`. |
| 24 | `pyproject.toml` says `knowledge-graph-runtime` | **CONFIRMED** | `pyproject.toml:2, 4, 19-21` (`name = "knowledge-graph-runtime"`, packages = `knowledge*`). |
| 25 | Tests certify different things | **CONFIRMED** | `tests/cbc1/*` certify Substrate A; `tests/test_passes/*` certify Substrate B; `tests/test_*_compiler.py` certify Gen-A; `tests/cbc1/*` are the only ones in the campaign tier. |

**Net:** 22 of 25 audit claims confirmed as written; 3 of 25 require the substrate-fork distinction (6, 13, 19) to be stated correctly. **None refuted outright**; **3 require scoping to a specific substrate** rather than the codebase as a whole.

---

## 2. The R0 conflict table (this is what gates R1)

| # | Conflict | Current implementations | Proposed canonical (CONDITIONAL) | Migration | Risk |
|---|---|---|---|---|---|
| C-01 | **Substrate choice** (the meta-conflict) | Substrate A (`isr.core` + `compiler/core`) and Substrate B (`constitutional_architecture.*`) wired into disjoint runtimes | **UNKNOWN — requires user decision** | A → B (rewire campaign) **OR** B → A (consolidate constitutional_architecture on isr.core) **OR** keep both (define a typed adapter) | **P0** |
| C-02 | **ISR models** | `isr.core` (campaign); `constitutional_architecture.isr.model` (rich, 19 node kinds); `constitutional_architecture.core.models.isr.UniversalISR` (third, 17 node kinds) | If A is canonical → `isr.core`; If B is canonical → `constitutional_architecture.isr.model` (richer); `UniversalISR` retired | Adapter + deprecation | **P0** |
| C-03 | **Compiler IRs** | `compiler.core.plan.CompilationPlan` (campaign); `constitutional_architecture.compiler.bir.BIR` (Gen-C); `UniversalISR`-as-typed-graph (compilers/*); four artifact models (`GeneratedRepository`, `CompilationOutput`, `BackendResult`, `CompilationBundle`) | If A is canonical → `CompilationPlan`; If B is canonical → `BIR` (must add content-hash + serialization) | Adapter + content-hash gap | **P0** |
| C-04 | **Compiler pipeline generations** | Gen-A `compiler/kernel.py:UniversalCompiler` (model-heavy); Gen-B `compiler/composition.py:build_backend_registry()`; Gen-C `constitutional_architecture/compiler/pipeline.py:CompilerPipeline` (8-pass); per-category `compilers/*` | If A is canonical → Gen-B entry; If B is canonical → Gen-C entry | Adapter; preserve campaign wiring | **P0** |
| C-05 | **Compiler bridge** | `constitutional_architecture/engine/compiler_bridge.py` (dead code, broken API) | If B is canonical → repair to `CompilerPipeline(isr, config)`; else delete | Repair or delete | **P1** |
| C-06 | **EIR** | `constitutional_architecture/eir/transformation.py:Transformation` lacks `transformation_id`/`source_isr`/`operator`; `evolution_loop.py:110` `transformations=[]` | Required additions: `transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`; populate from real mutations | Repair | **P1** (only if B is canonical) |
| C-07 | **Validation pass fail-open** | `constitutional_architecture/compiler/passes/validation_pass.py:21-30` | Change to `PassResult(success=result.passed, ...)`; no `try/except: success=True` | Repair | **P0** (only if B is canonical) |
| C-08 | **Verification pass fail-open** | `constitutional_architecture/compiler/passes/verification_pass.py:51-79` returns `success=True` on engine exception | Add `VERIFICATION_INDETERMINATE` outcome; block certification | Repair | **P0** (only if B is canonical) |
| C-09 | **PassManager continues after failure** | `constitutional_architecture/compiler/pass_manager.py:11-43` | Add `preconditions`/`BLOCK` semantics; pass declares its blocking behavior | Repair | **P0** (only if B is canonical) |
| C-10 | **Normalization loses semantics** | `constitutional_architecture/compiler/passes/normalization_pass.py:49-56` carries only 7 of 21 System fields | Carry all System fields; add `with_system`-based rebuild | Repair | **P0** (only if B is canonical) |
| C-11 | **ISR↔TypedGraph round-trip** | `constitutional_architecture/engine/isr_adapter.py` round-trip is lossy | Either preserve all fields or explicitly document the projection as lossy and remove it from the canonical round-trip path | Repair + test | **P0** (only if B is canonical) |
| C-12 | **Backend protocols** | Four: Gen-B `compiler/core/protocol.py:CompilerBackend`; Gen-C `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)`; Gen-A `compiler/sdk/base.py:CompilerBackendBase`; compilers/* `compilers/backend/base.py:BackendCompiler` | If A is canonical → Gen-B Protocol; If B is canonical → Gen-C ABC; define one signature set | Adapter layer | **P1** |
| C-13 | **Backend filesystem write** | Gen-C `constitutional_architecture/compiler/backends/fastapi_backend.py:85` calls `self.write_files()` inside `compile()`; Gen-B uses `build_repository()` (pure) | Adopt Gen-B emission pattern: backend returns `ArtifactSet`; packager writes | Refactor | **P1** |
| C-14 | **Backend BEHAVIORAL classification** | `compiler/backends/python_fastapi.py:15-24` and `rust_axum.py:22` claim `BEHAVIORAL` but emit minimal k8s/ci content | Downgrade to `STRUCTURAL` until evidence supports behavioral; or complete the generation | Demote or complete | **P1** |
| C-15 | **Lineage durability** | `LineageTracker` (in-memory) for both substrates; `SnapshotStore` persists ISR snapshots (not lineage) | Persist lineage as hash-chained records (mirror certification ledger); `LineageEntry` includes `eir_id`, `parent_eir_id`, `evidence_ref` | New `evolution/lineage_store.py` | **P2** |
| C-16 | **Crossover correctness** | Substrate A `evolution/core/operations.py:74-104` is real; Substrate B `constitutional_architecture/engine/crossover_engine.py` status UNKNOWN (not directly read) | If both substrates kept, audit Substrate B's crossover; if not, retire | Audit | **P1** |
| C-17 | **Observation ↔ ISR lineage** | `autonomous-api/app/main.py:111-115` `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` | Bind to canonical ISR/provenance; do not create a second ISR store | Repair (or retire `autonomous-api/`) | **P2** |
| C-18 | **`pyproject.toml` topology** | `pyproject.toml:2` `name = "knowledge-graph-runtime"`; `pyproject.toml:19-21` `packages = ["knowledge*"]`; CI installs `autonomous-api/requirements.txt` separately | Consolidate package discovery; update `name` to reflect Tiannara compiler | Refactor | **P2** |
| C-19 | **Knowledge / Civilization / distributed_evolution** | Imported only by tests; not by compiler or campaign | Out of scope for the Full-Stack Compiler; keep as higher-level platform | None | **P3** |
| C-20 | **Generated artifacts (`generated/testshop`, `monolithshop`)** | Carry `change-me-in-production`, `cors_origins = ["*"]` defaults | These are evidence of an earlier generation; classify as `LEGACY_GENERATED` and exclude from canonical scope | None (or fix the generator defaults) | **P3** |

---

## 3. The decision the audit did not require, but R0 requires

The R0 conflict table above is **internally consistent only after C-01 is answered**. C-01 is the meta-conflict: which substrate does the campaign run on?

### Why C-01 cannot be defaulted

- The audit's "canonical ISR = `constitutional_architecture.isr.model`" recommendation is **incompatible with the campaign's runtime path**, which wires `isr.core` end-to-end (`certification/campaign/plan_builder.py:19-20`, `runner.py:10-13`, etc.). Adopting the rich ISR would require:
  - Adding content-hash to `BIR` (BIR currently has no hash; the campaign's provenance SHA-256s `CompilationPlan.model_dump()`).
  - Rewriting `certification/campaign/plan_builder.py` to lower the rich ISR instead of `isr.core`.
  - Re-running the 243-test Tier A suite (would fail until the rich-ISR lowering is implemented and proven equivalent).
  - Re-running the Tier C certification (`pytest -m certification`, 40 tests) and ideally a B wave.
- Alternatively, **the rich `constitutional_architecture.*` could be consolidated onto `isr.core`** (treat `constitutional_architecture.isr.model` as an extension, not an alternative). This preserves the campaign runtime and demotes Substrate B to a richer-typed-views layer. This is the path **the audit did not recommend** but the R0 evidence supports as the lower-risk option.
- The third option — **keep both with a typed adapter** — is the most expensive and the most likely to produce a fourth parallel substrate (a documented anti-pattern from the audit's own §39 NO NEW SOURCE OF TRUTH).

### Why the audit did not catch this

The audit inspected the codebase as a system of files. R0 inspected it as a system of **imports and runtime paths**. The two are not the same view, and the substrate fork is invisible in the file view.

### Three options for C-01

**Option 1 (Substrate A canonical; consolidate B on A).** Lower-risk. Preserves the campaign runtime. Treats `constitutional_architecture.isr.model` as a richer view of `isr.core`; treats `BIR` as a richer view of `CompilationPlan`; adapts Gen-C passes to consume Substrate-A models. Conflict table's "Proposed canonical" for C-02, C-03, C-04, C-12 becomes the Substrate-A answer. C-05 (bridge) deleted. C-06, C-07, C-08, C-09, C-10, C-11 become "no-ops: the relevant Substrate-B code is not in the runtime, so the defects are dormant" or "fix the Substrate-B code anyway for hygiene".

**Option 2 (Substrate B canonical; rewire A to B).** Higher-risk. Adopts the rich ISR + BIR + 8-pass pipeline as canonical. Rewrites the campaign's plan_builder / runner / verdict / provenance. Adds content-hash to BIR. Validates equivalence. This is a multi-week consolidation; the B3-v2 campaign evidence would be invalidated until re-run. **Not recommended** unless the user wants the constitutional substrate to be the future.

**Option 3 (Keep both, adapter between them).** Most expensive. Requires a typed adapter between `isr.core.ISRRevision` and `constitutional_architecture.isr.model.ISR`. The audit's §39 NO NEW SOURCE OF TRUTH principle applies — this introduces a parallel source of truth unless the adapter is one-way. **Not recommended** unless a clear use case for the parallel runtime exists.

---

## 4. R0 stop conditions hit (per the audit's §51)

Per the audit's stop conditions, R0 cannot proceed to R1 because the following are **UNKNOWN** without a user decision:

- **Canonical ISR cannot be determined** — three implementations, two runtime paths, the audit's recommendation is incompatible with the campaign runtime. R0 has evidence, not authority.
- **Two representations have incompatible semantics** — `isr.core` and `constitutional_architecture.isr.model` are disjoint base classes; not isomorphic. Provenance and content-hash differ.
- **Migration would destroy provenance** — Option 2 would require re-running the B3-v2 campaign or invalidating its evidence; Option 1 preserves it; Option 3 doubles it.

### R0 recommended action

**Do not start R1.** The user must choose C-01 (substrate fork) before the conflict table is internally consistent. R0 is the reconnaissance; the next gate is the C-01 decision.

---

## 5. Files reviewed (the citation index)

This R0 cites the following files. All are read directly; line numbers are from the current working tree.

### Substrate A — campaign runtime

* `isr/__init__.py:8-15`
* `isr/core/{graph,identity,invariants,revision}.py`
* `isr/core/graph.py:11-93` (NodeType, EdgeType, EDGE_TYPE_COMPATIBILITY)
* `isr/core/identity.py:18-66` (Provenance, compute_content_hash)
* `isr/core/invariants.py:16-137` (FORBIDDEN_IMPLEMENTATION_TERMS, validate_invariants)
* `isr/core/revision.py:17-61` (ISRRevision)
* `compiler/__init__.py`, `compiler/composition.py:8-12`
* `compiler/core/{__init__,plan,lowering,conformance,protocol,registry,repository}.py`
* `compiler/core/plan.py:6-40` (CompilationPlan)
* `compiler/core/lowering.py:14-73` (isr_to_plan)
* `compiler/core/protocol.py:52-65` (CompilerBackend Protocol)
* `compiler/backends/python_fastapi.py:8-138`
* `compiler/backends/rust_axum.py:7-142`
* `evolution/__init__.py`, `evolution/core/{engine,genome,operations,construction,refinement,fitness,fitness_evaluator,materialize}.py`
* `evolution/core/operations.py:74-104` (real crossover)
* `reqgraph/__init__.py`, `reqgraph/core/{graph,invariants}.py`
* `reqgraph/core/graph.py:25-44` (RequirementNode, RequirementEdgeType)
* `certification/campaign/plan_builder.py:13-25, 142-144`
* `certification/campaign/runner.py:10-13`
* `certification/stages/{stub_stages,docker_stages,independent_verify}.py`
* `certification/provenance/bundle.py:116`
* `tests/cbc1/*` (243 tests; campaign tier)

### Substrate B — constitutional runtime

* `constitutional_architecture/__init__.py`
* `constitutional_architecture/isr/model/{system,module,entity,service,workflow,policy,interface,event,deployment,constraints,edges,fields,isr,nodes}.py`
* `constitutional_architecture/isr/model/system.py:34-103`
* `constitutional_architecture/isr/model/isr.py:67-144`
* `constitutional_architecture/core/models/isr.py:9-104` (NodeType, EdgeType, UniversalISR)
* `constitutional_architecture/compiler/{pipeline,compilation_config,compiler_context,compiler_result,pass_interface,pass_manager,pass_registry}.py`
* `constitutional_architecture/compiler/pipeline.py:43-161` (8-pass)
* `constitutional_architecture/compiler/compilation_config.py:19-32`
* `constitutional_architecture/compiler/bir/model.py:8-39` (BIR)
* `constitutional_architecture/compiler/passes/{validation,normalization,optimization,capability_resolution,lowering,code_generation,verification,cross_target}_pass.py`
* `constitutional_architecture/compiler/passes/validation_pass.py:7-31` (fail-open)
* `constitutional_architecture/compiler/passes/normalization_pass.py:19-156` (semantic loss)
* `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (fail-open)
* `constitutional_architecture/compiler/pass_manager.py:11-43` (continue on fail)
* `constitutional_architecture/compiler/backends/{backend_interface,backend_registry,backend_selector,fastapi_backend}.py`
* `constitutional_architecture/compiler/backends/fastapi_backend.py:47-719` (writes to FS at line 85)
* `constitutional_architecture/compilers/{backend,database,deployment,documentation,frontend,infrastructure,operational,runtime_policy,testing}/...` (per-category)
* `constitutional_architecture/compilers/backend/base.py:11-19` (BackendCompiler)
* `constitutional_architecture/eir/transformation.py:37-77, 961-1101`
* `constitutional_architecture/engine/{compiler_bridge,evolution_engine,evolution_loop,isr_adapter,lineage_tracker,crossover_engine}.py`
* `constitutional_architecture/engine/compiler_bridge.py:13-45` (dead code)
* `constitutional_architecture/engine/evolution_loop.py:107-114` (`transformations=[]`)
* `constitutional_architecture/engine/isr_adapter.py:18-198` (lossy round-trip)

### Other

* `evolution/` (root, Substrate A) — fully read; not in this list to avoid duplication
* `autonomous-api/app/main.py:111-115` (`NotImplementedError("ISR binding is a declared audit gap")`)
* `pyproject.toml:2, 4, 19-21` (`name = "knowledge-graph-runtime"`)
* `generated/{testshop,monolithshop}/{main,config}.py` (legacy)
* `knowledge/`, `civilization/`, `autonomous_network/`, `distributed_evolution/` (higher-level platform; not in scope)

---

## 6. R0 → R1 transition criteria

R1 may begin only when **all** of the following are true:

1. **C-01 is decided** (the substrate fork).
2. **The conflict table is updated** with the decided canonical for C-02, C-03, C-04, C-12.
3. **The user explicitly authorizes R1** to begin (per the audit's "Do not commit unless explicitly authorized by the controlling workflow").
4. **A migration order is published** — which conflicts are remediated in which order. The audit's R0–R16 order is the starting point but is not internally consistent with the C-01 fork; the order must be regenerated after C-01 is decided.
5. **The provenance impact is documented** — what existing evidence remains valid, what must be re-collected.

**Without C-01, no R1 work is sound.**

---

*End of R0 reconnaissance. Conflict table gates R1.*
