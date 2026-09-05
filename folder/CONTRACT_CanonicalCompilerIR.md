# CONTRACT_CanonicalCompilerIR (R1-B D07)

**Contract:** `CompilerIR`
**Status:** R1-B Deliverable D07. Where the R1-A C-03 refinement becomes concrete. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Canonical owner:** (D07 defines; stabilization is `compiler/core`)

**Invariants this contract satisfies:** INV-B05 (Compiler IR is distinct from ISR), INV-B06 (Compiler IR is distinct from generated artifacts), INV-B14 (no category-specific compiler becomes a new architectural authority).

---

## 1. Purpose

The `CompilerIR` is the compiled, technology-neutral representation of an architecture, ready for backend lowering. It is **distinct from ISR** (D03), **distinct from Architecture Model** (D04), and **distinct from generated artifacts** (D09).

## 2. The R1-A C-03 refinement (mandatory)

```text
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

`CompilationPlan` (the current stabilization implementation at `compiler/core/plan.py`) is **not** the final architectural definition of `CompilerIR`. The contract defines the future CompilerIR independently of `CompilationPlan`. The canonical CompilerIR module is created in R1-D.2.

**BIR is a semantic donor, not a competing IR.** The 9 BIRNodeTypes (`HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`) are read as references; the genuinely-semantic ones are absorbed into the canonical CompilerIR contract where appropriate. BIR is not modified; the canonical CompilerIR is a new module.

**Content-hash is added to the canonical CompilerIR, not to BIR.** This prevents BIR from accidentally becoming canonical via the stabilization layer.

## 3. Architecture

The canonical CompilerIR carries:

- compilation identity
- source ISR / architecture references
- target requirements
- component model
- interfaces
- data flows
- persistence requirements
- API contracts
- frontend / backend responsibilities
- security requirements
- deployment requirements
- observability requirements
- backend constraints
- lowering metadata
- provenance
- deterministic identity / hash

## 4. Identity

- **Compilation ID:** UUIDv5 over the canonical serialization.
- **Content hash:** SHA-256 over canonical serialization. The hash is the IR's identity.

## 5. Lifecycle and mutability

- **Frozen.** Each compilation is a new identity; the previous is immutable.
- **Append-only per compilation.**

## 6. Required fields

| Field | Required? | Classification |
|---|---|---|
| Compilation ID | yes | **semantic** (identity) |
| Source ISR revision reference (content hash) | yes | **semantic** |
| Source ArchitectureCandidate reference (content hash) | yes | **semantic** |
| Target requirements (links to RequirementGraph IDs) | yes | **semantic** |
| Component model | yes | **semantic** |
| Interfaces | yes | **semantic** |
| Data flows | yes | **semantic** |
| Persistence requirements | yes | **semantic** |
| API contracts | yes | **semantic** |
| Frontend / backend responsibilities | yes | **semantic** |
| Security requirements | yes | **semantic** |
| Deployment requirements | yes | **semantic** |
| Observability requirements | yes | **semantic** |
| Backend constraints (which backends can lower this IR) | yes | **semantic** |
| Lowering metadata (lowering operator, timestamp) | yes | **observational metadata** |
| Provenance (source ISR hash, source architecture hash, lowering chain) | yes | **observational metadata** |
| Serialization (deterministic JSON) | yes | **derived** |
| Content hash (SHA-256) | yes | **derived** |

## 7. Field classification (summary)

| Field | Classification |
|---|---|
| All component, interface, data-flow, persistence, API, security, deployment, observability, backend-constraint fields | **semantic** |
| Source ISR / architecture references | **semantic** (non-derivable) |
| Serialization, hashing | **derived** |
| Lowering metadata, timestamps, provenance | **observational metadata** |

## 8. Hashing and serialization

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization. The hash is the IR's identity.
- **Provenance hash:** the content hash of the Provenance carrier is included in the IR's content hash.

## 9. Provenance

- Source ISR revision content hash.
- Source ArchitectureCandidate content hash.
- Lowering operator identity.
- Lowering timestamp.
- Lowering chain (the sequence of lowering operations that produced this IR).

## 10. Failure semantics

- Lowering that produces a non-traceable IR (no provenance to ISR/Architecture) is rejected.
- An IR with `status=LOWERING_OK` and empty component model is forbidden (the lowering did something).
- The contract distinguishes:
  - `LOWERING_OK` — IR produced.
  - `LOWERING_FAILED` — lowering failed; no IR produced; reason recorded.
  - `LOWERING_BLOCKED` — a precondition (e.g. ISR invariant violation) was not met; no IR produced.
  - `LOWERING_INDETERMINATE` — operator could not determine the IR deterministically; reason recorded.

## 11. Extension mechanism

- New IR node types require an ADR; do not add them via the contract surface.
- New fields (e.g. additional observability kinds) require an ADR.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation (stabilization)

`compiler/core/plan.py:CompilationPlan` (Pydantic flat: `Service`, `DataModel`, `Event`, `SecurityPolicy`). Used by `certification/`. The stabilization implementation is **not** the final canonical contract; the canonical CompilerIR module is created in R1-D.2.

## 13. Legacy implementations

- `constitutional_architecture/compiler/bir/model.py:BIR` (BIRNodeType: `HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`). **LEGACY.** Treated as a semantic donor, not a competing IR. The 9 BIRNodeTypes are read as references; genuinely-semantic ones are absorbed into the canonical CompilerIR contract where appropriate. Retired as runtime per R1-D.5.
- `UniversalISR`-as-typed-graph (consumed by `constitutional_architecture/compilers/*`). **LEGACY.** Retired as runtime per R1-D.5.

## 14. Migration destination

- Legacy `BIR` → LEGACY classification (R1-B.D17); 9 BIRNodeTypes selectively absorbed as references into the canonical CompilerIR contract; BIR is **not** modified to add content-hash; the canonical CompilerIR is a new module with its own content-hash.
- Legacy `UniversalISR`-as-typed-graph → LEGACY; retired as runtime.

---

*End of D07. Cross-references: D01 (registry), D03 (ISR), D04 (ArchitectureCandidate), D08 (CompilerBackend consumes CompilerIR), D09 (ArtifactSet is the output).*
