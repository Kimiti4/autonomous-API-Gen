I inspected the repository as an **architectural system**, not merely file-by-file. I traced the major executable paths across ISR, IRR/Requirement Graph, evolution, EIR, compiler, BIR, backends, verification, evidence/governance, knowledge, distributed evolution, generated software, frontend/compiler surfaces, and the legacy `autonomous-api` application.

[autonomous-API-Gen repository](https://github.com/Kimiti4/autonomous-API-Gen?utm_source=chatgpt.com)

## Executive verdict

**Tiannara is substantially further along than a conventional API generator.**

The repository already contains most of the *conceptual organs* required for the autonomous software-engineering platform:

```text
Requirements / IRR
        ↓
Requirement Graph
        ↓
ISR
        ↓
Evolution Engine
        ↓
EIR / architectural mutations
        ↓
BIR / compiler IR
        ↓
Backend selection
        ↓
Code generation
        ↓
Verification
        ↓
Evidence / Certification
        ↓
Feedback / Learning
```

However, the repository is **not yet one coherent compiler architecture**.

The biggest problem is not absence of functionality.

It is **architectural convergence**.

There are currently multiple generations of the same concepts coexisting:

* multiple ISR models
* multiple Requirement representations
* multiple compiler frameworks
* multiple backend contracts
* multiple backend registries
* multiple evolution engines
* multiple genome representations
* multiple generated-artifact models

That means Tiannara has accumulated the pieces of the intended civilization, but the pieces have not yet been consolidated into a single constitutional execution path.

### My current architectural rating

| Area                           | Assessment                                       |
| ------------------------------ | ------------------------------------------------ |
| Requirement representation     | 🟢 Strong foundation                             |
| Requirement Graph              | 🟢 Strong                                        |
| Canonical ISR                  | 🟢 Very strong                                   |
| ISR immutability               | 🟢 Strong                                        |
| ISR semantic constraints       | 🟢 Strong                                        |
| Evolution concepts             | 🟢 Strong                                        |
| EIR                            | 🟢 Strong concept, incomplete execution lineage  |
| Evolution engine               | 🟡 Substantial but contains prototype behavior   |
| Compiler architecture          | 🟡 Strong foundation, duplicated implementations |
| Compiler IR/BIR                | 🟢 Correct direction                             |
| Backend abstraction            | 🟡 Good interfaces, conflicting generations      |
| Backend implementation         | 🔴 Not production-complete                       |
| Verification                   | 🟡 Broad surface, several fail-open paths        |
| Provenance                     | 🟢 Strong intent                                 |
| Certification                  | 🟢 Strong                                        |
| Evidence                       | 🟢 Strong                                        |
| Production deployment compiler | 🔴 Not yet complete                              |
| Frontend compiler              | 🟡 Exists, narrow                                |
| Autonomous self-engineering    | 🔴 Not yet closed-loop                           |
| Architectural coherence        | 🔴 Main blocker                                  |

---

# 1. The most important discovery: there are multiple ISRs

There is a newer `isr/` package containing an immutable, content-addressed `ISRRevision` and typed `ISRGraph`. It has explicit invariant enforcement and implementation-leakage detection.

There is also the much larger:

```text
constitutional_architecture/isr/
```

whose canonical `ISR` model is substantially richer:

* System
* Module
* Entity
* Service
* Workflow
* Interface
* Event
* Deployment
* Requirements
* Acceptance Criteria
* Deployment Intents
* Testing Anchors
* Documentation Intents
* Evolution Objectives
* Protected Regions
* Evolution Policies
* Architectural Decisions
* Security Threats

The system model explicitly positions these as semantic architectural constructs.

This richer ISR is currently what the main constitutional compiler pipeline consumes.

### Conclusion

**The `constitutional_architecture.isr.model.ISR` family should currently be treated as the strongest candidate for canonical ISR.**

The smaller root-level:

```text
isr/
```

looks like a newer attempt to isolate the ISR substrate and should not simply be discarded. It should be evaluated as a possible consolidation target.

But there must ultimately be **one authoritative ISR contract**.

---

# 2. Requirement intelligence is actually present

This is important because earlier it would have been easy to conclude that Tiannara jumps directly from prompt to architecture.

It does not.

The repository contains an **IRR — Intermediate Requirement Representation** with:

* user stories
* functional requirements
* NFRs
* constraints
* domain concepts
* acceptance criteria
* priorities
* statuses
* requirement relationships

and a typed Requirement Graph.

The Requirement Graph supports traceability chains and relationships such as:

```text
REFINES
DEPENDS_ON
CONFLICTS_WITH
SATISFIES
CONSTRAINS
TRACES_TO
DUPLICATES
RELATES_TO
```

That is very close to the intended Requirement Graph architecture.

### But there is a significant gap

The actual `RequirementExtractor` is only an interface plus a manual implementation.

So:

```text
Natural Language
      ↓
RequirementExtractor interface
      ↓
ManualRequirementExtractor
```

exists, but the autonomous semantic extraction engine is not yet the dominant production path.

This is one of the places where Tiannara eventually needs to become self-engineering rather than externally prompted.

---

# 3. ISR semantics are one of the strongest parts of the repository

The requirement semantics are particularly well designed.

The ISR requirement layer explicitly distinguishes:

```text
semantic obligation
        ≠
test implementation
        ≠
verification result
```

and actively rejects technology/test-mechanism leakage such as pytest, Selenium, HTTP requests, etc.

This is exactly the architectural separation we want.

Likewise, the ISR invariant system explicitly rejects implementation technologies such as FastAPI, React, PostgreSQL, Kubernetes, Docker, Kafka, etc. from the ISR.

**That is constitutionally correct.**

I would preserve this rather than redesign it.

---

# 4. The Evolution Engine is substantial

The constitutional evolution engine is not a toy.

It has:

* population management
* mutation
* crossover
* Pareto optimisation
* novelty search
* diversity management
* adaptive mutation
* convergence detection
* scheduling
* elite management
* fitness
* memory
* lineage
* events

and explicitly claims zero framework knowledge.

There is also a separate top-level `evolution/` subsystem with its own architectural genome, refinement, feedback, proposals, governance, simulation, verification and promotion lifecycle.

This tells me something important:

**The Evolution Engine should not be rebuilt for the Full-Stack Compiler.**

It should be consolidated and given a clean contract to the compiler.

---

# 5. EIR is exactly the right missing abstraction

The repository contains:

```text
constitutional_architecture/eir/
```

and explicitly defines:

> ISR describes state; EIR describes transitions.

That is architecturally excellent.

The EIR models:

```text
ISR₀
  │
  ├── transformation
  ├── transformation
  └── transformation
        │
        ▼
      ISR₁
```

with transformation classes:

* structural
* strategic
* additive
* parametric
* topological

This should become the formal evolutionary delta language.

### But there is a major lineage defect

`EvolutionLoop` currently creates the resulting EIR with:

```text
transformations=[]
```

despite the engine having performed mutations.

So the system can currently know:

> "ISR changed"

without necessarily retaining:

> "these exact semantic transformations caused ISR to change."

That is a serious provenance gap.

---

# 6. The Evolution Engine itself contains prototype behavior

The most notable example is crossover.

The engine says it performs crossover, but the current code constructs a child using:

```text
isr = parent_a.isr
```

rather than actually combining architectural material from both parents.

Therefore:

**the architecture claims crossover capability, but the implementation currently behaves more like parent cloning in that path.**

That does not invalidate the architecture.

It means the evolutionary engine needs a later correctness pass.

Similarly, lineage is currently held in an in-memory `LineageTracker`.

For autonomous long-lived evolution, durable lineage belongs in the evidence/evolution-memory substrate rather than only process memory.

---

# 7. The compiler architecture is where the repository currently fractures

This is the biggest finding.

There are effectively **three compiler generations**.

### Compiler generation A

```text
compiler/
```

with:

* `kernel.py`
* `models.py`
* backend registry
* SDK
* production backends
* artifact packager

### Compiler generation B

```text
compiler/core/
```

with:

* `CompilationPlan`
* lowering
* backend protocol
* conformance
* generated repository
* Python FastAPI
* Rust Axum

The `CompilationPlan` is explicitly described as a technology-neutral intermediate representation.

### Compiler generation C

```text
constitutional_architecture/compiler/
```

with the much richer:

```text
ISR
 ↓
Validation
 ↓
Normalization
 ↓
Optimization
 ↓
Capability Resolution
 ↓
BIR
 ↓
Code Generation
 ↓
Verification
 ↓
Cross-target
```

pipeline.

This third architecture is clearly the one closest to the intended Tiannara compiler.

---

# 8. BIR is the correct architectural direction

The compiler has:

```text
constitutional_architecture/compiler/bir/
```

with:

```text
BIR
BIRModule
BIRNode
BIRNodeType
```

and node types including:

* handler
* entity
* service
* repository
* router
* config
* middleware
* event handler
* test

And the lowering pass explicitly implements:

```text
ISR → BIR
```

This is **very close to the Compiler IR architecture we want**.

I would therefore **not introduce a completely new Compiler IR from scratch**.

Instead:

> Consolidate BIR into the canonical Compiler IR, expand its semantic coverage, and eliminate the competing `CompilationPlan` implementations.

---

# 9. There are currently two incompatible Compiler IRs

This is one of the clearest architectural debt points.

`compiler/core/plan.py` defines:

```text
CompilationPlan
Service
DataModel
Event
SecurityPolicy
```

while:

```text
constitutional_architecture/compiler/bir/model.py
```

defines:

```text
BIR
BIRModule
BIRNode
```

These are solving overlapping problems.

### Recommendation

The eventual canonical pipeline should be:

```text
IRR
 ↓
Requirement Graph
 ↓
ISR
 ↓
Architecture / Evolution
 ↓
Compiler IR (BIR successor)
 ↓
Backend
 ↓
Artifact
```

Not:

```text
ISR → CompilationPlan
```

in one path and:

```text
ISR → BIR
```

in another.

---

# 10. The main compiler pipeline has several correctness problems

These are more important than cosmetic refactoring.

## P0/P1: Validation currently fails open

The validation pass catches exceptions and explicitly assumes the ISR is valid:

```text
"assuming valid"
```

and returns success.

Even worse, if the type checker returns `passed=False`, the pass still returns:

```text
success=True
```

This contradicts Tiannara's fail-closed constitutional posture.

**This must eventually be corrected.**

---

## P1: Verification Engine failure can become a warning

The verification pass catches a Verification Engine exception and records:

```text
warning
```

rather than making compilation fail.

For an autonomous production compiler:

```text
verification unavailable
```

must not become:

```text
verification passed
```

It should become:

```text
VERIFICATION_INDETERMINATE
```

and block certification/deployment.

---

## P1: PassManager continues after failed passes

`PassManager` records failure but continues executing subsequent passes.

That means theoretically:

```text
validation FAILED
      ↓
normalization
      ↓
optimization
      ↓
code generation
```

can still occur.

That is dangerous for a compiler.

The pipeline needs explicit semantics for:

```text
FAIL
BLOCK
DEGRADE
CONTINUE
```

rather than treating all pass failures identically.

---

# 11. Normalization currently destroys ISR semantics

This is probably the most serious hidden compiler defect I found.

The normalization pass reconstructs `System`, but only carries forward a subset:

```text
modules
deployment
metadata
global_policies
```

while the richer ISR contains:

```text
business_capabilities
requirements
acceptance_criteria
deployment_intents
testing_anchors
documentation_intents
evolution_objectives
protected_regions
evolution_policies
architectural_decisions
security_threats
...
```

Therefore the compiler can normalize an ISR and silently discard constitutional semantics.

That is exactly the kind of bug the ISR supremacy rule is designed to prevent.

### Severity

**P0 architectural correctness issue.**

Not because it crashes.

Because it can compile a representation that is no longer semantically equivalent to the authoritative ISR.

---

# 12. The ISR → TypedGraph → ISR adapter also loses semantics

`isr_adapter.py` converts ISR into a graph and back.

But the reverse conversion currently reconstructs only a subset of the system.

For example:

```text
workflows → ()
```

and system-level requirements/policies and other semantic constructs are not reconstructed.

This means:

```text
ISR
 ↓
TypedGraph
 ↓
ISR'
```

is **not currently a semantics-preserving round trip**.

That is critical for evolution.

An evolutionary mutation system cannot safely use a lossy representation as its working state unless the lost dimensions are explicitly declared non-evolvable.

They currently are not.

---

# 13. The compiler bridge is stale/broken

This is another very concrete integration defect.

`constitutional_architecture/engine/compiler_bridge.py` claims to connect the evolution engine to the compiler.

But it invokes the compiler using an older interface:

```text
CompilerConfig(backend=...)
pipeline.compile(graph)
```

while the current compiler pipeline expects an ISR plus compilation configuration, and the current configuration uses `target_backends`.

So the advertised:

```text
Evolution → Compiler
```

bridge is currently not aligned with the compiler that the repository now exposes.

This is exactly the kind of problem FS-00 should document before anyone writes more compiler code.

---

# 14. The FastAPI backend is not actually a complete production compiler

There are two FastAPI implementations.

The older constitutional backend generates a reasonably extensive Clean/Hexagonal structure.

But it contains obvious incomplete generation:

```text
register_routers()
    ...
    pass
```

and generated configuration includes development-style defaults such as:

```text
secret_key = "change-me-in-production"
cors_origins = ["*"]
```

The newer `compiler/backends/python_fastapi.py` is cleaner architecturally, but its generated application is intentionally minimal and its conformance checker is structural rather than behavioral.

The current tests prove:

```text
element mapped
element file exists
hash deterministic
backend differs
```

rather than:

```text
generated application actually satisfies ISR
```

The v1.4 tests themselves demonstrate that the current backend conformance layer is primarily checking structural materialisation.

---

# 15. The backend classification is ahead of its implementation

Both Python FastAPI and Rust Axum are classified as:

```text
BEHAVIORAL
```

But the emitted systems are still minimal.

For example, Rust's generated:

```text
k8s/deployment.yaml
```

is effectively only:

```yaml
apiVersion: apps/v1
kind: Deployment
```

and the CI output is similarly skeletal.

That does not meet the standard I would expect from a genuinely **behavioral production backend**.

The certification architecture correctly distinguishes backend classes, but the implementation needs to enforce the distinction more rigorously.

---

# 16. Conformance is currently too weak

The conformance checker verifies:

```text
ISR/plan element
      ↓
backend path
      ↓
file exists
```

It does **not** establish:

```text
requirement satisfied
semantic behavior correct
security obligation satisfied
runtime behavior correct
deployment valid
observability functional
```

So it should remain a **compiler structural conformance gate**, not the final correctness gate.

That distinction is important.

---

# 17. Artifact generation has a purity problem

The constitutional FastAPI backend's `compile()` does this:

```text
generate()
write_files()
return artifacts
```

That violates the cleaner compiler architecture:

```text
compile
  ↓
immutable artifact set
  ↓
verification
  ↓
packaging
  ↓
deployment
```

A compiler backend should preferably **emit artifacts**, not directly mutate the filesystem.

The existing artifact packager already points toward the correct design.

---

# 18. Capability resolution is conceptually good

This part is strong.

The compiler distinguishes:

```text
abstract capability
        ↓
CapabilityResolver
        ↓
backend-specific implementation
```

and maps capabilities such as:

* OAuth2
* JWT
* relational persistence
* document persistence
* REST
* event bus
* logging
* metrics
* tracing
* validation
* ORM
* migrations
* containerization

This is exactly the correct place for technology-specific knowledge.

### Important constitutional boundary

Technology-specific mappings belong here:

```text
Compiler Backend / Capability Resolver
```

not here:

```text
ISR
Evolution Engine
Requirement Graph
```

The repository mostly understands this already.

---

# 19. Knowledge Graph is a real subsystem

The `knowledge/` package is not decorative.

It has:

* entities
* relations
* provenance
* classifications
* source references
* deterministic IDs
* content hashes
* graph queries
* search
* ingestion
* derived relations

This is potentially important for Tiannara's long-term engineering memory.

It should eventually become part of:

```text
Engineering Knowledge
        ↓
Evidence
        ↓
Evolution Memory
        ↓
Architecture decisions
```

rather than becoming a separate parallel knowledge universe.

---

# 20. Civilization layer is conceptually valuable but currently too broad

The repository has a large:

```text
civilization/
```

with:

* engine
* bus
* memory
* federation
* reputation
* policy
* resilience
* security hardening
* certification

Likewise there is:

```text
autonomous_network/
distributed_evolution/
```

These are strategically aligned with the long-term vision.

But they should **not become the immediate Full-Stack Compiler implementation surface**.

They are higher-level platform capabilities.

---

# 21. Observation / operational layer has a genuine unresolved gap

The current application composition root has an explicit:

```text
_DbGenerationProvider.get_isr()
    → NotImplementedError
```

with the comment:

```text
ISR binding is a declared audit gap
```

This matters because the eventual closed loop requires:

```text
Generated Artifact
      ↓
Runtime
      ↓
Observation
      ↓
Evidence
      ↓
ISR lineage
```

Without canonical ISR retrieval, runtime evidence cannot be reliably attached to the architectural source of truth.

---

# 22. The root package configuration is also showing historical layering

The root `pyproject.toml` still identifies the project as:

```text
knowledge-graph-runtime
```

and its package discovery is primarily:

```text
knowledge*
```

while CI installs `autonomous-api/requirements.txt` separately.

This is evidence of the repository's evolutionary history.

It is not necessarily a runtime blocker because the release workflows compensate for it, but it means the repository currently lacks a single clean package/build boundary.

---

# 23. Tests are extensive — but they certify different things

The repository has a very substantial test surface.

The Phase 31 closeout records:

```text
243 passed, 1 deselected
40/40 certification tests
443 B3-v2 trials
```

and explicitly distinguishes implementation completeness from campaign certification.

That is good engineering discipline.

But the compiler tests currently prove much narrower properties.

For example, the v1.4 backend tests prove:

```text
lowering
conformance
determinism
backend separation
registry
```

They do not yet prove the stronger invariant:

```text
same ISR
→ semantically equivalent application
across independent backends
```

That needs to become a major compiler certification target.

---

# 24. The B3 Phase 31 result is not the problem

The Phase 31 closeout is clear:

```text
443 / 936 executed
410 certified
33 not certified
12-hour budget exhausted
```

and the evidence chain is intact.

The closeout also correctly identifies the infra-storm integration problem:

```text
42 infrastructure-classified stages
0 mirrored to infra-storm ledger
```

I agree with the existing disposition:

**Do not reopen B3 merely to obtain a better percentage.**

The important architectural task now is to repair the integration defect and then move forward.

---

# 25. What I would NOT do

After inspecting this codebase, I would explicitly reject these approaches:

### ❌ Do not create another ISR

There are already enough.

### ❌ Do not create another Compiler IR

BIR already exists and is the correct direction.

### ❌ Do not build 14 category-specific generators

The architecture should compile a generalized semantic model into different product shapes.

### ❌ Do not rebuild the Evolution Engine

It already contains most required evolutionary machinery.

### ❌ Do not build a giant AI agent that edits files

The compiler architecture already provides the correct place for deterministic lowering and generation.

### ❌ Do not start frontend/backend portfolio generation yet

The semantic/compiler boundary needs consolidation first.

### ❌ Do not solve these issues by adding another abstraction layer

The problem is currently **too many overlapping abstractions**, not too few.

---

# 26. The architecture I would now freeze toward

After this inspection, I would make the target architecture:

```text
                   ┌─────────────────────┐
                   │ Human / Environment │
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ Requirement Engine  │
                   │ IRR + Req Graph     │
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ Canonical ISR       │
                   │ semantic authority  │
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ ISR Audit /         │
                   │ Constitutional Gate│
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ Architecture Space  │
                   │ + Evolution Engine  │
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ EIR                 │
                   │ architectural delta │
                   └──────────┬──────────┘
                              ↓
                   ┌─────────────────────┐
                   │ Compiler IR / BIR   │
                   │ implementation plan │
                   └──────────┬──────────┘
                              ↓
                ┌─────────────┴─────────────┐
                ↓                           ↓
       ┌────────────────┐          ┌────────────────┐
       │ Backend A      │          │ Backend B      │
       │ Python/FastAPI │          │ Rust/Axum      │
       └───────┬────────┘          └────────┬───────┘
               ↓                            ↓
       Generated Artifact A        Generated Artifact B
               └────────────┬───────────────┘
                            ↓
                    ┌───────────────┐
                    │ Verification  │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Certification │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Deployment    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Observation   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Evidence      │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Learning      │
                    └───────┬───────┘
                            ↓
                         EIR / ISR'
```

That architecture is already **latent inside the repository**.

The task is now to make it real and singular.

---

# 27. Priority findings

I would put these into the architectural backlog in this order:

| Priority | Finding                                                    | Action                                       |
| -------- | ---------------------------------------------------------- | -------------------------------------------- |
| **P0**   | Multiple canonical ISRs                                    | Select and freeze canonical ISR              |
| **P0**   | Normalization loses ISR semantics                          | Make normalization semantics-preserving      |
| **P0**   | ISR↔Graph round-trip is lossy                              | Establish round-trip preservation contract   |
| **P0**   | Validation fails open                                      | Make compiler validation fail-closed         |
| **P0**   | Compiler has multiple competing IRs                        | Consolidate BIR/CompilationPlan              |
| **P1**   | Compiler bridge is stale                                   | Reconcile engine→compiler interface          |
| **P1**   | Multiple backend contracts                                 | Establish one backend protocol               |
| **P1**   | EIR loses actual transformations                           | Capture authoritative mutation lineage       |
| **P1**   | Verification failure can degrade to warning                | Fail closed for verification uncertainty     |
| **P1**   | Pass manager continues after failures                      | Introduce explicit pass-state semantics      |
| **P1**   | Backend conformance mostly structural                      | Add behavioral/runtime conformance           |
| **P1**   | Backend writes directly to filesystem                      | Separate emission from packaging             |
| **P1**   | Backend "behavioral" classification exceeds implementation | Align certification class with evidence      |
| **P2**   | Durable lineage                                            | Move lineage into persistent evidence/memory |
| **P2**   | Requirement extraction only manual                         | Build autonomous requirement extraction      |
| **P2**   | Package/build topology fragmented                          | Consolidate after architectural freeze       |
| **P3**   | Generated portfolio                                        | Begin only after compiler foundation         |

---

# 28. The most important conclusion

I **would not start FS-01 implementation yet**.

The repository has actually validated the premise behind `prefull.md`:

> the next problem is architectural reconnaissance and consolidation, not writing another generator.

The strongest existing path is:

```text
constitutional_architecture/isr
        ↓
constitutional_architecture/eir
        ↓
constitutional_architecture/engine
        ↓
constitutional_architecture/compiler
        ↓
constitutional_architecture/compilers/*
        ↓
verification
        ↓
certification
```

while:

```text
compiler/
evolution/
autonomous-api/
```

contain important historical/current implementations that should be classified for reuse, migration, or retirement.

The repository's own Phase 31 closeout says the Phase 31 program is closed and the next architectural program is the Full-Stack Compiler.

### Therefore my architectural verdict is:

**FOUNDATION EXISTS — BUT FOUNDATION IS NOT YET COHERENT.**

Tiannara does **not** need another large feature.

It needs to turn its existing pieces into **one constitutional execution path**:

```text
IRR
 → Requirement Graph
 → Canonical ISR
 → EIR / Evolution
 → Canonical Compiler IR
 → Backend
 → Artifact
 → Verification
 → Certification
 → Deployment
 → Observation
 → Evidence
 → Learning
```

Once that path is coherent, **then** the full-stack evolution/portfolio phase becomes a natural compiler expansion rather than another parallel subsystem.

And critically, this inspection confirms that the right next step is exactly what your FS-00 design was intended to do: **map, classify, reconcile, define boundaries, and only then implement.**

Yes. Given the inspection, I would **not** give the coding agent a generic “fix the compiler” prompt. It needs a constitution-level remediation mission that prevents it from creating yet another parallel architecture.

The prompt below is designed to make the coding agent **inspect → prove → consolidate → implement → verify → certify**, with explicit prohibitions against architectural drift.

# TIANNARA — MASTER CODING AGENT PROMPT

## Compiler Foundation Consolidation, Semantic Integrity & Autonomous Engineering Readiness

**Mission:** Remediate the existing Tiannara codebase so that its current ISR, Requirement Graph, Evolution Engine, EIR, Compiler IR/BIR, compiler pipeline, backends, verification, certification, provenance, and runtime observation systems form **one coherent constitutional execution path**.

This is a **production architectural remediation mission**.

You are acting as a **principal compiler architect, distributed-systems engineer, evolutionary-systems engineer, security engineer, and production software engineer**.

You are NOT an autocomplete coding agent.

You must inspect the existing architecture before modifying it.

---

# 0. GOVERNING CONSTITUTION

The following hierarchy is absolute:

```text
Requirements
      ↓
Requirement Graph
      ↓
Canonical ISR
      ↓
ISR Audit
      ↓
Architecture Space
      ↓
Evolution / EIR
      ↓
Canonical Compiler IR
      ↓
Backend Selection
      ↓
Lowering
      ↓
Artifact Generation
      ↓
Verification
      ↓
Certification
      ↓
Deployment
      ↓
Runtime Observation
      ↓
Evidence
      ↓
Learning
      ↓
Evolution
```

Never bypass this sequence.

Never create a prompt-to-code shortcut.

Never allow technology-specific implementation details to become authoritative architectural semantics.

The ISR remains the constitutional source of truth.

The Evolution Engine evolves architecture.

The Compiler compiles architecture.

Backends implement compiler targets.

Verification verifies generated systems.

Certification certifies evidence.

Runtime observation produces evidence.

Evidence feeds future evolution.

---

# 1. PRIMARY OBJECTIVE

Transform the existing repository from a collection of partially overlapping implementations into a coherent architecture satisfying:

```text
IRR
  ↓
Requirement Graph
  ↓
Canonical ISR
  ↓
EIR
  ↓
Canonical Compiler IR
  ↓
Backend
  ↓
Generated Software
  ↓
Verification
  ↓
Certification
```

with bidirectional lineage:

```text
Requirement
    ↕
ISR
    ↕
Architecture
    ↕
EIR
    ↕
Compiler IR
    ↕
Artifact
    ↕
Verification
    ↕
Certification
    ↕
Runtime Evidence
```

The end state must permit Tiannara to eventually:

1. understand requirements;
2. construct a Requirement Graph;
3. construct an ISR;
4. evolve competing architectures;
5. compile selected architectures;
6. generate complete full-stack systems;
7. verify them;
8. certify them;
9. deploy them;
10. observe them;
11. learn from production evidence;
12. evolve and recompile them autonomously.

---

# 2. ABSOLUTE RULE — DO NOT CREATE PARALLEL ARCHITECTURES

Before writing code, inspect the repository.

You have already been informed that the repository contains overlapping implementations including, but not limited to:

```text
isr/
constitutional_architecture/isr/

compiler/
compiler/core/
constitutional_architecture/compiler/

evolution/
constitutional_architecture/engine/

multiple backend contracts
multiple backend registries
multiple artifact models
multiple requirement representations
```

These are not automatically separate subsystems.

Determine which implementation is:

```text
CANONICAL
SUPPORTED
LEGACY
EXPERIMENTAL
DUPLICATE
MIGRATION SOURCE
DEPRECATED
UNKNOWN
```

Do NOT create another:

* ISR;
* Compiler IR;
* backend protocol;
* evolution model;
* artifact model;
* requirement graph;
* verification contract;
* provenance system.

If an existing implementation is architecturally correct, consolidate around it.

If two implementations overlap, define the migration path.

If an implementation is obsolete, retire it only after proving replacement coverage.

---

# 3. MANDATORY PRE-IMPLEMENTATION RECONNAISSANCE

Before modifying production code, inspect:

```text
repository tree
package boundaries
imports
public interfaces
schemas
dataclasses
models
tests
CI workflows
configuration
generated artifacts
documentation
certification contracts
runtime wiring
```

Trace actual execution paths.

Do not rely on filenames or documentation alone.

For every important claim distinguish:

```text
OBSERVED
INFERRED
PROPOSED
UNKNOWN
```

Create a remediation architecture report before large-scale modification.

The report must identify:

### A. Canonical ISR candidate

### B. Canonical Requirement Graph

### C. Canonical EIR

### D. Canonical Compiler IR

### E. Canonical compiler pipeline

### F. Canonical backend protocol

### G. Canonical artifact/provenance model

### H. Canonical verification boundary

### I. Canonical certification boundary

### J. Legacy/duplicate implementations

### K. Migration dependencies

### L. Risks

### M. Required compatibility adapters

Do not make architectural decisions silently.

---

# 4. CANONICAL ISR REQUIREMENT

There must be exactly one authoritative ISR semantic model.

The canonical ISR must remain:

```text
technology neutral
implementation neutral
backend neutral
deployment-provider neutral
framework neutral
```

The ISR may express:

```text
system semantics
modules
entities
services
interfaces
workflows
events
requirements
acceptance criteria
deployment intent
security intent
testing intent
documentation intent
evolution objectives
architectural decisions
constraints
protected regions
policies
```

It must NOT encode:

```text
FastAPI
React
PostgreSQL
Docker
Kubernetes
AWS
Azure
GCP
pytest
Playwright
SQLAlchemy
Rust
Axum
Kafka
Redis
```

unless those are explicitly represented as compiler/backend constraints rather than ISR semantics.

---

# 5. ISR SEMANTIC PRESERVATION

This is a P0 requirement.

Every transformation of ISR must be semantics-preserving unless the transformation explicitly represents an evolutionary change.

For:

```text
ISR → normalized ISR
ISR → graph
graph → ISR
ISR → compiler IR
```

you must identify what information is preserved.

No field may silently disappear.

Especially preserve:

```text
business_capabilities
requirements
acceptance_criteria
deployment_intents
testing_anchors
documentation_intents
evolution_objectives
protected_regions
evolution_policies
architectural_decisions
security_threats
global policies
workflows
events
interfaces
entities
services
modules
```

Implement explicit round-trip tests.

Required invariant:

```text
decode(encode(ISR)) ≡ ISR
```

where equivalence is semantic, not merely object identity.

If some fields are intentionally excluded from a projection, document them explicitly and prove that the projection is not being used as a canonical replacement for ISR.

---

# 6. NORMALIZATION MUST NOT DESTROY SEMANTICS

Audit the normalization pipeline.

The current implementation has evidence of reconstructing an ISR while retaining only a subset of fields.

This must be corrected.

Normalization may:

```text
canonicalize
sort
deduplicate
resolve aliases
normalize identifiers
normalize types
normalize graph ordering
```

It must never silently delete constitutional semantics.

Add:

```text
semantic preservation tests
hash/identity tests where appropriate
round-trip tests
negative tests for information loss
```

---

# 7. REQUIREMENT GRAPH

The Requirement Graph is the semantic bridge between requirements and ISR.

It must support explicit relationships such as:

```text
REFINES
DEPENDS_ON
CONFLICTS_WITH
SATISFIES
CONSTRAINS
TRACES_TO
DUPLICATES
RELATES_TO
```

Every ISR requirement must have traceability to originating requirement semantics where available.

Every architecture/compiler obligation must be traceable back to one or more requirements.

No generated feature should exist without lineage unless explicitly marked as compiler/runtime infrastructure.

---

# 8. EIR — EVOLUTIONARY REPRESENTATION

EIR must represent the semantic transformation between architectural states.

Required conceptual model:

```text
ISR₀
  ↓
EIR transformation set
  ↓
ISR₁
```

Every mutation must produce explicit transformation records.

Do NOT allow:

```text
ISR changed
EIR transformations = []
```

unless the mutation was genuinely a no-op.

Transformation records must identify:

```text
transformation_id
source ISR
target ISR
type
target semantic path
old value
new value
reason
strategy
operator
parent architecture
child architecture
timestamp
evolution run
evidence
```

At minimum support:

```text
STRUCTURAL
STRATEGIC
ADDITIVE
PARAMETRIC
TOPOLOGICAL
```

Add deterministic serialization and hashing where required.

---

# 9. EVOLUTION ENGINE BOUNDARY

The Evolution Engine must not know:

```text
FastAPI
React
Rust
Docker
PostgreSQL
Kubernetes
```

It evolves architecture and semantic representations.

Its output should be conceptually:

```text
ArchitectureCandidate
+
EIR
+
fitness/evidence
+
lineage
```

not generated source code.

The Compiler consumes the selected architectural state.

Required boundary:

```text
Evolution
     ↓
ISR/EIR
     ↓
Compiler
```

Never:

```text
Evolution
     ↓
filesystem editing
```

---

# 10. FIX EVOLUTION CROSSOVER

Audit crossover.

If crossover claims to combine two parents, it must actually produce a child whose semantic state derives from both parents.

Do not retain pseudo-crossover implementations that simply reuse parent A.

Required tests:

```text
parent A != parent B
        ↓
crossover
        ↓
child contains valid contributions from both
```

Also test:

```text
invalid crossover
conflicting structures
protected regions
constraint violations
determinism
lineage
```

Do not invent arbitrary crossover semantics.

Define them in the architecture/evolution contract.

---

# 11. CANONICAL COMPILER IR

There must be exactly one authoritative Compiler IR.

The repository currently contains overlapping concepts including:

```text
CompilationPlan
BIR
other compiler plan models
```

Do not retain them as competing authorities.

Evaluate them and choose the strongest architecture.

The preferred conceptual direction is:

```text
BIR → Canonical Compiler IR
```

if BIR provides the richer architecture.

The Compiler IR must be distinct from ISR.

ISR:

```text
what the software means
```

Compiler IR:

```text
how that semantic architecture is decomposed into compilable structures
```

Compiler IR may contain:

```text
modules
services
entities
repositories
handlers
routes
events
configuration
middleware
tests
deployment units
security implementations
observability components
```

but these are compiler structures, not requirements.

---

# 12. COMPILER IR INVARIANTS

The Compiler IR must satisfy:

```text
IR is deterministic
IR is serializable
IR is inspectable
IR is hashable
IR is traceable
IR preserves required ISR semantics
IR contains no unresolved mandatory ambiguity
IR does not become a second source of truth
```

Every Compiler IR element must have lineage:

```text
compiler_ir_node
    ↓
ISR semantic source
    ↓
Requirement source
```

where applicable.

---

# 13. COMPILER PIPELINE

Canonical compiler pipeline:

```text
ISR
 ↓
Validation
 ↓
Normalization
 ↓
Capability Resolution
 ↓
Lowering
 ↓
Compiler IR
 ↓
Optimization
 ↓
Backend Selection
 ↓
Backend Lowering
 ↓
Artifact Emission
 ↓
Verification
```

The exact ordering may be adjusted if repository evidence proves a better architecture.

Do not reorder merely for aesthetics.

---

# 14. FAIL-CLOSED COMPILER VALIDATION

This is mandatory.

Validation failure MUST NOT result in:

```text
success=True
```

Do not catch validation errors and convert them into warnings.

Define explicit pass outcomes:

```text
PASS
FAIL
BLOCKED
INDETERMINATE
SKIPPED
```

Suggested semantics:

### PASS

Pass completed successfully.

### FAIL

The input violates the contract.

### BLOCKED

A prerequisite failed.

### INDETERMINATE

The system could not establish correctness.

### SKIPPED

Explicitly authorized and recorded.

No compiler stage may silently transform:

```text
FAIL
```

into:

```text
PASS
```

---

# 15. PASS MANAGER

The pass manager must have explicit failure semantics.

A failed prerequisite must prevent dependent passes from executing.

For example:

```text
validation FAIL
      ↓
normalization BLOCKED
      ↓
lowering BLOCKED
      ↓
generation BLOCKED
```

unless a pass explicitly declares that it can operate safely after that failure.

Each pass should declare:

```text
inputs
outputs
preconditions
postconditions
failure behavior
determinism
side effects
evidence produced
```

---

# 16. VERIFICATION MUST FAIL CLOSED

Verification infrastructure failure is not verification success.

Never convert:

```text
Verification Engine unavailable
```

into:

```text
warning
```

and then permit certification.

Correct behavior:

```text
VERIFICATION_INDETERMINATE
```

which blocks:

```text
CERTIFIED
DEPLOYABLE
```

unless an explicit constitutional exception exists.

Verification should distinguish:

```text
STATIC
STRUCTURAL
CONTRACT
BEHAVIORAL
SECURITY
PERFORMANCE
RUNTIME
```

---

# 17. BACKEND CONTRACT

There must be one canonical backend protocol.

A backend must declare:

```text
backend_id
version
supported_capabilities
supported_IR_version
artifact format
determinism properties
required tools
verification capabilities
deployment capabilities
security capabilities
```

Backend responsibilities:

```text
Compiler IR
    ↓
technology-specific lowering
    ↓
artifact set
```

Backends must never modify:

```text
ISR
Requirement Graph
Evolution policy
Certification policy
```

---

# 18. BACKEND POLYMORPHISM

At least two independent backend targets must eventually prove:

```text
same ISR
      ↓
different backend
      ↓
different implementation
```

without changing ISR.

Use:

```text
Python/FastAPI
Rust/Axum
```

or the strongest existing independent backends.

The test is not merely:

```text
different files
```

The test is:

```text
same semantic obligations
→ independently implemented target systems
→ equivalent required behavior
```

---

# 19. CAPABILITY RESOLUTION

Technology-specific knowledge belongs in:

```text
Capability Resolver
Backend
Lowering
```

not ISR.

Maintain abstract capabilities such as:

```text
authentication
authorization
persistence
REST
eventing
logging
metrics
tracing
validation
containerization
migration
```

and map them to backend-specific implementations.

A new backend must not require ISR modification.

---

# 20. ARTIFACT EMISSION MUST BE PURE

Separate:

```text
compile
emit
package
persist
deploy
```

Prefer:

```text
Compiler
   ↓
ArtifactSet
   ↓
Verifier
   ↓
Packager
   ↓
Deployment
```

rather than:

```text
compiler.compile()
    ↓
writes arbitrary filesystem state
```

Artifact emission must support:

```text
deterministic output
artifact hashes
manifest
source lineage
compiler version
backend version
ISR hash
Compiler IR hash
EIR hash
verification state
```

---

# 21. PROVENANCE

Every generated artifact must be traceable.

Minimum lineage:

```text
artifact
 ↓
backend
 ↓
compiler IR
 ↓
ISR
 ↓
architecture
 ↓
EIR
 ↓
Requirement Graph
 ↓
requirements
```

Where runtime evidence exists:

```text
runtime observation
 ↓
artifact
 ↓
architecture
 ↓
ISR
 ↓
requirements
```

No artifact should become an unexplained file dump.

---

# 22. GENERATED SOFTWARE BOUNDARY

Generated software must be separate from Tiannara source.

Never allow generated applications to become part of Tiannara's authoritative source tree merely because they were generated.

Use explicit artifact/workspace boundaries.

Generated software must carry its own:

```text
manifest
provenance
compiler metadata
backend metadata
verification evidence
```

---

# 23. FASTAPI BACKEND

Bring the Python/FastAPI backend to genuine production-grade compilation.

It must generate at minimum where required:

```text
application
configuration
routes
services
domain models
repositories
persistence
validation
authentication
authorization
middleware
logging
metrics
health
tests
deployment configuration
CI configuration
documentation
```

Do not generate placeholders such as:

```text
pass
TODO
change-me-in-production
allow all CORS
empty router registration
```

unless explicitly generated as an intentional, verifiable extension point.

Generated security defaults must be safe.

---

# 24. RUST/Axum BACKEND

Bring the Rust backend to the same semantic contract.

It must not merely produce skeletal files.

Ensure generated output contains actual implementations for every capability claimed by its backend contract.

Do not label a backend:

```text
BEHAVIORAL
```

if its certification evidence only proves:

```text
file exists
```

Backend classification must match evidence.

---

# 25. CONFORMANCE

Separate:

```text
STRUCTURAL CONFORMANCE
```

from:

```text
BEHAVIORAL CONFORMANCE
```

Structural conformance proves:

```text
required structures exist
```

Behavioral conformance proves:

```text
required behavior works
```

Certification must never confuse the two.

---

# 26. GENERATED APPLICATION VERIFICATION

For each generated reference application establish:

```text
build succeeds
tests execute
tests pass
application starts
health endpoint works
required API contracts work
persistence works where required
authentication works where required
security controls work
observability works
deployment artifact is valid
```

Where a requirement cannot be tested automatically, mark it:

```text
UNVERIFIED
```

not:

```text
VERIFIED
```

---

# 27. OBSERVATION ↔ ISR LINEAGE

Fix the observation layer's ISR binding.

A runtime observation must be able to identify:

```text
artifact
artifact version
architecture
ISR revision
compiler revision
backend
deployment
runtime
```

Do not implement an arbitrary duplicate ISR store.

Bind observation to the canonical ISR/provenance system.

---

# 28. EVOLUTIONARY LINEAGE PERSISTENCE

In-memory lineage is insufficient for long-lived autonomous engineering.

Retain in-memory structures for performance if useful, but establish durable lineage.

Every architecture candidate must be reproducible from:

```text
parent
EIR
random seed where applicable
strategy
configuration
compiler version
evidence
```

The objective is:

```text
reproduce architecture
reproduce compilation
reproduce verification
```

where deterministic guarantees permit.

---

# 29. SECURITY

Audit all modified paths for:

```text
secret leakage
unsafe defaults
credential handling
CORS
authentication
authorization
path traversal
arbitrary filesystem writes
generated code injection
shell execution
dependency injection
untrusted requirements
LLM-generated code
artifact poisoning
provenance forgery
evidence tampering
```

Generated software must never inherit unsafe development defaults into production.

Certification evidence must be tamper-evident.

---

# 30. AI BOUNDARY

LLMs may assist with:

```text
requirement interpretation
architecture proposals
mutation proposals
code synthesis where governed
failure analysis
documentation
```

but AI output must never become authoritative merely because a model produced it.

AI proposals must enter:

```text
Requirement Graph
ISR
EIR
Compiler IR
Verification
```

through typed contracts.

The architecture must remain deterministic and inspectable around nondeterministic AI components.

---

# 31. DETERMINISM

Where deterministic output is required, ensure:

```text
stable ordering
stable IDs
stable serialization
stable hashing
stable artifact manifests
stable backend output
```

If nondeterminism is intentional, record:

```text
seed
model
configuration
prompt/input hash
tool versions
environment
```

---

# 32. TESTING STRATEGY

Do not merely increase test count.

Create tests at the architectural boundaries.

Required categories:

### ISR

```text
schema
validation
immutability
technology leakage
round-trip
semantic preservation
hash stability
```

### Requirement Graph

```text
relationships
traceability
cycle handling
conflicts
determinism
```

### EIR

```text
mutation representation
application
reversal where supported
lineage
hashing
no-op detection
```

### Evolution

```text
mutation
crossover
constraints
protected regions
fitness
lineage
determinism
```

### Compiler IR

```text
ISR → IR
IR determinism
IR completeness
traceability
serialization
```

### Compiler

```text
pass ordering
failure propagation
validation
normalization
lowering
backend selection
```

### Backends

```text
structural conformance
behavioral conformance
determinism
security
build
runtime
```

### Provenance

```text
artifact lineage
hashes
reconstruction
tamper detection
```

### Certification

```text
fail closed
evidence completeness
indeterminate states
```

---

# 33. REQUIRED GOLDEN TEST

Create one canonical end-to-end reference case.

Example:

```text
Requirement:
"Users can create, read, update and delete a task."
```

The system must produce:

```text
Requirement
 ↓
Requirement Graph
 ↓
ISR
 ↓
Architecture
 ↓
EIR
 ↓
Compiler IR
 ↓
Python/FastAPI artifact
 ↓
Verification
 ↓
Evidence
```

Then compile the same ISR to:

```text
Rust/Axum
```

without modifying ISR.

The two generated applications must satisfy the same semantic acceptance criteria.

This becomes the **Compiler Constitutional Golden Path**.

---

# 34. REQUIRED NEGATIVE TESTS

Prove the system refuses:

```text
invalid ISR
technology-contaminated ISR
missing requirement
unresolved compiler IR
backend capability mismatch
invalid architecture
verification failure
missing evidence
tampered artifact
unknown deployment state
```

Do not test only the happy path.

---

# 35. MIGRATION STRATEGY

When consolidating overlapping modules:

```text
Existing implementation
        ↓
Adapter
        ↓
Canonical implementation
        ↓
Tests
        ↓
Deprecation
        ↓
Removal
```

Do not perform a destructive rewrite.

Preserve working behavior where architecturally sound.

Do not delete a subsystem until:

1. replacement exists;
2. behavior is covered;
3. references are migrated;
4. tests pass;
5. provenance is preserved;
6. rollback is understood.

---

# 36. LEGACY APPLICATION

The older:

```text
autonomous-api/
```

application must be classified.

Do not automatically delete it.

Determine:

```text
what is still canonical
what is reused
what is legacy
what belongs in generated software
what belongs in Tiannara infrastructure
```

If it is a legacy runtime/application implementation, establish a migration boundary rather than allowing it to compete with the constitutional compiler.

---

# 37. PACKAGE / BUILD ARCHITECTURE

Inspect package configuration and CI.

Establish a coherent dependency model.

Ensure:

```text
core semantic layers
compiler
backends
verification
certification
runtime
generated applications
```

do not accidentally become one circular package.

Dependency direction must be:

```text
requirements
   ↓
ISR
   ↓
evolution
   ↓
compiler
   ↓
backend
   ↓
generated artifact
```

and never the reverse.

---

# 38. DEPENDENCY RULE

Forbidden examples:

```text
ISR → FastAPI
ISR → React
ISR → Docker
Evolution → FastAPI
Evolution → filesystem
Certification → backend implementation
Backend → ISR mutation
Generated application → Tiannara internal state
```

Allowed:

```text
Backend → Compiler IR
Compiler → ISR
Verification → Artifact
Certification → Evidence
Observation → Artifact provenance
```

---

# 39. NO NEW SOURCE OF TRUTH

Before creating any database, registry, model, cache, manifest, or metadata store ask:

```text
Does this information already have an authoritative owner?
```

If yes:

```text
reference it
```

Do not duplicate it.

If duplication is required for performance:

```text
declare it as a derived projection
define synchronization
define invalidation
define integrity checks
```

---

# 40. PERFORMANCE

Do not sacrifice architectural integrity for premature performance.

However inspect:

```text
large ISR graphs
large populations
compiler IR size
artifact generation
parallel backend compilation
verification
lineage storage
event throughput
memory growth
```

Prefer immutable/content-addressed representations where they provide clear benefit.

Do not introduce distributed infrastructure merely because it sounds scalable.

---

# 41. OBSERVABILITY

Every compiler/evolution operation should expose:

```text
operation_id
run_id
ISR hash
EIR hash
Compiler IR hash
backend
compiler version
duration
status
failure class
artifact hash
verification result
```

Failures must be diagnosable without reading arbitrary logs.

---

# 42. CERTIFICATION

Certification must remain separate from implementation.

The implementation may produce:

```text
candidate
artifact
verification result
evidence
```

Certification decides:

```text
CERTIFIED
NOT_CERTIFIED
BLOCKED
INDETERMINATE
```

Never change certification rules merely to make the implementation pass.

Never classify:

```text
missing evidence
```

as:

```text
certified
```

---

# 43. PHASE 31 EVIDENCE

Preserve the integrity of the completed Phase 31 evidence.

Do not rewrite historical B3 evidence to make the campaign appear certified.

The known B3-v2 result remains:

```text
443 / 936 completed
410 certified
33 not certified
budget exhausted
```

The infrastructure-storm integration issue remains a historical finding until independently remediated.

Do not rerun the historical campaign simply to improve its headline number.

Future campaigns must have new identities.

---

# 44. DOCUMENTATION

Update architecture documentation to explain:

```text
why each canonical boundary exists
why one ISR is authoritative
why Compiler IR is separate
why Evolution does not compile
why backend does not mutate ISR
why verification is fail-closed
why certification is separate
how provenance works
how new backends are added
how new product categories are generated
```

Documentation must describe rationale, not merely filenames.

---

# 45. SELF-ENGINEERING READINESS

The final architecture must make it possible for Tiannara to eventually receive:

```text
"Build a project-management SaaS."
```

and internally execute:

```text
interpret requirement
      ↓
Requirement Graph
      ↓
ISR
      ↓
architecture candidates
      ↓
evolution
      ↓
selection
      ↓
Compiler IR
      ↓
frontend/backend/data/security/deployment
      ↓
generated full-stack application
      ↓
verification
      ↓
deployment
      ↓
observation
      ↓
evidence
```

without a human manually editing generated source.

This is the strategic end state.

---

# 46. PORTFOLIO READINESS

Do not hardcode fourteen generators.

The compiler must eventually support application categories through semantic capabilities.

Examples:

```text
CRUD SaaS
marketplace
dashboard
CMS
booking system
e-commerce
social platform
education platform
analytics system
workflow platform
developer tool
AI application
IoT platform
automation system
```

These should emerge from:

```text
requirements
ISR
capabilities
architecture
backend
```

rather than:

```text
if category == "marketplace":
    use marketplace_generator()
```

---

# 47. IMPLEMENTATION ORDER

Execute remediation in this order unless repository evidence proves a safer dependency order:

```text
R0  Reconnaissance
 ↓
R1  Canonical model decisions
 ↓
R2  ISR semantic preservation
 ↓
R3  Requirement Graph traceability
 ↓
R4  EIR correctness
 ↓
R5  Evolution boundary correction
 ↓
R6  Compiler IR consolidation
 ↓
R7  Compiler pass failure semantics
 ↓
R8  Compiler bridge repair
 ↓
R9  Backend contract consolidation
 ↓
R10 Artifact/provenance consolidation
 ↓
R11 Verification fail-closed
 ↓
R12 Observation lineage
 ↓
R13 Backend behavioral completeness
 ↓
R14 End-to-end golden path
 ↓
R15 Cross-backend semantic equivalence
 ↓
R16 Certification
```

Do not jump to R13 before R6–R12 are structurally sound.

---

# 48. GATE AFTER EACH MAJOR STAGE

At each stage report:

```text
WHAT CHANGED
WHY
FILES CHANGED
INTERFACES CHANGED
DEPENDENCIES CHANGED
TESTS ADDED
TESTS REMOVED
TESTS RUN
RESULTS
ARCHITECTURAL RISKS
MIGRATION STATUS
ROLLBACK PLAN
```

Do not say:

```text
"looks good"
```

Use evidence.

---

# 49. REQUIRED FINAL VALIDATION

Before declaring success, prove:

### V1

Exactly one canonical ISR.

### V2

Requirement Graph → ISR traceability works.

### V3

ISR round-trip preserves semantics.

### V4

EIR records actual architectural transformations.

### V5

Evolution crossover is genuine or explicitly reclassified.

### V6

Exactly one canonical Compiler IR.

### V7

Compiler validation fails closed.

### V8

Compiler pass failures block dependent passes.

### V9

Compiler bridge uses current canonical interfaces.

### V10

Exactly one backend contract.

### V11

Backend output is deterministic where required.

### V12

Artifacts carry complete provenance.

### V13

Verification failure cannot become certification.

### V14

Runtime observations can trace back to ISR.

### V15

Python backend passes structural and behavioral verification.

### V16

Rust backend passes structural and behavioral verification.

### V17

Same ISR can compile to both without ISR changes.

### V18

Golden end-to-end project succeeds.

### V19

Negative cases fail correctly.

### V20

No architectural P0 remains unresolved.

---

# 50. DEFINITION OF DONE

The mission is complete only when:

```text
Requirement
    ↓
Requirement Graph
    ↓
Canonical ISR
    ↓
EIR
    ↓
Canonical Compiler IR
    ↓
Backend
    ↓
Artifact
    ↓
Verification
    ↓
Certification
```

is executable and evidence-backed.

And:

```text
Artifact
    ↓
Observation
    ↓
Evidence
    ↓
ISR lineage
```

is also executable.

The architecture must no longer contain competing authorities for:

```text
ISR
Compiler IR
backend protocol
artifact provenance
evolution lineage
```

---

# 51. STOP CONDITIONS

STOP implementation and report instead of guessing when:

```text
canonical ISR cannot be determined
two representations have incompatible semantics
migration would destroy provenance
security boundary is unclear
verification semantics are ambiguous
certification contract conflicts with implementation
backend capability semantics are undefined
```

When stopped, report:

```text
UNKNOWN
WHY IT MATTERS
OPTIONS
RECOMMENDED DECISION
EVIDENCE REQUIRED
```

Do not invent an answer.

---

# 52. FORBIDDEN BEHAVIOR

Never:

```text
create another ISR
create another Compiler IR
create another backend protocol
create another source of truth
silently drop fields
convert failures to success
skip verification
claim behavioral correctness from structural checks
hardcode product categories
embed technology in ISR
modify historical certification evidence
rewrite tests merely to pass
disable failing tests
weaken certification criteria
commit generated artifacts as source
perform destructive rewrites without migration
```

Never optimize for:

```text
number of files changed
number of tests passing
shortest implementation
```

Optimize for:

```text
architectural correctness
semantic preservation
traceability
verifiability
evolvability
production safety
```

---

# 53. CODING STANDARD

All implementation must be:

```text
typed
modular
testable
deterministic where required
observable
secure
documented
production-oriented
```

Avoid unnecessary abstractions.

Every abstraction must have an architectural reason.

---

# 54. GIT / CHANGE CONTROL

Do not:

```text
force push
rewrite history
delete evidence
amend unrelated commits
```

Do not commit unless explicitly authorized by the controlling workflow.

Keep changes scoped.

Every commit, when authorized, should represent a coherent architectural unit.

---

# 55. FINAL REPORT FORMAT

At completion provide:

```text
# Tiannara Compiler Foundation Remediation Report

## 1. Executive Verdict

## 2. Canonical Architecture

## 3. Canonical ISR

## 4. Canonical Requirement Graph

## 5. Canonical EIR

## 6. Canonical Compiler IR

## 7. Compiler Pipeline

## 8. Backend Architecture

## 9. Verification Architecture

## 10. Provenance Architecture

## 11. Observation Lineage

## 12. Removed / Deprecated Duplicates

## 13. Migration Performed

## 14. Tests

## 15. Golden Path Result

## 16. Cross-Backend Result

## 17. Security Findings

## 18. Performance Findings

## 19. Remaining Risks

## 20. Autonomous Engineering Readiness

## 21. Files Changed

## 22. Git State

## 23. Certification Evidence
```

Every claim must have repository evidence.

---

# 56. FINAL ARCHITECTURAL TEST

Ask the following before declaring completion:

> Can Tiannara take one technology-neutral ISR, evolve it, compile it through a canonical Compiler IR, generate two independently implemented full-stack backends, verify them, certify them, deploy them, observe them, and trace runtime evidence back to the original requirements — without changing the ISR?

If the answer is:

```text
YES
```

the compiler foundation has achieved its intended architectural objective.

If the answer is:

```text
NO
```

do not claim completion.

Identify the exact missing boundary.

---

# 57. FINAL PRINCIPLE

The goal is NOT:

> "make the existing compiler pass its tests."

The goal is:

> **Turn the existing Tiannara implementation into a coherent autonomous software engineering compiler architecture without destroying the evolutionary, epistemic, verification, certification, and provenance foundations already built.**

The repository already contains substantial pieces.

Your responsibility is to **consolidate, repair, verify, and connect them**.

Do not rebuild what already works.

Do not preserve architecture merely because it already exists.

Do not add complexity without evidence.

Do not silently compromise the ISR.

Do not weaken verification.

Do not manufacture certification.

Build toward:

```text
UNDERSTAND
    ↓
REPRESENT
    ↓
EVOLVE
    ↓
COMPILE
    ↓
VERIFY
    ↓
CERTIFY
    ↓
DEPLOY
    ↓
OBSERVE
    ↓
LEARN
    ↓
EVOLVE AGAIN
```

That is the Tiannara autonomous software engineering loop.

### One important operational point

I would give this to the coding agent **before asking it to write any code**.

The first output from the agent should be its **R0 reconnaissance/remediation plan**, not a pile of edits. In particular, I would require it to return a table like:

| Conflict        | Current implementations                      | Proposed canonical     | Migration         | Risk |
| --------------- | -------------------------------------------- | ---------------------- | ----------------- | ---- |
| ISR             | `isr/` vs `constitutional_architecture/isr/` | one                    | adapter/migration | P0   |
| Compiler IR     | `CompilationPlan` vs BIR                     | BIR successor          | consolidate       | P0   |
| Compiler bridge | old/new APIs                                 | canonical compiler API | repair            | P1   |
| EIR             | declared vs actual transformations           | explicit EIR           | repair            | P1   |
| Verification    | fail-open paths                              | fail-closed            | repair            | P0   |
| Backends        | multiple protocols                           | one contract           | adapters          | P1   |

**Do not let it start R1 implementation until that table is internally consistent.**

That gives Tiannara a much safer path from the current codebase toward the point where **Tiannara itself can eventually perform this kind of architectural remediation**, rather than depending on an external LLM to continually invent patches.
