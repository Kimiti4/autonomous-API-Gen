# Canonical Contract Registry

**Status:** R1-B Deliverable D01. The 11 canonical contract surfaces are enumerated here. Each surface has a dedicated contract specification (D02–D12) that defines the contract's identity, ownership, immutability/mutability, provenance, hashing, lifecycle, failure semantics, and extension boundaries.

**Authority:** R1-A canonical substrate decision (`folder/CANONICAL_SUBSTRATE_DECISION.md`) and the R1-B specification in `folder/R1_PLAN.md`.

**Architectural principle (R1-B):**

```
ISR ≠ Architecture Model ≠ Compiler IR ≠ Generated Artifact
```

The four are distinct semantic surfaces. Conflating any two of them is the exact substrate-duplication problem R0 discovered. The contract hierarchy below enforces this principle.

---

## Contract hierarchy

```text
Requirement
    ↓
RequirementGraph
    ↓
Canonical ISR
    ↓
ArchitectureCandidate
    ↓
EvolutionOperation
    ↓
EvolutionRecord / EIR
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

A producer at level N may reference and depend on contracts at levels 0..N-1. A producer at level N may NOT depend on contracts at levels > N. (Forward references are forbidden.)

**Producer chain (downward dependencies are allowed; upward are forbidden):**

| Level | Contract | Producer | Direct consumer (next level) |
|---|---|---|---|
| 0 | `RequirementGraph` | Requirement extractor (out of R1-B scope) | `ISR` |
| 1 | `ISR` | `isr/core` (canonical) | `ArchitectureCandidate` |
| 2 | `ArchitectureCandidate` | Evolution engine (R1-B.D04) | `EvolutionOperation` |
| 3 | `EvolutionOperation` | Evolution engine (R1-B.D05) | `EvolutionRecord/EIR` |
| 4 | `EvolutionRecord/EIR` | Evolution engine recorder | `CompilerIR` |
| 5 | `CompilerIR` | Compiler lowering | `CompilerBackend` |
| 6 | `CompilerBackend` | Backend implementations | `ArtifactSet` |
| 7 | `ArtifactSet` | Backend emission + packager | `VerificationResult` |
| 8 | `VerificationResult` | Verifier implementations | `CertificationEvidence` |
| 9 | `CertificationEvidence` | Certifier (campaign) | (terminal; downstream of `RuntimeObservation`) |
| 10 | `RuntimeObservation` | Runtime instrumentation | Evidence ledger (terminal; feeds back to Evolution) |

The cycle `RuntimeObservation → Evidence → Learning → Evolution` is permitted at level ≥ 10 only. The Evolution contracts (D05/D06) read lineage but do not mutate RuntimeObservation.

---

## The 11 canonical contracts

For each contract the registry lists: **canonical owner**, **module/package**, **purpose**, **producer**, **consumer**, **identity**, **lifecycle**, **mutability**, **serialization**, **hashing**, **provenance**, **failure semantics**, **extension mechanism**, **current implementation**, **target implementation**, **legacy implementations**, **migration destination**.

The detailed contract specification for each surface is in D02–D12 (forthcoming). The fields below are the registry's *summary*; D02–D12 are the *authoritative* contracts.

### C01. RequirementGraph

| Field | Value |
|---|---|
| Canonical owner | `reqgraph/core` |
| Module/package | `reqgraph.core.graph`, `reqgraph.core.invariants` |
| Purpose | Typed semantic bridge from requirements to ISR construction. |
| Producer | Requirement extractor (out of R1-B scope; current: `reqgraph.core.graph.RequirementGraph` constructed manually; future: automated). |
| Consumer | ISR construction (D03), traceability queries. |
| Identity | Stable requirement IDs (UUIDv5-derived from a content-addressed input); stable graph ID. |
| Lifecycle | Append-only per revision. New graph revisions are new identities. |
| Mutability | Frozen at construction. Edits create a new revision, never mutate the existing. |
| Serialization | Deterministic JSON over sorted requirement IDs, sorted edge tuples, and stable requirement content. |
| Hashing | SHA-256 over canonical serialization. |
| Provenance | Source requirement text, source extractor identity, source prompt hash, timestamp. |
| Failure semantics | Validation errors (cycle, conflict, dangling reference) raise; partial graphs are not returned. |
| Extension mechanism | New relationship classes require ADR approval (per R1-B.D02; do NOT add new edge types merely for completeness). |
| Current implementation | `reqgraph/core/graph.py:25-44` (4 edge types: `DEPENDS_ON`, `CONFLICTS_WITH`, `REFINES`, `OWNED_BY`). |
| Target implementation | Same module; the contract specification (D02) freezes the API. |
| Legacy implementations | None observed. The audit's "8 edge types" claim (`REFINES, DEPENDS_ON, CONFLICTS_WITH, SATISFIES, CONSTRAINS, TRACES_TO, DUPLICATES, RELATES_TO`) is NOT in this module; the 4-edge implementation is the only RequirementGraph runtime. |
| Migration destination | n/a (canonical from inception). |

### C02. ISR

| Field | Value |
|---|---|
| Canonical owner | `isr/core` |
| Module/package | `isr.core.graph`, `isr.core.revision`, `isr.core.invariants`, `isr.core.identity` |
| Purpose | The **single authoritative semantic representation of a software system revision**. |
| Producer | RequirementGraph → ISR construction (via `isr_to_plan`-equivalent for ISR, not yet present); the canonical constructor is in `isr/core/`. |
| Consumer | ArchitectureCandidate (D04), CompilerIR (D07), all consumers that need system semantics. |
| Identity | Content hash (`compute_content_hash` at `isr/core/identity.py:44-66`) over canonical serialization. |
| Lifecycle | Append-only per revision. New revisions supersede; old revisions are immutable. |
| Mutability | Frozen (Pydantic `frozen=True`); `with_system` creates new revisions. |
| Serialization | Canonical JSON with sorted keys; forbidden-term check (25 forbidden implementation terms). |
| Hashing | SHA-256 over canonical serialization. |
| Provenance | `Provenance` (frozen Pydantic model at `isr/core/identity.py:18-32`): source, author, tool versions, timestamp. |
| Failure semantics | Forbidden-term leakage → `ISRInvariantViolation`. Type/edge mismatch → `ISRInvariantViolation`. Construction fails closed. |
| Extension mechanism | Node/edge taxonomy is frozen at 9 NodeType / 8 EdgeType (per D03). Extensions require ADR. |
| Current implementation | `isr/core/{graph,identity,invariants,revision}.py`. 9 NodeType (`DOMAIN, CAPABILITY, SERVICE, API, DATA_MODEL, EVENT, SECURITY_POLICY, INFRASTRUCTURE_TARGET, REQUIREMENT_REF`). 8 EdgeType (`SATISFIES, IMPLEMENTED_BY, EXPOSES, PERSISTS, PUBLISHES, CONSUMED_BY, DEPENDS_ON, SECURED_BY`). |
| Target implementation | Same module; the contract specification (D03) freezes the API and the **semantic-authority invariant** (INV-B01). |
| Legacy implementations | `constitutional_architecture/isr/model/isr.py:ISR` (rich System/Module/Entity/... dataclass model). `constitutional_architecture/core/models/isr.py:UniversalISR` (Pydantic 17-NodeType, 13-EdgeType typed graph). Both are **legacy** and **not in the canonical execution path**; semantic validators from `constitutional_architecture/isr/semantics/*` are selectively migrated in R1-D.1. |
| Migration destination | (none — these are LEGACY and retired as runtime per R1-D.5 with LEGACY classification per R1-B.D17). |

### C03. ArchitectureCandidate

| Field | Value |
|---|---|
| Canonical owner | `evolution/core` |
| Module/package | `evolution.core.individual`, `evolution.core.genome`, `evolution.core.construction` (R1-D.3 may add a new `evolution.core.architecture` module). |
| Purpose | The representation consumed by the evolution engine; **must reference a Canonical ISR revision** and must NOT become another ISR. |
| Producer | Evolution engine (mutation, crossover, recombination). |
| Consumer | Evolution selection, CompilerIR (D07). |
| Identity | Content hash over the architecture decisions, topology, component boundaries, constraints, objectives, and the referenced ISR revision's content hash. |
| Lifecycle | Append-only per generation. |
| Mutability | Frozen per candidate. New candidates are new identities. |
| Serialization | Deterministic JSON. |
| Hashing | SHA-256. |
| Provenance | Parent candidate identity, evolution operation identity, seed/randomness metadata, timestamp. |
| Failure semantics | Construction that produces a non-ISR representation (i.e., that defines system semantics independently of the referenced ISR) is rejected. |
| Extension mechanism | Architecture decisions and topology evolve via mutation operators. The contract surface is frozen. |
| Current implementation | `evolution/core/genome.py` (Genome model with chromosomes+genes). Operates on `isr.core.revision.ISRRevision`. The `Genome` is the de facto ArchitectureCandidate today; the contract (D04) will formalize it. |
| Target implementation | A typed `ArchitectureCandidate` module (R1-D.3); the contract specification (D04) freezes the API. |
| Legacy implementations | `constitutional_architecture/engine/individual.py` and the Substrate B Evolution engine (`constitutional_architecture/engine/evolution_engine.py`). These are LEGACY; their semantic properties are selectively migrated in R1-D. |
| Migration destination | LEGACY (per R1-D.5; semantic properties selectively migrated). |

### C04. EvolutionOperation

| Field | Value |
|---|---|
| Canonical owner | `evolution/core` |
| Module/package | `evolution.core.operations` (mutation, crossover, recombination, selection, evaluation). |
| Purpose | An operation that produces a new ArchitectureCandidate from one or more parents. |
| Producer | Evolution engine scheduler. |
| Consumer | Evolution engine recorder (D06). |
| Identity | Operation ID (UUIDv5 over operator type + parameters + timestamp). |
| Lifecycle | Stateless; one execution = one identity. |
| Mutability | Frozen per execution; parameters are immutable. |
| Serialization | Deterministic JSON over operator type, input candidate IDs, parameters, seed. |
| Hashing | SHA-256 over canonical serialization. |
| Provenance | Operator type, parent candidate IDs, randomness seed, timestamp, evolution run ID. |
| Failure semantics | Operation failure produces a failure record (D06.EvolutionRecord) and does not produce a candidate. |
| Extension mechanism | New operators are added by extending the operations module; the contract surface is frozen. |
| Current implementation | `evolution/core/operations.py:74-104` (real crossover verified in R0). Mutation, crossover, recombination, selection, evaluation all exist. |
| Target implementation | Same module; the contract specification (D05) freezes the API. |
| Legacy implementations | `constitutional_architecture/engine/mutation_*.py` and `constitutional_architecture/engine/crossover_engine.py`. These are LEGACY. |
| Migration destination | LEGACY (per R1-D.5). |

### C05. EvolutionRecord / EIR

| Field | Value |
|---|---|
| Canonical owner | `evolution/core` |
| Module/package | `evolution.core.record` (R1-D.3 will add this; today lineage is in `evolution/core/lineage` if present, otherwise inline). |
| Purpose | The **record of what happened** when an EvolutionOperation executed. Separate from the operation itself. |
| Producer | Evolution engine recorder. |
| Consumer | Lineage queries, learning, EIR replay. |
| Identity | Content hash over operation ID + parent IDs + result IDs + parameters + seed. |
| Lifecycle | Append-only; immutable. |
| Mutability | Frozen. |
| Serialization | Deterministic JSON. |
| Hashing | SHA-256. |
| Provenance | Operation ID, parent candidate IDs, resulting candidate IDs, operator, parameters, seed, evaluation results, timestamps, lineage references, evidence references, status, failure information. |
| Failure semantics | A failed operation produces a record with `status=FAILED` and `failure_information` populated; the record is not silently dropped. |
| Extension mechanism | The contract surface is frozen; new record fields require ADR. |
| Current implementation | `evolution/core/lineage` (lineage in-memory); `constitutional_architecture/eir/transformation.py:EIR` (defective: `evolution_loop.py:110 transformations=[]`). |
| Target implementation | A new `evolution/core/record.py` (R1-D.3) with the contract's required fields. The EIR schema from `constitutional_architecture/eir/transformation.py` is selectively absorbed; the `transformations=[]` defect is repaired or the path is retired. |
| Legacy implementations | `constitutional_architecture/eir/transformation.py:EIR`. LEGACY; the missing fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`) are added in the canonical EvolutionRecord (R1-D.3). |
| Migration destination | LEGACY (per R1-D.5; useful schema fields selectively absorbed). |

### C06. CompilerIR

| Field | Value |
|---|---|
| Canonical owner | (R1-B.D07 to be defined; stabilization owner is `compiler/core`.) |
| Module/package | (R1-D.2 to introduce; stabilization implementation is `compiler/core/plan.py:CompilationPlan`.) |
| Purpose | The compiled, technology-neutral representation of an architecture ready for backend lowering. **Distinct from Architecture Model, ISR, and generated artifacts.** |
| Producer | Compiler lowering (R1-B.D07). |
| Consumer | CompilerBackend (D08). |
| Identity | Content hash over canonical serialization (per R1-B.D07). |
| Lifecycle | Append-only per compilation. |
| Mutability | Frozen. |
| Serialization | Deterministic JSON (or other canonical form defined in D07). |
| Hashing | SHA-256. **BIR is a semantic donor; content-hash is added to the canonical CompilerIR, not to BIR.** |
| Provenance | Source ISR revision ID, source ArchitectureCandidate ID, lowering metadata, lowering timestamp, lowering operator ID, backend constraints. |
| Failure semantics | Lowering that produces a non-traceable IR (no provenance to ISR/Architecture) is rejected. |
| Extension mechanism | New IR node types require ADR; the contract surface is frozen. |
| Current implementation (stabilization) | `compiler/core/plan.py:CompilationPlan` (Pydantic flat: `Service`, `DataModel`, `Event`, `SecurityPolicy`). Used by `certification/`. |
| Target implementation | A new canonical CompilerIR module (R1-D.2) with the concepts listed in D07. The current `CompilationPlan` is the stabilization implementation; the canonical contract supersedes it. |
| Legacy implementations | `constitutional_architecture/compiler/bir/model.py:BIR` (BIRNodeType: `HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`). **BIR is a semantic donor, not a competing IR.** The 9 BIRNodeTypes are selectively absorbed into the canonical CompilerIR contract where genuinely semantic. `UniversalISR`-as-typed-graph (consumed by `constitutional_architecture/compilers/*`) is also LEGACY. |
| Migration destination | LEGACY (per R1-D.5; BIR semantic properties selectively migrated). |

### C07. CompilerBackend

| Field | Value |
|---|---|
| Canonical owner | `compiler/core/protocol.py` |
| Module/package | `compiler.core.protocol`, `compiler.core.registry`, `compiler.composition`. |
| Purpose | The canonical backend protocol: `CompilerIR → CompilerBackend → ArtifactSet`. |
| Producer | Backend implementer (e.g. `python-fastapi`, `rust-axum`). |
| Consumer | Compiler pipeline (R1-B.D08). |
| Identity | Backend ID + version (e.g. `python-fastapi@1.4.0`). |
| Lifecycle | Versioned; multiple versions may coexist temporarily. |
| Mutability | Backend code evolves; the protocol is frozen. |
| Serialization | Backend identity + manifest (supported capabilities, supported target, supported IR version). |
| Hashing | SHA-256 over manifest. |
| Provenance | Backend implementer, version, commit hash. |
| Failure semantics | Unsupported capability is an explicit `UNSUPPORTED_CAPABILITY` outcome, not a successful compilation. Backend errors are typed. |
| Extension mechanism | New backends are added by implementing the protocol; the protocol surface is frozen. |
| Current implementation | `compiler/core/protocol.py:CompilerBackend` (Protocol with `name, language, framework, version, backend_class, identity(), test_spec(), element_paths(plan), compile(plan), conformance(plan, repo)`). |
| Target implementation | Same protocol, with extensions as defined in D08. |
| Legacy implementations | `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` (Gen-C). `compiler/sdk/base.py:CompilerBackendBase` (Gen-A). `constitutional_architecture/compilers/backend/base.py:BackendCompiler` (per-category). |
| Migration destination | LEGACY (per R1-D.5; canonical protocol retains the Gen-B shape with the additions in D08). |

### C08. ArtifactSet

| Field | Value |
|---|---|
| Canonical owner | (R1-B.D09 to be defined; stabilization is `compiler/core/repository.py:GeneratedRepository`.) |
| Module/package | `compiler.core.repository` (stabilization); the canonical ArtifactSet will be a new module (R1-D.5). |
| Purpose | The canonical generated-software boundary. Every generated artifact is in an ArtifactSet. The packager writes; backends emit. |
| Producer | CompilerBackend (D07). |
| Consumer | Verifier (D10), packager, deployer. |
| Identity | Content hash over the manifest (file paths + content hashes + metadata). |
| Lifecycle | Append-only per compilation. |
| Mutability | Frozen. |
| Serialization | Manifest JSON (paths, hashes, metadata, provenance). |
| Hashing | SHA-256 per file; SHA-256 over the manifest. |
| Provenance | Backend ID + version, CompilerIR ID, ArchitectureCandidate ID, ISR revision ID, RequirementGraph ID. |
| Failure semantics | Incomplete manifest (missing files, hash mismatches) is rejected. Backend-emitted filesystem writes that bypass the ArtifactSet are forbidden. |
| Extension mechanism | New artifact kinds (e.g. SBOM, deployment manifests) are added by extending the manifest schema; the contract surface is frozen. |
| Current implementation (stabilization) | `compiler/core/repository.py:GeneratedRepository` (used by `certification/`). Gen-B backends emit via `build_repository(files_dict)` (pure emission). |
| Target implementation | A new canonical `ArtifactSet` module (R1-D.5) that formalizes the contract: files, directories, metadata, manifest, provenance, content hashes, and the explicit distinction between generated artifact / compiler workspace / temporary build output / runtime deployment artifact. |
| Legacy implementations | Gen-C `constitutional_architecture/compiler/backends/fastapi_backend.py:72-86` calls `self.write_files()` inside `compile()` — **forbidden**; this is the Gen-C artifact-purity defect. `CompilationOutput` (Gen-A `compiler/models.py`) is also LEGACY. |
| Migration destination | LEGACY (per R1-D.5; Gen-C's filesystem emission is corrected or the backend is retired per R1-E). |

### C09. VerificationResult

| Field | Value |
|---|---|
| Canonical owner | (R1-B.D10 to be defined; stabilization is `certification/stages/`.) |
| Module/package | `certification/stages/{stub_stages,docker_stages,independent_verify}.py` (stabilization). The canonical Verifier interface will be defined in D10. |
| Purpose | An **evidence-producing subsystem**. Not a boolean. A verifier exception must never silently become a successful result. |
| Producer | Verifier implementations (D10). |
| Consumer | Certifier (D11). |
| Identity | Verification ID (UUIDv5 over subject + verifier + timestamp). |
| Lifecycle | Append-only. |
| Mutability | Frozen. |
| Serialization | Deterministic JSON: `{verification_id, subject_artifact_id, subject_ir_id, verifier_id, verifier_version, checks_performed, evidence_refs, result, failure_reason, indeterminate_reason, provenance, timestamp}`. |
| Hashing | SHA-256 over canonical serialization. |
| Provenance | Subject identity, verifier identity/version, evidence references. |
| Failure semantics | **Mandatory states:** `PASS`, `FAIL`, `INDETERMINATE`, `NOT_RUN`, `BLOCKED`. An internal verifier exception produces `INDETERMINATE` (not `PASS`). |
| Extension mechanism | New verifier kinds are added by implementing the verifier protocol; the contract surface is frozen. |
| Current implementation (stabilization) | `certification/stages/{stub_stages,docker_stages,independent_verify}.py` (fail-closed in the campaign runtime; R0 verified this). |
| Target implementation | A canonical Verifier contract (D10) with the mandatory state model. R1-E.1 implements the canonical Verification contract. |
| Legacy implementations | `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (fail-open: returns `success=True` on engine exception). This is the Gen-C verification-purity defect; per R1-B.D17 it is LEGACY and will be adapted to the canonical contract in R1-E.1. |
| Migration destination | LEGACY (per R1-D.5 / R1-E.1; canonical contract is fail-closed). |

### C10. CertificationEvidence

| Field | Value |
|---|---|
| Canonical owner | `certification/evidence/`. |
| Module/package | `certification/evidence/{ledger,infra_storm,escalation,registry}.py`. |
| Purpose | The downstream-of-verification certification record. Historical B3-v2 evidence is immutable and is not altered by R1. |
| Producer | Certifier (campaign). |
| Consumer | Auditors, governance registry, downstream campaigns. |
| Identity | Evidence ID (UUIDv5 over subject + verifier + verification result + timestamp + campaign ID). |
| Lifecycle | Append-only. **Historical evidence is immutable (INV-B13).** |
| Mutability | Frozen. |
| Serialization | Deterministic JSON; hash-chained. |
| Hashing | SHA-256; hash chain links each record to its predecessor. |
| Provenance | Subject identity, verifier identity/version, verification result, ledger reference, campaign ID, run ID. |
| Failure semantics | Certification cannot manufacture verification evidence (INV-B11). Missing evidence produces `NOT_CERTIFIED`, not a substitute pass. |
| Extension mechanism | New evidence types are added by extending the schema; the contract surface is frozen. |
| Current implementation | `certification/evidence/ledger.py:EvidenceLedger` (JSONL, hash-chained, SHA-256). The B3-v2 ledger (443 records, chain intact) is preserved. |
| Target implementation | Same; the contract specification (D11) freezes the schema and the immutability invariant. |
| Legacy implementations | None observed at this layer. |
| Migration destination | n/a (canonical from inception). |

### C11. RuntimeObservation

| Field | Value |
|---|---|
| Canonical owner | (R1-B.D12 to be defined; stabilization is `autonomous-api/app/observation/`, which is **LEGACY** and C-17-deferred.) |
| Module/package | (out of R1 scope; D12 specifies the contract; C-17 deferred.) |
| Purpose | The reverse path: deployed artifact → runtime observation → evidence → learning → evolution. Runtime observations retain reverse lineage to ISR. |
| Producer | Runtime instrumentation (out of R1 scope; C-17 deferred). |
| Consumer | Evidence ledger, learning, evolution. |
| Identity | Observation ID (UUIDv5 over deployment + artifact + timestamp). |
| Lifecycle | Append-only. |
| Mutability | Frozen. |
| Serialization | Deterministic JSON with reverse-lineage fields. |
| Hashing | SHA-256. |
| Provenance | Deployment ID, ArtifactSet ID, CompilerIR ID, ArchitectureCandidate ID, ISR revision ID, RequirementGraph ID, runtime identity. |
| Failure semantics | Observations with missing reverse lineage are rejected (cannot attach to evidence). |
| Extension mechanism | New observation kinds are added by extending the schema; the contract surface is frozen. |
| Current implementation | None in the canonical runtime. `autonomous-api/app/observation/` exists but is **LEGACY** (C-17 deferred). The campaign runtime does not depend on `autonomous-api/`. |
| Target implementation | The RuntimeObservation contract (D12) is defined in R1-B; the implementation is **out of R1 scope** (deferred to R2/R3 platform integration). |
| Legacy implementations | `autonomous-api/app/observation/{gateway,sequences,projectors}.py` — LEGACY. `autonomous-api/app/main.py:111-115` `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` is the audit-flagged observation-ISR binding gap; **C-17 deferred**. |
| Migration destination | LEGACY (per R1-D.5; C-17 deferred to R2/R3). |

---

## Cross-references

- **Canonical-substrate decision (R1-A):** `folder/CANONICAL_SUBSTRATE_DECISION.md` (`9bb3df8`). This registry is consistent with the R1-A canonical module map.
- **R0 reconnaissance:** `folder/R0_RECONNAISSANCE_REPORT.md` (the 20-conflict table and the audit-claim verification).
- **R1 plan:** `folder/R1_PLAN.md` (R1-B spec D01–D20 captured in §R1-B).
- **Compatibility matrix (D15):** forthcoming.
- **Migration constraints (D19):** forthcoming.

---

## Field classification legend

Each contract field in the registry above is classified as:

- **semantic** — defines the contract's meaning; cannot be derived or omitted.
- **derived** — computed from other fields; included for efficiency.
- **observational metadata** — describes the contract (e.g. provenance, timestamps) but does not define its semantics.

For each of the 11 contracts, the field classification will be detailed in the per-contract D02–D12 specifications.

| Field | Classification (default) |
|---|---|
| Canonical owner, Module/package, Purpose, Producer, Consumer, Identity, Lifecycle, Mutability, Failure semantics, Extension mechanism | **semantic** |
| Serialization, Hashing | **derived** (but part of the contract surface) |
| Provenance, Timestamp, Current implementation, Target implementation, Legacy implementations, Migration destination | **observational metadata** |

---

*End of D01. R1-B continues with D02–D12 (per-contract specifications) and D13–D20 (cross-cutting + gate report).*
