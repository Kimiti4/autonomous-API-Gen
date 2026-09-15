# R1 — Migration and Implementation Plan

**Mission:** Migrate the repository from two parallel substrate families to a single coherent runtime with Substrate A as the canonical execution substrate, and Substrate B's strongest semantic properties selectively absorbed into Substrate A.

**Status:** R0 PASS (per user's acceptance). C-01 DECIDED (Option 1, with the C-03 refinement below). R1 BLOCKED until user explicitly authorizes "Proceed with Option 1 and begin R1".

**This document is the first R1 deliverable (the plan itself).** Per the user's instruction, R1 produces the plan first, before modifying production code. The plan is untracked (per the `.md` policy: internal analysis/spec) and is the gate for any code work. No code is modified by this plan.

---

## 0. C-01 decision record

### 0.1 Decision

**OPTION 1 — Substrate A is canonical; Substrate B is consolidated onto A.**

| Layer | Canonical |
|---|---|
| ISR | `isr/core` |
| Requirement Graph | `reqgraph/core` |
| Evolution | `evolution/` (root) |
| Compiler IR (current) | `compiler/core/plan.py:CompilationPlan` (stabilization substrate) |
| Compiler IR (target) | **future canonical Compiler IR contract** (R1-B) — initially implemented by/adapted from `CompilationPlan`; BIR is a **semantic donor** (its useful semantic properties are extracted and implemented in the new contract), not a patched implementation |
| Compiler pipeline | Gen-B `compiler/composition.py:build_backend_registry()` (current); future compiler IR will replace `CompilationPlan` as the lower target |
| Backend contract | `compiler/core/protocol.py:CompilerBackend` (current) |
| Certification | `certification/` (existing) |
| Provenance | existing campaign provenance + ledger |
| Constitutional architecture | **governance/specification layer** over the canonical substrate — not a second runtime |

### 0.2 C-03 refinement (per user)

The user's instruction modifies the C-03 row of the R0 conflict table:

> `CompilationPlan` itself appears too close to a compilation plan/artifact mapping to serve as Tiannara's ultimate compiler IR. The eventual distinction should be: ISR → Architecture Model → Compiler IR → Backend Lowering → ArtifactSet (not ISR → CompilationPlan → files).

So the canonical Compiler IR is **not** `CompilationPlan` long-term. `CompilationPlan` is the **stabilization substrate** that the campaign runtime uses today.

#### BIR is a semantic donor, not the implementation (correction 1)

Per the user's correction:

> Extract the required semantic properties from BIR and implement them in the new canonical Compiler IR contract. Do not modify BIR merely to make it canonical. BIR can then be retired.

The desired migration is:

```text
BIR
 │
 ├── useful semantic concepts
 │
 ▼
Canonical Compiler IR specification
 │
 ▼
canonical implementation
 │
 ▼
content hash
serialization
determinism
provenance
```

Concretely: R1-D.2 does **not** "add content-hash to BIR". Content-hash is added to the **canonical Compiler IR contract** (the new implementation). BIR is read as reference material, and its useful semantic properties (e.g. HANDLER/ENTITY/SERVICE/REPOSITORY/ROUTER/CONFIG/MIDDLEWARE/EVENT_HANDLER/TEST node types where genuinely semantic) are extracted into the canonical contract's specification. The canonical implementation is a new module, not a patched BIR. BIR can then be retired.

This is consistent with the C-03 refinement and prevents the temporary stabilization layer (or BIR) from becoming permanent by accident.

### 0.3 Rejected alternatives

- **Option 2 (Substrate B canonical; rewire A to B).** Rejected. Would require re-running the B3-v2 campaign or invalidating its evidence; promotes the less-proven runtime to the constitutional execution path. The strongest argument against is **evidence continuity**: Substrate A has 243 Tier A tests passing, 40/40 Tier C tests passing, an intact B3-v2 443-trial evidence chain, a working fail-closed certification, and a content-addressed ISR. Substrate B has more ambitious architecture but several of its most important properties are presently less trustworthy (fail-open validation/verification, semantic loss during normalization, lossy ISR adapters, broken/dead compiler bridge, incomplete transformation recording, filesystem emission inside compilation, multiple backend abstractions). Promoting B would mean moving the system onto a less-proven substrate.
- **Option 3 (keep both; typed adapter).** Rejected. Audit §39 (NO NEW SOURCE OF TRUTH) explicitly forbids this. A bidirectional adapter recreates the dual-source-of-truth problem.

### 0.4 Evidence-preservation rationale

The B3-v2 evidence chain is preserved. It is historical evidence of the old canonical runtime (Substrate A as it exists today). After migration, a new campaign identity proves equivalence where required, and Tiannara's history is:

```
Historical Evidence (B3-v2, etc.)
       │
       ▼
Migration Evidence
       │
       ▼
Canonical Substrate Certification
       │
       ▼
Future Evolution Campaigns
```

not "the old campaign happened on the new architecture". The historical evidence is not invalidated; a new campaign runs on the new architecture.

### 0.5 Canonical module map (the executable substrate)

```
isr/core/                 (canonical ISR)
reqgraph/core/            (canonical Requirement Graph)
evolution/core/           (canonical Evolution)
compiler/core/            (canonical Compiler substrate; CompilationPlan is the stabilization Compiler IR)
compiler/composition.py   (canonical compiler entry / registry builder)
compiler/core/protocol.py (canonical backend contract)
certification/            (canonical Certification)
release/evidence/         (canonical Provenance / evidence ledger)
tests/cbc1/               (canonical Tier A test surface)
tests/cbc1/conftest.py    (canonical Phase 31 fixtures)
```

### 0.6 Constitutional layer (governance/specification, NOT a second runtime)

```
constitutional_architecture/
    ├── governance/        (canonical governance contracts)
    ├── isr/semantics/     (semantic validators that are genuinely semantic — selective migration)
    ├── isr/views/         (rich views over isr/core; not a runtime)
    ├── isr/profiles/      (architecture profiles / target architecture specifications)
    ├── eir/               (eventual evolution record schema; selective migration into evolution/)
    ├── compiler/          (eventual canonical Compiler IR contract; selective migration)
    ├── validation/        (canonical validation contracts)
    └── verification/      (canonical verification contracts; SELECTIVE; fail-closed)
```

### 0.7 Forbidden parallel implementations (R1 enforcement)

The forbidden parallel implementations are stated below. Each is enforced as a **semantic-authority invariant**, not merely a directory count: a directory may have multiple representations, but only one may independently define system semantics. Views, projections, serialized forms, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics.

**Semantic-authority invariants:**

- **ISR:** There must be exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches and backend-specific representations may exist, but none may independently define system semantics.
- **Compiler IR:** There must be exactly one authoritative semantic representation of a compiled architecture's compilation plan. The same semantic-authority principle applies: views are permitted; independent definitions are forbidden.
- **Evolution:** There must be exactly one authoritative Evolution engine. Mutations, lineage, EIR records flow through it.
- **Backend contract:** There must be exactly one authoritative backend protocol that backends implement.
- **Requirement Graph:** There must be exactly one authoritative Requirement Graph.
- **Provenance:** There must be exactly one authoritative Provenance store.

**Concrete prohibitions (enforcement of the above):**

- No second `isr/` package as a runtime.
- No second `Compiler IR` type as a runtime.
- No second `Evolution` engine as a runtime.
- No second `BackendProtocol` as a runtime.
- No second `RequirementGraph` as a runtime.
- No second `ProvenanceStore` as a runtime.
- No bidirectional A↔B adapter.
- No rewriting historical certification evidence.
- No new artifact-emission path that writes to filesystem inside `compile()`.

### 0.8 Recommended final R1 architecture (per user)

The R1 target architecture (canonical execution path):

```text
                    REQUIREMENTS
                         │
                         ▼
                  Requirement Graph
                         │
                         ▼
                  ┌──────────────┐
                  │ CANONICAL ISR│
                  └──────┬───────┘
                         │
                         ▼
                 Architecture Model
                         │
                         ▼
               Evolution / Candidates
                         │
                         ▼
                Canonical Compiler IR
                         │
                         ▼
                  Backend Contract
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           FastAPI                Rust
              │                     │
              └──────────┬──────────┘
                         ▼
                     ArtifactSet
                         │
                         ▼
                    Verification
                         │
                         ▼
                    Certification
                         │
                         ▼
                    Provenance
                         │
                         ▼
                  Runtime Evidence
                         │
                         ▼
                      Evolution
```

The constitutional layer sits **above/beside this as governance**, rather than competing with it:

```text
              CONSTITUTION
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
    Invariants   Policies   Governance
       │           │           │
       └───────────┼───────────┘
                   ▼
             Canonical Runtime
```

The constitutional layer is `constitutional_architecture/` as a governance/specification layer (invariants, policies, governance contracts) over the canonical runtime. It is not a second runtime. Its strongest semantic capabilities (validated semantic invariants, fail-closed verification contracts) are selectively absorbed into the canonical runtime; its duplicated runtimes are retired.

---

## 1. Regenerated conflict table (per Option 1 + the 5 corrections)

This is the regeneration of the R0 conflict table with C-01 decided as Option 1 + C-03 refinement. R1 sequencing is keyed to this table.

| # | Conflict | Decision (per Option 1) | Migration path | Risk |
|---|---|---|---|---|
| C-01 | Substrate choice | **DECIDED: Option 1 (A canonical)** | n/a | — |
| C-02 | ISR models | Canonical: `isr.core` (frozen, content-hashed, 9 node kinds, fail-closed invariants). `constitutional_architecture.isr.model` and `UniversalISR` retired as runtime; semantic validators selectively migrated into `isr.core` | Adapter (read-only) for `constitutional_architecture.isr.semantics.*`; deprecate `model.isr.ISR` and `core.models.isr.UniversalISR` from runtime; keep as documentation/spec | P0 |
| C-03 | Compiler IRs | Stabilization: `compiler.core.plan.CompilationPlan` (current). Target: future canonical Compiler IR contract (R1-B), initially implemented by/adapted from `CompilationPlan`. **BIR is a semantic donor**: its useful semantic properties (HANDLER/ENTITY/SERVICE/REPOSITORY/ROUTER/CONFIG/MIDDLEWARE/EVENT_HANDLER/TEST) are extracted and implemented in the new contract. **Content-hash is added to the canonical Compiler IR contract, not to BIR.** `UniversalISR`-as-typed-graph retired. BIR can be retired after its semantic properties are extracted. | Define canonical Compiler IR contract; extract BIR semantics as references, not patches; preserve campaign's content-hash provenance | P0 |
| C-04 | Compiler pipeline generations | Canonical: Gen-B `compiler/composition.py:build_backend_registry()`. Gen-A `compiler/kernel.py:UniversalCompiler` is supported but not the campaign path. Gen-C `constitutional_architecture/compiler/pipeline.py` becomes the **future canonical pipeline** (R1-B) | Migrate Gen-C 8-pass design (after fail-closed repair) into the canonical pipeline; preserve campaign wiring | P0 |
| C-05 | Compiler bridge | **Delete** `constitutional_architecture/engine/compiler_bridge.py` (dead code, broken API, no callers). If a future bridge is needed it is rebuilt against the canonical Compiler IR | Delete; record deletion in evidence | P1 |
| C-06 | EIR | Canonical: `evolution/` (root) emits evolution records (lineage + transformation). `constitutional_architecture.eir.transformation.Transformation` is the **eventual schema**; its missing fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`) are added in R1-D. The `evolution_loop.py:110 transformations=[]` defect is repaired (in Substrate B's path; if retired it is moot) | Selective migration of EIR schema into `evolution/` | P1 |
| C-07 | Validation pass fail-open | Repair in `constitutional_architecture/compiler/passes/validation_pass.py` ONLY if the path is preserved. **Per C-04, the Gen-C pipeline is the future canonical pipeline; therefore the repair is required.** Change to `PassResult(success=result.passed, ...)`; no `try/except: success=True` | Repair | P0 |
| C-08 | Verification pass fail-open | Repair in `constitutional_architecture/compiler/passes/verification_pass.py`. Add `VERIFICATION_INDETERMINATE` outcome; block certification. **Required because Gen-C is the future canonical pipeline.** | Repair | P0 |
| C-09 | PassManager continue-on-failure | Repair in `constitutional_architecture/compiler/pass_manager.py`. Add `preconditions` / `BLOCK` semantics; pass declares its blocking behavior | Repair | P0 |
| C-10 | Normalization loses semantics | Repair in `constitutional_architecture/compiler/passes/normalization_pass.py`. Carry all System fields; rebuild via `with_system` | Repair | P0 |
| C-11 | ISR↔TypedGraph round-trip | Repair in `constitutional_architecture/engine/isr_adapter.py` (or retire if Substrate B's typed-graph projection is not needed). If preserved, make round-trip semantics-preserving with explicit round-trip tests | Repair + test | P0 |
| C-12 | Backend protocols | Canonical: `compiler/core/protocol.py:CompilerBackend` (the campaign path). `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` and `compilers/*/base.py:BackendCompiler` are retired as runtime; their interface contracts selectively migrate into the canonical backend protocol if needed | Adapter (read-only) where the contract differs; deprecate | P1 |
| C-13 | Backend filesystem write | Adopt Gen-B emission pattern: backend returns `ArtifactSet`; packager writes. Gen-C `constitutional_architecture/compiler/backends/fastapi_backend.py:85` `self.write_files()` is removed | Refactor | P1 |
| C-14 | Backend BEHAVIORAL classification | Demote `python-fastapi` and `rust-axum` to `STRUCTURAL` until evidence supports `BEHAVIORAL`; OR complete the generation. Per the audit, this is a certification concern. Decision deferred to R1-E | Demote or complete | P1 |
| C-15 | Lineage durability | Persist lineage as hash-chained records in `release/evidence/lineage/{wave}.jsonl` (mirror certification ledger). `LineageEntry` includes `eir_id`, `parent_eir_id`, `evidence_ref` | New `evolution/lineage_store.py` | P2 |
| C-16 | Crossover correctness | Substrate A `evolution/core/operations.py:74-104` is real — keep. Audit Substrate B's `constitutional_architecture/engine/crossover_engine.py`; if defects, repair or retire | Audit | P1 |
| C-17 | Observation ↔ ISR lineage | **Deferred out of R1** unless `autonomous-api/` is part of the runtime path required for the first full-stack compiler vertical slice. `autonomous-api/` is classified as a **legacy application/runtime surface**. It must not introduce an ISR source of truth. Its final disposition is deferred to the platform integration phase (R2/R3). | Classify LEGACY; no R1 work | **DEFERRED** |
| C-18 | `pyproject.toml` topology | **Deferred to post-R1 packaging cleanup.** Changing `name = "knowledge-graph-runtime"` and `packages = ["knowledge*"]` is not architecturally important enough to sit inside this P0/P1 migration. More importantly, changing package topology while canonicalization is underway can create noise in import paths and CI. First stabilize architecture; then clean packaging. | Defer | **DEFERRED (post-R1)** |
| C-19 | Knowledge / Civilization / distributed_evolution | Out of scope. Higher-level platform | None | P3 |
| C-20 | Generated artifacts | `generated/testshop`, `generated/monolithshop` are evidence of an earlier generation; classify as `LEGACY_GENERATED`; exclude from canonical scope; do not regenerate with unsafe defaults | None (or fix the generator defaults in C-13/C-14) | P3 |

---

## 2. R1 sequencing (R1-A through R1-F)

### R1-A — Freeze the canonical-substrate decision

**Deliverable:** `folder/CANONICAL_SUBSTRATE_DECISION.md` (a tracked governance ADR, like `adr-phase28-constitutional-governance-closure.md` and `PHASE31_CLOSEOUT_ADR.md`).

**Content:**
- The C-01 decision (Option 1).
- The C-03 refinement (CompilationPlan is the stabilization substrate; future canonical Compiler IR contract).
- The rejected alternatives (Option 2, Option 3).
- The canonical module map (§0.5).
- The constitutional layer (§0.6).
- The forbidden parallel implementations (§0.7).
- The evidence-preservation rationale (§0.4).
- The migration principles (adapters are LEGACY → CANONICAL, never A↔B).
- The historical evidence chain (B3-v2, etc.) is preserved.

**Out of scope:** code changes.

**Gate:** the user explicitly approves the ADR before R1-B begins.

### R1-B — Canonical contract freeze

**Deliverable:** A `folder/CANONICAL_CONTRACTS.md` (or a `canonical_architecture/contracts/` set) that defines the authoritative contracts for:

```
RequirementGraph
ISR
ArchitectureCandidate
EvolutionOperation
EvolutionRecord / EIR
CompilerIR
CompilerBackend
ArtifactSet
VerificationResult
CertificationEvidence
RuntimeObservation
```

For each contract: the canonical Python class/module, the immutable field set, the content-hash scheme, the forbidden implementation terms, the relationship to Substrate B's analogous types (if any), and the migration plan.

**Out of scope:** code changes. The contracts are defined as documentation/spec; implementation follows in R1-D/E.

**Gate:** the user reviews and approves each contract before migration.

### R1-C — Establish adapters only temporarily

**Rule:** Adapters are always:

```
LEGACY → CANONICAL
```

**never:**

```
A ↔ B
```

because bidirectional adapters recreate the dual-source-of-truth problem.

Adapters are explicitly marked `LEGACY` and are deprecated when the canonical replacement is fully covered.

**Out of scope:** code changes. This is a rule recorded in `CANONICAL_SUBSTRATE_DECISION.md` and `CANONICAL_CONTRACTS.md`.

### R1-D — Migrate semantics

**Deliverables (in order):**

1. **Migrate rich ISR semantics into canonical ISR.** From `constitutional_architecture/isr/semantics/*` and `constitutional_architecture/isr/validation/checker.py`, identify the validators that are genuinely semantic (e.g., requirement-layer semantic obligation / test / verification distinction, technology-leakage rejection). Add them to `isr/core/invariants.py` (or a new `isr/core/semantics/`) preserving the fail-closed invariant. Keep the canonical ISR's 9-node taxonomy (do not bloat).
2. **Extract useful BIR semantics into the canonical Compiler IR contract (BIR is a semantic donor).** From `constitutional_architecture/compiler/bir/model.py` (HANDLER/ENTITY/SERVICE/REPOSITORY/ROUTER/CONFIG/MIDDLEWARE/EVENT_HANDLER/TEST), identify the node types that the canonical Compiler IR needs. **Content-hash is added to the canonical Compiler IR contract, not to BIR.** The canonical Compiler IR is a new module — the next-generation IR, not a patched BIR. BIR is read as reference material; its useful semantic properties are extracted into the canonical contract's specification. The campaign's `CompilationPlan` is the stabilization implementation. BIR can be retired after its semantic properties are extracted.
3. **Migrate EIR semantics into canonical evolution.** From `constitutional_architecture/eir/transformation.py:Transformation`, add the missing fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`). The canonical evolution is `evolution/` (root). Repair `evolution_loop.py:110` (or retire, since Substrate B's EvolutionLoop is not the canonical path).
4. **Consolidate backend contracts.** Define one canonical `CompilerBackend` Protocol (per R1-B). Wrap Gen-A's `CompilerBackendBase`, Gen-C's `CompilerBackend(ABC)`, and `compilers/*/base.py:BackendCompiler` as adapters if needed; the canonical protocol is `compiler/core/protocol.py:CompilerBackend`.
5. **Remove/deprecate duplicate runtime paths.** `constitutional_architecture/core/models/isr.py:UniversalISR` retired as a runtime. `constitutional_architecture/isr/model/isr.ISR` retired as a runtime (semantic validators selectively migrated per R1-D.1). Gen-A `compiler/kernel.py:UniversalCompiler` retained as a supported entry but not the campaign path. Per-category `compilers/*` retired as runtime. BIR retired as a runtime after its semantic properties are extracted per R1-D.2.

**Out of scope:** correctness repairs (these are R1-E). The migration preserves the legacy behavior; the correctness repairs are separate.

**Gate:** each migration step is unit-tested AND the campaign's 243 Tier A tests still pass.

### R1-E — Repair canonical contracts first; then adapt implementations

Per the user's correction 2, R1-E does **not** repair Gen-C defects wholesale. Gen-C is **reference material**, not automatically the implementation to preserve. R1-E defines the **canonical contracts** (verification, failure semantics, pass execution) first, and only then migrates/adapts Gen-C implementations to those contracts.

**The principle:** *Canonical contracts first, implementation adapted second.* Specifically:

```text
Canonical verification contract
        ↓
Canonical failure semantics
        ↓
Canonical pass execution semantics
        ↓
Gen-C implementation migrated/adapted
```

**not:**

```text
Find bad Gen-C code
        ↓
Patch it
        ↓
Hope it becomes canonical
```

**Deliverables (in order; each gated on the prior):**

1. **Define the canonical Verification contract** (R1-B carries the contract; R1-E.1 formalizes the implementation under it). Add the `VERIFICATION_INDETERMINATE` outcome; block certification when verification is indeterminate. (Replaces ad-hoc WARN-on-exception in `constitutional_architecture/compiler/passes/verification_pass.py:51-79`.)
2. **Define the canonical Validation pass contract.** `PassResult(success=..., state=...)` where `state ∈ {PASS, FAIL, BLOCKED, INDETERMINATE, SKIPPED}`. Fail-closed: no `try/except: success=True`; no return of `success=True` on type-check failure. (Replaces ad-hoc fail-open in `constitutional_architecture/compiler/passes/validation_pass.py:21-30`.)
3. **Define the canonical Pass execution contract.** A pass declares `inputs, outputs, preconditions, postconditions, failure_behavior, determinism, side_effects, evidence_produced`. The PassManager blocks dependent passes when a precondition fails. (Replaces continue-on-failure in `constitutional_architecture/compiler/pass_manager.py:11-43`.)
4. **Define the canonical Normalization contract.** A normalization pass declares that it preserves all `System` fields (or an explicitly documented subset). Carry all 21 System fields; rebuild via `with_system`. (Replaces lossy normalization in `constitutional_architecture/compiler/passes/normalization_pass.py:49-56`.)
5. **Adapt Gen-C implementations to the canonical contracts.** Only after the contracts are frozen (R1-E.1 through R1-E.4), modify the Gen-C code to satisfy them. If a Gen-C implementation cannot satisfy the canonical contract without inventing a new source of truth, retire it instead. The goal is conformance to the contract, not preservation of the Gen-C code.
6. **Provenance.** Add content-hash to the canonical Compiler IR contract (per R1-D.2). Persist lineage as hash-chained records.
7. **Artifact purity.** Gen-C backend `constitutional_architecture/compiler/backends/fastapi_backend.py:85` calls `self.write_files()` inside `compile()`; refactor to return `ArtifactSet`; packager writes. If the Gen-C backend cannot be refactored without breaking the canonical Backend contract (per R1-D.4), retire it instead.
8. **Behavioral conformance.** `compiler/core/conformance.py:32-50` is structural-only; extend to behavioral where the backend can be exercised in tests. Demote `python-fastapi` and `rust-axum` to `STRUCTURAL` until evidence supports `BEHAVIORAL`.

**Deferred out of R1 (per corrections 3 and 4):**

- **C-17 (observation lineage via `autonomous-api/`)** — deferred to R2/R3 platform integration phase unless `autonomous-api/` is part of the runtime path required for the first full-stack compiler vertical slice. `autonomous-api/` is classified as a legacy application/runtime surface; it must not introduce an ISR source of truth. Its final disposition is deferred.
- **C-18 (`pyproject.toml` topology)** — deferred to post-R1 packaging cleanup. First stabilize architecture; then clean packaging. Changing `name` and `packages` while canonicalization is underway creates noise in import paths and CI.

**Out of scope:** R1-D migrations. R1-E works on canonical contracts first; migration runs in parallel per R1-D.

**Gate:** each canonical contract is reviewed and approved BEFORE the corresponding Gen-C adaptation begins. Each adaptation is unit-tested AND the campaign's 243 Tier A tests still pass AND no historical evidence is invalidated.

### R1-F — Establish Post-Migration Certification Baseline (renamed from "Re-certify")

Per the user's correction 7, R1-F is **not** a re-certification of B3-v2. It is a new **canonical-substrate certification campaign**.

**Framing (replaces old "do not rerun B3-v2" framing):**

```text
B3-v2
  = historical campaign
  = valid evidence for historical substrate

R1 migration
  = transformation

R2 campaign
  = evidence that canonical substrate satisfies its contracts
```

**Rule:** The B3-v2 evidence chain is preserved as historical evidence of the old canonical runtime. It is **not** the baseline for the new architecture. The new campaign (R2) is the **post-migration certification baseline** — evidence that the canonical substrate satisfies its contracts.

**Deliverable:** A new campaign identity (R2) and plan. The B3-v2 evidence chain is preserved and continues to be valid for what it is (a 443-trial / 410-CERTIFIED / 33-NOT_CERTIFIED / budget-exhausted honest campaign). Equivalence testing is an **explicit evidence category**, not an implicit obligation to repeat the old campaign. The new campaign runs on the migrated canonical substrate.

**Gate:** the user explicitly authorizes the new campaign.

---

## R1-B — Canonical Contract Definition & Boundary Gate (D01–D20)

**Status:** SPEC CAPTURED. R1-B is **NOT AUTHORIZED**. Awaiting explicit "Proceed with R1-B" from the user.

**Objective:** Establish the authoritative contracts for the single canonical Tiannara runtime selected by R1-A. R1-B is a **contract-design gate, not a coding/migration gate**. Its purpose is to freeze the interfaces that R1-C through R1-F must conform to.

**Scope:** Contract design, formalization, validation, compatibility analysis, and documentation.

**Forbidden:** Production migration, semantic implementation, deletion of legacy systems, campaign reruns, certification changes, or deployment.

### Architectural principle

```
ISR ≠ Architecture Model ≠ Compiler IR ≠ Generated Artifact
```

This is the principle R1-B must enforce. The four are distinct semantic surfaces; conflating any two of them is the exact substrate-duplication problem R0 discovered.

### Contract hierarchy

```
Requirement
    ↓
RequirementGraph
    ↓
Canonical ISR
    ↓
ArchitectureCandidate
    ↓
EvolutionOperation / EvolutionRecord
    ↓
Canonical CompilerIR
    ↓
CompilerBackend
    ↓
ArtifactSet
    ↓
VerificationResult
    ↓
CertificationEvidence
    ↓
RuntimeObservation
```

### D01 — Canonical Contract Registry

Create: `folder/CANONICAL_CONTRACT_REGISTRY.md`

Authoritatively enumerate the **eleven** contract surfaces (the original count of ten is corrected because `EvolutionRecord/EIR` is distinct from `EvolutionOperation`):

1. `RequirementGraph`
2. `ISR`
3. `ArchitectureCandidate`
4. `EvolutionOperation`
5. `EvolutionRecord / EIR`
6. `CompilerIR`
7. `CompilerBackend`
8. `ArtifactSet`
9. `VerificationResult`
10. `CertificationEvidence`
11. `RuntimeObservation`

The registry must identify for every contract: canonical owner, module/package, purpose, producer, consumer, identity, lifecycle, mutability, serialization, hashing, provenance, failure semantics, extension mechanism, current implementation, target implementation, legacy implementations, migration destination.

### D02 — RequirementGraph Contract

Canonical owner: `reqgraph/core`

Minimum semantics:

```
RequirementGraph
├── requirements
├── relationships
└── graph identity
```

Must establish: requirement identity, requirement content, graph identity, node ownership, edge types, deterministic serialization, graph hashing, immutability/versioning rules, validation rules, conflict semantics, refinement semantics, ownership semantics.

The four existing relationship classes must be explicitly assessed:

```
DEPENDS_ON
CONFLICTS_WITH
REFINES
OWNED_BY
```

**Do not add new edge types merely for completeness.**

### D03 — Canonical ISR Contract

This is the most important R1-B deliverable.

Canonical owner: `isr/core`

Define the ISR as the **single authoritative semantic representation of a software system revision**.

The contract must specify:

```
ISR
├── identity
├── revision
├── nodes
├── relationships
├── semantic properties
├── provenance
└── content hash
```

**Mandatory invariant:** There must be exactly one authoritative semantic representation for an ISR revision. Views, projections, indexes, caches, adapters, and analysis structures may exist, but **none may independently define ISR semantics**.

Explicitly document:

```
ISR
≠
Architecture Model
≠
Compiler IR
≠
Generated Artifact
```

Also define what semantic information from the constitutional ISR implementation is allowed to migrate into `isr/core`.

### D04 — ArchitectureCandidate Contract

Define the representation consumed by the evolution engine.

Must establish: candidate identity, parent identity, ISR revision reference, architecture decisions, topology, component boundaries, constraints, objectives, fitness/evaluation metadata, provenance, lineage, deterministic serialization, content identity.

Most importantly:

```
ArchitectureCandidate
        ↓
must reference
        ↓
Canonical ISR revision
```

It must **not become another ISR**.

### D05 — EvolutionOperation Contract

Canonical owner: `evolution/`

Define operations (mutation, crossover, recombination, selection, evaluation) without hardcoding unnecessary operators into the constitutional contract.

Each operation needs: operation ID, operator type, input candidate(s), output candidate(s), parameters, deterministic/randomness metadata, parentage, provenance, preconditions, postconditions, failure semantics.

Explicitly preserve the existing genuine crossover capability in root `evolution/`.

### D06 — EvolutionRecord / EIR Contract

Separate **an operation** from **the record of what happened**:

```
EvolutionOperation
        ↓ executes
EvolutionRecord / EIR
```

The record captures: operation identity, parent candidate(s), resulting candidate(s), operator, parameters, seed/randomness provenance, evaluation results, timestamps, lineage, evidence references, status, failure information.

This is where useful semantics from the constitutional EIR should be selectively absorbed.

**Do not recreate a second EIR runtime.**

### D07 — Canonical Compiler IR Contract

This is where the R1-A C-03 refinement becomes concrete.

The contract must explicitly establish:

```
Canonical ISR
      ↓
Architecture Model
      ↓
Compiler IR
      ↓
Backend Lowering
      ↓
ArtifactSet
```

`CompilationPlan` remains the **current stabilization implementation**, not the final architectural definition. The contract should define the future Compiler IR independently of that implementation.

Compiler IR concepts: compilation identity, source ISR/architecture references, target requirements, component model, interfaces, data flows, persistence requirements, API contracts, frontend/backend responsibilities, security requirements, deployment requirements, observability requirements, backend constraints, lowering metadata, provenance, deterministic identity/hash.

BIR is a **semantic donor**, not a competing IR.

### D08 — CompilerBackend Contract

Canonical owner: `compiler/core/protocol.py`

Define the backend boundary:

```
CompilerIR
     ↓
CompilerBackend
     ↓
ArtifactSet
```

A backend must not: redefine ISR semantics, modify the RequirementGraph, own architecture evolution, become a verification authority, directly mutate certification state, silently write arbitrary files outside ArtifactSet semantics.

Define: backend identity, supported target, capabilities, input contract, output contract, lowering responsibility, deterministic behavior, errors, unsupported capability behavior, versioning.

### D09 — ArtifactSet Contract

Define the canonical generated-software boundary:

```
ArtifactSet
├── files
├── directories
├── metadata
├── manifests
├── provenance
└── content hashes
```

Every generated artifact must be traceable to:

```
Requirement
→ RequirementGraph
→ ISR
→ ArchitectureCandidate
→ CompilerIR
→ Backend
→ ArtifactSet
```

The contract must explicitly distinguish:

```
generated artifact
vs
compiler workspace
vs
temporary build output
vs
runtime deployment artifact
```

This prevents backend filesystem emission from becoming an implicit architectural API.

### D10 — VerificationResult Contract

Define verification as an **evidence-producing subsystem**, not merely a boolean.

Minimum states:

```
PASS
FAIL
INDETERMINATE
NOT_RUN
BLOCKED
```

Critical invariant: an internal verifier exception must never silently become a successful verification result. `VERIFICATION_INDETERMINATE` must be representable.

The contract must include: verification ID, subject artifact/IR identity, verifier identity/version, checks performed, evidence, result, failure reason, indeterminate reason, provenance, timestamps, deterministic identity where applicable.

### D11 — CertificationEvidence Contract

Certification must remain downstream of verification:

```
Artifact
   ↓
Verification
   ↓
Evidence
   ↓
Certification
```

Define: evidence identity, subject identity, evidence type, source, verifier, verification result, hash, timestamp, campaign/run identity, ledger/provenance reference, certification status, historical immutability.

**Critical invariant:** R1-B must not alter historical B3-v2 evidence.

### D12 — RuntimeObservation Contract

Define the reverse path:

```
Deployed Artifact
       ↓
Runtime Observation
       ↓
Evidence
       ↓
Learning
       ↓
Evolution
```

Runtime observations must include enough lineage to identify:

```
deployment
→ ArtifactSet
→ CompilerIR
→ Architecture
→ ISR
→ RequirementGraph
```

This contract should not make `autonomous-api` canonical. **C-17 remains deferred.**

### D13 — Cross-Contract Identity & Provenance Model

Create one explicit identity model:

```
RequirementGraph ID
        ↓
ISR Revision ID
        ↓
ArchitectureCandidate ID
        ↓
EvolutionRecord ID
        ↓
CompilerIR ID
        ↓
ArtifactSet ID
        ↓
VerificationResult ID
        ↓
CertificationEvidence ID
        ↓
RuntimeObservation ID
```

Define: content hashes, parent references, immutable identities, version identities, provenance references, lineage rules.

This is critical because Tiannara ultimately needs **reconstructable engineering lineage**, not merely generated files.

### D14 — Contract State & Failure Semantics

Create a common state/error model. Explicitly answer:

- What does failure mean?
- What does indeterminate mean?
- What is blocked?
- What is invalid?
- What can be retried?
- What can be evolved?
- What must halt the pipeline?
- What is merely advisory?

Especially establish:

```
Validation failure
      ≠ warning

Verification exception
      ≠ success

Unsupported backend capability
      ≠ successful compilation
```

### D15 — Contract Compatibility Matrix

Create: `folder/R1_B_COMPATIBILITY_MATRIX.md`

Map:

| Canonical contract | Current A           | Constitutional B            | Action                                   |
| ------------------ | ------------------- | --------------------------- | ---------------------------------------- |
| ISR                | `isr/core`          | constitutional ISR          | retain A / selectively migrate semantics |
| CompilerIR         | CompilationPlan     | BIR                         | stabilize A / extract BIR semantics      |
| Evolution          | root evolution      | EIR engine                  | retain A / migrate semantics             |
| Backend            | Gen-B protocol      | Gen-C protocols             | retain A                                 |
| Verification       | certification stack | constitutional verification | reconcile selectively                    |

For every B component: `KEEP` / `MIGRATE` / `ADAPT TEMPORARILY` / `RETIRE` / `DEFER` with rationale.

### D16 — Contract Invariant Catalogue

Create formal invariants, extending the R1-A invariants.

- **INV-B01** — One canonical ISR semantic authority.
- **INV-B02** — RequirementGraph precedes ISR construction.
- **INV-B03** — ISR is technology-neutral.
- **INV-B04** — Architecture Model is distinct from ISR.
- **INV-B05** — Compiler IR is distinct from ISR.
- **INV-B06** — Compiler IR is distinct from generated artifacts.
- **INV-B07** — Evolution does not depend on backend technology.
- **INV-B08** — Backend cannot redefine upstream semantics.
- **INV-B09** — ArtifactSet is the generated-software boundary.
- **INV-B10** — Verification cannot fail open.
- **INV-B11** — Certification cannot manufacture verification evidence.
- **INV-B12** — Runtime observations retain reverse lineage.
- **INV-B13** — Historical evidence is immutable.
- **INV-B14** — No category-specific compiler becomes a new architectural authority.
- **INV-B15** — Legacy adapters are one-way: `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY`.

### D17 — Legacy Boundary Specification

Explicitly define the temporary R1-C boundary. Every surviving legacy subsystem must have:

```
LEGACY
Owner
Purpose
Input
Output
Canonical destination
Adapter direction
Retirement condition
```

This allows temporary coexistence **without creating a second source of truth**.

### D18 — Contract Test Specification

Define tests for the contracts **before migration**. Examples:

```
test_isr_identity_stable
test_isr_hash_deterministic
test_requirement_graph_identity_stable
test_architecture_references_isr
test_evolution_preserves_lineage
test_compiler_ir_references_architecture
test_backend_returns_artifact_set
test_backend_cannot_mutate_isr
test_verification_exception_is_indeterminate
test_certification_requires_evidence
test_runtime_observation_traces_to_artifact
```

These are contract tests, not the full implementation migration.

### D19 — Migration Constraints

Create: `folder/R1_B_MIGRATION_CONSTRAINTS.md`

Specify what R1-C/R1-D may and may not change.

**May:**

- Add canonical contract definitions.
- Add semantic validators.
- Add contract tests.
- Introduce temporary legacy→canonical adapters.
- Migrate semantic properties.

**May not:**

- Rewrite B3-v2.
- Modify historical certification evidence.
- Create bidirectional adapters.
- Introduce another ISR.
- Make BIR canonical.
- Make Gen-C a second compiler runtime.
- Alter campaign identity.
- Rerun B3-v2.
- Delete legacy components before mapping them.

### D20 — R1-B Gate Report

Final artifact: `folder/R1_B_CONTRACT_GATE_REPORT.md`

It must answer:

1. Are all canonical contracts defined?
2. Is ownership unambiguous?
3. Is ISR authority unambiguous?
4. Is Compiler IR distinct from ISR?
5. Is Compiler IR distinct from Architecture Model?
6. Is ArtifactSet the compiler output boundary?
7. Are verification failures fail-closed?
8. Is certification downstream of evidence?
9. Is runtime lineage defined?
10. Are legacy boundaries explicit?
11. Are BIR/EIR/Gen-C semantic contributions classified?
12. Can R1-C begin without architectural ambiguity?

Final verdict: `R1-B: PASS` or `R1-B: NOT_READY` with blocking conditions.

### R1-B Acceptance Gate

R1-B PASSES only if:

```
                 ┌─────────────────────┐
                 │ Canonical contracts │
                 │      complete       │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Ownership explicit  │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Identity/provenance │
                 │      defined        │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Failure semantics   │
                 │      defined        │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Legacy boundaries   │
                 │      defined        │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Contract tests      │
                 │      specified      │
                 └──────────┬──────────┘
                            ↓
                      R1-B PASS
```

### Most important constraint

**Do not implement the contracts as another parallel runtime.** R1-B should establish the **constitutional interfaces** first. R1-C can then create temporary legacy-to-canonical adapters, and R1-D can migrate semantic capabilities against those frozen boundaries.

### Resulting architecture (R1-B invariant)

```
Requirements
     ↓
RequirementGraph
     ↓
Canonical ISR
     ↓
Architecture Model
     ↓
Evolution
     ↓
Canonical Compiler IR
     ↓
Backend
     ↓
ArtifactSet
     ↓
Verification
     ↓
Certification
     ↓
Runtime Observation
     ↓
Evolution
```

with `constitutional_architecture/` governing the system rather than competing with it.

### R1-B execution discipline (captured from prior user guidance)

- R1-B produces the contract-design artifacts (D01–D20). It does not produce code.
- Each contract artifact is reviewed and approved individually before the next.
- The compatibility matrix (D15) and migration constraints (D19) are the gates between R1-B and R1-C.
- The gate report (D20) is the final R1-B deliverable. R1-B PASS requires all 12 gate questions to be answered.
- The canonical runtime code remains frozen throughout R1-B.

---

## 3. Forbidden actions (R1 enforcement)

The R1-A ADR codifies the forbidden parallel implementations (§0.7) as **semantic-authority invariants** (not directory counts). The R1-B contracts codify the canonical module map. R1-D migration does not invent new sources of truth. R1-E repairs do not weaken verification or manufacture certification. R1-F (renamed to "Establish Post-Migration Certification Baseline") does not rerun historical campaigns or rewrite evidence.

**Additionally (per the user's master-prompt refinements):**

- The agent MUST NOT "fix" Substrate B defects merely because they exist. First determine whether the affected component survives canonicalization. No implementation effort may be spent repairing a component that the canonicalization plan will retire, unless the repair is explicitly required for migration or safety.
- The agent MUST NOT delete Substrate B components until every semantic responsibility they contain has been mapped to a canonical destination and provenance/evidence impact has been recorded.
- The agent MUST NOT add content-hash to BIR. Content-hash is added to the canonical Compiler IR contract (per R1-D.2). BIR is a semantic donor.
- The agent MUST NOT repair Gen-C code wholesale. R1-E defines the canonical contracts first; only then are Gen-C implementations migrated/adapted to those contracts. Gen-C code that cannot satisfy the canonical contract is retired, not patched.
- The agent MUST NOT redefine "one canonical ISR" as a directory count. The invariant is **semantic authority**: there is exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics. The same principle applies to Compiler IR, Evolution, Backend contract, Requirement Graph, and Provenance.

This prevents the classic failure mode of architectural remediation: fixing obsolete code instead of fixing the architecture.

---

## 4. R1 stop conditions (per the audit's §51)

R1 implementation is paused and the user is consulted when any of the following is true:

- Canonical ISR cannot be determined for a migrated semantic.
- Two representations have incompatible semantics.
- Migration would destroy provenance.
- A canonical contract cannot be defined without inventing a new source of truth.
- A repair cannot be made without weakening verification.
- A certification contract conflicts with the migrated implementation.
- Backend capability semantics are undefined.
- The Tier A 243-test suite would fail under the proposed migration.

In each case, R1 reports:

```
UNKNOWN
WHY IT MATTERS
OPTIONS
RECOMMENDED DECISION
EVIDENCE REQUIRED
```

and waits for the user's decision.

---

## 5. R1-A ADR draft (embedded for review)

The R1-A deliverable is `folder/CANONICAL_SUBSTRATE_DECISION.md`. The draft is included below for the user's review before commit. After the user reviews and approves, R1-A is committed (as a tracked governance ADR per the existing pattern of `adr-phase28-constitutional-governance-closure.md` and `PHASE31_CLOSEOUT_ADR.md`).

### Draft: `folder/CANONICAL_SUBSTRATE_DECISION.md`

```markdown
# Canonical Substrate Decision

**Status:** Accepted. The C-01 substrate fork is decided as Option 1.

**Authority:** R0 reconnaissance (`folder/R0_RECONNAISSANCE_REPORT.md`) and user acceptance.

## Decision

**OPTION 1 — Substrate A is the canonical execution substrate; Substrate B is consolidated onto A.**

The canonical module map is:

| Layer | Canonical |
|---|---|
| ISR | `isr/core` |
| Requirement Graph | `reqgraph/core` |
| Evolution | `evolution/` (root) |
| Compiler IR (current) | `compiler/core/plan.py:CompilationPlan` (stabilization) |
| Compiler IR (target) | future canonical Compiler IR contract (R1-B) |
| Compiler pipeline | Gen-B `compiler/composition.py` (current); Gen-C `constitutional_architecture/compiler/pipeline.py` is the future canonical pipeline (after fail-closed repair) |
| Backend contract | `compiler/core/protocol.py:CompilerBackend` (current) |
| Certification | `certification/` |
| Provenance | existing campaign provenance + ledger |

The constitutional layer (`constitutional_architecture/`) is a governance/specification layer over the canonical substrate, not a second runtime.

## C-03 refinement + BIR as semantic donor

`CompilationPlan` is the stabilization Compiler IR, not the eventual one. The eventual Compiler IR is a future canonical contract.

BIR is a **semantic donor**, not the implementation:

```text
BIR
 │
 ├── useful semantic concepts
 │
 ▼
Canonical Compiler IR specification
 │
 ▼
canonical implementation
 │
 ▼
content hash
serialization
determinism
provenance
```

Content-hash is added to the **canonical Compiler IR contract** (the new implementation), not to BIR. The canonical implementation is a new module. BIR can be retired after its semantic properties are extracted.

## R1-E principle: canonical contracts first, then adapt implementations

R1-E does **not** repair Gen-C defects wholesale. R1-E defines the **canonical contracts** (Verification, Validation, Pass execution, Normalization) first; only then are Gen-C implementations migrated/adapted to those contracts. Gen-C code that cannot satisfy the canonical contract is retired, not patched.

## Semantic-authority invariant

`one canonical ISR` is enforced as a **semantic-authority invariant**, not a directory count: there is exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics. The same principle applies to Compiler IR, Evolution, Backend contract, Requirement Graph, and Provenance.

## Rejected alternatives

- **Option 2 (Substrate B canonical; rewire A to B).** Rejected for evidence continuity. Substrate A has a working campaign runtime, real evolution/crossover, content-addressed ISR provenance, fail-closed certification, 243 Tier A tests, 40 Tier C tests, an intact B3-v2 evidence chain. Substrate B has fail-open validation/verification, semantic loss during normalization, lossy ISR adapters, broken/dead compiler bridge, incomplete transformation recording, filesystem emission inside compilation, multiple backend abstractions. Promoting B would move the system onto a less-proven substrate and invalidate/require the B3-v2 evidence.
- **Option 3 (keep both; typed adapter).** Rejected per audit §39 (NO NEW SOURCE OF TRUTH). Bidirectional adapters recreate the dual-source-of-truth problem.

## Evidence-preservation rationale

The B3-v2 evidence chain is preserved as historical evidence of the old canonical runtime:

```text
B3-v2
  = historical campaign
  = valid evidence for historical substrate

R1 migration
  = transformation

R2 campaign
  = evidence that canonical substrate satisfies its contracts
```

After migration, the new campaign (R2) is the **post-migration certification baseline** — not a re-certification of B3-v2. The historical evidence is not invalidated; a new campaign runs on the new architecture.

## Migration principles

1. Adapters are always `LEGACY → CANONICAL`, never `A ↔ B`.
2. No second source of truth is introduced.
3. Substrate B components are not deleted until every semantic responsibility is mapped to a canonical destination and provenance/evidence impact is recorded.
4. The agent does not "fix" Substrate B defects merely because they exist. First determine whether the component survives canonicalization. No implementation effort is spent repairing a component that the canonicalization plan will retire, unless the repair is explicitly required for migration or safety.
5. The Tier A 243-test suite must continue to pass after every migration step.
6. No historical certification evidence is rewritten.
7. **Canonical contracts are defined first; implementations are migrated/adapted second.** This applies to R1-E and prevents the canonicalization plan from becoming a wholesale Gen-C repair.
8. **BIR is a semantic donor, not the implementation.** Content-hash is added to the canonical Compiler IR contract, not to BIR.
9. **One canonical ISR / Compiler IR / etc. is enforced as semantic authority**, not directory count.

## Forbidden parallel implementations (semantic-authority invariant)

After R1 is complete:

- **ISR:** exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations may exist; none may independently define system semantics.
- **Compiler IR:** exactly one authoritative semantic representation of a compiled architecture's compilation plan. Same semantic-authority principle.
- **Evolution:** exactly one authoritative Evolution engine.
- **Backend contract:** exactly one authoritative backend protocol.
- **Requirement Graph:** exactly one authoritative Requirement Graph.
- **Provenance:** exactly one authoritative Provenance store.
- No bidirectional A↔B adapter.
- No rewriting historical certification evidence.
- No new artifact-emission path that writes to filesystem inside `compile()`.

## Legacy code: temporary existence is permitted

A legacy implementation may still exist temporarily while its replacement is being validated. The condition for temporary existence:

- Explicit `LEGACY` classification.
- Owner (the migration step that retires it).
- Migration destination.
- Dependency boundary (which canonical paths may still reach it).
- Retirement condition.

A legacy implementation without these markings is forbidden.

## Deferred out of R1

- **C-17 (observation lineage via `autonomous-api/`).** Deferred to R2/R3 platform integration phase. `autonomous-api/` is classified as a legacy application/runtime surface; it must not introduce an ISR source of truth. Its final disposition is deferred.
- **C-18 (`pyproject.toml` topology).** Deferred to post-R1 packaging cleanup. First stabilize architecture; then clean packaging.

## Future Compiler IR contract (R1-B)

The eventual Compiler IR is not `CompilationPlan` long-term. The R1-B deliverable defines the canonical Compiler IR contract. `CompilationPlan` is the stabilization implementation; BIR's useful semantic properties are extracted (as references) into the canonical contract's specification; content-hash is added to the canonical Compiler IR.

## Transition

- R1 is blocked until the user explicitly authorizes "Proceed with Option 1 and begin R1".
- R1-A (this ADR) is committed as a tracked governance ADR before R1-B begins.
- R1-B through R1-F (Establish Post-Migration Certification Baseline) are sequenced per `folder/R1_PLAN.md`.
- R1-A authorization is not authorization to silently commit every subsequent phase. Each code-changing gate (R1-B, R1-D, R1-E, R1-F) requires separate explicit review.
```

(The ADR draft is shown above for the user's review. The committed file is a markdown rendering of this draft.)

---

## 6. Files this R1 plan will produce (when authorized)

When R1 is authorized, the following files are produced in order. Each is committed only after the user reviews and approves. **R1-A authorization is not authorization to silently commit every subsequent phase; each code-changing gate requires separate explicit review.**

| Step | File | Status | Risk |
|---|---|---|---|
| R1-A | `folder/CANONICAL_SUBSTRATE_DECISION.md` | TRACKED governance ADR (✅ committed at `9bb3df8`) | — |
| R1-B.D01 | `folder/CANONICAL_CONTRACT_REGISTRY.md` (11 contract surfaces enumerated) | TRACKED | P0 (contract freeze) |
| R1-B.D02 | `folder/CONTRACT_RequirementGraph.md` | TRACKED | P0 |
| R1-B.D03 | `folder/CONTRACT_CanonicalISR.md` | TRACKED | P0 (most important) |
| R1-B.D04 | `folder/CONTRACT_ArchitectureCandidate.md` | TRACKED | P0 |
| R1-B.D05 | `folder/CONTRACT_EvolutionOperation.md` | TRACKED | P0 |
| R1-B.D06 | `folder/CONTRACT_EvolutionRecord_EIR.md` | TRACKED | P0 |
| R1-B.D07 | `folder/CONTRACT_CanonicalCompilerIR.md` | TRACKED | P0 |
| R1-B.D08 | `folder/CONTRACT_CompilerBackend.md` | TRACKED | P0 |
| R1-B.D09 | `folder/CONTRACT_ArtifactSet.md` | TRACKED | P0 |
| R1-B.D10 | `folder/CONTRACT_VerificationResult.md` | TRACKED | P0 |
| R1-B.D11 | `folder/CONTRACT_CertificationEvidence.md` | TRACKED | P0 |
| R1-B.D12 | `folder/CONTRACT_RuntimeObservation.md` | TRACKED | P0 |
| R1-B.D13 | `folder/CONTRACT_CrossContractIdentity_Provenance.md` | TRACKED | P0 |
| R1-B.D14 | `folder/CONTRACT_State_FailureSemantics.md` | TRACKED | P0 |
| R1-B.D15 | `folder/R1_B_COMPATIBILITY_MATRIX.md` | TRACKED | P0 |
| R1-B.D16 | `folder/CONTRACT_INVARIANTS.md` (INV-B01…INV-B15) | TRACKED | P0 |
| R1-B.D17 | `folder/CONTRACT_LegacyBoundarySpecification.md` | TRACKED | P0 |
| R1-B.D18 | `folder/CONTRACT_TestSpecification.md` (contract test specs, not implementation) | TRACKED | P0 |
| R1-B.D19 | `folder/R1_B_MIGRATION_CONSTRAINTS.md` | TRACKED | P0 |
| R1-B.D20 | `folder/R1_B_CONTRACT_GATE_REPORT.md` (the R1-B gate report) | TRACKED governance ADR | — |
| R1-D.1 | `isr/core/semantics/*.py` (selective migration from `constitutional_architecture/isr/semantics/*`) | TRACKED code | P0 |
| R1-D.2 | new canonical Compiler IR module (per R1-B.D07 contract) — BIR is a semantic donor; content-hash is on the canonical IR, not on BIR | TRACKED code | P0 |
| R1-D.3 | `evolution/` extensions for EIR fields + `evolution_loop.py:110` repair | TRACKED code | P1 |
| R1-D.4 | backend contract consolidation | TRACKED code | P1 |
| R1-D.5 | deprecation of `constitutional_architecture/core/models/isr.py:UniversalISR`, `constitutional_architecture/isr/model/isr.py:ISR`, Gen-A kernel, per-category compilers (runtime) | TRACKED code | P1 |
| R1-E.1 | canonical **Verification contract** implementation (per R1-B.D10) | TRACKED code | P0 |
| R1-E.2 | canonical **Validation pass contract** implementation (per R1-B state/failure semantics) | TRACKED code | P0 |
| R1-E.3 | canonical **Pass execution contract** implementation | TRACKED code | P0 |
| R1-E.4 | canonical **Normalization contract** implementation | TRACKED code | P0 |
| R1-E.5 | adapt Gen-C implementations to the canonical contracts (R1-E.1–R1-E.4) — retire what cannot satisfy | TRACKED code | P0 |
| R1-E.6 | provenance + lineage hash chain | TRACKED code | P2 |
| R1-E.7 | `constitutional_architecture/compiler/backends/fastapi_backend.py` artifact purity (return `ArtifactSet`; packager writes) | TRACKED code | P1 |
| R1-E.8 | backend conformance extension (structural + behavioral); demote `python-fastapi`/`rust-axum` to `STRUCTURAL` until evidence supports `BEHAVIORAL` | TRACKED code | P1 |
| R1-F | **Post-Migration Certification Baseline** (new campaign identity, NOT a re-certification of B3-v2) | TRACKED governance ADR | — |

**Deferred out of R1 (per corrections 3 and 4):**

| Conflict | Status | Deferred to |
|---|---|---|
| C-17 (`autonomous-api/` observation lineage) | DEFERRED — classified as legacy application/runtime; must not introduce an ISR source of truth | R2/R3 platform integration phase |
| C-18 (`pyproject.toml` topology) | DEFERRED — first stabilize architecture; then clean packaging | post-R1 packaging cleanup |

---

## 7. R1 → R2 transition criteria

R1 is complete when all of the following are true:

1. The R1-A ADR is committed. ✅ (committed at `9bb3df8`)
2. **R1-B** is PASS (per the D20 gate report): all 11 canonical contracts defined (D02–D12), the cross-contract identity/provenance model (D13), the state/failure semantics (D14), the compatibility matrix (D15), the invariants (D16), the legacy boundary specification (D17), the contract test specification (D18), the migration constraints (D19), and the D20 gate report are committed. The 12 R1-B gate questions are all answered.
3. R1-D migration is complete and the Tier A 243-test suite still passes.
4. R1-E canonical contracts are defined and the Gen-C adaptations are complete; the Tier A 243-test suite still passes.
5. **No forbidden parallel implementation remains on any canonical execution path, and every retained legacy representation has an explicit LEGACY classification, owner, migration destination, dependency boundary, and retirement condition.** (Per the user's correction 6: "A legacy implementation may still exist temporarily while its replacement is being validated. Use the explicit LEGACY classification, owner, migration destination, dependency boundary, and retirement condition.")
6. The historical B3-v2 evidence chain is preserved and continues to be valid.
7. The user explicitly authorizes R2.

**R1-B → R1-C transition:** R1-C (adapters + migration) does NOT begin until R1-B PASS. R1-B is the contract gate; R1-C is the first implementation phase. The D20 gate report is the explicit authorization to begin R1-C.

R2 begins only after R1 is complete. R2 is the **post-migration certification baseline** — the new campaign identity, NOT a re-certification of B3-v2. It is the evidence that the canonical substrate satisfies its contracts.

---

## 8. R1 audit-checklist (V1–V20 from the audit, mapped to R1 deliverables)

The audit's V1–V20 final validation list maps to R1:

| Validation | R1 deliverable | Status |
|---|---|---|
| V1 — Exactly one canonical ISR (semantic authority) | R1-D.1, R1-D.5 | pending |
| V2 — Requirement Graph → ISR traceability | R1-B | pending |
| V3 — ISR round-trip preserves semantics | R1-D.1 | pending |
| V4 — EIR records actual architectural transformations | R1-D.3 | pending |
| V5 — Evolution crossover is genuine or reclassified | R1-D.3 covers Substrate A; Substrate B's `crossover_engine.py` audited under R1-D.5 | pending |
| V6 — Exactly one canonical Compiler IR (semantic authority) | R1-D.2 | pending |
| V7 — Compiler validation fails closed | R1-E.2 (canonical Validation pass contract) | pending |
| V8 — Compiler pass failures block dependent passes | R1-E.4 (canonical Pass execution contract) | pending |
| V9 — Compiler bridge uses current canonical interfaces | R1-D.5 (delete the dead bridge) | pending |
| V10 — Exactly one backend contract (semantic authority) | R1-D.4 | pending |
| V11 — Backend output is deterministic where required | R1-E.8 | pending |
| V12 — Artifacts carry complete provenance | R1-E.6 | pending |
| V13 — Verification failure cannot become certification | R1-E.1 (canonical Verification contract) | pending |
| V14 — Runtime observations can trace back to ISR | **DEFERRED to R2/R3** (C-17 deferred) | deferred |
| V15 — Python backend passes structural and behavioral verification | R1-E.8 | pending |
| V16 — Rust backend passes structural and behavioral verification | R1-E.8 | pending |
| V17 — Same ISR can compile to both without ISR changes | R1-D.2, R1-E.8 | pending |
| V18 — Golden end-to-end project succeeds | R1-F (post-migration certification baseline) | pending |
| V19 — Negative cases fail correctly | R1-E.2, R1-E.1, R1-E.4 | pending |
| V20 — No architectural P0 remains unresolved | end of R1 (C-17 and C-18 deferred) | pending |

### INV-B01–INV-B15 (R1-B contract invariants, per D16)

| Invariant | Maps to | R1-B deliverable |
|---|---|---|
| INV-B01 — One canonical ISR semantic authority | V1 | D03 |
| INV-B02 — RequirementGraph precedes ISR construction | V2 | D02, D03 |
| INV-B03 — ISR is technology-neutral | V1 | D03 |
| INV-B04 — Architecture Model is distinct from ISR | V1, V6 | D04 |
| INV-B05 — Compiler IR is distinct from ISR | V6 | D07 |
| INV-B06 — Compiler IR is distinct from generated artifacts | V6 | D07, D09 |
| INV-B07 — Evolution does not depend on backend technology | V5, V10 | D05, D08 |
| INV-B08 — Backend cannot redefine upstream semantics | V1, V10 | D08 |
| INV-B09 — ArtifactSet is the generated-software boundary | V6, V11, V12 | D09 |
| INV-B10 — Verification cannot fail open | V7, V13, V19 | D10, D14 |
| INV-B11 — Certification cannot manufacture verification evidence | V13 | D11, D14 |
| INV-B12 — Runtime observations retain reverse lineage | V14 (deferred) | D12 |
| INV-B13 — Historical evidence is immutable | V20 | D11, D14, D19 |
| INV-B14 — No category-specific compiler becomes a new architectural authority | V1, V6, V10 | D07, D08, D15 |
| INV-B15 — Legacy adapters are one-way: `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY` | V1, V6, V20 | D15, D17, D19 |

---

*End of R1 plan. R1-A is committed at `9bb3df8`. R1-B is the next gate but is **NOT AUTHORIZED**. Awaiting explicit "Proceed with R1-B" from the user. The R1-B specification (D01–D20) is captured above as the contract-design scope.*
