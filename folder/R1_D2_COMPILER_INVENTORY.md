# R1_D2_COMPILER_INVENTORY (R1-D.2 D2-D1)

**Status:** R1-D.2 Deliverable D2-D1. Compiler/IR inventory. Index: `folder/CONTRACT_CanonicalCompilerIR.md` (D07 R1-B), `folder/R1_D1_GATE_REPORT.md` (D9 R1-D.1), `folder/R1_C_GATE_REPORT.md` (C12 R1-C).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt (`folder/R1d2.md`).

**Method:** File:line-cited enumeration of every compiler/IR implementation. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

**Scope:** R1-D.2 ONLY. R1-D.3 (Evolution/EIR) is HARD-STOPPED.

---

## 0. Inventory scope

The R1-D.2 master prompt requires inventorying every compiler-related implementation, including:
- `compiler/core/plan.py`
- `compiler/core/protocol.py`
- `compiler/composition.py`
- `constitutional_architecture/compiler/`
- `constitutional_architecture/compiler/bir/`
- `constitutional_architecture/compiler/pipeline.py`
- `constitutional_architecture/engine/compiler_bridge.py`
- All category-specific compiler implementations (`constitutional_architecture/compilers/*`)
- All compiler-related tests
- All compiler provenance/certification code

The inventory covers:
1. Canonical compiler substrate (Section 1).
2. Constitutional compiler (Gen-C) (Section 2).
3. BIR (semantic donor) (Section 3).
4. Compiler bridge (dead code) (Section 4).
5. Category compilers (Section 5).
6. Compiler consumers (Section 6).
7. Tests (Section 7).
8. Cross-cutting symbols (Section 8).

---

## 1. Canonical compiler substrate (`compiler/core/`)

### 1.1 Files

| File | Size | Purpose |
|---|---|---|
| `compiler/core/__init__.py` | (small) | Package init |
| `compiler/core/plan.py` | 1,050B | `CompilationPlan`, `DataModel`, `Event`, `SecurityPolicy`, `Service` (Pydantic frozen) |
| `compiler/core/protocol.py` | 2,200B | `CompilerBackend` Protocol, `BackendClass` enum, `BackendIdentity`, `TestSpec`, `eligible_for_behavioral_certification` |
| `compiler/core/lowering.py` | 2,900B | `isr_to_plan(revision: ISRRevision) -> CompilationPlan` |
| `compiler/core/conformance.py` | (medium) | `ConformanceReport`, `CHECKER` |
| `compiler/core/protocol.py` | 2,200B | (above) |
| `compiler/core/registry.py` | (small) | `BackendRegistry` |
| `compiler/core/repository.py` | (medium) | `GeneratedRepository` (the canonical ArtifactSet equivalent) |

### 1.2 CompilationPlan taxonomy (current)

| Type | Fields | Semantic |
|---|---|---|
| `CompilationPlan` | `plan_id`, `isr_id`, `services: list[Service]`, `security: list[SecurityPolicy]` | The tech-neutral IR between ISR lowering and backend emission |
| `Service` | `id`, `name`, `data_models: list[DataModel]`, `published_events: list[Event]`, `consumed_events: list[Event]` | A service that exposes capabilities |
| `DataModel` | `id`, `entity_name` | A data model (entity or aggregate) |
| `Event` | `id`, `name` | A domain event |
| `SecurityPolicy` | `policy_id` | A security policy (authn, authz, secret handling) |

**Observation:** `CompilationPlan` is a **flat Pydantic** model. It has 4 node types (`Service`, `DataModel`, `Event`, `SecurityPolicy`) and no explicit edges. Relationships are encoded as nested lists (e.g., `Service.data_models` is a list of `DataModel` references). This is **in contrast** to the canonical ISR's edge-based model.

**Identity:** `plan_id = "plan:" + revision.content_hash[:16]`. There is **no content-hash on CompilationPlan** — the plan_id is derived from the ISR's content_hash, not from the plan's own serialization.

**Classification:** `CompilationPlan` is the **stabilization implementation** of the canonical Compiler IR. Per R1-A C-03 and R1-D.2 §6, it is **not automatically the final Compiler IR**. The R1-D.2 prompt requires determining whether its semantics are KEEP, MIGRATE, REPLACE, SPLIT, or DEFER.

### 1.3 CompilerBackend Protocol (current)

| Element | Definition |
|---|---|
| `BackendClass` | Enum: `STUB`, `STRUCTURAL`, `BEHAVIORAL`, `PRODUCTION` |
| `BEHAVIORAL_CLASSES` | `{BackendClass.BEHAVIORAL, BackendClass.PRODUCTION}` |
| `BackendIdentity` | `name`, `language`, `framework`, `version`, `backend_class` |
| `TestSpec` | `command: list[str]`, `runs_in: Literal["runtime","build"]`, `build_target` |
| `eligible_for_behavioral_certification(identity)` | Returns `True` if `backend_class in BEHAVIORAL_CLASSES` |
| `CompilerBackend` Protocol | `name`, `language`, `framework`, `version`, `identity()`, `test_spec()`, `element_paths(plan)`, `compile(plan)`, `conformance(plan, repo)` |

**Observation:** The Protocol is duck-typed. There is no `BEHAVIORAL` enforcement; `eligible_for_behavioral_certification` is a function. Backends register via `BackendRegistry` and are wired by `compiler/composition.py:build_backend_registry()`.

### 1.4 Lowering (`isr_to_plan`)

```python
# compiler/core/lowering.py:14-71
def isr_to_plan(revision: ISRRevision) -> CompilationPlan:
    graph = revision.graph
    services: list[Service] = []
    dm_by_id: dict[str, DataModel] = {}
    ev_by_id: dict[str, Event] = {}
    sec_by_id: dict[str, SecurityPolicy] = {}
    # ... iterate graph.nodes, build services from SERVICE nodes,
    # data_models from PERSISTS edges, events from PUBLISHES/CONSUMED_BY,
    # security from SECURED_BY.
    return CompilationPlan(
        plan_id=f"plan:{revision.content_hash[:16]}",
        isr_id=revision.system_id,
        services=services,
        security=all_security,
    )
```

**Observation:** The lowering consumes the canonical ISR's 9 NodeType and the 4 relevant EdgeType (`PERSISTS`, `PUBLISHES`, `CONSUMED_BY`, `SECURED_BY`). The other 5 NodeType (`DOMAIN`, `CAPABILITY`, `API`, `INFRASTRUCTURE_TARGET`, `REQUIREMENT_REF`) and the other 4 EdgeType (`SATISFIES`, `IMPLEMENTED_BY`, `EXPOSES`, `DEPENDS_ON`) are **not consumed** by the lowering. This is a **partial** lowering — the canonical ISR's full semantics are not preserved in the plan.

**Classification:** The lowering is a **stabilization** mapping. It is the canonical runtime's Compiler IR entry point. It is not the final Compiler IR contract.

### 1.5 Canonical backends

| File | Backend |
|---|---|
| `compiler/backends/python_fastapi.py` | `PythonFastAPIBackend` (Python/FastAPI) |
| `compiler/backends/rust_axum.py` | `RustAxumBackend` (Rust/Axum) |
| `compiler/backends/reference_backend.py` | `ReferenceBackend` (reference implementation) |
| `compiler/backends/production/fastapi_backend.py` | `FastAPIFoundationBackend` (Gen-A) |
| `compiler/backends/production/postgres_schema.py` | (Gen-A) |
| `compiler/backends/production/openapi.py` | (Gen-A) |
| `compiler/backends/production/docker.py` | (Gen-A) |
| `compiler/backends/production/cicd.py` | (Gen-A) |
| `compiler/backends/production/register.py` | `register_production_backends` (Gen-A) |
| `compiler/backends/production/isr_helpers.py` | (Gen-A) |

**Classification:** The Gen-B backends (`python_fastapi.py`, `rust_axum.py`, `reference_backend.py`) are the canonical runtime. The Gen-A backends (`production/*`) are LEGACY (per R1-A).

---

## 2. Constitutional compiler (Gen-C) (`constitutional_architecture/compiler/`)

### 2.1 Files

| File/Dir | Size | Purpose |
|---|---|---|
| `constitutional_architecture/compiler/__init__.py` | (small) | Package init; lazy imports |
| `constitutional_architecture/compiler/pipeline.py` | 161 lines | `CompilerPipeline` (8-pass), `CompilerConfig`, `CompilationResult`, `build_default_pipeline()`, `build_default_backend_registry()` |
| `constitutional_architecture/compiler/compilation_config.py` | (small) | `CompilationConfig` (different from R1-B D07) |
| `constitutional_architecture/compiler/compiler_context.py` | (medium) | `CompilerContext` |
| `constitutional_architecture/compiler/compiler_result.py` | (medium) | `CompilationResult` |
| `constitutional_architecture/compiler/pass_interface.py` | (medium) | `Pass` ABC |
| `constitutional_architecture/compiler/pass_manager.py` | (small) | `PassManager` |
| `constitutional_architecture/compiler/pass_registry.py` | (medium) | `PassRegistry` |
| `constitutional_architecture/compiler/capability.py` | (medium) | `CapabilityResolver` |
| `constitutional_architecture/compiler/contract.py` | (medium) | Contracts |
| `constitutional_architecture/compiler/bir/model.py` | 1,100B | `BIR`, `BIRModule`, `BIRNode`, `BIRNodeType` (semantic donor) |
| `constitutional_architecture/compiler/bir/__init__.py` | (small) | Package init |
| `constitutional_architecture/compiler/backends/backend_interface.py` | (medium) | `CompilerBackend(ABC)` (Gen-C; different from canonical Protocol) |
| `constitutional_architecture/compiler/backends/backend_registry.py` | (medium) | Gen-C backend registry |
| `constitutional_architecture/compiler/backends/backend_selector.py` | (medium) | Gen-C backend selector |
| `constitutional_architecture/compiler/backends/fastapi_backend.py` | ~720 lines | Gen-C FastAPI backend (with `self.write_files()` defect — fixed in R1-C C06) |
| `constitutional_architecture/compiler/backends/__init__.py` | (small) | Package init |
| `constitutional_architecture/compiler/passes/validation_pass.py` | 31 lines | **Fail-open** validation (line 21-30: `success=True` on exception) |
| `constitutional_architecture/compiler/passes/normalization_pass.py` | 156 lines | **Lossy** normalization (carries only 7 of 21 System fields) |
| `constitutional_architecture/compiler/passes/optimization_pass.py` | 44 lines | Optimization pass |
| `constitutional_architecture/compiler/passes/capability_resolution_pass.py` | 78 lines | 13+ capabilities (OAUTH2, JWT_AUTH, etc.) |
| `constitutional_architecture/compiler/passes/lowering_pass.py` | 59 lines | ISR → BIR lowering |
| `constitutional_architecture/compiler/passes/code_generation_pass.py` | 110 lines | Code generation |
| `constitutional_architecture/compiler/passes/verification_pass.py` | 132 lines | **Fail-open** verification (line 51-79) |
| `constitutional_architecture/compiler/passes/cross_target_pass.py` | 38 lines | Cross-target pass |
| `constitutional_architecture/compiler/quality/optimization_engine.py` | (medium) | Optimization engine |
| `constitutional_architecture/compiler/artifacts/artifact_model.py` | (medium) | `Artifact`, `ArtifactType` |
| `constitutional_architecture/compiler/cache/` | (directory) | Compilation cache |
| `constitutional_architecture/compiler/observability/` | (directory) | Observability |
| `constitutional_architecture/compiler/quality/diagnostics.py` | (medium) | `Diagnostic` |

### 2.2 Gen-C 8-pass pipeline

| # | Pass | File | Status |
|---|---|---|---|
| 1 | Validation | `passes/validation_pass.py:7-31` | **Fail-open** (returns `success=True` on exception) |
| 2 | Normalization | `passes/normalization_pass.py:19-156` | **Lossy** (carries only 7 of 21 System fields) |
| 3 | Optimization | `passes/optimization_pass.py:8-44` | (MIGRATE_SEMANTICS) |
| 4 | Capability Resolution | `passes/capability_resolution_pass.py:8-78` | (MIGRATE_SEMANTICS) |
| 5 | Lowering | `passes/lowering_pass.py:8-59` | ISR → BIR |
| 6 | Code Generation | `passes/code_generation_pass.py:11-110` | (MIGRATE_SEMANTICS) |
| 7 | Verification | `passes/verification_pass.py:12-132` | **Fail-open** (returns `success=True` on engine exception) |
| 8 | Cross-Target | `passes/cross_target_pass.py:7-38` | (MIGRATE_SEMANTICS) |

### 2.3 Gen-C `CompilerPipeline` signature

```python
# constitutional_architecture/compiler/pipeline.py:86
def compile(self, isr: ISR, config: Optional[CompilationConfig] = None) -> CompilationResult:
```

**Observation:** The Gen-C pipeline takes an `ISR` (the rich `constitutional_architecture.isr.model.isr.ISR`), not the canonical `isr.core.revision.ISRRevision`. This is a **mismatch** with the canonical runtime. The canonical `isr_to_plan` takes `ISRRevision`; the Gen-C `compile` takes `ISR`.

**Classification:** The Gen-C pipeline is **not used by the canonical campaign runtime** (per R0 and R1-C C10). It is LEGACY and on the retirement path (R1-D.5).

### 2.4 Gen-C PassManager

| File | Line | Behavior |
|---|---|---|
| `constitutional_architecture/compiler/pass_manager.py:11-43` | (small) | `execute_all(ctx) -> bool` iterates `self._registry.resolved_order`. If a pass `result.success is False`, records error and **continues** (does not break). |

**Observation:** The PassManager **continues after a failed pass** (R0 confirmed this). This is a fail-open pattern. The canonical runtime does not use the PassManager.

---

## 3. BIR (semantic donor) (`constitutional_architecture/compiler/bir/`)

### 3.1 BIR model

| File | Type | Fields |
|---|---|---|
| `constitutional_architecture/compiler/bir/model.py:8-17` | `BIRNodeType` (str, Enum) | `HANDLER`, `ENTITY`, `SERVICE`, `REPOSITORY`, `ROUTER`, `CONFIG`, `MIDDLEWARE`, `EVENT_HANDLER`, `TEST` |
| `constitutional_architecture/compiler/bir/model.py:20-26` | `BIRNode` (@dataclass, frozen) | `id`, `node_type: BIRNodeType`, `name`, `attributes: dict`, `children: tuple[BIRNode, ...]` |
| `constitutional_architecture/compiler/bir/model.py:29-33` | `BIRModule` (@dataclass, frozen) | `id`, `name`, `nodes: tuple[BIRNode, ...]` |
| `constitutional_architecture/compiler/bir/model.py:36-40` | `BIR` (@dataclass, frozen) | `project_name`, `modules: tuple[BIRModule, ...]`, `metadata: dict` |

### 3.2 BIR semantics

- **Tree-structured:** `BIR` contains `BIRModule`s, each contains `BIRNode`s, each can have `children: tuple[BIRNode, ...]`. This is a **hierarchical** representation, in contrast to the canonical `CompilationPlan` which is flat.
- **9 node types:** `HANDLER`, `ENTITY`, `SERVICE`, `REPOSITORY`, `ROUTER`, `CONFIG`, `MIDDLEWARE`, `EVENT_HANDLER`, `TEST`.
- **No content-hash:** `BIR` is a `@dataclass(frozen=True)` with no hash method. **No deterministic identity.**
- **No provenance:** `BIR` has no `provenance` field. The `metadata: dict` is unstructured.
- **Used by:** `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` (ISR → BIR lowering), `constitutional_architecture/compiler/backends/fastapi_backend.py:31-32, 73-86` (consuming BIR). **Not used by the canonical campaign runtime.**

### 3.3 BIR as semantic donor

Per R1-A and R1-B D07, BIR is a **semantic donor**, not the canonical Compiler IR. The 9 BIRNodeType concepts may be selectively absorbed into the canonical Compiler IR where genuinely semantic. BIR is **not modified** to add content-hash; content-hash is added to the canonical Compiler IR.

---

## 4. Compiler bridge (dead code)

| File | Status |
|---|---|
| `constitutional_architecture/engine/compiler_bridge.py:13-45` | **DEAD CODE** — no callers (per R0 and R1-C C02 §11) |

**Classification:** RETIRE (per R1-C C02 §11, R1-D.5). Immediate removal is R1-D.5 work.

---

## 5. Category compilers (`constitutional_architecture/compilers/*`)

### 5.1 Directory structure

```
constitutional_architecture/compilers/
├── backend/
│   ├── base.py (BackendCompiler contract)
│   └── fastapi/compiler.py (consumes UniversalISR)
├── database/
│   ├── base.py
│   └── postgres/compiler.py
├── deployment/
│   ├── base.py
│   └── cicd/compiler.py
├── documentation/
│   ├── base.py
│   └── markdown/compiler.py
├── frontend/
│   ├── base.py
│   └── react/compiler.py
├── infrastructure/
│   ├── base.py
│   └── terraform/compiler.py
├── operational/
│   ├── base.py
│   └── intelligence/compiler.py
├── runtime_policy/
│   └── compiler.py
└── testing/
    ├── base.py
    └── pytest/compiler.py
```

**Total: 9 per-category compilers.**

### 5.2 BackendCompiler contract

```python
# constitutional_architecture/compilers/backend/base.py:11-19
class BackendCompiler:
    def compile(self, universal_isr: UniversalISR, architecture_genome, context) -> CompilationBundle:
        ...
```

**Observation:** Each per-category compiler takes a `UniversalISR` (the third ISR model from `constitutional_architecture/core/models/isr.py`) and an `ArchitectureGenome`, and produces a `CompilationBundle`. The 9 per-category compilers form a **second compiler runtime** that bypasses the canonical `CompilationPlan`.

**Classification:** **LEGACY; RETIRE** (per R1-A, R1-B D17 L10, R1-D.2 §29). Per INV-B14, no category-specific compiler becomes a new architectural authority.

---

## 6. Compiler consumers

### 6.1 Direct importers of `compiler/core/*` (canonical)

| Path | Imports | Purpose |
|---|---|---|
| `certification/campaign/plan_builder.py:13-14, 142-144` | `compiler.core.lowering.isr_to_plan`, `CompilationPlan` | Campaign plan builder (canonical runtime) |
| `certification/campaign/runner.py:10-13` | `CompilationPlan`, `CHECKER`, `GeneratedRepository`, `build_repository`, `BEHAVIORAL_CLASSES` | Campaign runner (canonical) |
| `certification/campaign/verdict.py:8` | `CompilationPlan` | Verdict (canonical) |
| `certification/campaign/verify_campaign.py:8` | `CompilationPlan` | Verify (canonical) |
| `certification/campaign/campaign_a.py:20-23` | `compiler.core.*` | Campaign A (canonical) |
| `certification/campaign/campaign_b.py:20-23` | `compiler.core.*` | Campaign B (canonical) |
| `certification/stages/stub_stages.py:32` | `compiler.core.*` | Stub stages (canonical) |
| `certification/stages/docker_stages.py:188` | `compiler.core.*` | Docker stages (canonical) |
| `certification/stages/independent_verify.py:33` | `compiler.core.*` | Independent verify (canonical) |
| `certification/provenance/bundle.py:116` | `plan.model_dump()` (provenance hash) | Provenance (canonical) |

**Total: 10 canonical consumers.** All use the canonical `CompilationPlan` and `isr_to_plan`. None use Gen-C or BIR.

### 6.2 Direct importers of `constitutional_architecture/compiler/*` (Gen-C)

| Path | Imports | Purpose |
|---|---|---|
| `constitutional_architecture/tests/test_end_to_end.py:68, 567` | `constitutional_architecture.compiler.*` | Constitutional tests |
| `constitutional_architecture/compiler/__init__.py:17` | `constitutional_architecture.compiler.backends.fastapi_backend` | Gen-C init |
| `constitutional_architecture/compiler/pipeline.py:66` | `constitutional_architecture.compiler.backends.fastapi_backend` | Gen-C pipeline |
| `constitutional_architecture/compiler/backends/__init__.py:11` | `constitutional_architecture.compiler.backends.fastapi_backend` | Gen-C backends init |

**Total: 4 Gen-C consumers.** All within the constitutional substrate. None in the canonical runtime.

### 6.3 Direct importers of `constitutional_architecture/compilers/*` (per-category)

| Path | Imports | Purpose |
|---|---|---|
| `tests/test_build_system.py:5-8` | `constitutional_architecture.compilers.backend.fastapi.compiler` | Test |
| `tests/test_backend_compiler.py:5` | `constitutional_architecture.compilers.backend.fastapi.compiler` | Test |
| `tests/test_deployment_compiler.py:3-7` | `constitutional_architecture.compilers.deployment.cicd.compiler` | Test |
| `tests/test_documentation_compiler.py:5` | `constitutional_architecture.compilers.documentation.markdown.compiler` | Test |
| `tests/test_operational_compiler.py:6` | `constitutional_architecture.compilers.operational.intelligence.compiler` | Test |
| `tests/test_react_compiler.py:5` | `constitutional_architecture.compilers.frontend.react.compiler` | Test |
| `tests/test_runtime_policy_compiler.py:3` | `constitutional_architecture.compilers.runtime_policy.compiler` | Test |
| `tests/test_terraform_compiler.py:5-8` | `constitutional_architecture.compilers.infrastructure.terraform.compiler` | Test |
| `tests/test_test_compiler.py:3` | `constitutional_architecture.compilers.testing.pytest.compiler` | Test |
| `tests/test_cap_*.py` | `constitutional_architecture.compilers.*` | Test |
| `tests/test_r29_10_7_backend_conformance.py:44` | `constitutional_architecture.compilers.backend.fastapi.compiler` | Test |

**Total: ~11 per-category compiler consumers.** All in tests. None in the canonical runtime.

### 6.4 Direct importers of `constitutional_architecture/compiler/bir/*`

| Path | Imports | Purpose |
|---|---|---|
| `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` | `BIR`, `BIRModule`, `BIRNode` | Lowering |
| `constitutional_architecture/compiler/backends/fastapi_backend.py:31-32, 73-86` | `BIR` | Backend consumption |
| `constitutional_architecture/tests/test_*bir*.py` | `BIR` | Constitutional tests |

**Total: 3+ BIR consumers.** All within the constitutional substrate.

---

## 7. Tests

### 7.1 Canonical compiler tests

| Test file | Purpose |
|---|---|
| `tests/cbc1/test_campaign_a.py` | Campaign A tests (canonical) |
| `tests/cbc1/test_campaign_b.py` | Campaign B tests (canonical) |
| `tests/cbc1/test_cbc1_gates.py` | CBC1 gates (canonical) |
| `tests/cbc1/test_plan_builder.py` | Plan builder tests (canonical) |
| `tests/v14/test_multi_backend.py:14, 92, 97, 125, 138, 150, 167, 185` | Multi-backend tests (Gen-B canonical) |
| `tests/r1c/test_artifact_adapter.py` | R1-C adapter tests (ADAPTER-ARTIFACT-001) |
| `tests/r1d1/test_isr_semantic_migration.py` | R1-D.1 ISR tests |

### 7.2 Constitutional compiler tests

| Test file | Purpose |
|---|---|
| `constitutional_architecture/tests/test_end_to_end.py` | Gen-C end-to-end tests |
| `constitutional_architecture/tests/test_*bir*.py` | BIR tests |
| `tests/test_build_system.py` | Build system tests (compilers/*) |
| `tests/test_backend_compiler.py` | Backend compiler tests |
| `tests/test_database_compiler.py` | Database compiler tests |
| `tests/test_deployment_compiler.py` | Deployment compiler tests |
| `tests/test_documentation_compiler.py` | Documentation compiler tests |
| `tests/test_operational_compiler.py` | Operational compiler tests |
| `tests/test_react_compiler.py` | React compiler tests |
| `tests/test_runtime_policy_compiler.py` | Runtime policy compiler tests |
| `tests/test_terraform_compiler.py` | Terraform compiler tests |
| `tests/test_test_compiler.py` | Test compiler tests |
| `tests/test_cap_*.py` | Capability compiler tests |
| `tests/test_r29_10_7_backend_conformance.py` | Backend conformance tests |

---

## 8. Cross-cutting symbols

### 8.1 `CompilationPlan` usages (canonical)

Found in: `compiler/core/plan.py:32-40` (definition), `compiler/core/lowering.py:5-11, 68-71` (construction), `compiler/core/protocol.py:12, 63-64` (consumed by CompilerBackend Protocol), `compiler/core/conformance.py` (conformance check), `certification/campaign/*` (canonical runtime), `certification/stages/*` (canonical runtime), `certification/provenance/bundle.py:116` (provenance hash via `plan.model_dump()`).

### 8.2 `BIR` usages (constitutional)

Found in: `constitutional_architecture/compiler/bir/model.py:36-40` (definition), `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` (lowering output), `constitutional_architecture/compiler/backends/fastapi_backend.py:31-32, 73-86` (backend input). **Not in the canonical runtime.**

### 8.3 `CompilerPipeline` usages (constitutional)

Found in: `constitutional_architecture/compiler/pipeline.py:72-161` (definition), `constitutional_architecture/compiler/__init__.py:17` (lazy import), `constitutional_architecture/tests/test_end_to_end.py:68, 567` (test). **Not in the canonical runtime.**

### 8.4 `CompilerBackend` usages

| Protocol | File | Definition |
|---|---|---|
| Gen-B | `compiler/core/protocol.py:52-65` | Duck-typed Protocol; used by canonical backends |
| Gen-C | `constitutional_architecture/compiler/backends/backend_interface.py:16-36` | `CompilerBackend(ABC)`; used by Gen-C |
| Gen-A | `compiler/sdk/base.py:CompilerBackendBase` | Legacy |

**Observation:** Three different `CompilerBackend` definitions. Only the Gen-B Protocol (`compiler/core/protocol.py:52-65`) is in the canonical runtime. Per R1-A, the canonical backend protocol is the Gen-B Protocol.

### 8.5 `isr_to_plan` (canonical lowering)

Found in: `compiler/core/lowering.py:14-73` (definition), `certification/campaign/plan_builder.py:13-14, 142-144` (canonical runtime usage). **The canonical ISR → CompilationPlan lowering.**

### 8.6 `compiler_bridge` (dead code)

Found in: `constitutional_architecture/engine/compiler_bridge.py:13-45` (definition). **No callers** (per R0 and R1-C C02 §11). **DEAD CODE.**

---

## 9. Ownership summary

| Module | Owner | Status | R1-D.2 classification |
|---|---|---|---|
| `compiler/core/plan.py:CompilationPlan` | Canonical | Stabilization (not final IR) | **D2-D3/D2-D5** (classify) |
| `compiler/core/protocol.py:CompilerBackend` | Canonical | KEEP (canonical backend protocol) | (none) |
| `compiler/core/lowering.py:isr_to_plan` | Canonical | KEEP (canonical lowering) | (none) |
| `compiler/core/conformance.py:CHECKER` | Canonical | KEEP (structural conformance; behavioral in R1-E) | (none) |
| `compiler/core/repository.py:GeneratedRepository` | Canonical | Stabilization (ArtifactSet equivalent) | **D2-D5/D2-D7** (ArtifactSet module in R1-D.5) |
| `compiler/composition.py:build_backend_registry` | Canonical | KEEP | (none) |
| `compiler/backends/python_fastapi.py` | Canonical | KEEP | (none) |
| `compiler/backends/rust_axum.py` | Canonical | KEEP | (none) |
| `compiler/backends/reference_backend.py` | Canonical | KEEP | (none) |
| `compiler/backends/production/*` (Gen-A) | Canonical | LEGACY | **RETIRE** (R1-D.5) |
| `constitutional_architecture/compiler/pipeline.py:CompilerPipeline` | Constitutional | LEGACY | **RETIRE** (R1-D.5) |
| `constitutional_architecture/compiler/passes/*` (8 passes) | Constitutional | LEGACY | **ADAPT/RETIRE** (R1-D.5/R1-E.x) |
| `constitutional_architecture/compiler/bir/model.py:BIR` | Constitutional | LEGACY (semantic donor) | **RETAIN AS DONOR** (per R1-A; R1-D.2 selective migration) |
| `constitutional_architecture/compiler/backends/fastapi_backend.py` | Constitutional | LEGACY (ADAPTER-ARTIFACT-001 already in R1-C) | (artifact purity done) |
| `constitutional_architecture/compiler/backends/backend_interface.py` | Constitutional | LEGACY | **RETIRE** (R1-D.5) |
| `constitutional_architecture/compiler/quality/*` | Constitutional | LEGACY | (MIGRATE_SEMANTICS) |
| `constitutional_architecture/compiler/observability/*` | Constitutional | LEGACY | (out of scope) |
| `constitutional_architecture/compiler/cache/*` | Constitutional | LEGACY | (out of scope) |
| `constitutional_architecture/engine/compiler_bridge.py` | Constitutional | DEAD CODE | **RETIRE** (R1-D.5; immediate) |
| `constitutional_architecture/compilers/*` (9 per-category) | Constitutional | LEGACY | **RETIRE** (R1-D.5; INV-B14) |

---

## 10. Cross-references

- D07 (R1-B): `folder/CONTRACT_CanonicalCompilerIR.md`
- D9 (R1-D.1): `folder/R1_D1_GATE_REPORT.md`
- R1-C C12: `folder/R1_C_GATE_REPORT.md`
- R0: `folder/R0_RECONNAISSANCE_REPORT.md`

---

*End of D2-D1. The R1-D.2 compiler/IR inventory is complete. 10 canonical consumers, 4 Gen-C consumers, ~11 per-category compiler consumers, 3+ BIR consumers. Classification: KEEP / MIGRATE_SEMANTICS / RETIRE / RETAIN AS DONOR. D2-D2 (execution graph) follows.*
